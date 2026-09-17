"""
LoginService, LoginCookieService: exchange a login/password for a JWT.
"""

from typing import Any

from ycappuccino.api.endpoints_service import IExposedService, ServiceResult, ServiceRoute
from ycappuccino.api.endpoints_storage import NotFound
from ycappuccino.api.permissions import ILoginService
from ycappuccino.api.storage import IManager
from ycappuccino.permissions import jwt_codec, passwords


async def _issue_token(manager: IManager, key: str, timeout: int, body: dict) -> str:
    account_id = await passwords.check_login(manager, body["login"], body["password"])
    organization_id = await passwords.organization_of(manager, account_id)
    return jwt_codec.encode({"sub": account_id, "tid": organization_id}, key, timeout)


class LoginService(IExposedService, ILoginService):
    name = "login"
    secure = False
    routes = (ServiceRoute(method="POST", summary="exchange a login and a password for a token"),)

    def __init__(
        self,
        manager: IManager,
        key: str = jwt_codec.DEFAULT_KEY,
        timeout: int = jwt_codec.DEFAULT_TIMEOUT,
    ) -> None:
        self._manager, self._key, self._timeout = manager, key, timeout

    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass

    async def call(
        self, method: str, extra_path: list, params: dict, body: Any, subject: dict | None
    ) -> ServiceResult:
        if method != "POST":
            raise NotFound("not found")
        return ServiceResult(body={"token": await self.login(body["login"], body["password"])})

    async def login(self, login: str, password: str) -> str:
        return await _issue_token(self._manager, self._key, self._timeout, {"login": login, "password": password})


class LoginCookieService(IExposedService):
    name = "login_cookie"
    secure = False
    routes = (
        ServiceRoute(method="POST", summary="log in and receive the token as a cookie"),
    )

    def __init__(
        self,
        manager: IManager,
        key: str = jwt_codec.DEFAULT_KEY,
        timeout: int = jwt_codec.DEFAULT_TIMEOUT,
    ) -> None:
        self._manager, self._key, self._timeout = manager, key, timeout

    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass

    async def call(
        self, method: str, extra_path: list, params: dict, body: Any, subject: dict | None
    ) -> ServiceResult:
        if method != "POST":
            raise NotFound("not found")
        token = await _issue_token(self._manager, self._key, self._timeout, body)
        return ServiceResult(
            body={"token": token},
            headers={"set-cookie": f"_ycappuccino={token};Path=/;HttpOnly"},
        )
