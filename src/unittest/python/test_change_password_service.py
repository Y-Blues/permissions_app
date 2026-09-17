import shutil
import unittest

from permissions_fixtures import create_manager

from ycappuccino.api.decorators import get_rpc_methods
from ycappuccino.api.endpoints_storage import IAuthorization, InvalidRequest, NotFound
from ycappuccino.endpoints_service.endpoint import ServiceEndpoint
from ycappuccino.permissions import passwords
from ycappuccino.permissions.models.account import Account
from ycappuccino.permissions.models.login import Login
from ycappuccino.permissions.services.change_password import ChangePasswordService

SUBJECT = {"sub": "acc-alice", "tid": "acme"}


class FakeAuthorization(IAuthorization):

    async def is_authorized(self, subject, action, item_id):
        return True

    async def start(self):
        pass

    async def stop(self):
        pass


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

    async def test_it_declares_a_secure_post_method(self):
        metadata = get_rpc_methods(ChangePasswordService)["change_password"]

        self.assertEqual((metadata["method"], metadata["path"], metadata["secure"]), ("POST", "", True))
        self.assertTrue(metadata["summary"])

    async def test_changes_the_password(self):
        service = ChangePasswordService(self.manager)

        await service.change_password("alice", "old", "new")

        account_id = await passwords.check_login(self.manager, "alice", "new")
        self.assertEqual(account_id, "acc-alice")

    async def test_the_old_password_no_longer_works(self):
        service = ChangePasswordService(self.manager)

        await service.change_password("alice", "old", "new")

        with self.assertRaises(InvalidRequest):
            await passwords.check_login(self.manager, "alice", "old")

    async def test_rejects_a_wrong_old_password(self):
        service = ChangePasswordService(self.manager)

        with self.assertRaises(InvalidRequest):
            await service.change_password("alice", "wrong", "new")

    async def test_only_supports_post(self):
        endpoint = ServiceEndpoint([ChangePasswordService(self.manager)], [FakeAuthorization()])

        with self.assertRaises(NotFound):
            await endpoint.call("change_password", "GET", [], {}, None, SUBJECT)

    async def test_post_changes_the_password(self):
        endpoint = ServiceEndpoint([ChangePasswordService(self.manager)], [FakeAuthorization()])

        result = await endpoint.call(
            "change_password", "POST", [], {}, {"login": "alice", "password": "old", "new_password": "new"}, SUBJECT
        )

        self.assertEqual(result.body, {})
        self.assertEqual(await passwords.check_login(self.manager, "alice", "new"), "acc-alice")


if __name__ == "__main__":
    unittest.main()
