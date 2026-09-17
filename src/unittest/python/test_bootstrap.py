import shutil
import unittest
from unittest import mock

from permissions_fixtures import create_manager

from ycappuccino.permissions import passwords
from ycappuccino.permissions.authorization import RolePermissionAuthorization
from ycappuccino.permissions.bootstrap import AccountBootStrap


class FakeConfiguration:
    def __init__(self, values=None):
        self._values = values or {}

    def get(self, key, default):
        return self._values.get(key, default)


class TestAccountBootStrap(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.manager, directory = create_manager()
        self.addCleanup(shutil.rmtree, directory, True)
        self.logger = mock.Mock()

    def _bootstrap(self, values=None):
        return AccountBootStrap(self.manager, FakeConfiguration(values), self.logger)

    async def test_creates_the_superadmin_with_a_configured_password(self):
        bootstrap = self._bootstrap({"permissions.superadmin.password": "demo"})

        await bootstrap.start()

        account_id = await passwords.check_login(self.manager, "superadmin", "demo")
        organization_id = await passwords.organization_of(self.manager, account_id)
        self.assertEqual(organization_id, "system")

    async def test_the_superadmin_login_can_be_configured(self):
        await self._bootstrap(
            {"permissions.superadmin.login": "admin", "permissions.superadmin.password": "admin"}
        ).start()

        account_id = await passwords.check_login(self.manager, "admin", "admin")
        authorization = RolePermissionAuthorization(self.manager)

        self.assertEqual(await passwords.organization_of(self.manager, account_id), "system")
        self.assertTrue(await authorization.is_authorized({"sub": account_id, "tid": "system"}, "write", "role"))
        self.assertIsNone(await self.manager.get_one("login", "superadmin", subject=None))

    async def test_a_configured_password_is_not_logged(self):
        bootstrap = self._bootstrap({"permissions.superadmin.password": "demo"})

        await bootstrap.start()

        self.logger.warning.assert_not_called()

    async def test_the_superadmin_is_allowed_everything(self):
        await self._bootstrap({"permissions.superadmin.password": "demo"}).start()
        authorization = RolePermissionAuthorization(self.manager)

        subject = {"sub": "superadmin", "tid": "system"}
        self.assertTrue(await authorization.is_authorized(subject, "read", "book"))
        self.assertTrue(await authorization.is_authorized(subject, "call", "change_password"))

    async def test_generates_and_logs_a_password_when_unconfigured(self):
        bootstrap = self._bootstrap()

        await bootstrap.start()

        self.logger.warning.assert_called_once()
        message = self.logger.warning.call_args[0][0]
        generated_password = message.rsplit(" ", 1)[-1]
        self.assertGreater(len(generated_password), 10)
        # the logged password is the real one: it opens the account that was just created
        self.assertEqual(
            await passwords.check_login(self.manager, "superadmin", generated_password),
            "superadmin",
        )

    async def test_is_idempotent(self):
        bootstrap = self._bootstrap({"permissions.superadmin.password": "demo"})
        await bootstrap.start()

        await bootstrap.start()

        logins = await self.manager.get_many("login", {"filter": {}}, subject=None)
        self.assertEqual(len(logins), 1)

    async def test_a_second_start_does_not_change_the_password(self):
        bootstrap = self._bootstrap()
        await bootstrap.start()
        generated_password = self.logger.warning.call_args[0][0].rsplit(" ", 1)[-1]

        await bootstrap.start()

        self.logger.warning.assert_called_once()
        self.assertEqual(
            await passwords.check_login(self.manager, "superadmin", generated_password),
            "superadmin",
        )


if __name__ == "__main__":
    unittest.main()
