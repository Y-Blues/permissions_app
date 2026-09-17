"""Starts the frontend process and hands control to FrontendShell.run_menu() once its backend proxies exist."""

import logging
import os
import sys
import time

from ycappuccino.core.framework import Framework

_HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    # the console draws on this terminal (textual writes to stderr): logs go to a file, never over it
    logs = os.path.join(_HERE, "..", "logs")
    os.makedirs(logs, exist_ok=True)
    logging.basicConfig(filename=os.path.join(logs, "frontend.log"), level=logging.INFO)
    framework = Framework.get_framework()
    framework.init(os.path.join(_HERE, "conf", "application.yml"))
    try:
        deadline = time.time() + 120
        while framework.context.get_service_reference("FrontendShell") is None:
            if time.time() > deadline:
                sys.exit("no backend reached on http://localhost:8202: is ./run.sh running the other two processes?")
            time.sleep(0.5)
        shell = framework.context.get_service(framework.context.get_service_reference("FrontendShell"))
        shell.run_menu()
    finally:
        framework.stop()


if __name__ == "__main__":
    main()
