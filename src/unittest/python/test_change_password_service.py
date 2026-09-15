import shutil
import unittest

from permissions_fixtures import create_manager

from ycappuccino.api.endpoints_service import ServiceRoute
from ycappuccino.api.endpoints_storage import InvalidRequest, NotFound
from ycappuccino.permissions import passwords
from ycappuccino.permissions.models.account import Account
from ycappuccino.permissions.models.login import Login
from ycappuccino.permissions.services.change_password import ChangePasswordService

SUBJECT = {"sub": "acc-alice", "tid": "acme"}


class TestChangePasswordService(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.manager, directory = create_manager()
        self.addCleanup(shutil.rmtree, directory, True)

        login = Login()
        login.id("alice")
        login.login("alice")
        login.password("old")
        await self.manager.up_sert_model(login)

        account = Account()
        account.id("acc-alice")
        account.login("alice")
        await self.manager.up_sert_model(account)

    async def test_secure_flag(self):
        self.assertTrue(ChangePasswordService.secure)

    async def test_it_declares_a_post_route(self):
        self.assertEqual(len(ChangePasswordService.routes), 1)
        self.assertIsInstance(ChangePasswordService.routes[0], ServiceRoute)
        self.assertEqual(ChangePasswordService.routes[0].method, "POST")
        self.assertTrue(ChangePasswordService.routes[0].summary)

    async def test_changes_the_password(self):
        service = ChangePasswordService(self.manager)

        await service.call(
            "POST", [], {}, {"login": "alice", "password": "old", "new_password": "new"}, SUBJECT
        )

        account_id = await passwords.check_login(self.manager, "alice", "new")
        self.assertEqual(account_id, "acc-alice")

    async def test_the_old_password_no_longer_works(self):
        service = ChangePasswordService(self.manager)

        await service.call(
            "POST", [], {}, {"login": "alice", "password": "old", "new_password": "new"}, SUBJECT
        )

        with self.assertRaises(InvalidRequest):
            await passwords.check_login(self.manager, "alice", "old")

    async def test_rejects_a_wrong_old_password(self):
        service = ChangePasswordService(self.manager)

        with self.assertRaises(InvalidRequest):
            await service.call(
                "POST",
                [],
                {},
                {"login": "alice", "password": "wrong", "new_password": "new"},
                SUBJECT,
            )

    async def test_only_supports_post(self):
        service = ChangePasswordService(self.manager)

        with self.assertRaises(NotFound):
            await service.call("GET", [], {}, None, SUBJECT)


if __name__ == "__main__":
    unittest.main()
