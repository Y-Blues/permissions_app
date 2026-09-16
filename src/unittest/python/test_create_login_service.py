import shutil
import unittest

from permissions_fixtures import create_manager

from ycappuccino.api.endpoints_storage import InvalidRequest, NotFound
from ycappuccino.permissions.services.create_login import CreateLoginService


class TestCreateLoginService(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.manager, directory = create_manager()
        self.addCleanup(shutil.rmtree, directory, True)

    async def test_creates_a_login_with_a_hashed_password(self):
        service = CreateLoginService(self.manager)

        result = await service.call("POST", [], {}, {"login": "bob", "password": "secret"}, None)

        self.assertEqual(result.body, {})
        stored = (await self.manager.get_one("login", "bob", subject=None)).get_storage_model()
        # "password" is private (never in get_storage_model()'s output); a non-empty "salt" is
        # only ever set by Login.password(cleartext) -- proof the hashed path ran, not a raw write
        self.assertNotIn("password", stored)
        self.assertTrue(stored["salt"])

    async def test_rejects_an_already_existing_login(self):
        service = CreateLoginService(self.manager)
        await service.call("POST", [], {}, {"login": "bob", "password": "secret"}, None)

        with self.assertRaises(InvalidRequest):
            await service.call("POST", [], {}, {"login": "bob", "password": "other"}, None)

    async def test_only_supports_post(self):
        service = CreateLoginService(self.manager)

        with self.assertRaises(NotFound):
            await service.call("GET", [], {}, None, None)

    async def test_secure_flag_and_name(self):
        self.assertTrue(CreateLoginService.secure)
        self.assertEqual(CreateLoginService.name, "create_login")


if __name__ == "__main__":
    unittest.main()
