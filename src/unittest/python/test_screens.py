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
    load_application,
    load_screen,
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



class TestApplication(unittest.TestCase):
    """the layout both consoles render: menu, chained screens and their transports"""

    def test_the_menu_sections_of_both_consoles(self):
        application = load_application()

        self.assertEqual(
            [(group.label, [entry.label for entry in group.entries]) for group in application.menu],
            [
                ("Mon compte", ["Changer mon mot de passe"]),
                ("Organisations", ["Créer une organisation"]),
                ("Rôles et permissions", ["Créer un rôle", "Créer une permission", "Attribuer un rôle"]),
                ("Utilisateurs", ["Créer un utilisateur"]),
            ],
        )
        self.assertEqual(application.user_field, "login")

    def test_every_step_names_a_screen_and_a_known_transport(self):
        application = load_application()

        steps = [step for group in application.menu for entry in group.entries for step in entry.steps]
        for step in [application.login] + steps:
            with self.subTest(screen=step.screen):
                self.assertIsNotNone(load_screen(step.screen))
                self.assertIn(step.transport, ("login", "services", "crud"))

    def test_creating_a_user_prefills_the_login_then_the_account_id(self):
        entry = next(
            entry for group in load_application().menu for entry in group.entries if entry.label == "Créer un utilisateur"
        )

        self.assertEqual(
            [(step.screen, step.transport, step.prefill) for step in entry.steps],
            [
                ("create_login", "services", {}),
                ("account", "crud", {"login": "values.login"}),
                ("role_account", "crud", {"account": "result._id"}),
            ],
        )

if __name__ == "__main__":
    unittest.main()
