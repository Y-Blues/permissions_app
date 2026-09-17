"""
FrontendShell: terminal admin console for permissions_app -- login, tenants, roles, permissions,
users. Screens are the shared YAML templates of ycappuccino.permissions.screens. Talks to its backend
through its interfaces only (ILoginService, IServiceEndpoint, ICrud), local or proxied.

create_user() chains 3 screens: create_login (hashed password), account (profile), role_account
(tenant grant) -- same records AccountBootStrap creates by hand for the superadmin. A tenant-wide
role/permission (e.g. admin) is granted at the root organization ("system"), not a special case.

Login is local-only; an external identity provider is a future direction, not built here.
"""

from ycappuccino.api.core_base import YCappuccinoComponent
from ycappuccino.api.endpoints_service import IServiceEndpoint
from ycappuccino.api.endpoints_storage import ICrud
from ycappuccino.api.permissions import ILoginService
from ycappuccino.permissions import jwt_codec
from ycappuccino.permissions.screens import (
    load_account_screen,
    load_change_password_screen,
    load_create_login_screen,
    load_login_screen,
    load_organization_screen,
    load_role_account_screen,
    load_role_permission_screen,
    load_role_screen,
    with_defaults,
)
from ycappuccino.ui.model import Screen
from ycappuccino.ui.ycappuccino_transport import ComponentTransport, CrudTransport, ServiceEndpointTransport
from ycappuccino.ui_shell.app import ScreenApp


class FrontendShell(YCappuccinoComponent):

    def __init__(
        self, login: ILoginService, endpoint: IServiceEndpoint, crud: ICrud, key: str = jwt_codec.DEFAULT_KEY
    ) -> None:
        self._login = login
        self._endpoint = endpoint
        self._crud = crud
        self._key = key
        self._subject: dict | None = None  # set by log_in(), reused by every screen run after that

    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass

    def log_in(self) -> bool:
        login_app = ScreenApp(load_login_screen(), ComponentTransport({"login": self._login}))
        login_app.run()
        if login_app.last_result is None:
            return False
        self._subject = jwt_codec.decode(login_app.last_result, self._key)
        return True

    def run(self) -> None:
        if not self.log_in():
            return
        transport = ServiceEndpointTransport(self._endpoint, subject=self._subject)
        ScreenApp(load_change_password_screen(), transport).run()

    def create_organization(self) -> None:
        self._run_crud_screen(load_organization_screen())

    def create_role(self) -> None:
        self._run_crud_screen(load_role_screen())

    def grant_permission(self) -> None:
        self._run_crud_screen(load_role_permission_screen())

    def grant_role(self) -> None:
        self._run_crud_screen(load_role_account_screen())

    def create_user(self) -> None:
        transport = ServiceEndpointTransport(self._endpoint, subject=self._subject)
        credentials_app = ScreenApp(load_create_login_screen(), transport)
        credentials_app.run()
        if credentials_app.last_result is None:
            return

        # each step prefilled with what the previous one created: the login, then the account's id
        account_app = self._run_crud_screen(
            with_defaults(load_account_screen(), login=credentials_app.last_values["login"])
        )
        if account_app.last_result is None:
            return

        self._run_crud_screen(with_defaults(load_role_account_screen(), account=account_app.last_result["_id"]))

    def _run_crud_screen(self, screen: Screen) -> ScreenApp:
        transport = CrudTransport(self._crud, subject=self._subject)
        app = ScreenApp(screen, transport)
        app.run()
        return app

    def run_menu(self) -> None:
        print("permissions_app -- console d'administration")
        while True:
            if self._subject is None:
                print("\n1) Se connecter\n0) Quitter")
                choice = input("> ").strip()
                if choice == "1":
                    self.log_in()
                elif choice == "0":
                    return
                continue

            print(
                "\n1) Changer mon mot de passe"
                "\n2) Créer une organisation (tenant)"
                "\n3) Créer un rôle"
                "\n4) Créer une permission"
                "\n5) Créer un utilisateur"
                "\n6) Attribuer un rôle"
                "\n0) Quitter"
            )
            choice = input("> ").strip()
            if choice == "1":
                transport = ServiceEndpointTransport(self._endpoint, subject=self._subject)
                ScreenApp(load_change_password_screen(), transport).run()
            elif choice == "2":
                self.create_organization()
            elif choice == "3":
                self.create_role()
            elif choice == "4":
                self.grant_permission()
            elif choice == "5":
                self.create_user()
            elif choice == "6":
                self.grant_role()
            elif choice == "0":
                return
