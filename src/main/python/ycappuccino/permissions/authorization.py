"""
RolePermissionAuthorization: re-reads RoleAccount/RolePermission on every check (see spec section 2.3).
"""

import re

from ycappuccino.api.endpoints_storage import IAuthorization
from ycappuccino.api.storage import IManager


class RolePermissionAuthorization(IAuthorization):

    def __init__(self, manager: IManager) -> None:
        self._manager = manager

    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass

    async def is_authorized(self, subject: dict, action: str, item_id: str) -> bool:
        if "sub" not in subject or "tid" not in subject:
            # a peer calling on nobody's behalf has no role: its trust is its own, not a user's
            return False
        role_accounts = await self._manager.get_many(
            "roleAccount",
            {"filter": {"account.ref": subject["sub"], "organization.ref": subject["tid"]}},
            subject=None,
        )
        if not role_accounts:
            return False
        role_id = role_accounts[0].get_storage_model()["role"]["ref"]
        permissions = await self._manager.get_many(
            "rolePermission", {"filter": {"role.ref": role_id}}, subject=None
        )
        rights = [
            right
            for model in permissions
            for right in model.get_storage_model().get("rights") or ()
        ]
        return any(_matches(pattern, action, item_id) for pattern in rights)


def _matches(pattern: str, action: str, item_id: str) -> bool:
    """a right "<action>:<item_id>", where * stands for any sequence of characters"""
    return re.fullmatch(re.escape(pattern).replace(r"\*", ".*"), f"{action}:{item_id}") is not None
