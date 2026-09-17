"""
OrganizationTree: the tenant filter for storage (IFilter) and the trigger keeping it in sync (ITrigger).
"""

from ycappuccino.api.models import Model
from ycappuccino.api.storage import IFilter, IManager, ITrigger

_PAGE = 1000


class OrganizationTree(ITrigger, IFilter):

    item_id = "organization"
    actions = ("upsert", "delete")
    post = True

    def __init__(self, manager: IManager) -> None:
        self._manager = manager
        self._children: dict[str, set[str]] = {}

    async def start(self) -> None:
        await self._load_tree()

    async def stop(self) -> None:
        pass

    async def get_filter(self, item_id: str, subject: dict) -> dict | None:
        return {"_tid": {"$in": self._descendants(subject["tid"])}}

    async def execute(self, action: str, item_id: str, model: Model) -> None:
        document = model.get_storage_model()
        if action == "delete":
            self._remove(document["_id"])
        else:
            self._add(document["_id"], document.get("father"))

    async def _load_tree(self) -> None:
        offset = 0
        while True:
            organizations = await self._manager.get_many(
                "organization", {"limit": _PAGE, "offset": offset}, subject=None
            )
            for organization in organizations:
                document = organization.get_storage_model()
                self._add(document["_id"], document.get("father"))
            if len(organizations) < _PAGE:
                return
            offset += _PAGE

    def _add(self, organization_id: str, father_id: str | None) -> None:
        if father_id:
            self._children.setdefault(father_id, set()).add(organization_id)

    def _remove(self, organization_id: str) -> None:
        for children in self._children.values():
            children.discard(organization_id)
        self._children.pop(organization_id, None)

    def _descendants(self, root_id: str) -> list[str]:
        result = [root_id]
        for child in self._children.get(root_id, ()):
            result.extend(self._descendants(child))
        return result
