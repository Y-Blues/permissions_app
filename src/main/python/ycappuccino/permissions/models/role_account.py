from ycappuccino.core.decorator_app import App

from ycappuccino.api.decorators import Item, ItemReference, Empty, Property, Reference
from ycappuccino.api.models import Model

"""
    model that describe link between role and account
"""


@Empty()
def empty():
    _empty = RoleAccount()
    _empty.id("test")
    _empty.role("test")
    _empty.account("test")
    _empty.organization("test")
    return _empty


@App(name="ycappuccino-permissions")
@Item(
    collection="roleAccounts",
    name="roleAccount",
    plural="role-accounts",
    secure_write=True,
    secure_read=True,
)
@ItemReference(from_name="roleAccounts", field="account", item="account")
@ItemReference(from_name="roleAccounts", field="role", item="role")
@ItemReference(from_name="roleAccounts", field="organization", item="organization")
class RoleAccount(Model):
    def __init__(self, a_dict=None):
        super().__init__(a_dict)
        self._role = None
        self._account = None
        self._organization = None

    @Reference(name="role")
    def role(self, a_value):
        self._role = a_value

    @Reference(name="account")
    def account(self, a_values):
        """list of right permission"""
        self._account = a_values

    @Reference(name="organization")
    def organization(self, a_organization):
        """list of right permission"""
        self._organization = a_organization


empty()
