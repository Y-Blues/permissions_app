import unittest

from ycappuccino.permissions.frontend_shell.service_endpoint_transport import ServiceEndpointTransport


class FakeResult:
    def __init__(self, body):
        self.body = body


class FakeServiceEndpoint:

    def __init__(self, result=None):
        self.result = result
        self.calls = []

    async def call(self, name, method, extra_path, params, body, subject):
        self.calls.append((name, method, extra_path, params, body, subject))
        return FakeResult(self.result)


class TestServiceEndpointTransport(unittest.IsolatedAsyncioTestCase):

    async def test_calls_the_service_endpoint_directly_no_subject_by_default(self):
        endpoint = FakeServiceEndpoint(result={"token": "abc"})
        transport = ServiceEndpointTransport(endpoint)

        result = await transport.call("login", "POST", (), {}, {"login": "aurelien", "password": "x"})

        self.assertEqual(result, {"token": "abc"})
        self.assertEqual(
            endpoint.calls,
            [("login", "POST", [], {}, {"login": "aurelien", "password": "x"}, None)],
        )

    async def test_subject_given_at_construction_is_forwarded(self):
        endpoint = FakeServiceEndpoint(result={})
        transport = ServiceEndpointTransport(endpoint, subject={"sub": "acc-1"})

        await transport.call("change_password", "POST", (), {}, {})

        self.assertEqual(endpoint.calls[0][5], {"sub": "acc-1"})

    async def test_subject_can_be_set_after_construction(self):
        endpoint = FakeServiceEndpoint(result={})
        transport = ServiceEndpointTransport(endpoint)

        transport.subject = {"sub": "acc-1"}
        await transport.call("change_password", "POST", (), {}, {})

        self.assertEqual(endpoint.calls[0][5], {"sub": "acc-1"})

    async def test_extra_path_is_forwarded_as_a_list(self):
        endpoint = FakeServiceEndpoint(result={})
        transport = ServiceEndpointTransport(endpoint)

        await transport.call("scripts", "POST", ("run",), {}, {})

        self.assertEqual(endpoint.calls[0][2], ["run"])


if __name__ == "__main__":
    unittest.main()
