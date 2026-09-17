"""
PermissionsWebApp: the browser admin console. Its layout is ycappuccino.permissions.screens' application.yml,
rendered by ycappuccino.ui_web's WebApplication -- the same one FrontendShell renders in a terminal. It knows
interfaces only: ILoginService, IServiceEndpoint and ICrud (the generated proxies of ycappuccino.client in a
browser), ISession for the token, IWebPage to draw. No subject is sent: the backend derives it from the token.
"""

from pathlib import Path
from typing import Any

from ycappuccino.api.core_base import YCappuccinoComponent
from ycappuccino.api.endpoints_service import IServiceEndpoint
from ycappuccino.api.endpoints_storage import ICrud
from ycappuccino.api.permissions import ILoginService
from ycappuccino.client.transport import ISession
from ycappuccino.permissions.screens import load_application, load_screen
from ycappuccino.ui.ycappuccino_transport import ComponentTransport, CrudTransport, ServiceEndpointTransport
from ycappuccino.ui_web.application import WebApplication
from ycappuccino.ui_web.page import IWebPage

# the console's theme, on the yc-* classes ui_web puts on its elements
STYLESHEET = Path(__file__).parent / "style.css"


class PermissionsWebApp(YCappuccinoComponent):

    def __init__(
        self, page: IWebPage, login: ILoginService, endpoint: IServiceEndpoint, crud: ICrud, session: ISession
    ) -> None:
        self._page = page
        self._session = session
        self._transports = {
            "login": ComponentTransport({"login": login}),
            "services": ServiceEndpointTransport(endpoint),
            "crud": CrudTransport(crud),
        }

    async def start(self) -> None:
        self._page.add_stylesheet(STYLESHEET.read_text(encoding="utf-8"))
        WebApplication(
            load_application(), self._page.navigator(), load_screen, self._transports, self._signed_in, self._signed_out
        ).start()

    async def stop(self) -> None:
        pass

    async def _signed_in(self, token: Any) -> None:
        self._session.set_token(token)

    async def _signed_out(self) -> None:
        self._session.clear_token()
