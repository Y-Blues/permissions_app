from ycappuccino.api.decorators import Item, ItemReference, Reference
from ycappuccino.api.models import Model
from ycappuccino.core.decorator_app import App


@App(name="ycappuccino-permissions")
@Item(
    collection="role_accounts",
    name="roleAccount",
    plural="role-accounts",
    secure_read=True,
    secure_write=True,
)
@ItemReference(from_name="roleAccount", field="account", item="account")
@ItemReference(from_name="roleAccount", field="role", item="role")
@ItemReference(from_name="roleAccount", field="organization", item="organization")
class RoleAccount(Model):

    def __init__(self, a_dict: dict | None = None) -> None:
        super().__init__(a_dict)
        self._role = None
        self._account = None
        self._organization = None

    @Reference(name="role")
    def role(self, a_value: str) -> None:
        self._role = a_value

    @Reference(name="account")
    def account(self, a_value: str) -> None:
        self._account = a_value

    @Reference(name="organization")
    def organization(self, a_value: str) -> None:
        self._organization = a_value
