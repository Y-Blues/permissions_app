import shutil
import unittest

from permissions_fixtures import create_manager

from ycappuccino.api.endpoints_service import ServiceRoute
from ycappuccino.api.endpoints_storage import InvalidRequest, NotFound
from ycappuccino.permissions import jwt_codec
from ycappuccino.permissions.models.account import Account
from ycappuccino.permissions.models.login import Login
from ycappuccino.permissions.models.role_account import RoleAccount
from ycappuccino.permissions.services.login import LoginCookieService, LoginService


class TestLoginServices(unittest.IsolatedAsyncioTestCase):

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
        account.login("alice")
        await self.manager.up_sert_model(account)

        role_account = RoleAccount()
        role_account.id("ra-1")
        role_account.account("acc-alice")
        role_account.role("editor")
        role_account.organization("acme")
        await self.manager.up_sert_model(role_account)

    async def test_login_returns_a_valid_token(self):
        service = LoginService(self.manager, key="test-key")

        result = await service.call("POST", [], {}, {"login": "alice", "password": "secret"}, None)

        decoded = jwt_codec.decode(result.body["token"], "test-key")
        self.assertEqual((decoded["sub"], decoded["tid"]), ("acc-alice", "acme"))

    async def test_typed_login_returns_a_valid_token(self):
        service = LoginService(self.manager, key="test-key")

        token = await service.login("alice", "secret")

        decoded = jwt_codec.decode(token, "test-key")
        self.assertEqual((decoded["sub"], decoded["tid"]), ("acc-alice", "acme"))

    async def test_login_service_provides_the_typed_interface(self):
        from ycappuccino.api.permissions import ILoginService

        self.assertTrue(issubclass(LoginService, ILoginService))

    async def test_login_rejects_a_wrong_password(self):
        service = LoginService(self.manager, key="test-key")

        with self.assertRaises(InvalidRequest):
            await service.call("POST", [], {}, {"login": "alice", "password": "wrong"}, None)

    async def test_login_rejects_an_unknown_login(self):
        service = LoginService(self.manager, key="test-key")

        with self.assertRaises(NotFound):
            await service.call("POST", [], {}, {"login": "bob", "password": "secret"}, None)

    async def test_login_only_supports_post(self):
        service = LoginService(self.manager, key="test-key")

        with self.assertRaises(NotFound):
            await service.call("GET", [], {}, None, None)

    async def test_the_login_services_are_public(self):
        self.assertFalse(LoginService.secure)
        self.assertFalse(LoginCookieService.secure)

    async def test_the_login_services_declare_a_post_route(self):
        for service in (LoginService, LoginCookieService):
            with self.subTest(service=service.name):
                self.assertEqual(len(service.routes), 1)
                self.assertIsInstance(service.routes[0], ServiceRoute)
                self.assertEqual(service.routes[0].method, "POST")
                self.assertTrue(service.routes[0].summary)

    async def test_login_cookie_sets_the_header(self):
        service = LoginCookieService(self.manager, key="test-key")

        result = await service.call("POST", [], {}, {"login": "alice", "password": "secret"}, None)

        self.assertIn(f"_ycappuccino={result.body['token']}", result.headers["set-cookie"])


if __name__ == "__main__":
    unittest.main()
