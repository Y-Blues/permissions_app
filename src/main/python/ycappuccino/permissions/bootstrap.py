"""
AccountBootStrap: idempotently creates the system organization and the superadmin account.

Its login is permissions.superadmin.login ("superadmin" by default), its password
permissions.superadmin.password (generated and logged when unset), both read from conf/config.properties.
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
        name = self._config.get("permissions.superadmin.login", SUPERADMIN)
        if await self._manager.get_one("login", name, subject=None) is not None:
            return  # already initialized

        # written as the superadmin, in the system organization: like any user's records, they carry their
        # organization (_tid), so the tenant filter shows them to the system organization's members
        owner = {"sub": name, "tid": SYSTEM}
        password = self._config.get("permissions.superadmin.password", None)
        if password is None:
            password = secrets.token_urlsafe(16)
            self._logger.warning(f"generated superadmin password: {password}")

        organization = Organization()
        organization.id(SYSTEM)
        organization.name(SYSTEM)
        await self._manager.up_sert_model(organization, subject=owner)

        role = Role()
        role.id(SUPERADMIN)
        role.name(SUPERADMIN)
        await self._manager.up_sert_model(role, subject=owner)

        login = Login()
        login.id(name)
        login.login(name)
        login.password(password)
        await self._manager.up_sert_model(login, subject=owner)

        account = Account()
        account.id(name)
        account.name(name)
        account.login(name)
        account.role(SUPERADMIN)
        await self._manager.up_sert_model(account, subject=owner)

        role_account = RoleAccount()
        role_account.id(name)
        role_account.role(SUPERADMIN)
        role_account.account(name)
        role_account.organization(SYSTEM)
        await self._manager.up_sert_model(role_account, subject=owner)

        role_permission = RolePermission()
        role_permission.id(SUPERADMIN)
        role_permission.role(SUPERADMIN)
        role_permission.rights(["*:*"])
        await self._manager.up_sert_model(role_permission, subject=owner)
