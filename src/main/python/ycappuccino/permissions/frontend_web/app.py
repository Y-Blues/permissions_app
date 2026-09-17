"""
PermissionsWebApp: the browser admin console -- login, password change, tenants, roles, permissions and
users -- on the shared screens of ycappuccino.permissions.screens. It knows interfaces only: ILoginService,
IServiceEndpoint and ICrud (the generated proxies of ycappuccino.client in a browser), ISession for the
token, IWebPage to draw. No subject is sent: the backend derives it from the token.
"""

from typing import Any, Awaitable, Callable

from ycappuccino.api.core_base import YCappuccinoComponent
from ycappuccino.api.endpoints_service import IServiceEndpoint
from ycappuccino.api.endpoints_storage import ICrud
from ycappuccino.api.permissions import ILoginService
from ycappuccino.client.transport import ISession
from ycappuccino.permissions.screens import (
    load_account_screen,
    load_change_password_screen,
    load_create_login_screen,
    load_login_screen,
    load_organization_screen,
    load_role_account_screen,
    load_role_permission_screen,
    load_role_screen,
)
from ycappuccino.ui.model import Screen
from ycappuccino.ui.transport import Transport
from ycappuccino.ui.ycappuccino_transport import ComponentTransport, CrudTransport, ServiceEndpointTransport
from ycappuccino.ui_web.page import IWebPage

MENU_TITLE = "Administration des permissions"
SAVED = "Enregistré."
BACK = "Retour au menu"


class PermissionsWebApp(YCappuccinoComponent):

    def __init__(
        self, page: IWebPage, login: ILoginService, endpoint: IServiceEndpoint, crud: ICrud, session: ISession
    ) -> None:
        self._page = page
        self._login = login
        self._services = ServiceEndpointTransport(endpoint)
        self._crud = CrudTransport(crud)
        self._session = session

    async def start(self) -> None:
        self.show_login()

    async def stop(self) -> None:
        pass

    def show_login(self) -> None:
        self._page.navigator().show_screen(
            load_login_screen(), ComponentTransport({"login": self._login}), on_result=self._signed_in
        )

    def show_menu(self) -> None:
        self._page.navigator().show_menu(
            MENU_TITLE,
            [
                ("Changer mon mot de passe", self._form(load_change_password_screen, self._services)),
                ("Créer une organisation", self._form(load_organization_screen, self._crud)),
                ("Créer un rôle", self._form(load_role_screen, self._crud)),
                ("Créer une permission", self._form(load_role_permission_screen, self._crud)),
                ("Créer un utilisateur", self._create_user),
                ("Attribuer un rôle", self._form(load_role_account_screen, self._crud)),
                ("Se déconnecter", self._sign_out),
            ],
        )

    async def _signed_in(self, token: str) -> None:
        self._session.set_token(token)
        self.show_menu()

    async def _sign_out(self) -> None:
        self._session.clear_token()
        self.show_login()

    def _form(self, load: Callable[[], Screen], transport: Transport) -> Callable[[], Awaitable[None]]:
        async def show() -> None:
            self._page.navigator().show_screen(load(), transport, on_result=self._saved)

        return show

    async def _create_user(self) -> None:
        # the three records AccountBootStrap creates for the superadmin: credentials (hashed password,
        # never a raw CRUD write), profile, then the role in a tenant. Each step is prefilled with what the
        # previous one created: the login, then the id the backend gave the account.
        async def grant(account: dict) -> None:
            view = self._page.navigator().show_screen(load_role_account_screen(), self._crud, on_result=self._saved)
            view.set_value("account", account["_id"])

        async def profile(_: Any) -> None:
            view = self._page.navigator().show_screen(load_account_screen(), self._crud, on_result=grant)
            view.set_value("login", credentials.last_values["login"])

        credentials = self._page.navigator().show_screen(
            load_create_login_screen(), self._services, on_result=profile
        )

    async def _saved(self, _: Any) -> None:
        self._page.navigator().show_message(SAVED, back=(BACK, self._back_to_menu))

    async def _back_to_menu(self) -> None:
        self.show_menu()
