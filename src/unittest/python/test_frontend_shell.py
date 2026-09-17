"""
Proves the frontend_shell wiring end-to-end with fake ILoginService/IServiceEndpoint/ICrud (no real network, no
real HTTP, no real backend process -- exactly the point: this frontend talks to its backend as a
Python service/CRUD call, see main.py's docstring): every screen loads correctly from its YAML
template, and the subject decoded from a real login token (real ycappuccino.permissions.jwt_codec,
only IServiceEndpoint/ICrud are fake) is carried across screens -- the same glue
FrontendShell.log_in()/run()/create_user() perform, without invoking their own blocking
ScreenApp.run() (never unit tested directly, same convention as ycappuccino-ui-shell's own
run_screen()).
"""

import unittest

from ycappuccino.permissions import jwt_codec
from ycappuccino.permissions.screens import (
    load_account_screen,
    load_change_password_screen,
    load_create_login_screen,
    load_login_screen,
    load_organization_screen,
    load_role_account_screen,
    load_role_permission_screen,
)
from ycappuccino.ui.ycappuccino_transport import ComponentTransport, CrudTransport, ServiceEndpointTransport
from ycappuccino.ui_shell.app import ScreenApp

_KEY = "test-key"


class FakeResult:
    def __init__(self, body):
        self.body = body


class FakeServiceEndpoint:

    def __init__(self, results: dict):
        self.results = results
        self.calls = []

    async def call(self, name, method, extra_path, params, body, subject):
        self.calls.append((name, method, extra_path, params, body, subject))
        return FakeResult(self.results[name])


class FakeLogin:

    def __init__(self, token):
        self.token = token
        self.calls = []

    async def login(self, login, password):
        self.calls.append((login, password))
        return self.token


class FakeCrud:

    def __init__(self, result=None):
        self.result = result
        self.calls = []

    async def create(self, item_id, fields, subject=None):
        self.calls.append(("create", item_id, fields, subject))
        return self.result


class TestChaining(unittest.IsolatedAsyncioTestCase):

    async def test_login_subject_is_carried_to_change_password(self):
        token = jwt_codec.encode({"sub": "aurelien", "tid": "system"}, _KEY, 3600)
        login = FakeLogin(token)
        endpoint = FakeServiceEndpoint(results={"change_password": {}})

        login_app = ScreenApp(load_login_screen(), ComponentTransport({"login": login}))
        async with login_app.run_test() as pilot:
            login_app.query_one("#field-login").value = "aurelien"
            login_app.query_one("#field-password").value = "secret"
            await pilot.click("#action-submit")

        self.assertEqual((login_app.last_result, login.calls), (token, [("aurelien", "secret")]))

        # the same one line FrontendShell.log_in() performs
        transport = ServiceEndpointTransport(endpoint, subject=jwt_codec.decode(login_app.last_result, _KEY))

        change_app = ScreenApp(load_change_password_screen(), transport)
        async with change_app.run_test() as pilot:
            change_app.query_one("#field-login").value = "aurelien"
            change_app.query_one("#field-password").value = "secret"
            change_app.query_one("#field-new_password").value = "new-secret"
            await pilot.click("#action-submit")

        change_password_call = endpoint.calls[0]
        self.assertEqual(change_password_call[0], "change_password")
        self.assertEqual(
            change_password_call[4],
            {"login": "aurelien", "password": "secret", "new_password": "new-secret"},
        )
        subject = change_password_call[5]
        self.assertEqual(subject["sub"], "aurelien")
        self.assertEqual(subject["tid"], "system")

    async def test_create_organization_calls_crud_create_with_the_subject(self):
        crud = FakeCrud(result={"_id": "acme", "name": "Acme"})
        transport = CrudTransport(crud, subject={"sub": "admin"})

        app = ScreenApp(load_organization_screen(), transport)
        async with app.run_test() as pilot:
            app.query_one("#field-name").value = "Acme"
            await pilot.click("#action-submit")

        self.assertEqual(crud.calls, [("create", "organization", {"name": "Acme", "father": ""}, {"sub": "admin"})])

    async def test_grant_permission_splits_rights_into_a_list(self):
        crud = FakeCrud(result={})
        transport = CrudTransport(crud, subject={"sub": "admin"})

        app = ScreenApp(load_role_permission_screen(), transport)
        async with app.run_test() as pilot:
            app.query_one("#field-role").value = "editor"
            app.query_one("#field-rights").value = "read:book, write:book"
            await pilot.click("#action-submit")

        self.assertEqual(
            crud.calls,
            [("create", "rolePermission", {"role": "editor", "rights": ["read:book", "write:book"]}, {"sub": "admin"})],
        )

    async def test_create_user_chains_credentials_then_profile_then_tenant_grant(self):
        endpoint = FakeServiceEndpoint(results={"create_login": {}})
        crud = FakeCrud(result={"_id": "bob"})
        subject = {"sub": "admin"}
        credentials_transport = ServiceEndpointTransport(endpoint, subject=subject)
        crud_transport = CrudTransport(crud, subject=subject)

        # 1. credentials (a Python service call, hashed password -- see CreateLoginService)
        credentials_app = ScreenApp(load_create_login_screen(), credentials_transport)
        async with credentials_app.run_test() as pilot:
            credentials_app.query_one("#field-login").value = "bob"
            credentials_app.query_one("#field-password").value = "secret"
            await pilot.click("#action-submit")

        self.assertIsNotNone(credentials_app.last_result)  # FrontendShell.create_user() only
        # continues to the next screen when this is not None, exactly like login/create_user

        # 2. profile (a CRUD create referencing the login just created)
        profile_app = ScreenApp(load_account_screen(), crud_transport)
        async with profile_app.run_test() as pilot:
            profile_app.query_one("#field-name").value = "Bob"
            profile_app.query_one("#field-login").value = "bob"
            profile_app.query_one("#field-role").value = "editor"
            await pilot.click("#action-submit")

        self.assertIsNotNone(profile_app.last_result)

        # 3. tenant grant (scopes the role to one organization -- the actual "tenancy" link)
        grant_app = ScreenApp(load_role_account_screen(), crud_transport)
        async with grant_app.run_test() as pilot:
            grant_app.query_one("#field-account").value = "bob"
            grant_app.query_one("#field-role").value = "editor"
            grant_app.query_one("#field-organization").value = "acme"
            await pilot.click("#action-submit")

        self.assertEqual(endpoint.calls[0][0], "create_login")
        self.assertEqual(endpoint.calls[0][4], {"login": "bob", "password": "secret"})
        self.assertEqual(
            crud.calls,
            [
                ("create", "account", {"name": "Bob", "login": "bob", "role": "editor"}, subject),
                ("create", "roleAccount", {"account": "bob", "role": "editor", "organization": "acme"}, subject),
            ],
        )


if __name__ == "__main__":
    unittest.main()
