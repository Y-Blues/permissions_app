"""Boots permissions_app and hands control to FrontendShell.run_menu(). Login: superadmin / demo."""

import os

from ycappuccino.core.framework import Framework

_HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    framework = Framework.get_framework()
    framework.init(os.path.join(_HERE, "conf", "application.yml"))
    try:
        shell = framework.context.get_service(framework.context.get_service_reference("FrontendShell"))
        shell.run_menu()
    finally:
        framework.stop()


if __name__ == "__main__":
    main()
