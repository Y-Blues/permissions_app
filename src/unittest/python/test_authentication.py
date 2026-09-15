import unittest

from ycappuccino.permissions import jwt_codec
from ycappuccino.permissions.authentication import JwtAuthentication


class TestJwtAuthentication(unittest.IsolatedAsyncioTestCase):

    async def test_bearer_header(self):
        authentication = JwtAuthentication(key="test-key")
        token = jwt_codec.encode({"sub": "alice", "tid": "acme"}, "test-key", 60)

        subject = await authentication.authenticate({"authorization": f"Bearer {token}"})

        self.assertEqual((subject["sub"], subject["tid"]), ("alice", "acme"))

    async def test_ycappuccino_cookie(self):
        authentication = JwtAuthentication(key="test-key")
        token = jwt_codec.encode({"sub": "alice", "tid": "acme"}, "test-key", 60)

        subject = await authentication.authenticate({"cookie": f"lang=fr; _ycappuccino={token}"})

        self.assertEqual(subject["sub"], "alice")

    async def test_no_credentials(self):
        authentication = JwtAuthentication(key="test-key")

        self.assertIsNone(await authentication.authenticate({}))

    async def test_invalid_token(self):
        authentication = JwtAuthentication(key="test-key")

        self.assertIsNone(await authentication.authenticate({"authorization": "Bearer garbage"}))

    async def test_a_token_signed_with_another_key_is_refused(self):
        authentication = JwtAuthentication(key="test-key")
        token = jwt_codec.encode({"sub": "alice", "tid": "acme"}, "another-key", 60)

        self.assertIsNone(await authentication.authenticate({"authorization": f"Bearer {token}"}))

    async def test_default_key_logs_a_warning(self):
        authentication = JwtAuthentication()

        with self.assertLogs("ycappuccino.permissions.authentication", "WARNING"):
            await authentication.start()

    async def test_configured_key_does_not_warn(self):
        authentication = JwtAuthentication(key="a-real-key")

        with self.assertNoLogs("ycappuccino.permissions.authentication", "WARNING"):
            await authentication.start()


if __name__ == "__main__":
    unittest.main()
