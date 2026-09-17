from ycappuccino.api.decorators import Item, Property
from ycappuccino.api.models import Model
from ycappuccino.core.decorator_app import App


@App(name="ycappuccino-permissions")
@Item(
    collection="roles",
    name="role",
    plural="roles",
    secure_read=True,
    secure_write=True,
)
class Role(Model):

    def __init__(self, a_dict: dict | None = None) -> None:
        super().__init__(a_dict)
        self._name = None

    @Property(name="name")
    def name(self, a_value: str) -> None:
        self._name = a_value
