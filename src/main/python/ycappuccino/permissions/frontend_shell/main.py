"""
FrontendShell: terminal admin console for permissions_app -- login, tenants, roles, permissions,
users. Screens are YAML templates (screens/*.yml). Talks to its own backend via a Python service/
CRUD call (never HTTP, see ServiceEndpointTransport/CrudTransport) -- same-process only, until
ycappuccino-remote's peer dispatch design lands (remote/docs/superpowers/plans/2026-09-16-transparent-rpc.md).

create_user() chains 3 screens: create_login (hashed password), account (profile), role_account
(tenant grant) -- same records AccountBootStrap creates by hand for the superadmin. A tenant-wide
role/permission (e.g. admin) is granted at the root organization ("system"), not a special case.

Login is local-only; an external identity provider is a future direction, not built here.
"""

from pathlib import Path

from ycappuccino.api.core_base import YCappuccinoComponent
from ycappuccino.api.endpoints_service import IServiceEndpoint
from ycappuccino.api.endpoints_storage import ICrud
from ycappuccino.permissions import jwt_codec
from ycappuccino.permissions.frontend_shell.crud_transport import CrudTransport
from ycappuccino.permissions.frontend_shell.service_endpoint_transport import ServiceEndpointTransport
from ycappuccino.ui.loader import load_screen_yaml
from ycappuccino.ui_shell.app import ScreenApp

_SCREENS_DIR = Path(__file__).parent / "screens"


def _load(name: str):
    return load_screen_yaml((_SCREENS_DIR / f"{name}.yml").read_text())


def load_login_screen():
    return _load("login")


def load_change_password_screen():
    return _load("change_password")


def load_organization_screen():
    return _load("organization")


def load_role_screen():
    return _load("role")


def load_role_permission_screen():
    return _load("role_permission")


def load_create_login_screen():
    return _load("create_login")


def load_account_screen():
    return _load("account")


def load_role_account_screen():
    return _load("role_account")


class FrontendShell(YCappuccinoComponent):

    def __init__(self, endpoint: IServiceEndpoint, crud: ICrud, key: str = jwt_codec.DEFAULT_KEY):
        self._endpoint = endpoint
        self._crud = crud
        self._key = key
        self._subject = None  # set by log_in(), reused by every screen run after that

    async def start(self):
        pass

    async def stop(self):
        pass

    def log_in(self) -> bool:
        transport = ServiceEndpointTransport(self._endpoint)
        login_app = ScreenApp(load_login_screen(), transport)
        login_app.run()
        if login_app.last_result is None:
            return False
        self._subject = jwt_codec.decode(login_app.last_result["token"], self._key)
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

        account_app = self._run_crud_screen(load_account_screen())
        if account_app.last_result is None:
            return

        self._run_crud_screen(load_role_account_screen())

    def _run_crud_screen(self, screen) -> ScreenApp:
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
