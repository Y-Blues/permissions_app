import shutil
import unittest

from permissions_fixtures import create_manager

from ycappuccino.api.decorators import get_rpc_methods
from ycappuccino.api.endpoints_storage import InvalidRequest, NotFound
from ycappuccino.api.permissions import ILoginService
from ycappuccino.endpoints_service.endpoint import ServiceEndpoint
from ycappuccino.permissions import jwt_codec
from ycappuccino.permissions.models.account import Account
from ycappuccino.permissions.models.login import Login
from ycappuccino.permissions.models.role_account import RoleAccount
from ycappuccino.permissions.password_login import PasswordLogin
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

        self.password_login = PasswordLogin(self.manager, key="test-key")
        self.endpoint = ServiceEndpoint([LoginService(self.password_login), LoginCookieService(self.password_login)], [])

    def _credentials(self, password="secret", login="alice"):
        return {"login": login, "password": password}

    async def test_password_login_returns_a_valid_token(self):
        token = await self.password_login.login("alice", "secret")

        decoded = jwt_codec.decode(token, "test-key")
        self.assertEqual((decoded["sub"], decoded["tid"]), ("acc-alice", "acme"))

    async def test_password_login_provides_the_typed_interface(self):
        self.assertTrue(issubclass(PasswordLogin, ILoginService))

    async def test_password_login_rejects_a_wrong_password(self):
        with self.assertRaises(InvalidRequest):
            await self.password_login.login("alice", "wrong")

    async def test_password_login_rejects_an_unknown_login(self):
        with self.assertRaises(NotFound):
            await self.password_login.login("bob", "secret")

    async def test_post_login_answers_the_token(self):
        result = await self.endpoint.call("login", "POST", [], {}, self._credentials(), None)

        decoded = jwt_codec.decode(result.body["token"], "test-key")
        self.assertEqual(decoded["sub"], "acc-alice")

    async def test_login_only_supports_post(self):
        with self.assertRaises(NotFound):
            await self.endpoint.call("login", "GET", [], {}, None, None)

    async def test_the_rest_services_are_not_the_typed_interface(self):
        for service in (LoginService, LoginCookieService):
            with self.subTest(service=service.name):
                self.assertFalse(issubclass(service, ILoginService))

    async def test_the_login_services_are_public(self):
        self.assertFalse(LoginService.secure)
        self.assertFalse(LoginCookieService.secure)

    async def test_the_login_services_declare_a_public_post_method(self):
        for service in (LoginService, LoginCookieService):
            with self.subTest(service=service.name):
                methods = list(get_rpc_methods(service).values())
                self.assertEqual(len(methods), 1)
                self.assertEqual((methods[0]["method"], methods[0]["path"], methods[0]["secure"]), ("POST", "", False))
                self.assertTrue(methods[0]["summary"])

    async def test_login_cookie_sets_the_header(self):
        result = await self.endpoint.call("login_cookie", "POST", [], {}, self._credentials(), None)

        self.assertIn(f"_ycappuccino={result.body['token']}", result.headers["set-cookie"])
        self.assertEqual(jwt_codec.decode(result.body["token"], "test-key")["sub"], "acc-alice")


if __name__ == "__main__":
    unittest.main()
