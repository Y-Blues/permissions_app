"""
LoginService, LoginCookieService: exchange a login/password for a JWT.
"""

from ycappuccino.api.endpoints_service import IExposedService, ServiceResult, ServiceRoute
from ycappuccino.api.endpoints_storage import NotFound
from ycappuccino.api.storage import IManager
from ycappuccino.permissions import jwt_codec, passwords


async def _issue_token(manager, key, timeout, body):
    account_id = await passwords.check_login(manager, body["login"], body["password"])
    organization_id = await passwords.organization_of(manager, account_id)
    return jwt_codec.encode({"sub": account_id, "tid": organization_id}, key, timeout)


class LoginService(IExposedService):
    name = "login"
    secure = False
    routes = (ServiceRoute(method="POST", summary="exchange a login and a password for a token"),)

    def __init__(
        self,
        manager: IManager,
        key: str = jwt_codec.DEFAULT_KEY,
        timeout: int = jwt_codec.DEFAULT_TIMEOUT,
    ):
        self._manager, self._key, self._timeout = manager, key, timeout

    async def start(self):
        pass

    async def stop(self):
        pass

    async def call(self, method, extra_path, params, body, subject):
        if method != "POST":
            raise NotFound("not found")
        token = await _issue_token(self._manager, self._key, self._timeout, body)
        return ServiceResult(body={"token": token})


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
    ):
        self._manager, self._key, self._timeout = manager, key, timeout

    async def start(self):
        pass

    async def stop(self):
        pass

    async def call(self, method, extra_path, params, body, subject):
        if method != "POST":
            raise NotFound("not found")
        token = await _issue_token(self._manager, self._key, self._timeout, body)
        return ServiceResult(
            body={"token": token},
            headers={"set-cookie": f"_ycappuccino={token};Path=/;HttpOnly"},
        )
