"""
The examples of README.md, kept runnable.
"""

# section "Tester avec permissions_app"
import unittest

from ycappuccino.storage.files import LocalFileStore
from ycappuccino.storage.items import ItemManager
from ycappuccino.storage.manager import Manager
from ycappuccino.storage.memory import MemoryStorage

from ycappuccino.permissions.authorization import RolePermissionAuthorization
from ycappuccino.permissions.models.role_account import RoleAccount
from ycappuccino.permissions.models.role_permission import RolePermission


class TestAuthorization(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.manager = Manager(
            MemoryStorage(), ItemManager(), [], [], LocalFileStore("/tmp/files")
        )

        role_account = RoleAccount()
        role_account.id("ra-alice")
        role_account.account("alice")
        role_account.role("admin")
        role_account.organization("acme")
        await self.manager.up_sert_model(role_account)

        role_permission = RolePermission()
        role_permission.id("rp-admin")
        role_permission.role("admin")
        role_permission.rights(["*:*"])
        await self.manager.up_sert_model(role_permission)

    async def test_the_admin_role_may_read_a_book(self):
        authorization = RolePermissionAuthorization(self.manager)

        subject = {"sub": "alice", "tid": "acme"}
        self.assertTrue(await authorization.is_authorized(subject, "read", "book"))


if __name__ == "__main__":
    unittest.main()
