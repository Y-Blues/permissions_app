from ycappuccino.api.decorators import Item, ItemReference, Property, Reference
from ycappuccino.api.models import Model
from ycappuccino.core.decorator_app import App


@App(name="ycappuccino-permissions")
@Item(
    collection="role_permissions",
    name="rolePermission",
    plural="role-permissions",
    secure_read=True,
    secure_write=True,
)
@ItemReference(from_name="rolePermission", field="role", item="role")
class RolePermission(Model):

    def __init__(self, a_dict: dict | None = None) -> None:
        super().__init__(a_dict)
        self._role = None
        self._rights = None

    @Reference(name="role")
    def role(self, a_value: str) -> None:
        self._role = a_value

    @Property(name="rights")
    def rights(self, a_value: list[str]) -> None:
        self._rights = a_value
