"""
CreateLoginService: creates a new Login (login + password), correctly hashed.

Not a generic CRUD create on item_id="login": Login.password(cleartext) is the only safe entry
point that salts and scrypt-hashes a password (see models/login.py) -- a plain CRUD write would
set the raw "password" field's storage value directly (private=True only hides it from reads, it
does not stop a write), storing the cleartext. This service exists precisely so nothing else ever
needs to do that.
"""

from ycappuccino.api.endpoints_service import IExposedService, ServiceResult, ServiceRoute
from ycappuccino.api.endpoints_storage import InvalidRequest, NotFound
from ycappuccino.api.storage import IManager
from ycappuccino.permissions.models.login import Login


class CreateLoginService(IExposedService):
    name = "create_login"
    secure = True
    routes = (ServiceRoute(method="POST", summary="create a new login with a hashed password"),)

    def __init__(self, manager: IManager):
        self._manager = manager

    async def start(self):
        pass

    async def stop(self):
        pass

    async def call(self, method, extra_path, params, body, subject):
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
