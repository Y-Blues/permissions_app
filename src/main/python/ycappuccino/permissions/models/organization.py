from ycappuccino.api.decorators import Item, Property
from ycappuccino.api.models import Model
from ycappuccino.core.decorator_app import App


@App(name="ycappuccino-permissions")
@Item(
    collection="organizations",
    name="organization",
    plural="organizations",
    secure_read=True,
    secure_write=True,
)
class Organization(Model):

    def __init__(self, a_dict=None):
        super().__init__(a_dict)
        self._name = None
        self._father = None

    @Property(name="name")
    def name(self, a_value):
        self._name = a_value

    @Property(name="father")
    def father(self, a_value):
        self._father = a_value
