"""
Fixtures shared by the permissions_app tests: a real Manager on MemoryStorage, no framework.
"""

import os
import tempfile

from ycappuccino.storage.files import LocalFileStore
from ycappuccino.storage.items import ItemManager
from ycappuccino.storage.manager import Manager
from ycappuccino.storage.memory import MemoryStorage

# importing the models registers them with ItemManager
from ycappuccino.permissions.models import (  # noqa: F401
    account,
    login,
    organization,
    role,
    role_account,
    role_permission,
)


def create_manager(triggers=None, filters=None):
    """manager on a memory storage; the caller removes the returned directory"""
    directory = tempfile.mkdtemp()
    manager = Manager(
        MemoryStorage(),
        ItemManager(),
        triggers if triggers is not None else [],
        filters if filters is not None else [],
        LocalFileStore(os.path.join(directory, "files")),
    )
    return manager, directory
