"""
The screens shared by the terminal (frontend_shell) and the browser (frontend_web) consoles.
"""

import unittest

from ycappuccino.permissions.screens import (
    load_account_screen,
    load_change_password_screen,
    load_create_login_screen,
    load_login_screen,
    load_organization_screen,
    load_role_account_screen,
    load_role_permission_screen,
    load_role_screen,
    with_defaults,
)


class TestScreensLoad(unittest.TestCase):

    def test_login_screen_shape(self):
        screen = load_login_screen()

        self.assertEqual(screen.title, "Connexion")
        self.assertEqual({a_field.name for a_field in screen.fields}, {"login", "password"})
        self.assertEqual((screen.actions[0].endpoint.service, screen.actions[0].endpoint.method), ("login", "login"))

    def test_change_password_screen_shape(self):
        screen = load_change_password_screen()

        self.assertEqual({a_field.name for a_field in screen.fields}, {"login", "password", "new_password"})
        self.assertEqual(screen.actions[0].endpoint.service, "change_password")

    def test_organization_screen_shape(self):
        screen = load_organization_screen()

        self.assertEqual({a_field.name for a_field in screen.fields}, {"name", "father"})
        self.assertEqual(screen.actions[0].endpoint.service, "organization")

    def test_role_screen_shape(self):
        screen = load_role_screen()

        self.assertEqual({a_field.name for a_field in screen.fields}, {"name"})
        self.assertEqual(screen.actions[0].endpoint.service, "role")

    def test_role_permission_screen_shape(self):
        screen = load_role_permission_screen()

        fields = {a_field.name: a_field for a_field in screen.fields}
        self.assertEqual(set(fields), {"role", "rights"})
        self.assertEqual(fields["rights"].type, "list")
        self.assertEqual(screen.actions[0].endpoint.service, "rolePermission")

    def test_create_login_screen_shape(self):
        screen = load_create_login_screen()

        fields = {a_field.name: a_field for a_field in screen.fields}
        self.assertEqual(set(fields), {"login", "password"})
        self.assertEqual(fields["password"].type, "password")
        self.assertEqual(screen.actions[0].endpoint.service, "create_login")

    def test_account_screen_shape(self):
        screen = load_account_screen()

        self.assertEqual({a_field.name for a_field in screen.fields}, {"name", "login", "role"})
        self.assertEqual(screen.actions[0].endpoint.service, "account")

    def test_role_account_screen_shape(self):
        screen = load_role_account_screen()

        self.assertEqual({a_field.name for a_field in screen.fields}, {"account", "role", "organization"})
        self.assertEqual(screen.actions[0].endpoint.service, "roleAccount")



class TestWithDefaults(unittest.TestCase):

    def test_prefills_the_named_fields_only(self):
        screen = with_defaults(load_role_account_screen(), account="created-id")

        defaults = {a_field.name: a_field.default for a_field in screen.fields}
        self.assertEqual(defaults, {"account": "created-id", "role": None, "organization": None})
        self.assertIsNone({a_field.name: a_field.default for a_field in load_role_account_screen().fields}["account"])

    def test_an_unknown_field_is_refused(self):
        with self.assertRaises(ValueError):
            with_defaults(load_role_account_screen(), nope="x")


if __name__ == "__main__":
    unittest.main()
