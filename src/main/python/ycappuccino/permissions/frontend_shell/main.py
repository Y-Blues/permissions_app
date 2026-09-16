"""
FrontendShell: a terminal admin console for permissions_app -- log in, change password, and
manage organizations (tenancy), roles, permissions and users -- every screen loaded from a YAML
template (screens/*.yml, never hand-built in Python), chained through the same decoded subject
once logged in.

Talks to its own backend as a Python service call (ServiceEndpointTransport, a real
IServiceEndpoint) or a Python CRUD call (CrudTransport, a real ICrud) -- never HTTP. This
component therefore only runs installed in the SAME process/Framework as permissions_app's own
backend. Calling a *remote* permissions_app instance (a separate process/machine) is not possible
today and is NOT sketched as a real code path here: it is ycappuccino-remote's job, once its
typed, peer-authenticated dispatch design lands
(remote/docs/superpowers/specs/2026-09-16-transparent-rpc-design.md, plan written at
remote/docs/superpowers/plans/2026-09-16-transparent-rpc.md, not yet implemented). Until then, this
stays a single-process tool.

Creating a user is three chained screens, not one: create_login.yml (a Python service call to
CreateLoginService -- the only safe way to set a hashed password, see that service's docstring),
account.yml (a CRUD create of the profile that references it), then role_account.yml (grants that
account a role *within a tenant* -- see below). Same recipe AccountBootStrap follows in code for
the superadmin, just run interactively, one screen at a time; each step only continues if the
previous one actually created something. Neither of ui_shell's screens has any notion of the
others; this module is exactly the "generic loading + generic event wiring" ycappuccino-ui is
meant to be, plus the one bit of real chaining logic (decode the token, carry the subject) that
could not itself be expressed in a template.

Tenancy model (see permissions_app's own README, "Multi-tenant"): a Role/RolePermission is *not*
itself tied to one tenant -- "editor" or its rights are the same definition everywhere. A
RoleAccount is what actually scopes a grant to one organization (tenant); role_account.yml is that
screen. A role-independent-of-tenant grant (e.g. a global "admin") is not a special case in the
data model: pick the root organization ("system") when granting it -- OrganizationTree's own
descendant-inclusion filter (see README) already makes a subject scoped to the root see everything
below it, exactly how AccountBootStrap's own superadmin grant already works. Nothing new to build
for that "except the global role/permission" case; it falls out of the existing tree filter.

Login is local-only today (LoginService/JwtAuthentication, permissions_app's own accounts). A
pluggable external identity provider (OIDC/SAML/...) is a real, intentionally *not yet built*
direction: it would need its own IServiceEndpoint (or IAuthentication) implementation on the
backend and, on this frontend, a different kind of screen entirely -- a redirect/device-code flow
does not fit the "form with fields, one submit action" model ycappuccino-ui's Screen describes
today. Not sketched here as a stub to avoid a half-built abstraction; flagged for when it is
actually taken on.
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
        """runs the login screen alone, keeping the decoded subject for the screens below;
        returns whether login actually happened (False if the screen was closed without one)"""
        transport = ServiceEndpointTransport(self._endpoint)
        login_app = ScreenApp(load_login_screen(), transport)
        login_app.run()
        if login_app.last_result is None:
            return False
        self._subject = jwt_codec.decode(login_app.last_result["token"], self._key)
        return True

    def run(self) -> None:
        """log in, then change the password -- the original two-screen flow"""
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
        """scopes an existing role to an account within a tenant (organization) -- pick the root
        organization ("system") to grant a role that should apply everywhere, see this module's
        docstring, "Tenancy model": nothing tenant-specific lives on Role/RolePermission itself."""
        self._run_crud_screen(load_role_account_screen())

    def create_user(self) -> None:
        """chained like run(): credentials (create_login, hashed), then profile (account), then
        tenant grant (role_account) -- the same three records AccountBootStrap creates by hand for
        the superadmin. Each step only continues if the previous one actually created something."""
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
