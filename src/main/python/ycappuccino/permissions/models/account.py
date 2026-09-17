from ycappuccino.api.decorators import Item, ItemReference, Property, Reference
from ycappuccino.api.models import Model
from ycappuccino.core.decorator_app import App


@App(name="ycappuccino-permissions")
@Item(
    collection="accounts",
    name="account",
    plural="accounts",
    secure_read=True,
    secure_write=True,
)
@ItemReference(from_name="account", field="login", item="login")
@ItemReference(from_name="account", field="role", item="role")
class Account(Model):

    def __init__(self, a_dict: dict | None = None) -> None:
        super().__init__(a_dict)
        self._name = None
        self._login = None
        self._role = None

    @Property(name="name")
    def name(self, a_value: str) -> None:
        self._name = a_value

    @Reference(name="login")
    def login(self, a_value: str) -> None:
        self._login = a_value

    @Reference(name="role")
    def role(self, a_value: str) -> None:
        self._role = a_value
