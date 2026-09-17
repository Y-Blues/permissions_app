"""
FrontendShell: the terminal admin console. Its layout is ycappuccino.permissions.screens' application.yml,
rendered by ycappuccino.ui_shell's ShellApplication -- the same one PermissionsWebApp renders in a browser. It
knows interfaces only (ILoginService, IServiceEndpoint, ICrud) and runs next to its backend: the subject
decoded from the login token goes with every later call, hence its `key`.

Login is local-only; an external identity provider is a future direction, not built here.
"""

from typing import Any

from ycappuccino.api.core_base import YCappuccinoComponent
from ycappuccino.api.endpoints_service import IServiceEndpoint
from ycappuccino.api.endpoints_storage import ICrud
from ycappuccino.api.permissions import ILoginService
from ycappuccino.permissions import jwt_codec
from ycappuccino.permissions.screens import load_application, load_screen
from ycappuccino.ui.ycappuccino_transport import ComponentTransport, CrudTransport, ServiceEndpointTransport
from ycappuccino.ui_shell.application import ShellApplication


class FrontendShell(YCappuccinoComponent):

    def __init__(
        self, login: ILoginService, endpoint: IServiceEndpoint, crud: ICrud, key: str = jwt_codec.DEFAULT_KEY
    ) -> None:
        self._key = key
        self._services = ServiceEndpointTransport(endpoint)
        self._crud = CrudTransport(crud)
        self._login = ComponentTransport({"login": login})

    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass

    @property
    def subject(self) -> dict | None:
        """the signed-in subject, passed to every call; None before login and after sign-out"""
        return self._crud.subject

    def application(self) -> ShellApplication:
        return ShellApplication(
            load_application(),
            load_screen,
            {"login": self._login, "services": self._services, "crud": self._crud},
            self._signed_in,
            self._signed_out,
        )

    def run_menu(self) -> None:
        self.application().run()

    async def _signed_in(self, token: Any) -> None:
        self._set_subject(jwt_codec.decode(token, self._key))

    async def _signed_out(self) -> None:
        self._set_subject(None)

    def _set_subject(self, subject: dict | None) -> None:
        self._services.subject = subject
        self._crud.subject = subject
