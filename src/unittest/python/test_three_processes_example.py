"""
example/three_processes, end to end, from its own configuration files (only the ports are changed):

- the storage process (MemoryStorage) and the backend process (Manager, use cases, permissions, HTTP) run as
  real subprocesses, the backend's IStorage being a proxy to the storage process;
- the frontend runs here, its FrontendShell getting ILoginService, IServiceEndpoint and ICrud as proxies to the
  backend, and its real textual console is driven: sign in as admin / admin, create a role;
- a call signed as the backend then reads that role straight from the storage process's IStorage.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from textual.widgets import Label, Select

from ycappuccino.core.framework import Framework
from ycappuccino.core.testing import wait_until
from ycappuccino.permissions.screens import load_application
from ycappuccino.remote._http import call_peer

EXAMPLE = Path(__file__).resolve().parents[3] / "example" / "three_processes"
PORTS = {"8201": "18184", "8202": "18185"}


def _copy_process(name: str, root: str) -> str:
    """the example's process directory under root, its ports replaced by the test ones"""
    target = os.path.join(root, name)
    shutil.copytree(EXAMPLE / name, target, ignore=shutil.ignore_patterns("data", "__pycache__"))
    for directory, _, files in os.walk(target):
        for file_name in files:
            path = os.path.join(directory, file_name)
            if file_name.endswith((".yml", ".properties", ".py")):
                text = Path(path).read_text(encoding="utf-8")
                for example_port, test_port in PORTS.items():
                    text = text.replace(example_port, test_port)
                Path(path).write_text(text, encoding="utf-8")
    return target


def _start(directory: str) -> subprocess.Popen:
    return subprocess.Popen(
        [sys.executable, "-m", "ycappuccino.core.runner", "--root_path", "."],
        cwd=directory, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


def _backend_signs_in() -> bool:
    request = urllib.request.Request(
        f"http://localhost:{PORTS['8202']}/api/services/login",
        data=json.dumps({"login": "admin", "password": "admin"}).encode(), method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=2) as response:
            return response.status == 200
    except (urllib.error.URLError, ConnectionError):
        return False


def _secret() -> str:
    for line in (EXAMPLE / "backend" / "conf" / "application.yml").read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("secret:"):
            return line.split(":", 1)[1].strip().strip('"')
    raise AssertionError("no shared secret in the backend configuration")


class TestThreeProcessesExample(unittest.IsolatedAsyncioTestCase):

    @classmethod
    def setUpClass(cls):
        cls.root = tempfile.mkdtemp(prefix="three-processes-")
        cls.addClassCleanup(shutil.rmtree, cls.root, True)
        cls.processes = []
        for name in ("storage", "backend"):
            process = _start(_copy_process(name, cls.root))
            cls.processes.append(process)
            cls.addClassCleanup(process.wait, 10)
            cls.addClassCleanup(process.terminate)
        if not wait_until(_backend_signs_in, timeout=60):
            raise RuntimeError("the backend never signed admin in: its storage proxy did not come up")

        frontend = _copy_process("frontend", cls.root)
        cls.previous_cwd = os.getcwd()
        os.chdir(frontend)
        cls.addClassCleanup(os.chdir, cls.previous_cwd)
        sys.path.insert(0, frontend)
        cls.framework = Framework()
        cls.framework.init(os.path.join(frontend, "conf", "application.yml"))
        cls.addClassCleanup(cls.framework.stop)
        if not wait_until(lambda: cls.framework.context.get_service_reference("FrontendShell"), timeout=60):
            raise RuntimeError("FrontendShell never got its backend proxies")
        shell = cls.framework.context.get_service(cls.framework.context.get_service_reference("FrontendShell"))
        cls.shell = object.__getattribute__(shell, "_obj")

    async def test_the_console_signs_in_and_the_role_it_creates_lands_in_the_storage_process(self):
        app = self.shell.application()
        async with app.run_test(size=(100, 30)) as pilot:
            await pilot.pause()
            app.query_one("#field-login").value = "admin"
            app.query_one("#field-password").value = "admin"
            await pilot.click("#action-submit")
            await wait_for(pilot, lambda: app.query_one("#nav").display)
            self.assertEqual(str(app.query_one("#user", Label).content), "admin")

            sections = [group.label for group in load_application().menu]
            menu = app.query_one(f"#menu-{sections.index('Roles and permissions')}", Select)
            menu.value = 0  # Create a role
            await wait_for(pilot, lambda: len(app.query("#field-name")) == 1)
            app.query_one("#field-name").value = "three-processes-editor"
            await pilot.click("#action-submit")
            await wait_for(pilot, lambda: len(app.query("#message")) == 1)
            self.assertEqual(str(app.query_one("#message", Label).content), "Saved.")

        storage = {"_id": "storage", "scheme": "http", "host": "localhost", "port": int(PORTS["8201"]), "secret": _secret()}
        result = call_peer(
            storage, "__remote_dispatch__", "POST", ("ycappuccino.api.storage.IStorage", "get_many"), None,
            {"kwargs": {"collection": "roles", "query": {"name": "three-processes-editor"}}},
            local_peer_id="backend",
        )
        self.assertEqual([role["name"] for role in result.body["result"]], ["three-processes-editor"])


async def wait_for(pilot, condition, timeout: float = 20.0) -> None:
    deadline = time.time() + timeout
    while not condition():
        if time.time() > deadline:
            raise AssertionError("condition not met in time")
        await pilot.pause(0.1)


if __name__ == "__main__":
    unittest.main()
