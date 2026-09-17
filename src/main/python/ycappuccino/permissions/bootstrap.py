"""
AccountBootStrap: idempotently creates the system organization and the superadmin account.
"""

import secrets

from ycappuccino.api.core import IActivityLogger, IConfiguration
from ycappuccino.api.core_base import YCappuccinoComponent, YCappuccinoType
from ycappuccino.api.storage import IManager
from ycappuccino.permissions.models.account import Account
from ycappuccino.permissions.models.login import Login
from ycappuccino.permissions.models.organization import Organization
from ycappuccino.permissions.models.role import Role
from ycappuccino.permissions.models.role_account import RoleAccount
from ycappuccino.permissions.models.role_permission import RolePermission

SUPERADMIN = "superadmin"
SYSTEM = "system"


class AccountBootStrap(YCappuccinoComponent):

    def __init__(
        self,
        manager: IManager,
        config: IConfiguration,
        logger: YCappuccinoType(IActivityLogger, "(name=main)"),
    ) -> None:
        self._manager, self._config, self._logger = manager, config, logger

    async def stop(self) -> None:
        pass

    async def start(self) -> None:
        if await self._manager.get_one("login", SUPERADMIN, subject=None) is not None:
            return  # already initialized

        password = self._config.get("permissions.superadmin.password", None)
        if password is None:
            password = secrets.token_urlsafe(16)
            self._logger.warning(f"generated superadmin password: {password}")

        organization = Organization()
        organization.id(SYSTEM)
        organization.name(SYSTEM)
        await self._manager.up_sert_model(organization, subject=None)

        role = Role()
        role.id(SUPERADMIN)
        role.name(SUPERADMIN)
        await self._manager.up_sert_model(role, subject=None)

        login = Login()
        login.id(SUPERADMIN)
        login.login(SUPERADMIN)
        login.password(password)
        await self._manager.up_sert_model(login, subject=None)

        account = Account()
        account.id(SUPERADMIN)
        account.name(SUPERADMIN)
        account.login(SUPERADMIN)
        account.role(SUPERADMIN)
        await self._manager.up_sert_model(account, subject=None)

        role_account = RoleAccount()
        role_account.id(SUPERADMIN)
        role_account.role(SUPERADMIN)
        role_account.account(SUPERADMIN)
        role_account.organization(SYSTEM)
        await self._manager.up_sert_model(role_account, subject=None)

        role_permission = RolePermission()
        role_permission.id(SUPERADMIN)
        role_permission.role(SUPERADMIN)
        role_permission.rights(["*:*"])
        await self._manager.up_sert_model(role_permission, subject=None)
