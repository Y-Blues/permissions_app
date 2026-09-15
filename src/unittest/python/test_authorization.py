import shutil
import unittest

from permissions_fixtures import create_manager

from ycappuccino.permissions.authorization import RolePermissionAuthorization
from ycappuccino.permissions.models.role_account import RoleAccount
from ycappuccino.permissions.models.role_permission import RolePermission

SUBJECT = {"sub": "alice", "tid": "acme"}


class TestRolePermissionAuthorization(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.manager, directory = create_manager()
        self.addCleanup(shutil.rmtree, directory, True)

    async def _grant(self, rights):
        role_account = RoleAccount()
        role_account.id("ra-1")
        role_account.account("alice")
        role_account.role("editor")
        role_account.organization("acme")
        await self.manager.up_sert_model(role_account)

        role_permission = RolePermission()
        role_permission.id("rp-1")
        role_permission.role("editor")
        role_permission.rights(rights)
        await self.manager.up_sert_model(role_permission)

    async def test_no_role_account_is_refused(self):
        authorization = RolePermissionAuthorization(self.manager)

        self.assertFalse(await authorization.is_authorized(SUBJECT, "read", "book"))

    async def test_exact_right_is_authorized(self):
        await self._grant(["read:book"])
        authorization = RolePermissionAuthorization(self.manager)

        self.assertTrue(await authorization.is_authorized(SUBJECT, "read", "book"))
        self.assertFalse(await authorization.is_authorized(SUBJECT, "write", "book"))

    async def test_wildcard_right(self):
        await self._grant(["*:*"])
        authorization = RolePermissionAuthorization(self.manager)

        self.assertTrue(await authorization.is_authorized(SUBJECT, "call", "login"))

    async def test_wildcard_on_the_item_only(self):
        await self._grant(["read:*"])
        authorization = RolePermissionAuthorization(self.manager)

        self.assertTrue(await authorization.is_authorized(SUBJECT, "read", "book"))
        self.assertFalse(await authorization.is_authorized(SUBJECT, "write", "book"))

    async def test_a_role_without_permission_is_refused(self):
        await self._grant([])
        authorization = RolePermissionAuthorization(self.manager)

        self.assertFalse(await authorization.is_authorized(SUBJECT, "read", "book"))

    async def test_wrong_tenant_is_refused(self):
        await self._grant(["*:*"])
        authorization = RolePermissionAuthorization(self.manager)

        self.assertFalse(
            await authorization.is_authorized({"sub": "alice", "tid": "other"}, "read", "book")
        )

    async def test_rights_from_several_role_permissions_are_combined(self):
        await self._grant(["read:book"])
        second = RolePermission()
        second.id("rp-2")
        second.role("editor")
        second.rights(["write:book"])
        await self.manager.up_sert_model(second)
        authorization = RolePermissionAuthorization(self.manager)

        self.assertTrue(await authorization.is_authorized(SUBJECT, "write", "book"))


if __name__ == "__main__":
    unittest.main()
