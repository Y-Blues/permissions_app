"""
Proves the frontend_shell wiring end-to-end with a fake IServiceEndpoint (no real network, no real
HTTP, no real backend process -- exactly the point: this frontend talks to its backend as a Python
service call, see main.py's docstring): both screens load correctly from their YAML templates, and
the subject decoded from a real login token (real ycappuccino.permissions.jwt_codec, only the
IServiceEndpoint is fake) is carried to the change_password screen's call -- the same three lines
of glue FrontendShell.run() performs, without invoking its own blocking ScreenApp.run() (never unit
tested directly, same convention as ycappuccino-ui-shell's own run_screen()).
"""

import unittest

from ycappuccino.permissions import jwt_codec
from ycappuccino.permissions.frontend_shell.main import load_change_password_screen, load_login_screen
from ycappuccino.permissions.frontend_shell.service_endpoint_transport import ServiceEndpointTransport
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


class TestScreensLoad(unittest.TestCase):

    def test_login_screen_shape(self):
        screen = load_login_screen()

        self.assertEqual(screen.title, "Connexion")
        self.assertEqual({a_field.name for a_field in screen.fields}, {"login", "password"})
        self.assertEqual(screen.actions[0].endpoint.service, "login")

    def test_change_password_screen_shape(self):
        screen = load_change_password_screen()

        self.assertEqual({a_field.name for a_field in screen.fields}, {"login", "password", "new_password"})
        self.assertEqual(screen.actions[0].endpoint.service, "change_password")


class TestChaining(unittest.IsolatedAsyncioTestCase):

    async def test_login_subject_is_carried_to_change_password(self):
        token = jwt_codec.encode({"sub": "aurelien", "tid": "system"}, _KEY, 3600)
        endpoint = FakeServiceEndpoint(results={"login": {"token": token}, "change_password": {}})
        transport = ServiceEndpointTransport(endpoint)

        login_app = ScreenApp(load_login_screen(), transport)
        async with login_app.run_test() as pilot:
            login_app.query_one("#field-login").value = "aurelien"
            login_app.query_one("#field-password").value = "secret"
            await pilot.click("#action-submit")

        self.assertEqual(login_app.last_result, {"token": token})

        # the same one line FrontendShell.run() performs between the two screens
        transport.subject = jwt_codec.decode(login_app.last_result["token"], _KEY)

        change_app = ScreenApp(load_change_password_screen(), transport)
        async with change_app.run_test() as pilot:
            change_app.query_one("#field-login").value = "aurelien"
            change_app.query_one("#field-password").value = "secret"
            change_app.query_one("#field-new_password").value = "new-secret"
            await pilot.click("#action-submit")

        self.assertEqual(endpoint.calls[0][0], "login")
        change_password_call = endpoint.calls[1]
        self.assertEqual(change_password_call[0], "change_password")
        self.assertEqual(
            change_password_call[4],
            {"login": "aurelien", "password": "secret", "new_password": "new-secret"},
        )
        subject = change_password_call[5]
        self.assertEqual(subject["sub"], "aurelien")
        self.assertEqual(subject["tid"], "system")


if __name__ == "__main__":
    unittest.main()
