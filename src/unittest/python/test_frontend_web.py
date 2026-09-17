"""
The browser admin console, driven through a real in-memory DOM (ycappuccino.ui_web.testing.FakeDom):
every backend interface is a fake, as the generated proxies would be in a browser.
"""

import unittest

from ycappuccino.api.endpoints_storage import InvalidRequest
from ycappuccino.permissions.frontend_web.app import PermissionsWebApp
from ycappuccino.ui_web.navigation import Navigator
from ycappuccino.ui_web.page import IWebPage
from ycappuccino.ui_web.testing import FakeDom, find_button, find_field, texts


def _by_class(element, name):
    found = [element] if name in element.attrs.get("class", "").split() else []
    for child in element.children:
        found.extend(_by_class(child, name))
    return found


class FakePage(IWebPage):

    def __init__(self):
        self.dom = FakeDom()
        self.mount = self.dom.create_element("div")
        self._navigator = Navigator(self.dom, self.mount)

    async def start(self):
        pass

    async def stop(self):
        pass

    def navigator(self):
        return self._navigator


class FakeLogin:

    async def login(self, login, password):
        if password != "demo":
            raise InvalidRequest("wrong login or password")
        return "token-" + login


class FakeSession:

    def __init__(self):
        self.token = None

    def set_token(self, token):
        self.token = token

    def get_token(self):
        return self.token

    def clear_token(self):
        self.token = None


class FakeResult:
    def __init__(self, body):
        self.body = body


class FakeServiceEndpoint:

    def __init__(self):
        self.calls = []

    async def call(self, name, method, extra_path, params, body, subject):
        self.calls.append((name, method, body))
        return FakeResult({})


class FakeCrud:

    def __init__(self):
        self.calls = []

    async def create(self, item_id, fields, subject=None):
        self.calls.append((item_id, fields))
        return {"_id": "created"}


class TestPermissionsWebApp(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.page = FakePage()
        self.session = FakeSession()
        self.endpoint = FakeServiceEndpoint()
        self.crud = FakeCrud()
        self.app = PermissionsWebApp(self.page, FakeLogin(), self.endpoint, self.crud, self.session)
        await self.app.start()

    async def _submit(self, values, label):
        for name, value in values.items():
            self.page.dom.set_value(find_field(self.page.mount, name), value)
        await self.page.dom.click(find_button(self.page.mount, label))

    async def _choose(self, label):
        await self.page.dom.click(find_button(self.page.mount, label))

    async def _sign_in(self):
        await self._submit({"login": "superadmin", "password": "demo"}, "Se connecter")

    def test_it_starts_on_the_login_screen(self):
        self.assertIn("Connexion", texts(self.page.mount))

    async def test_signing_in_keeps_the_token_and_shows_the_sections_and_the_user(self):
        await self._sign_in()

        self.assertEqual(self.session.token, "token-superadmin")
        (nav,) = _by_class(self.page.mount, "yc-nav")
        self.assertEqual(
            [texts(menu)[0] for menu in _by_class(nav, "yc-menu")],
            ["Mon compte", "Organisations", "Rôles et permissions", "Utilisateurs"],
        )
        self.assertEqual(texts(_by_class(nav, "yc-user")[0]), ["superadmin"])
        self.assertIn("Bienvenue superadmin.", texts(self.page.mount))

    async def test_wrong_credentials_stay_on_the_login_screen_with_the_message(self):
        await self._submit({"login": "superadmin", "password": "wrong"}, "Se connecter")

        self.assertIsNone(self.session.token)
        self.assertIn("wrong login or password", texts(self.page.mount))
        self.assertIsNotNone(find_button(self.page.mount, "Se connecter"))

    async def test_a_crud_screen_creates_then_confirms_under_the_bar(self):
        await self._sign_in()
        await self._choose("Créer une organisation")

        await self._submit({"name": "Acme"}, "Créer")

        self.assertEqual(self.crud.calls, [("organization", {"name": "Acme", "father": ""})])
        self.assertIn("Enregistré.", texts(self.page.mount))
        self.assertIsNotNone(find_button(self.page.mount, "Créer une organisation"))

    async def test_changing_the_password_calls_the_exposed_service(self):
        await self._sign_in()
        await self._choose("Changer mon mot de passe")

        await self._submit({"login": "superadmin", "password": "demo", "new_password": "new"}, "Valider")

        self.assertEqual(
            self.endpoint.calls,
            [("change_password", "POST", {"login": "superadmin", "password": "demo", "new_password": "new"})],
        )

    async def test_creating_a_user_chains_credentials_profile_and_tenant_grant(self):
        await self._sign_in()
        await self._choose("Créer un utilisateur")

        await self._submit({"login": "bob", "password": "secret"}, "Créer les identifiants")
        self.assertEqual(find_field(self.page.mount, "login").value, "bob")
        await self._submit({"name": "Bob", "role": "editor"}, "Créer le compte")
        self.assertEqual(find_field(self.page.mount, "account").value, "created")
        await self._submit({"role": "editor", "organization": "acme"}, "Attribuer")

        self.assertEqual(self.endpoint.calls, [("create_login", "POST", {"login": "bob", "password": "secret"})])
        self.assertEqual(
            self.crud.calls,
            [
                ("account", {"name": "Bob", "login": "bob", "role": "editor"}),
                ("roleAccount", {"account": "created", "role": "editor", "organization": "acme"}),
            ],
        )
        self.assertIn("Enregistré.", texts(self.page.mount))

    async def test_signing_out_forgets_the_token_and_shows_the_login_screen(self):
        await self._sign_in()

        await self._choose("Se déconnecter")

        self.assertIsNone(self.session.token)
        self.assertIsNotNone(find_button(self.page.mount, "Se connecter"))


if __name__ == "__main__":
    unittest.main()
