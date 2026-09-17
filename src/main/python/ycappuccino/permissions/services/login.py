"""
LoginService, LoginCookieService: the HTTP faces of ILoginService, answering the token as a JSON body
(and as a cookie).
"""

from ycappuccino.api.decorators import rpc_method
from ycappuccino.api.endpoints_service import IExposedService, ServiceResult
from ycappuccino.api.permissions import ILoginService


class LoginService(IExposedService):
    name = "login"
    secure = False

    def __init__(self, login_service: ILoginService) -> None:
        self._login_service = login_service

    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass

    @rpc_method(method="POST", summary="exchange a login and a password for a token", secure=False)
    async def login(self, login: str, password: str) -> dict:
        return {"token": await self._login_service.login(login, password)}


class LoginCookieService(IExposedService):
    name = "login_cookie"
    secure = False

    def __init__(self, login_service: ILoginService) -> None:
        self._login_service = login_service

    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass

    @rpc_method(method="POST", summary="log in and receive the token as a cookie", secure=False)
    async def login_cookie(self, login: str, password: str) -> ServiceResult:
        token = await self._login_service.login(login, password)
        return ServiceResult(
            body={"token": token},
            headers={"set-cookie": f"_ycappuccino={token};Path=/;HttpOnly"},
        )
