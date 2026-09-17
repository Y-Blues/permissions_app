import asyncio
import unittest

from ycappuccino.core.framework import Framework
from ycappuccino.core.testing import TemporaryApplication, wait_until
from ycappuccino.permissions import jwt_codec

APPLICATION = {
    "conf/application.yml": """
        name: permissionstest
        bundle_prefix:
          - ycappuccino.storage
          - ycappuccino.endpoints_service
          - ycappuccino.permissions
        layers:
          ycappuccino_storage_memory:
            active: true
        components:
          JwtAuthentication:
            key: test-key
          LoginService:
            key: test-key
        config:
          shell:
            console: false
    """,
    # IConfiguration only ever reads ./conf/config.properties (a flat key=value file),
    # never the yml's config: section - see core/bundles/configuration.py.
    "conf/config.properties": "permissions.superadmin.password=demo-password\n",
}


class TestPermissionsInFramework(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = TemporaryApplication(APPLICATION).open()
        cls.addClassCleanup(cls.app.close)
        cls.framework = Framework()
        cls.framework.init(cls.app.yml_path)
        cls.addClassCleanup(cls.framework.stop)
        wait_until(lambda: cls.framework.context.get_service_reference("RolePermissionAuthorization"))

    def _service(self, specification):
        reference = self.framework.context.get_service_reference(specification)
        self.assertIsNotNone(reference, specification)
        return self.framework.context.get_service(reference)

    def test_services_are_published(self):
        for specification in (
            "IAuthentication",
            "JwtAuthentication",
            "IAuthorization",
            "RolePermissionAuthorization",
            "LoginService",
            "LoginCookieService",
            "ChangePasswordService",
            "OrganizationTree",
            "AccountBootStrap",
        ):
            with self.subTest(specification=specification):
                self.assertIsNotNone(self.framework.context.get_service_reference(specification))

    def test_bootstrap_then_login_then_authorized_call(self):
        login = self._service("LoginService")
        authorization = self._service("IAuthorization")

        result = asyncio.run(
            login.call("POST", [], {}, {"login": "superadmin", "password": "demo-password"}, None)
        )
        self.assertIn("token", result.body)

        subject = jwt_codec.decode(result.body["token"], "test-key")
        self.assertEqual(subject["tid"], "system")
        self.assertTrue(asyncio.run(authorization.is_authorized(subject, "read", "book")))

    def test_the_authentication_decodes_the_token_of_the_login_service(self):
        login = self._service("LoginService")
        authentication = self._service("IAuthentication")

        result = asyncio.run(
            login.call("POST", [], {}, {"login": "superadmin", "password": "demo-password"}, None)
        )
        subject = asyncio.run(
            authentication.authenticate({"authorization": f"Bearer {result.body['token']}"}, "GET", "/", b"")
        )

        self.assertEqual(subject["sub"], "superadmin")

    def test_a_secure_service_is_refused_to_an_anonymous_caller(self):
        from ycappuccino.api.endpoints_storage import NotAuthenticated

        endpoint = self._service("IServiceEndpoint")

        with self.assertRaises(NotAuthenticated):
            asyncio.run(endpoint.call("change_password", "POST", [], {}, {}, None))


if __name__ == "__main__":
    unittest.main()
