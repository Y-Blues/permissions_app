import unittest

from ycappuccino.permissions.frontend_shell.crud_transport import CrudTransport


class FakeCrud:

    def __init__(self, result=None):
        self.result = result
        self.calls = []

    async def get_one(self, item_id, id, params=None, subject=None):
        self.calls.append(("get_one", item_id, id, params, subject))
        return self.result

    async def get_many(self, item_id, params=None, subject=None):
        self.calls.append(("get_many", item_id, params, subject))
        return self.result

    async def create(self, item_id, fields, subject=None):
        self.calls.append(("create", item_id, fields, subject))
        return self.result

    async def update(self, item_id, id, fields, subject=None):
        self.calls.append(("update", item_id, id, fields, subject))
        return self.result

    async def delete(self, item_id, id, subject=None):
        self.calls.append(("delete", item_id, id, subject))


class TestCrudTransport(unittest.IsolatedAsyncioTestCase):

    async def test_post_without_path_creates(self):
        crud = FakeCrud(result={"_id": "acme"})
        transport = CrudTransport(crud, subject={"sub": "admin"})

        result = await transport.call("organization", "POST", (), {}, {"name": "Acme"})

        self.assertEqual(result, {"_id": "acme"})
        self.assertEqual(crud.calls, [("create", "organization", {"name": "Acme"}, {"sub": "admin"})])

    async def test_get_without_path_lists(self):
        crud = FakeCrud(result={"items": [], "total": 0})
        transport = CrudTransport(crud)

        await transport.call("role", "GET", (), {"limit": "10"}, None)

        self.assertEqual(crud.calls, [("get_many", "role", {"limit": "10"}, None)])

    async def test_get_with_path_reads_one(self):
        crud = FakeCrud(result={"_id": "admin"})
        transport = CrudTransport(crud)

        await transport.call("role", "GET", ("admin",), {}, None)

        self.assertEqual(crud.calls, [("get_one", "role", "admin", {}, None)])

    async def test_put_updates(self):
        crud = FakeCrud(result={"_id": "admin"})
        transport = CrudTransport(crud)

        await transport.call("role", "PUT", ("admin",), {}, {"name": "Admin"})

        self.assertEqual(crud.calls, [("update", "role", "admin", {"name": "Admin"}, None)])

    async def test_delete(self):
        crud = FakeCrud()
        transport = CrudTransport(crud)

        result = await transport.call("role", "DELETE", ("admin",), {}, None)

        self.assertIsNone(result)
        self.assertEqual(crud.calls, [("delete", "role", "admin", None)])

    async def test_subject_can_be_set_after_construction(self):
        crud = FakeCrud(result={})
        transport = CrudTransport(crud)

        transport.subject = {"sub": "admin"}
        await transport.call("organization", "POST", (), {}, {})

        self.assertEqual(crud.calls[0][3], {"sub": "admin"})


if __name__ == "__main__":
    unittest.main()
