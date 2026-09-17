"""
PasswordLogin: ILoginService over the local Login/Account/RoleAccount items, issuing a JWT.
"""

from ycappuccino.api.permissions import ILoginService
from ycappuccino.api.storage import IManager
from ycappuccino.permissions import jwt_codec, passwords


class PasswordLogin(ILoginService):

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

    async def login(self, login: str, password: str) -> str:
        account_id = await passwords.check_login(self._manager, login, password)
        organization_id = await passwords.organization_of(self._manager, account_id)
        return jwt_codec.encode({"sub": account_id, "tid": organization_id}, self._key, self._timeout)
