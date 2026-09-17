"""Creates a Login with a hashed password. Not a CRUD create: a raw write would store the
password in cleartext (private=True only hides it from reads, not writes)."""

from typing import Any

from ycappuccino.api.endpoints_service import IExposedService, ServiceResult, ServiceRoute
from ycappuccino.api.endpoints_storage import InvalidRequest, NotFound
from ycappuccino.api.storage import IManager
from ycappuccino.permissions.models.login import Login


class CreateLoginService(IExposedService):
    name = "create_login"
    secure = True
    routes = (ServiceRoute(method="POST", summary="create a new login with a hashed password"),)

    def __init__(self, manager: IManager) -> None:
        self._manager = manager

    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass

    async def call(
        self, method: str, extra_path: list, params: dict, body: Any, subject: dict | None
    ) -> ServiceResult:
        if method != "POST":
            raise NotFound("not found")
        login_id = body["login"]
        if await self._manager.get_one("login", login_id, subject=None) is not None:
            raise InvalidRequest(f"login {login_id!r} already exists")
        login = Login()
        login.id(login_id)
        login.login(login_id)
        login.password(body["password"])
        await self._manager.up_sert_model(login, subject=None)
        return ServiceResult(body={})
