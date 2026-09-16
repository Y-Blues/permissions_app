"""
FrontendShell: log in, then change the password -- two screens loaded from YAML templates
(screens/login.yml, screens/change_password.yml, never hand-built in Python), chained through the
same ServiceEndpointTransport: the account/organization decoded from a successful login's token
becomes the `subject` of the change_password call automatically, exactly what an authenticated
HTTP request would carry via ApiServlet._authenticate -- done by hand here since there is no HTTP
request at all.

This component only runs installed in the SAME process/Framework as permissions_app's own backend
(constructor-injected a real IServiceEndpoint) -- it calls services the same way any other
in-process component does, deliberately never over HTTP (explicit choice: communication between
this frontend and its backend is a Python service call, not a network request).

Calling a *remote* permissions_app instance (a separate process/machine) is not possible today and
is NOT sketched as a real code path here: it is ycappuccino-remote's job, once its typed,
peer-authenticated dispatch design lands
(remote/docs/superpowers/specs/2026-09-16-transparent-rpc-design.md, plan written at
remote/docs/superpowers/plans/2026-09-16-transparent-rpc.md, not yet implemented). Until then, this
stays a single-process tool.
"""

from pathlib import Path

from ycappuccino.api.core_base import YCappuccinoComponent
from ycappuccino.api.endpoints_service import IServiceEndpoint
from ycappuccino.permissions import jwt_codec
from ycappuccino.permissions.frontend_shell.service_endpoint_transport import ServiceEndpointTransport
from ycappuccino.ui.loader import load_screen_yaml
from ycappuccino.ui_shell.app import ScreenApp

_SCREENS_DIR = Path(__file__).parent / "screens"


def load_login_screen():
    return load_screen_yaml((_SCREENS_DIR / "login.yml").read_text())


def load_change_password_screen():
    return load_screen_yaml((_SCREENS_DIR / "change_password.yml").read_text())


class FrontendShell(YCappuccinoComponent):

    def __init__(self, endpoint: IServiceEndpoint, key: str = jwt_codec.DEFAULT_KEY):
        self._endpoint = endpoint
        self._key = key

    async def start(self):
        pass

    async def stop(self):
        pass

    def run(self) -> None:
        transport = ServiceEndpointTransport(self._endpoint)

        login_app = ScreenApp(load_login_screen(), transport)
        login_app.run()
        if login_app.last_result is None:
            return  # cancelled (no action ran) -- nothing to chain to

        transport.subject = jwt_codec.decode(login_app.last_result["token"], self._key)
        ScreenApp(load_change_password_screen(), transport).run()
