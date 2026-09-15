import hashlib
import shutil
import unittest

from permissions_fixtures import create_manager

from ycappuccino.api.endpoints_storage import InvalidRequest, NotFound
from ycappuccino.permissions import passwords
from ycappuccino.permissions.models.account import Account
from ycappuccino.permissions.models.login import Login
from ycappuccino.permissions.models.role_account import RoleAccount


class TestPasswords(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.manager, directory = create_manager()
        self.addCleanup(shutil.rmtree, directory, True)

        login = Login()
        login.id("alice")
        login.login("alice")
        login.password("secret")
        await self.manager.up_sert_model(login)

        account = Account()
        account.id("acc-alice")
        account.name("Alice")
        account.login("alice")
        await self.manager.up_sert_model(account)

    async def test_hash_scrypt_is_prefixed_and_deterministic_for_the_same_salt(self):
        self.assertTrue(passwords.hash_scrypt("secret", "salt").startswith("scrypt$"))
        self.assertEqual(
            passwords.hash_scrypt("secret", "salt"), passwords.hash_scrypt("secret", "salt")
        )
        self.assertNotEqual(
            passwords.hash_scrypt("secret", "salt"), passwords.hash_scrypt("other", "salt")
        )

    async def test_check_login_succeeds(self):
        account_id = await passwords.check_login(self.manager, "alice", "secret")

        self.assertEqual(account_id, "acc-alice")

    async def test_check_login_rejects_a_wrong_password(self):
        with self.assertRaises(InvalidRequest):
            await passwords.check_login(self.manager, "alice", "wrong")

    async def test_check_login_rejects_an_unknown_login(self):
        with self.assertRaises(NotFound):
            await passwords.check_login(self.manager, "unknown", "secret")

    async def test_check_login_falls_back_to_md5_and_rehashes(self):
        legacy = Login()
        legacy.id("bob")
        legacy.login("bob")
        legacy.salt("abc")
        legacy._stored_password(hashlib.md5(b"abcold").hexdigest())
        await self.manager.up_sert_model(legacy)
        account = Account()
        account.id("acc-bob")
        account.login("bob")
        await self.manager.up_sert_model(account)

        account_id = await passwords.check_login(self.manager, "bob", "old")

        self.assertEqual(account_id, "acc-bob")
        stored = (
            await self.manager.get_one("login", "bob", {"content": "privateField"})
        ).get_storage_model()
        self.assertTrue(stored["password"].startswith("scrypt$"))

    async def test_the_password_is_not_readable_without_the_private_content(self):
        stored = (await self.manager.get_one("login", "alice")).get_storage_model()

        self.assertNotIn("password", stored)

    async def test_organization_of(self):
        role_account = RoleAccount()
        role_account.id("ra-1")
        role_account.account("acc-alice")
        role_account.role("some-role")
        role_account.organization("acme")
        await self.manager.up_sert_model(role_account)

        self.assertEqual(await passwords.organization_of(self.manager, "acc-alice"), "acme")

    async def test_organization_of_without_a_role_account(self):
        with self.assertRaises(NotFound):
            await passwords.organization_of(self.manager, "unknown-account")


if __name__ == "__main__":
    unittest.main()
