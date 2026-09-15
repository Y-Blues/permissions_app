import secrets

from ycappuccino.api.decorators import Item, Property
from ycappuccino.api.models import Model
from ycappuccino.core.decorator_app import App
from ycappuccino.permissions import passwords


@App(name="ycappuccino-permissions")
@Item(
    collection="logins",
    name="login",
    plural="logins",
    secure_read=True,
    secure_write=True,
)
class Login(Model):

    def __init__(self, a_dict=None):
        super().__init__(a_dict)
        self._login = None
        self._salt = None
        self._password = None

    @Property(name="login")
    def login(self, a_value):
        self._login = a_value

    @Property(name="salt")
    def salt(self, a_value):
        self._salt = a_value

    @Property(name="password", private=True)
    def _stored_password(self, a_value):
        self._password = a_value

    def password(self, cleartext):
        """sets a fresh salt and stores its scrypt hash - do not call _stored_password directly"""
        self.salt(secrets.token_hex(32))
        self._stored_password(passwords.hash_scrypt(cleartext, self._salt))
