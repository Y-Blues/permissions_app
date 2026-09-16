"""
CrudTransport: a ycappuccino.ui.transport.Transport that calls a local ICrud directly in Python --
no HTTP, same reasoning as ServiceEndpointTransport (see its docstring), for screens managing
@Item models (Organization, Role, RolePermission, Account) rather than IExposedService operations.

`service` is an item_id (e.g. "organization", "rolePermission" -- the @Item `name`, not its
`plural`), `path` is either empty (list/create) or a single document id (read/update/delete).
Every ICrud method is wired, not only create, so a future list/edit screen costs nothing extra
here -- only create is used by today's screens (ui_shell has no list/table widget yet, see
remote/docs/superpowers/specs/2026-09-16-ui-screen-library-checkpoint.md, "Pas encore fait").
"""

from typing import Any, Optional

from ycappuccino.api.endpoints_storage import ICrud


class CrudTransport:

    def __init__(self, crud: ICrud, subject: Optional[dict] = None):
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
