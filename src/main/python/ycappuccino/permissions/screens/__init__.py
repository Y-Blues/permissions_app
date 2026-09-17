"""
The admin console's screens, YAML templates shared by the terminal (frontend_shell) and the browser
(frontend_web) consoles. Their endpoints name what the console wires them to: login is ILoginService's
login method (ComponentTransport), change_password and create_login are exposed services
(ServiceEndpointTransport), the others CRUD items (CrudTransport).
"""

from pathlib import Path

from ycappuccino.ui.loader import load_screen_yaml
from ycappuccino.ui.model import Screen

_SCREENS_DIR = Path(__file__).parent


def _load(name: str) -> Screen:
    return load_screen_yaml((_SCREENS_DIR / f"{name}.yml").read_text(encoding="utf-8"))


def load_login_screen() -> Screen:
    return _load("login")


def load_change_password_screen() -> Screen:
    return _load("change_password")


def load_organization_screen() -> Screen:
    return _load("organization")


def load_role_screen() -> Screen:
    return _load("role")


def load_role_permission_screen() -> Screen:
    return _load("role_permission")


def load_create_login_screen() -> Screen:
    return _load("create_login")


def load_account_screen() -> Screen:
    return _load("account")


def load_role_account_screen() -> Screen:
    return _load("role_account")
