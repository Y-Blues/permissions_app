"""Transport calling a local ICrud directly (no HTTP). `service` is an item_id, `path` is empty
or a single document id."""

from typing import Any

from ycappuccino.api.endpoints_storage import ICrud


class CrudTransport:

    def __init__(self, crud: ICrud, subject: dict | None = None) -> None:
        self._crud = crud
        self.subject = subject

    async def call(self, service: str, method: str, path: tuple, params: dict, body: Any) -> Any:
        if method == "GET" and not path:
            return await self._crud.get_many(service, params, self.subject)
        if method == "GET":
            return await self._crud.get_one(service, path[0], params, self.subject)
        if method == "POST":
            return await self._crud.create(service, body, self.subject)
        if method == "PUT":
            return await self._crud.update(service, path[0], body, self.subject)
        if method == "DELETE":
            await self._crud.delete(service, path[0], self.subject)
            return None
        raise ValueError(f"CrudTransport: unsupported method {method!r}")
