import unittest

from ycappuccino.permissions import jwt_codec


class TestJwtCodec(unittest.TestCase):

    def test_round_trip(self):
        token = jwt_codec.encode({"sub": "alice"}, "key", 60)

        self.assertEqual(jwt_codec.decode(token, "key")["sub"], "alice")

    def test_wrong_key_is_rejected(self):
        token = jwt_codec.encode({"sub": "alice"}, "key", 60)

        self.assertIsNone(jwt_codec.decode(token, "other"))

    def test_expired_token_is_rejected(self):
        token = jwt_codec.encode({"sub": "alice"}, "key", -1)

        self.assertIsNone(jwt_codec.decode(token, "key"))

    def test_default_timeout_is_fifteen_minutes_in_seconds(self):
        self.assertEqual(jwt_codec.DEFAULT_TIMEOUT, 900)


if __name__ == "__main__":
    unittest.main()
