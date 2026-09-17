"""
WebSite: the Host serving site/ (built by run.sh) on "/", next to the backend's /api.
"""

import os

from ycappuccino.api.core_base import YCappuccinoComponent
from ycappuccino.api.storage import IManager
from ycappuccino.hosts.models.host import Host

_SITE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "site")


class WebSite(YCappuccinoComponent):

    def __init__(self, manager: IManager) -> None:
        self._manager = manager

    async def start(self) -> None:
        host = Host()
        host.id("permissions-web")
        host.path("/")
        host.directory(os.path.normpath(_SITE))
        host.priority(0)
        host.secure(False)
        await self._manager.up_sert_model(host, subject=None)

    async def stop(self) -> None:
        pass
