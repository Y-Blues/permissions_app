"""
The terminal admin console, driven through its real textual application (ShellApplication over the shared
application.yml): every backend interface is a fake. After login, the subject decoded from the real token
(ycappuccino.permissions.jwt_codec) goes with every call, since the console runs next to its backend.
"""

import unittest

from textual.widgets import Button, Label

from ycappuccino.api.endpoints_storage import InvalidRequest
from ycappuccino.permissions import jwt_codec
from ycappuccino.permissions.frontend_shell.main import FrontendShell

_KEY = "test-key"
_TOKEN = jwt_codec.encode({"sub": "superadmin", "tid": "system"}, _KEY, 3600)


class FakeLogin:

    async def login(self, login, password):
        if password != "demo":
            raise InvalidRequest("wrong login or password")
        return _TOKEN


class FakeResult:
    def __init__(self, body):
        self.body = body


class FakeServiceEndpoint:

    def __init__(self):
        self.calls = []

    async def call(self, name, method, extra_path, params, body, subject):
        self.calls.append((name, body, subject))
        return FakeResult({})


class FakeCrud:

    def __init__(self):
        self.calls = []

    async def create(self, item_id, fields, subject=None):
        self.calls.append((item_id, fields, subject))
        return {"_id": "created"}


class TestFrontendShell(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.endpoint = FakeServiceEndpoint()
        self.crud = FakeCrud()
        self.shell = FrontendShell(FakeLogin(), self.endpoint, self.crud, key=_KEY)
        self.app = self.shell.application()

    async def _submit(self, pilot, **values):
        for name, value in values.items():
            self.app.query_one(f"#field-{name}").value = value
        await pilot.click("#action-submit")
        await pilot.pause()

    async def _choose(self, pilot, label):
        button = next(button for button in self.app.query(Button) if str(button.label) == label)
        await pilot.click(f"#{button.id}")
        await pilot.pause()

    async def _sign_in(self, pilot):
        await pilot.pause()
        await self._submit(pilot, login="superadmin", password="demo")

    def _subject(self):
        return {"sub": "superadmin", "tid": "system"}

    async def test_wrong_credentials_stay_on_the_login_screen(self):
        async with self.app.run_test() as pilot:
            await pilot.pause()
            await self._submit(pilot, login="superadmin", password="wrong")

            self.assertEqual(str(self.app.query_one("#status", Label).content), "wrong login or password")

    async def test_a_crud_entry_creates_with_the_subject_of_the_token(self):
        async with self.app.run_test() as pilot:
            await self._sign_in(pilot)
            await self._choose(pilot, "Créer une organisation")
            await self._submit(pilot, name="Acme")

            self.assertEqual(len(self.crud.calls), 1)
            item_id, fields, subject = self.crud.calls[0]
            self.assertEqual((item_id, fields["name"]), ("organization", "Acme"))
            self.assertEqual({key: subject[key] for key in ("sub", "tid")}, self._subject())
            self.assertEqual(str(self.app.query_one("#message", Label).content), "Enregistré.")

    async def test_changing_the_password_calls_the_exposed_service(self):
        async with self.app.run_test() as pilot:
            await self._sign_in(pilot)
            await self._choose(pilot, "Changer mon mot de passe")
            await self._submit(pilot, login="superadmin", password="demo", new_password="new")

            name, body, subject = self.endpoint.calls[0]
            self.assertEqual((name, body), ("change_password", {"login": "superadmin", "password": "demo", "new_password": "new"}))
            self.assertEqual(subject["sub"], "superadmin")

    async def test_creating_a_user_prefills_the_login_then_the_account_id(self):
        async with self.app.run_test() as pilot:
            await self._sign_in(pilot)
            await self._choose(pilot, "Créer un utilisateur")
            await self._submit(pilot, login="bob", password="secret")

            self.assertEqual(self.app.query_one("#field-login").value, "bob")
            await self._submit(pilot, name="Bob", role="editor")
            self.assertEqual(self.app.query_one("#field-account").value, "created")
            await self._submit(pilot, role="editor", organization="acme")

            self.assertEqual(self.endpoint.calls[0][:2], ("create_login", {"login": "bob", "password": "secret"}))
            self.assertEqual(
                [(item_id, fields) for item_id, fields, _ in self.crud.calls],
                [
                    ("account", {"name": "Bob", "login": "bob", "role": "editor"}),
                    ("roleAccount", {"account": "created", "role": "editor", "organization": "acme"}),
                ],
            )

    async def test_signing_out_forgets_the_subject(self):
        async with self.app.run_test() as pilot:
            await self._sign_in(pilot)
            await self._choose(pilot, "Se déconnecter")
            await self._sign_in(pilot)
            await self._choose(pilot, "Se déconnecter")

            self.assertEqual(len(self.app.query("#field-login")), 1)
            self.assertIsNone(self.shell.subject)


if __name__ == "__main__":
    unittest.main()
