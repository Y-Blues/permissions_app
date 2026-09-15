"""
ChangePasswordService: verifies the old password, then stores a fresh scrypt hash.
"""

from ycappuccino.api.endpoints_service import IExposedService, ServiceResult, ServiceRoute
from ycappuccino.api.endpoints_storage import NotFound
from ycappuccino.api.storage import IManager
from ycappuccino.permissions import passwords


class ChangePasswordService(IExposedService):
    name = "change_password"
    secure = True  # in addition to the old-password check itself
    routes = (
        ServiceRoute(method="POST", summary="replace the password of a login"),
    )

    def __init__(self, manager: IManager):
        self._manager = manager

    async def start(self):
        pass

    async def stop(self):
        pass

    async def call(self, method, extra_path, params, body, subject):
        if method != "POST":
            raise NotFound("not found")
        await passwords.check_login(self._manager, body["login"], body["password"])
        login = await self._manager.get_one("login", body["login"], subject=None)
        login.password(body["new_password"])
        await self._manager.up_sert_model(login, subject=None)
        return ServiceResult(body={})
