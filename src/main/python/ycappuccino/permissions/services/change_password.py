"""
ChangePasswordService: verifies the old password, then stores a fresh scrypt hash.
"""

from ycappuccino.api.decorators import rpc_method
from ycappuccino.api.endpoints_service import IExposedService
from ycappuccino.api.storage import IManager
from ycappuccino.permissions import passwords


class ChangePasswordService(IExposedService):
    name = "change_password"
    secure = True  # in addition to the old-password check itself

    def __init__(self, manager: IManager) -> None:
        self._manager = manager

    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass

    @rpc_method(method="POST", summary="replace the password of a login")
    async def change_password(self, login: str, password: str, new_password: str) -> dict:
        await passwords.check_login(self._manager, login, password)
        stored = await self._manager.get_one("login", login, subject=None)
        stored.password(new_password)
        await self._manager.up_sert_model(stored, subject=None)
        return {}
