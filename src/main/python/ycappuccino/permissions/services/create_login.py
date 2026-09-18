"""Creates a Login with a hashed password. Not a CRUD create: a raw write would store the
password in cleartext (private=True only hides it from reads, not writes)."""

from ycappuccino.api.decorators import rpc_method
from ycappuccino.api.endpoints_service import IExposedService
from ycappuccino.api.endpoints_storage import InvalidRequest
from ycappuccino.api.storage import IManager
from ycappuccino.permissions.models.login import Login


class CreateLoginService(IExposedService):
    name = "create_login"
    secure = True

    def __init__(self, manager: IManager) -> None:
        self._manager = manager

    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass

    @rpc_method(method="POST", summary="create a new login with a hashed password")
    async def create_login(self, login: str, password: str, subject: dict | None = None) -> dict:
        """the login belongs to the organization of whoever creates it (subject); unique across all of them"""
        if await self._manager.get_one("login", login, subject=None) is not None:
            raise InvalidRequest(f"login {login!r} already exists")
        created = Login()
        created.id(login)
        created.login(login)
        created.password(password)
        await self._manager.up_sert_model(created, subject=subject)
        return {}
