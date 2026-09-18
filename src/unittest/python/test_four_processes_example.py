"""
example/four_processes, end to end, from its own configuration files (only the ports are changed). Storage,
use cases, HTTP adapter and web front run as real subprocesses; this test plays the browser:

- the web front serves the page configuration, whose API is the HTTP adapter, which allows its origin;
- against the HTTP adapter: discovery, CORS preflight, sign-in through the ILoginService proxy, a role created
  through ICrud, a login created through IServiceEndpoint (forwarded to the use cases), an anonymous call
  refused;
- a call signed as the use cases then reads the role and the login straight from the storage process.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from ycappuccino.core.testing import wait_until
from ycappuccino.remote._http import call_peer

EXAMPLE = Path(__file__).resolve().parents[3] / "example" / "four_processes"
PORTS = {"8301": "18186", "8302": "18187", "8303": "18188", "8304": "18189"}
API = f"http://localhost:{PORTS['8303']}/api"
WEB = f"http://localhost:{PORTS['8304']}"
DISPATCH = f"{API}/services/__remote_dispatch__"


def _copy_process(name: str, root: str) -> str:
    """the example's process directory under root, its ports replaced by the test ones"""
    target = os.path.join(root, name)
    shutil.copytree(EXAMPLE / name, target, ignore=shutil.ignore_patterns("data", "site", "__pycache__"))
    for directory, _, files in os.walk(target):
        for file_name in files:
            if file_name.endswith((".yml", ".properties", ".json")):
                path = Path(directory, file_name)
                text = path.read_text(encoding="utf-8")
                for example_port, test_port in PORTS.items():
                    text = text.replace(example_port, test_port)
                path.write_text(text, encoding="utf-8")
    return target


def _http(method: str, url: str, body=None, headers=None) -> tuple[int, dict, dict]:
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(url, data=data, method=method, headers={"Content-Type": "application/json", **(headers or {})})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            content = response.read()
            return response.status, _lowered(response.headers), json.loads(content) if content else {}
    except urllib.error.HTTPError as error:
        with error:
            content = error.read()
            try:
                payload = json.loads(content) if content else {}
            except ValueError:
                payload = {}
            return error.code, _lowered(error.headers), payload
    except (urllib.error.URLError, ConnectionError):
        return 0, {}, {}


def _lowered(headers) -> dict:
    """header names are case-insensitive"""
    return {name.lower(): value for name, value in headers.items()}


def _dispatch(interface: str, method: str, kwargs: dict, token: str | None = None) -> tuple[int, dict, dict]:
    headers = {"Origin": WEB}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return _http("POST", f"{DISPATCH}/{interface}/{method}", {"kwargs": kwargs}, headers)


def _public_interfaces() -> set:
    status, _, payload = _http("GET", f"{API}/services/__remote_capabilities__")
    if status != 200:
        return set()
    return {path for component in payload["data"].get("components", []) for path in component["provides"]}


def _secret() -> str:
    for line in (EXAMPLE / "usecases" / "conf" / "application.yml").read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("secret:"):
            return line.split(":", 1)[1].strip().strip('"')
    raise AssertionError("no shared secret in the use cases configuration")


LOGIN = "ycappuccino.api.permissions.ILoginService"
CRUD = "ycappuccino.api.endpoints_storage.ICrud"
SERVICES = "ycappuccino.api.endpoints_service.IServiceEndpoint"


class TestFourProcessesExample(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.root = tempfile.mkdtemp(prefix="four-processes-")
        cls.addClassCleanup(shutil.rmtree, cls.root, True)
        for name in ("storage", "usecases", "http", "web"):
            directory = _copy_process(name, cls.root)
            if name == "web":
                os.makedirs(os.path.join(directory, "site"))
                shutil.copy(os.path.join(directory, "ycappuccino.json"), os.path.join(directory, "site"))
            process = subprocess.Popen(
                [sys.executable, "-m", "ycappuccino.core.runner", "--root_path", "."],
                cwd=directory, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            cls.addClassCleanup(process.wait, 10)
            cls.addClassCleanup(process.terminate)
        if not wait_until(lambda: {LOGIN, CRUD, SERVICES} <= _public_interfaces(), timeout=90):
            raise RuntimeError("the HTTP adapter never exposed the use cases' interfaces")
        status, _, payload = _dispatch(LOGIN, "login", {"login": "admin", "password": "admin"})
        if status != 200:
            raise RuntimeError(f"admin could not sign in: {status} {payload}")
        cls.token = payload["data"]["result"]

    def test_the_web_front_serves_a_page_configured_for_the_http_adapter_which_allows_it(self):
        status, _, configuration = _http("GET", f"{WEB}/ycappuccino.json")

        self.assertEqual(status, 200)
        self.assertEqual(configuration["properties"]["client.base_url"], API)
        http = (EXAMPLE / "http" / "conf" / "application.yml").read_text(encoding="utf-8")
        self.assertIn('allowed_origins: "http://localhost:8304"', http)

    def test_the_preflight_of_the_web_front_is_allowed(self):
        status, headers, _ = _http("OPTIONS", f"{DISPATCH}/{CRUD}/create", headers={
            "Origin": WEB, "Access-Control-Request-Method": "POST",
        })

        self.assertEqual(status, 204)
        self.assertEqual(headers.get("access-control-allow-origin"), WEB)

    def test_a_user_call_goes_http_adapter_to_use_cases_to_storage(self):
        status, headers, _ = _dispatch(CRUD, "create", {"item_id": "role", "fields": {"name": "four-processes-editor"}}, self.token)
        self.assertEqual(status, 200)
        self.assertEqual(headers.get("access-control-allow-origin"), WEB)

        status, _, _ = _dispatch(SERVICES, "call", {
            "name": "create_login", "method": "POST", "extra_path": [], "params": {},
            "body": {"login": "four-processes-bob", "password": "secret"},
        }, self.token)
        self.assertEqual(status, 200)

        storage = {"_id": "storage", "scheme": "http", "host": "localhost", "port": int(PORTS["8301"]), "secret": _secret()}
        roles = call_peer(storage, "__remote_dispatch__", "POST", ("ycappuccino.api.storage.IStorage", "get_many"), None,
                          {"kwargs": {"collection": "roles", "query": {"name": "four-processes-editor"}}}, local_peer_id="usecases")
        logins = call_peer(storage, "__remote_dispatch__", "POST", ("ycappuccino.api.storage.IStorage", "get_one"), None,
                           {"kwargs": {"collection": "logins", "query": {"_id": "four-processes-bob"}}}, local_peer_id="usecases")
        self.assertEqual([role["name"] for role in roles.body["result"]], ["four-processes-editor"])
        self.assertEqual(logins.body["result"]["login"], "four-processes-bob")

    def test_the_admin_lists_the_system_records_created_at_bootstrap(self):
        status, _, payload = _dispatch(CRUD, "get_many", {"item_id": "role"}, self.token)

        self.assertEqual(status, 200)
        self.assertIn("superadmin", [role["_id"] for role in payload["data"]["result"]["items"]])

    def test_an_anonymous_call_is_refused(self):
        status, _, _ = _dispatch(CRUD, "get_many", {"item_id": "role"})

        self.assertEqual(status, 401)


if __name__ == "__main__":
    unittest.main()
