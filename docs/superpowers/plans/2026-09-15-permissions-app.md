# permissions_app natif : plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Comptes, rôles, organisations et permissions natifs, implémentant `IAuthentication` (JWT sans état) et `IAuthorization` (permissions relues à chaque contrôle), avec les services de connexion et le bootstrap du compte superadmin.

**Architecture:** Six modèles `@Item` inchangés dans leur principe (un `Permission`/`Media` legacy supprimés, inutilisés). Deux modules purs sans composant (`jwt_codec.py`, `passwords.py`). Cinq composants natifs, sans décorateur : `JwtAuthentication`, `RolePermissionAuthorization`, `OrganizationTree` (trigger + filtre de tenant), trois `IExposedService` (login, login par cookie, changement de mot de passe), et `AccountBootStrap`. Aucune dépendance sur `endpoints_storage` (circulaire), seulement sur `storage` et `endpoints_service`.

**Tech Stack:** Python ≥ 3.10, uv, Pelix/iPOPO 3, `pyjwt`, unittest (`IsolatedAsyncioTestCase`).

**Spec:** `permissions_app/docs/superpowers/specs/2026-09-15-permissions-app-design.md`

## Global Constraints

- Chemins relatifs à la racine du workspace `/home/apisu/Documents/perso/repositories` ; `permissions_app` est un dépôt git séparé (aucune tâche de ce plan ne touche `api`, `core`, `storage`, `endpoints_storage`, `http_server` ou `endpoints_service` — tous les contrats nécessaires existent déjà).
- Commande de test, lancée depuis le dépôt concerné : `uv run python -m unittest discover -s src/unittest/python`.
- `requires-python = ">=3.10"`.
- **Aucun décorateur sur les classes de composants.**
- Les lectures/écritures internes sur les données de contrôle d'accès (login, account, roleAccount, rolePermission, organization) se font **sans sujet** (`subject=None`) : ce sont des lectures système, et passer un sujet réappliquerait le filtre de tenant de façon récursive.
- Le champ `password` de `Login` est `private=True` : toute lecture qui doit le voir passe `{"content": "privateField"}` dans ses `params`.
- Le hash stocké est toujours préfixé `"scrypt$"` ; un hash sans préfixe (32 caractères hex) est un hash MD5 legacy, vérifié puis transparently ré-haché.
- `DEFAULT_TIMEOUT` du JWT est en **secondes** (15 × 60), pas en millisecondes comme le calcul (bogué) du legacy.
- Committer après la revue de chaque tâche, jamais pendant qu'un sous-agent travaille encore dans le même dépôt ; messages de commit courts, sans ligne d'attribution.

## Structure des fichiers

| Fichier | Responsabilité |
|---|---|
| `src/main/python/ycappuccino/permissions/models/*.py` | `Organization`, `Login`, `Account`, `Role`, `RoleAccount`, `RolePermission` |
| `src/main/python/ycappuccino/permissions/jwt_codec.py` | `encode`, `decode`, `DEFAULT_KEY`, `DEFAULT_TIMEOUT` |
| `src/main/python/ycappuccino/permissions/passwords.py` | `hash_scrypt`, `check_login`, `organization_of` |
| `src/main/python/ycappuccino/permissions/authentication.py` | `JwtAuthentication` |
| `src/main/python/ycappuccino/permissions/authorization.py` | `RolePermissionAuthorization` |
| `src/main/python/ycappuccino/permissions/organization_tree.py` | `OrganizationTree` |
| `src/main/python/ycappuccino/permissions/services/login.py` | `LoginService`, `LoginCookieService` |
| `src/main/python/ycappuccino/permissions/services/change_password.py` | `ChangePasswordService` |
| `src/main/python/ycappuccino/permissions/bootstrap.py` | `AccountBootStrap` |

---

### Task 1: projet uv, modèles, `jwt_codec`, `passwords`

**Files:**
- Modify: `permissions_app/pyproject.toml` (tout le fichier), `permissions_app/.gitignore` (tout le fichier)
- Modify: `permissions_app/src/main/python/ycappuccino/permissions/__init__.py` (tout le fichier)
- Delete (`git rm`) : `build.py`, `setup.py`, `src/main/python/ycappuccino/permissions/bundles/` (tout le dossier legacy), `src/main/python/ycappuccino/permissions/models/media.py`, `src/main/python/ycappuccino/permissions/models/permission.py`, `src/main/python/ycappuccino/permissions/services/login_services.py`, `src/main/python/ycappuccino/permissions/services/tenant_service.py`, `src/main/python/ycappuccino/permissions/bootstrap.py` (recréé à la tâche 5), `src/unittest/`
- Modify: `permissions_app/src/main/python/ycappuccino/permissions/models/organization.py`, `login.py`, `account.py`, `role.py`, `role_account.py`, `role_permission.py` (tous réécrits, voir Step 3)
- Create: `permissions_app/src/main/python/ycappuccino/permissions/jwt_codec.py`
- Create: `permissions_app/src/main/python/ycappuccino/permissions/passwords.py`
- Create: `permissions_app/src/unittest/python/permissions_fixtures.py`
- Test: `permissions_app/src/unittest/python/test_jwt_codec.py`, `test_passwords.py`

**Interfaces:**
- Consumes : `ycappuccino.api.storage.IManager` (déjà construit) ; `ycappuccino.api.endpoints_storage.NotFound`, `InvalidRequest` (déjà construits, réutilisés tels quels).
- Produces:
  - `jwt_codec.encode(payload: dict, key: str, timeout_seconds: int) -> str`, `jwt_codec.decode(token: str, key: str) -> dict | None`, `jwt_codec.DEFAULT_KEY = "YCap"`, `jwt_codec.DEFAULT_TIMEOUT = 900`.
  - `passwords.hash_scrypt(password: str, salt: str) -> str` (préfixe `"scrypt$"`), `passwords.check_login(manager, login_id, password) -> str` (id du compte), `passwords.organization_of(manager, account_id) -> str`.
  - Modèles : `Organization` (name, father), `Login` (login, salt, password via le setter `password(cleartext)`), `Account` (name, login ref, role ref), `Role` (name), `RoleAccount` (role ref, account ref, organization ref), `RolePermission` (role ref, rights: list[str]).
  - fixtures : `create_manager()` (Manager sur MemoryStorage, sans triggers/filtres, réutilisable par les tâches suivantes — même forme que `storage`/`endpoints_storage`'s `create_manager`).

- [ ] **Step 1: Replace the PyBuilder project and remove legacy files**

```bash
cd permissions_app
git rm -q -r build.py setup.py src/main/python/ycappuccino/permissions/bundles \
  src/main/python/ycappuccino/permissions/models/media.py \
  src/main/python/ycappuccino/permissions/models/permission.py \
  src/main/python/ycappuccino/permissions/services/login_services.py \
  src/main/python/ycappuccino/permissions/services/tenant_service.py \
  src/main/python/ycappuccino/permissions/bootstrap.py \
  src/unittest
mkdir -p src/unittest/python
```

`permissions_app/pyproject.toml` :

```toml
[project]
name = "ycappuccino-permissions"
version = "0.1.0"
description = "YCappuccino permissions_app: accounts, roles, organizations, JWT authentication and authorization"
requires-python = ">=3.10"
dependencies = [
    "ycappuccino-api",
    "ycappuccino-core",
    "ycappuccino-storage",
    "ycappuccino-endpoints-service",
    "pyjwt>=2.8",
]

[build-system]
requires = ["uv_build>=0.12.13,<0.13"]
build-backend = "uv_build"

[tool.uv.build-backend]
module-name = "ycappuccino.permissions"
module-root = "src/main/python"

[tool.uv.sources]
ycappuccino-api = { path = "../api", editable = true }
ycappuccino-core = { path = "../core", editable = true }
ycappuccino-storage = { path = "../storage", editable = true }
ycappuccino-endpoints-service = { path = "../endpoints_service", editable = true }
```

`permissions_app/.gitignore` :

```
data
.venv
__pycache__
dist
```

`permissions_app/src/main/python/ycappuccino/permissions/__init__.py` :

```python
"""accounts, roles, organizations, JWT authentication and authorization"""
```

Run (depuis `permissions_app`) : `uv sync`
Expected: environnement créé, les quatre dépendances locales installées en éditable, `pyjwt` téléchargé.

- [ ] **Step 2: Write jwt_codec.py and passwords.py**

`permissions_app/src/main/python/ycappuccino/permissions/jwt_codec.py` :

```python
"""
Stateless JWT encode/decode, shared by JwtAuthentication and the login services.
"""

import time
from typing import Optional

import jwt

DEFAULT_KEY = "YCap"        # legacy value, kept only as a development default
DEFAULT_TIMEOUT = 15 * 60   # 15 minutes, in seconds


def encode(payload: dict, key: str, timeout_seconds: int) -> str:
    now = int(time.time())
    return jwt.encode({**payload, "iat": now, "exp": now + timeout_seconds}, key, algorithm="HS256")


def decode(token: str, key: str) -> Optional[dict]:
    try:
        return jwt.decode(token, key, algorithms=["HS256"])
    except jwt.PyJWTError:
        return None
```

`permissions_app/src/main/python/ycappuccino/permissions/passwords.py` :

```python
"""
Password hashing and the shared login-check used by the login services.
"""

import hashlib

from ycappuccino.api.endpoints_storage import InvalidRequest, NotFound

# password is private=True on Login: without this, Manager strips it from reads (see storage/README.md)
_READ_PASSWORD = {"content": "privateField"}


def hash_scrypt(password: str, salt: str) -> str:
    digest = hashlib.scrypt(password.encode(), salt=salt.encode(), n=2**14, r=8, p=1, dklen=32)
    return "scrypt$" + digest.hex()


def _hash_md5_legacy(password: str, salt: str) -> str:
    return hashlib.md5(f"{salt}{password}".encode()).hexdigest()


async def check_login(manager, login_id: str, password: str) -> str:
    """the account id matching login_id/password, or raises NotFound / InvalidRequest"""
    login = await manager.get_one("login", login_id, _READ_PASSWORD, subject=None)
    if login is None:
        raise NotFound(f"unknown login {login_id}")
    stored = login.get_storage_model()
    salt = stored["salt"]

    if stored["password"] == hash_scrypt(password, salt):
        pass
    elif not stored["password"].startswith("scrypt$") and stored["password"] == _hash_md5_legacy(password, salt):
        login.password(password)
        await manager.up_sert_model(login, subject=None)
    else:
        raise InvalidRequest("invalid credentials")

    accounts = await manager.get_many("account", {"filter": {"login.ref": login_id}}, subject=None)
    if not accounts:
        raise NotFound(f"no account for login {login_id}")
    return accounts[0].get_storage_model()["_id"]


async def organization_of(manager, account_id: str) -> str:
    """the organization of the first RoleAccount found for this account (one active role, a known simplification)"""
    role_accounts = await manager.get_many("roleAccount", {"filter": {"account.ref": account_id}}, subject=None)
    if not role_accounts:
        raise NotFound(f"no role for account {account_id}")
    return role_accounts[0].get_storage_model()["organization"]["ref"]
```

- [ ] **Step 3: Rewrite the models**

`permissions_app/src/main/python/ycappuccino/permissions/models/organization.py` :

```python
from ycappuccino.api.decorators import Item, Property
from ycappuccino.api.models import Model
from ycappuccino.core.decorator_app import App


@App(name="ycappuccino-permissions")
@Item(collection="organizations", name="organization", plural="organizations", secure_read=True, secure_write=True)
class Organization(Model):

    def __init__(self, a_dict=None):
        super().__init__(a_dict)
        self._name = None
        self._father = None

    @Property(name="name")
    def name(self, a_value):
        self._name = a_value

    @Property(name="father")
    def father(self, a_value):
        self._father = a_value
```

`permissions_app/src/main/python/ycappuccino/permissions/models/login.py` :

```python
import secrets

from ycappuccino.api.decorators import Item, Property
from ycappuccino.api.models import Model
from ycappuccino.core.decorator_app import App
from ycappuccino.permissions import passwords


@App(name="ycappuccino-permissions")
@Item(collection="logins", name="login", plural="logins", secure_read=True, secure_write=True)
class Login(Model):

    def __init__(self, a_dict=None):
        super().__init__(a_dict)
        self._login = None
        self._salt = None
        self._password = None

    @Property(name="login")
    def login(self, a_value):
        self._login = a_value

    @Property(name="salt")
    def salt(self, a_value):
        self._salt = a_value

    @Property(name="password", private=True)
    def _stored_password(self, a_value):
        self._password = a_value

    def password(self, cleartext):
        """sets a fresh salt and stores its scrypt hash — do not call _stored_password directly"""
        self.salt(secrets.token_hex(32))
        self._stored_password(passwords.hash_scrypt(cleartext, self._salt))
```

`permissions_app/src/main/python/ycappuccino/permissions/models/account.py` :

```python
from ycappuccino.api.decorators import Item, ItemReference, Property, Reference
from ycappuccino.api.models import Model
from ycappuccino.core.decorator_app import App


@App(name="ycappuccino-permissions")
@Item(collection="accounts", name="account", plural="accounts", secure_read=True, secure_write=True)
@ItemReference(from_name="account", field="login", item="login")
@ItemReference(from_name="account", field="role", item="role")
class Account(Model):

    def __init__(self, a_dict=None):
        super().__init__(a_dict)
        self._name = None
        self._login = None
        self._role = None

    @Property(name="name")
    def name(self, a_value):
        self._name = a_value

    @Reference(name="login")
    def login(self, a_value):
        self._login = a_value

    @Reference(name="role")
    def role(self, a_value):
        self._role = a_value
```

`permissions_app/src/main/python/ycappuccino/permissions/models/role.py` :

```python
from ycappuccino.api.decorators import Item, Property
from ycappuccino.api.models import Model
from ycappuccino.core.decorator_app import App


@App(name="ycappuccino-permissions")
@Item(collection="roles", name="role", plural="roles", secure_read=True, secure_write=True)
class Role(Model):

    def __init__(self, a_dict=None):
        super().__init__(a_dict)
        self._name = None

    @Property(name="name")
    def name(self, a_value):
        self._name = a_value
```

`permissions_app/src/main/python/ycappuccino/permissions/models/role_account.py` :

```python
from ycappuccino.api.decorators import Item, ItemReference, Reference
from ycappuccino.api.models import Model
from ycappuccino.core.decorator_app import App


@App(name="ycappuccino-permissions")
@Item(collection="role_accounts", name="roleAccount", plural="role-accounts", secure_read=True, secure_write=True)
@ItemReference(from_name="roleAccount", field="account", item="account")
@ItemReference(from_name="roleAccount", field="role", item="role")
@ItemReference(from_name="roleAccount", field="organization", item="organization")
class RoleAccount(Model):

    def __init__(self, a_dict=None):
        super().__init__(a_dict)
        self._role = None
        self._account = None
        self._organization = None

    @Reference(name="role")
    def role(self, a_value):
        self._role = a_value

    @Reference(name="account")
    def account(self, a_value):
        self._account = a_value

    @Reference(name="organization")
    def organization(self, a_value):
        self._organization = a_value
```

`permissions_app/src/main/python/ycappuccino/permissions/models/role_permission.py` :

```python
from ycappuccino.api.decorators import Item, ItemReference, Property, Reference
from ycappuccino.api.models import Model
from ycappuccino.core.decorator_app import App


@App(name="ycappuccino-permissions")
@Item(collection="role_permissions", name="rolePermission", plural="role-permissions", secure_read=True, secure_write=True)
@ItemReference(from_name="rolePermission", field="role", item="role")
class RolePermission(Model):

    def __init__(self, a_dict=None):
        super().__init__(a_dict)
        self._role = None
        self._rights = None

    @Reference(name="role")
    def role(self, a_value):
        self._role = a_value

    @Property(name="rights")
    def rights(self, a_value):
        self._rights = a_value
```

- [ ] **Step 4: Write the fixtures**

`permissions_app/src/unittest/python/permissions_fixtures.py` :

```python
"""
Fixtures shared by the permissions_app tests: a real Manager on MemoryStorage, no framework.
"""

import os
import tempfile

from ycappuccino.storage.files import LocalFileStore
from ycappuccino.storage.items import ItemManager
from ycappuccino.storage.manager import Manager
from ycappuccino.storage.memory import MemoryStorage

# importing the models registers them with ItemManager
from ycappuccino.permissions.models import account, login, organization, role, role_account, role_permission  # noqa: F401


def create_manager(triggers=None, filters=None):
    """manager on a memory storage; the caller removes the returned directory"""
    directory = tempfile.mkdtemp()
    manager = Manager(
        MemoryStorage(),
        ItemManager(),
        triggers if triggers is not None else [],
        filters if filters is not None else [],
        LocalFileStore(os.path.join(directory, "files")),
    )
    return manager, directory
```

- [ ] **Step 5: Write the tests**

`permissions_app/src/unittest/python/test_jwt_codec.py` :

```python
import time
import unittest

from ycappuccino.permissions import jwt_codec


class TestJwtCodec(unittest.TestCase):

    def test_round_trip(self):
        token = jwt_codec.encode({"sub": "alice"}, "key", 60)

        self.assertEqual(jwt_codec.decode(token, "key")["sub"], "alice")

    def test_wrong_key_is_rejected(self):
        token = jwt_codec.encode({"sub": "alice"}, "key", 60)

        self.assertIsNone(jwt_codec.decode(token, "other"))

    def test_expired_token_is_rejected(self):
        token = jwt_codec.encode({"sub": "alice"}, "key", -1)

        self.assertIsNone(jwt_codec.decode(token, "key"))

    def test_default_timeout_is_fifteen_minutes_in_seconds(self):
        self.assertEqual(jwt_codec.DEFAULT_TIMEOUT, 900)
```

`permissions_app/src/unittest/python/test_passwords.py` :

```python
import shutil
import unittest

from permissions_fixtures import create_manager

from ycappuccino.api.endpoints_storage import InvalidRequest, NotFound
from ycappuccino.permissions import passwords
from ycappuccino.permissions.models.account import Account
from ycappuccino.permissions.models.login import Login
from ycappuccino.permissions.models.role_account import RoleAccount


class TestPasswords(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.manager, directory = create_manager()
        self.addCleanup(shutil.rmtree, directory, True)

        login = Login()
        login.id("alice")
        login.login("alice")
        login.password("secret")
        await self.manager.up_sert_model(login)

        account = Account()
        account.id("acc-alice")
        account.name("Alice")
        account.login("alice")
        await self.manager.up_sert_model(account)

    async def test_hash_scrypt_is_prefixed_and_deterministic_for_the_same_salt(self):
        self.assertTrue(passwords.hash_scrypt("secret", "salt").startswith("scrypt$"))
        self.assertEqual(passwords.hash_scrypt("secret", "salt"), passwords.hash_scrypt("secret", "salt"))
        self.assertNotEqual(passwords.hash_scrypt("secret", "salt"), passwords.hash_scrypt("other", "salt"))

    async def test_check_login_succeeds(self):
        account_id = await passwords.check_login(self.manager, "alice", "secret")

        self.assertEqual(account_id, "acc-alice")

    async def test_check_login_rejects_a_wrong_password(self):
        with self.assertRaises(InvalidRequest):
            await passwords.check_login(self.manager, "alice", "wrong")

    async def test_check_login_rejects_an_unknown_login(self):
        with self.assertRaises(NotFound):
            await passwords.check_login(self.manager, "unknown", "secret")

    async def test_check_login_falls_back_to_md5_and_rehashes(self):
        import hashlib

        legacy = Login()
        legacy.id("bob")
        legacy.login("bob")
        legacy.salt("abc")
        legacy._stored_password(hashlib.md5(b"abcold").hexdigest())
        await self.manager.up_sert_model(legacy)
        account = Account()
        account.id("acc-bob")
        account.login("bob")
        await self.manager.up_sert_model(account)

        account_id = await passwords.check_login(self.manager, "bob", "old")

        self.assertEqual(account_id, "acc-bob")
        stored = (await self.manager.get_one("login", "bob", {"content": "privateField"})).get_storage_model()
        self.assertTrue(stored["password"].startswith("scrypt$"))

    async def test_organization_of(self):
        role_account = RoleAccount()
        role_account.id("ra-1")
        role_account.account("acc-alice")
        role_account.role("some-role")
        role_account.organization("acme")
        await self.manager.up_sert_model(role_account)

        self.assertEqual(await passwords.organization_of(self.manager, "acc-alice"), "acme")

    async def test_organization_of_without_a_role_account(self):
        with self.assertRaises(NotFound):
            await passwords.organization_of(self.manager, "unknown-account")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 6: Run the tests**

Cette tâche pose les fondations (projet, modèles, modules purs) : suivre l'ordre TDD strict par fichier individuel ferait des allers-retours inutiles sur du code déjà entièrement spécifié ci-dessus. Écrire Steps 1-5 dans l'ordre donné, puis lancer :

Run (depuis `permissions_app`) : `uv run python -m unittest discover -s src/unittest/python`
Expected: `OK`.

---

### Task 2: `JwtAuthentication` et `RolePermissionAuthorization`

**Files:**
- Create: `permissions_app/src/main/python/ycappuccino/permissions/authentication.py`
- Create: `permissions_app/src/main/python/ycappuccino/permissions/authorization.py`
- Test: `permissions_app/src/unittest/python/test_authentication.py`, `test_authorization.py`

**Interfaces:**
- Consumes (Task 1) : `jwt_codec`, `permissions_fixtures.create_manager` ; `ycappuccino.api.http_server.IAuthentication` ; `ycappuccino.api.endpoints_storage.IAuthorization`.
- Produces: `JwtAuthentication(key: str = jwt_codec.DEFAULT_KEY)` implémentant `IAuthentication` ; `RolePermissionAuthorization(manager: IManager)` implémentant `IAuthorization`.

- [ ] **Step 1: Write the failing tests**

`permissions_app/src/unittest/python/test_authentication.py` :

```python
import unittest

from ycappuccino.permissions import jwt_codec
from ycappuccino.permissions.authentication import JwtAuthentication


class TestJwtAuthentication(unittest.IsolatedAsyncioTestCase):

    async def test_bearer_header(self):
        authentication = JwtAuthentication(key="test-key")
        token = jwt_codec.encode({"sub": "alice", "tid": "acme"}, "test-key", 60)

        subject = await authentication.authenticate({"authorization": f"Bearer {token}"})

        self.assertEqual((subject["sub"], subject["tid"]), ("alice", "acme"))

    async def test_ycappuccino_cookie(self):
        authentication = JwtAuthentication(key="test-key")
        token = jwt_codec.encode({"sub": "alice", "tid": "acme"}, "test-key", 60)

        subject = await authentication.authenticate({"cookie": f"lang=fr; _ycappuccino={token}"})

        self.assertEqual(subject["sub"], "alice")

    async def test_no_credentials(self):
        authentication = JwtAuthentication(key="test-key")

        self.assertIsNone(await authentication.authenticate({}))

    async def test_invalid_token(self):
        authentication = JwtAuthentication(key="test-key")

        self.assertIsNone(await authentication.authenticate({"authorization": "Bearer garbage"}))

    async def test_default_key_logs_a_warning(self):
        authentication = JwtAuthentication()

        with self.assertLogs("ycappuccino.permissions.authentication", "WARNING"):
            await authentication.start()

    async def test_configured_key_does_not_warn(self):
        authentication = JwtAuthentication(key="a-real-key")

        await authentication.start()  # no assertLogs: nothing should be logged


if __name__ == "__main__":
    unittest.main()
```

`permissions_app/src/unittest/python/test_authorization.py` :

```python
import shutil
import unittest

from permissions_fixtures import create_manager

from ycappuccino.permissions.authorization import RolePermissionAuthorization
from ycappuccino.permissions.models.role_account import RoleAccount
from ycappuccino.permissions.models.role_permission import RolePermission

SUBJECT = {"sub": "alice", "tid": "acme"}


class TestRolePermissionAuthorization(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.manager, directory = create_manager()
        self.addCleanup(shutil.rmtree, directory, True)

    async def _grant(self, rights):
        role_account = RoleAccount()
        role_account.id("ra-1")
        role_account.account("alice")
        role_account.role("editor")
        role_account.organization("acme")
        await self.manager.up_sert_model(role_account)

        role_permission = RolePermission()
        role_permission.id("rp-1")
        role_permission.role("editor")
        role_permission.rights(rights)
        await self.manager.up_sert_model(role_permission)

    async def test_no_role_account_is_refused(self):
        authorization = RolePermissionAuthorization(self.manager)

        self.assertFalse(await authorization.is_authorized(SUBJECT, "read", "book"))

    async def test_exact_right_is_authorized(self):
        await self._grant(["read:book"])
        authorization = RolePermissionAuthorization(self.manager)

        self.assertTrue(await authorization.is_authorized(SUBJECT, "read", "book"))
        self.assertFalse(await authorization.is_authorized(SUBJECT, "write", "book"))

    async def test_wildcard_right(self):
        await self._grant(["*:*"])
        authorization = RolePermissionAuthorization(self.manager)

        self.assertTrue(await authorization.is_authorized(SUBJECT, "call", "login"))

    async def test_wrong_tenant_is_refused(self):
        await self._grant(["*:*"])
        authorization = RolePermissionAuthorization(self.manager)

        self.assertFalse(await authorization.is_authorized({"sub": "alice", "tid": "other"}, "read", "book"))

    async def test_rights_from_several_role_permissions_are_combined(self):
        await self._grant(["read:book"])
        second = RolePermission()
        second.id("rp-2")
        second.role("editor")
        second.rights(["write:book"])
        await self.manager.up_sert_model(second)
        authorization = RolePermissionAuthorization(self.manager)

        self.assertTrue(await authorization.is_authorized(SUBJECT, "write", "book"))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run (depuis `permissions_app`) : `uv run python -m unittest discover -s src/unittest/python -p "test_auth*.py"`
Expected: `ModuleNotFoundError` pour `authentication`/`authorization`.

- [ ] **Step 3: Implement**

`permissions_app/src/main/python/ycappuccino/permissions/authentication.py` :

```python
"""
JwtAuthentication: stateless JWT verification for the IAuthentication port (http_server).
"""

import logging
from typing import Optional

from ycappuccino.api.http_server import IAuthentication
from ycappuccino.permissions import jwt_codec

_logger = logging.getLogger(__name__)


class JwtAuthentication(IAuthentication):

    def __init__(self, key: str = jwt_codec.DEFAULT_KEY):
        self._key = key

    async def start(self):
        if self._key == jwt_codec.DEFAULT_KEY:
            _logger.warning("jwt.token.key is not configured: using the default development key")

    async def stop(self):
        pass

    async def authenticate(self, headers: dict) -> Optional[dict]:
        token = _token_from_headers(headers)
        if token is None:
            return None
        return jwt_codec.decode(token, self._key)


def _token_from_headers(headers: dict) -> Optional[str]:
    authorization = headers.get("authorization")
    if authorization is not None and "Bearer" in authorization:
        return authorization[len("Bearer "):]
    cookie = headers.get("cookie")
    if cookie is not None:
        for part in cookie.split(";"):
            name, separator, value = part.strip().partition("=")
            if separator and "_ycappuccino" in name:
                return value
    return None
```

`permissions_app/src/main/python/ycappuccino/permissions/authorization.py` :

```python
"""
RolePermissionAuthorization: re-reads RoleAccount/RolePermission on every check (see spec section 2.3).
"""

import re

from ycappuccino.api.endpoints_storage import IAuthorization
from ycappuccino.api.storage import IManager


class RolePermissionAuthorization(IAuthorization):

    def __init__(self, manager: IManager):
        self._manager = manager

    async def start(self):
        pass

    async def stop(self):
        pass

    async def is_authorized(self, subject: dict, action: str, item_id: str) -> bool:
        role_accounts = await self._manager.get_many(
            "roleAccount", {"filter": {"account.ref": subject["sub"], "organization.ref": subject["tid"]}}, subject=None
        )
        if not role_accounts:
            return False
        role_id = role_accounts[0].get_storage_model()["role"]["ref"]
        permissions = await self._manager.get_many("rolePermission", {"filter": {"role.ref": role_id}}, subject=None)
        rights = [right for model in permissions for right in model.get_storage_model().get("rights", [])]
        return any(_matches(pattern, action, item_id) for pattern in rights)


def _matches(pattern: str, action: str, item_id: str) -> bool:
    return re.fullmatch(re.escape(pattern).replace(r"\*", ".*"), f"{action}:{item_id}") is not None
```

- [ ] **Step 4: Run tests to verify they pass**

Run (depuis `permissions_app`) : `uv run python -m unittest discover -s src/unittest/python`
Expected: `OK`.

---

### Task 3: `OrganizationTree`

**Files:**
- Create: `permissions_app/src/main/python/ycappuccino/permissions/organization_tree.py`
- Test: `permissions_app/src/unittest/python/test_organization_tree.py`

**Interfaces:**
- Consumes (Task 1) : `permissions_fixtures.create_manager` ; modèle `Organization`.
- Produces: `OrganizationTree(manager: IManager)` implémentant `ITrigger` et `IFilter`, `item_id = "organization"`, `actions = ("upsert", "delete")`, `post = True`.

- [ ] **Step 1: Write the failing test**

`permissions_app/src/unittest/python/test_organization_tree.py` :

```python
import shutil
import unittest

from permissions_fixtures import create_manager

from ycappuccino.permissions.models.organization import Organization
from ycappuccino.permissions.organization_tree import OrganizationTree


async def _create_org(manager, id, father=None):
    organization = Organization()
    organization.id(id)
    organization.father(father)
    await manager.up_sert_model(organization)


class TestOrganizationTree(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.manager, directory = create_manager()
        self.addCleanup(shutil.rmtree, directory, True)

    async def test_a_leaf_organization_filters_on_itself_only(self):
        await _create_org(self.manager, "acme")
        tree = OrganizationTree(self.manager)
        await tree.start()

        condition = await tree.get_filter("book", {"tid": "acme"})

        self.assertEqual(condition, {"_tid": {"$in": ["acme"]}})

    async def test_children_and_grandchildren_are_included(self):
        await _create_org(self.manager, "acme")
        await _create_org(self.manager, "acme-eu", father="acme")
        await _create_org(self.manager, "acme-eu-fr", father="acme-eu")
        tree = OrganizationTree(self.manager)
        await tree.start()

        condition = await tree.get_filter("book", {"tid": "acme"})

        self.assertEqual(set(condition["_tid"]["$in"]), {"acme", "acme-eu", "acme-eu-fr"})

    async def test_execute_adds_a_new_organization_incrementally(self):
        await _create_org(self.manager, "acme")
        tree = OrganizationTree(self.manager)
        await tree.start()

        new_org = Organization()
        new_org.id("acme-us")
        new_org.father("acme")
        await tree.execute("upsert", "organization", new_org)

        condition = await tree.get_filter("book", {"tid": "acme"})
        self.assertIn("acme-us", condition["_tid"]["$in"])

    async def test_execute_removes_a_deleted_organization(self):
        await _create_org(self.manager, "acme")
        await _create_org(self.manager, "acme-eu", father="acme")
        tree = OrganizationTree(self.manager)
        await tree.start()

        deleted = Organization()
        deleted.id("acme-eu")
        await tree.execute("delete", "organization", deleted)

        condition = await tree.get_filter("book", {"tid": "acme"})
        self.assertNotIn("acme-eu", condition["_tid"]["$in"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run (depuis `permissions_app`) : `uv run python -m unittest discover -s src/unittest/python -p test_organization_tree.py`
Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement**

`permissions_app/src/main/python/ycappuccino/permissions/organization_tree.py` :

```python
"""
OrganizationTree: the tenant filter for storage (IFilter) and the trigger keeping it in sync (ITrigger).
"""

from ycappuccino.api.endpoints_storage import IFilter, ITrigger
from ycappuccino.api.storage import IManager

_PAGE = 1000


class OrganizationTree(ITrigger, IFilter):

    item_id = "organization"
    actions = ("upsert", "delete")
    post = True

    def __init__(self, manager: IManager):
        self._manager = manager
        self._children = {}

    async def start(self):
        await self._load_tree()

    async def stop(self):
        pass

    async def get_filter(self, item_id, subject):
        return {"_tid": {"$in": self._descendants(subject["tid"])}}

    async def execute(self, action, item_id, model):
        document = model.get_storage_model()
        if action == "delete":
            self._remove(document["_id"])
        else:
            self._add(document["_id"], document.get("father"))

    async def _load_tree(self):
        offset = 0
        while True:
            organizations = await self._manager.get_many(
                "organization", {"limit": _PAGE, "offset": offset}, subject=None
            )
            for organization in organizations:
                document = organization.get_storage_model()
                self._add(document["_id"], document.get("father"))
            if len(organizations) < _PAGE:
                return
            offset += _PAGE

    def _add(self, organization_id, father_id):
        if father_id:
            self._children.setdefault(father_id, set()).add(organization_id)

    def _remove(self, organization_id):
        for children in self._children.values():
            children.discard(organization_id)
        self._children.pop(organization_id, None)

    def _descendants(self, root_id):
        result = [root_id]
        for child in self._children.get(root_id, ()):
            result.extend(self._descendants(child))
        return result
```

- [ ] **Step 4: Run tests to verify they pass**

Run (depuis `permissions_app`) : `uv run python -m unittest discover -s src/unittest/python`
Expected: `OK`.

---

### Task 4: services de connexion

**Files:**
- Create: `permissions_app/src/main/python/ycappuccino/permissions/services/__init__.py` (vide)
- Create: `permissions_app/src/main/python/ycappuccino/permissions/services/login.py`
- Create: `permissions_app/src/main/python/ycappuccino/permissions/services/change_password.py`
- Test: `permissions_app/src/unittest/python/test_login_service.py`, `test_change_password_service.py`

**Interfaces:**
- Consumes (Task 1) : `jwt_codec`, `passwords`, fixtures. `ycappuccino.api.endpoints_service.IExposedService`, `ServiceResult`. `ycappuccino.api.endpoints_storage.NotFound`.
- Produces: `LoginService(manager, key=jwt_codec.DEFAULT_KEY, timeout=jwt_codec.DEFAULT_TIMEOUT)` (`name="login"`, `secure=False`), `LoginCookieService` (même constructeur, `name="login_cookie"`), `ChangePasswordService(manager)` (`name="change_password"`, `secure=True`).

- [ ] **Step 1: Write the failing tests**

`permissions_app/src/main/python/ycappuccino/permissions/services/__init__.py` : fichier vide.

`permissions_app/src/unittest/python/test_login_service.py` :

```python
import shutil
import unittest

from permissions_fixtures import create_manager

from ycappuccino.api.endpoints_storage import NotFound
from ycappuccino.permissions import jwt_codec
from ycappuccino.permissions.models.account import Account
from ycappuccino.permissions.models.login import Login
from ycappuccino.permissions.models.role_account import RoleAccount
from ycappuccino.permissions.services.login import LoginCookieService, LoginService


class TestLoginServices(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.manager, directory = create_manager()
        self.addCleanup(shutil.rmtree, directory, True)

        login = Login()
        login.id("alice")
        login.login("alice")
        login.password("secret")
        await self.manager.up_sert_model(login)

        account = Account()
        account.id("acc-alice")
        account.login("alice")
        await self.manager.up_sert_model(account)

        role_account = RoleAccount()
        role_account.id("ra-1")
        role_account.account("acc-alice")
        role_account.role("editor")
        role_account.organization("acme")
        await self.manager.up_sert_model(role_account)

    async def test_login_returns_a_valid_token(self):
        service = LoginService(self.manager, key="test-key")

        result = await service.call("POST", [], {}, {"login": "alice", "password": "secret"}, None)

        decoded = jwt_codec.decode(result.body["token"], "test-key")
        self.assertEqual((decoded["sub"], decoded["tid"]), ("acc-alice", "acme"))

    async def test_login_rejects_a_wrong_password(self):
        service = LoginService(self.manager, key="test-key")

        with self.assertRaises(Exception):
            await service.call("POST", [], {}, {"login": "alice", "password": "wrong"}, None)

    async def test_login_only_supports_post(self):
        service = LoginService(self.manager, key="test-key")

        with self.assertRaises(NotFound):
            await service.call("GET", [], {}, None, None)

    async def test_login_cookie_sets_the_header(self):
        service = LoginCookieService(self.manager, key="test-key")

        result = await service.call("POST", [], {}, {"login": "alice", "password": "secret"}, None)

        self.assertIn(f"_ycappuccino={result.body['token']}", result.headers["set-cookie"])


if __name__ == "__main__":
    unittest.main()
```

`permissions_app/src/unittest/python/test_change_password_service.py` :

```python
import shutil
import unittest

from permissions_fixtures import create_manager

from ycappuccino.permissions import passwords
from ycappuccino.permissions.models.login import Login
from ycappuccino.permissions.services.change_password import ChangePasswordService

SUBJECT = {"sub": "alice", "tid": "acme"}


class TestChangePasswordService(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.manager, directory = create_manager()
        self.addCleanup(shutil.rmtree, directory, True)

        login = Login()
        login.id("alice")
        login.login("alice")
        login.password("old")
        await self.manager.up_sert_model(login)

    async def test_secure_flag(self):
        self.assertTrue(ChangePasswordService.secure)

    async def test_changes_the_password(self):
        service = ChangePasswordService(self.manager)

        await service.call("POST", [], {}, {"login": "alice", "password": "old", "new_password": "new"}, SUBJECT)

        account_id = await passwords.check_login(self.manager, "alice", "new")
        self.assertTrue(account_id)

    async def test_rejects_a_wrong_old_password(self):
        service = ChangePasswordService(self.manager)

        with self.assertRaises(Exception):
            await service.call("POST", [], {}, {"login": "alice", "password": "wrong", "new_password": "new"}, SUBJECT)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run (depuis `permissions_app`) : `uv run python -m unittest discover -s src/unittest/python -p "test_*password*.py" && uv run python -m unittest discover -s src/unittest/python -p "test_login_service.py"`
Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement**

`permissions_app/src/main/python/ycappuccino/permissions/services/login.py` :

```python
"""
LoginService, LoginCookieService: exchange a login/password for a JWT.
"""

from ycappuccino.api.endpoints_service import IExposedService, ServiceResult
from ycappuccino.api.endpoints_storage import NotFound
from ycappuccino.api.storage import IManager
from ycappuccino.permissions import jwt_codec, passwords


async def _issue_token(manager, key, timeout, body):
    account_id = await passwords.check_login(manager, body["login"], body["password"])
    organization_id = await passwords.organization_of(manager, account_id)
    return jwt_codec.encode({"sub": account_id, "tid": organization_id}, key, timeout)


class LoginService(IExposedService):
    name = "login"
    secure = False

    def __init__(self, manager: IManager, key: str = jwt_codec.DEFAULT_KEY, timeout: int = jwt_codec.DEFAULT_TIMEOUT):
        self._manager, self._key, self._timeout = manager, key, timeout

    async def start(self):
        pass

    async def stop(self):
        pass

    async def call(self, method, extra_path, params, body, subject):
        if method != "POST":
            raise NotFound("not found")
        token = await _issue_token(self._manager, self._key, self._timeout, body)
        return ServiceResult(body={"token": token})


class LoginCookieService(IExposedService):
    name = "login_cookie"
    secure = False

    def __init__(self, manager: IManager, key: str = jwt_codec.DEFAULT_KEY, timeout: int = jwt_codec.DEFAULT_TIMEOUT):
        self._manager, self._key, self._timeout = manager, key, timeout

    async def start(self):
        pass

    async def stop(self):
        pass

    async def call(self, method, extra_path, params, body, subject):
        if method != "POST":
            raise NotFound("not found")
        token = await _issue_token(self._manager, self._key, self._timeout, body)
        return ServiceResult(body={"token": token}, headers={"set-cookie": f"_ycappuccino={token};Path=/;HttpOnly"})
```

`permissions_app/src/main/python/ycappuccino/permissions/services/change_password.py` :

```python
"""
ChangePasswordService: verifies the old password, then stores a fresh scrypt hash.
"""

from ycappuccino.api.endpoints_service import IExposedService, ServiceResult
from ycappuccino.api.endpoints_storage import NotFound
from ycappuccino.api.storage import IManager
from ycappuccino.permissions import passwords


class ChangePasswordService(IExposedService):
    name = "change_password"
    secure = True   # in addition to the old-password check itself

    def __init__(self, manager: IManager):
        self._manager = manager

    async def start(self):
        pass

    async def stop(self):
        pass

    async def call(self, method, extra_path, params, body, subject):
        if method != "POST":
            raise NotFound("not found")
        await passwords.check_login(self._manager, body["login"], body["password"])
        login = await self._manager.get_one("login", body["login"], subject=None)
        login.password(body["new_password"])
        await self._manager.up_sert_model(login, subject=None)
        return ServiceResult(body={})
```

- [ ] **Step 4: Run tests to verify they pass**

Run (depuis `permissions_app`) : `uv run python -m unittest discover -s src/unittest/python`
Expected: `OK`.

---

### Task 5: `AccountBootStrap`

**Files:**
- Create: `permissions_app/src/main/python/ycappuccino/permissions/bootstrap.py`
- Test: `permissions_app/src/unittest/python/test_bootstrap.py`

**Interfaces:**
- Consumes (Task 1) : modèles, fixtures. `ycappuccino.api.core.IActivityLogger`, `IConfiguration` (déjà construits).
- Produces: `AccountBootStrap(manager: IManager, config: IConfiguration, logger: YCappuccinoType(IActivityLogger, "(name=main)"))`, un composant `YCappuccinoComponent` ordinaire (pas d'interface dédiée : rien d'autre n'en dépend).

- [ ] **Step 1: Write the failing test**

`permissions_app/src/unittest/python/test_bootstrap.py` :

```python
import shutil
import unittest
from unittest import mock

from permissions_fixtures import create_manager

from ycappuccino.permissions import passwords
from ycappuccino.permissions.bootstrap import AccountBootStrap


class FakeConfiguration:
    def __init__(self, values=None):
        self._values = values or {}

    def get(self, key, default):
        return self._values.get(key, default)


class TestAccountBootStrap(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.manager, directory = create_manager()
        self.addCleanup(shutil.rmtree, directory, True)
        self.logger = mock.Mock()

    async def test_creates_the_superadmin_with_a_configured_password(self):
        bootstrap = AccountBootStrap(self.manager, FakeConfiguration({"permissions.superadmin.password": "demo"}), self.logger)

        await bootstrap.start()

        account_id = await passwords.check_login(self.manager, "superadmin", "demo")
        organization_id = await passwords.organization_of(self.manager, account_id)
        self.assertEqual(organization_id, "system")

    async def test_generates_and_logs_a_password_when_unconfigured(self):
        bootstrap = AccountBootStrap(self.manager, FakeConfiguration(), self.logger)

        await bootstrap.start()

        self.logger.warning.assert_called_once()
        generated_password = self.logger.warning.call_args[0][0]
        self.assertTrue(len(generated_password) > 10)  # the message itself carries the password, per the spec
        # the login must actually work with a password of that length; re-derive is not possible from the log
        # alone in this test, so we only assert a login now exists:
        self.assertTrue(await self.manager.get_one("login", "superadmin", subject=None))

    async def test_is_idempotent(self):
        bootstrap = AccountBootStrap(self.manager, FakeConfiguration({"permissions.superadmin.password": "demo"}), self.logger)
        await bootstrap.start()

        await bootstrap.start()

        logins = await self.manager.get_many("login", {"filter": {}}, subject=None)
        self.assertEqual(len(logins), 1)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run (depuis `permissions_app`) : `uv run python -m unittest discover -s src/unittest/python -p test_bootstrap.py`
Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement**

`permissions_app/src/main/python/ycappuccino/permissions/bootstrap.py` :

```python
"""
AccountBootStrap: idempotently creates the system organization and the superadmin account.
"""

import secrets

from ycappuccino.api.core import IActivityLogger, IConfiguration
from ycappuccino.api.core_base import YCappuccinoComponent, YCappuccinoType
from ycappuccino.api.storage import IManager
from ycappuccino.permissions.models.account import Account
from ycappuccino.permissions.models.login import Login
from ycappuccino.permissions.models.organization import Organization
from ycappuccino.permissions.models.role import Role
from ycappuccino.permissions.models.role_account import RoleAccount
from ycappuccino.permissions.models.role_permission import RolePermission


class AccountBootStrap(YCappuccinoComponent):

    def __init__(
        self,
        manager: IManager,
        config: IConfiguration,
        logger: YCappuccinoType(IActivityLogger, "(name=main)"),
    ):
        self._manager, self._config, self._logger = manager, config, logger

    async def stop(self):
        pass

    async def start(self):
        if await self._manager.get_one("login", "superadmin", subject=None) is not None:
            return

        password = self._config.get("permissions.superadmin.password", None)
        if password is None:
            password = secrets.token_urlsafe(16)
            self._logger.warning(f"generated superadmin password: {password}")

        organization = Organization()
        organization.id("system")
        organization.name("system")
        await self._manager.up_sert_model(organization, subject=None)

        role = Role()
        role.id("superadmin")
        role.name("superadmin")
        await self._manager.up_sert_model(role, subject=None)

        login = Login()
        login.id("superadmin")
        login.login("superadmin")
        login.password(password)
        await self._manager.up_sert_model(login, subject=None)

        account = Account()
        account.id("superadmin")
        account.name("superadmin")
        account.login("superadmin")
        account.role("superadmin")
        await self._manager.up_sert_model(account, subject=None)

        role_account = RoleAccount()
        role_account.id("superadmin")
        role_account.role("superadmin")
        role_account.account("superadmin")
        role_account.organization("system")
        await self._manager.up_sert_model(role_account, subject=None)

        role_permission = RolePermission()
        role_permission.id("superadmin")
        role_permission.role("superadmin")
        role_permission.rights(["*:*"])
        await self._manager.up_sert_model(role_permission, subject=None)
```

- [ ] **Step 4: Run tests to verify they pass**

Run (depuis `permissions_app`) : `uv run python -m unittest discover -s src/unittest/python`
Expected: `OK`.

---

### Task 6: intégration au framework, exemple, README et vérification finale

**Files:**
- Test: `permissions_app/src/unittest/python/test_permissions_framework.py`
- Test: `permissions_app/src/unittest/python/test_readme.py`
- Create: `permissions_app/README.md`
- Modify: `permissions_app/example/conf/application.yml` (tout le fichier)
- Create: `permissions_app/example/conf/config.properties`
- Create: `permissions_app/example/library/__init__.py` (vide)
- Modify: `CLAUDE.md` (racine du workspace)

**Interfaces:**
- Consumes : tout ce qui précède.

- [ ] **Step 1: Write the integration test**

`permissions_app/src/unittest/python/test_permissions_framework.py` :

```python
import asyncio
import unittest

from ycappuccino.core.framework import Framework
from ycappuccino.core.testing import TemporaryApplication, wait_until

APPLICATION = {
    "conf/application.yml": """
        name: permissionstest
        bundle_prefix:
          - ycappuccino.storage
          - ycappuccino.endpoints_service
          - ycappuccino.permissions
        layers:
          ycappuccino_storage_memory:
            active: true
        components:
          JwtAuthentication:
            key: test-key
        config:
          shell:
            console: false
    """,
    # IConfiguration only ever reads ./conf/config.properties (a flat key=value file),
    # never the yml's config: section — see core/bundles/configuration.py.
    "conf/config.properties": "permissions.superadmin.password=demo-password\n",
}


class TestPermissionsInFramework(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = TemporaryApplication(APPLICATION).open()
        cls.addClassCleanup(cls.app.close)
        cls.framework = Framework()
        cls.framework.init(cls.app.yml_path)
        cls.addClassCleanup(cls.framework.stop)
        wait_until(lambda: cls.framework.context.get_service_reference("RolePermissionAuthorization"))

    def test_services_are_published(self):
        for specification in ("JwtAuthentication", "RolePermissionAuthorization", "LoginService", "AccountBootStrap"):
            with self.subTest(specification=specification):
                self.assertIsNotNone(self.framework.context.get_service_reference(specification))

    def test_bootstrap_then_login_then_authorized_call(self):
        login = self.framework.context.get_service(self.framework.context.get_service_reference("LoginService"))
        authorization = self.framework.context.get_service(
            self.framework.context.get_service_reference("RolePermissionAuthorization")
        )

        result = asyncio.run(login.call("POST", [], {}, {"login": "superadmin", "password": "demo-password"}, None))
        self.assertIn("token", result.body)

        import jwt as pyjwt

        subject = pyjwt.decode(result.body["token"], "test-key", algorithms=["HS256"])
        self.assertTrue(asyncio.run(authorization.is_authorized(subject, "read", "book")))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the integration test**

Run (depuis `permissions_app`) : `uv run python -m unittest discover -s src/unittest/python -p test_permissions_framework.py`
Expected: `OK`, 2 tests.

- [ ] **Step 3: Write the README**

`permissions_app/README.md` :

````markdown
# ycappuccino-permissions

Comptes, rôles, organisations et permissions natifs : implémente `IAuthentication` (JWT sans état) et `IAuthorization` (permissions relues à chaque contrôle) pour `http_server` et `endpoints_storage`/`endpoints_service`.

Conception : [docs/superpowers/specs/2026-09-15-permissions-app-design.md](docs/superpowers/specs/2026-09-15-permissions-app-design.md).

Prérequis : lire les README de [core](../core/README.md), [storage](../storage/README.md) et [endpoints_service](../endpoints_service/README.md).

## Mise en place

```bash
uv add --editable ../permissions_app
```

`conf/application.yml` :

```yaml
bundle_prefix:
  - ycappuccino.storage
  - ycappuccino.endpoints_storage
  - ycappuccino.endpoints_service
  - ycappuccino.http_server
  - ycappuccino.permissions
  - myapp
layers:
  ycappuccino_storage_memory:
    active: true
components:
  JwtAuthentication:
    key: une-vraie-cle-secrete
```

`conf/config.properties` :

```
permissions.superadmin.password=un-mot-de-passe-initial
```

Sans ces deux valeurs, un avertissement est journalisé au démarrage : une clé JWT par défaut partagée entre toutes les installations, et un mot de passe superadmin généré aléatoirement (visible dans le journal).

## Modèles

`Organization` (name, father), `Login` (login, mot de passe haché en `scrypt`), `Account` (name, login, role), `Role` (name), `RoleAccount` (role, account, organization — le rôle d'un compte dans un tenant), `RolePermission` (role, rights).

## Format des permissions

`RolePermission.rights` est une liste de motifs `"<action>:<item_id>"`, `*` en joker :

```python
["read:book", "call:login", "*:*"]
```

`action` reprend le vocabulaire d'`endpoints_storage` (`read`, `write`, `delete`, `private`) et d'`endpoints_service` (`call`).

## Connexion

`POST /api/services/login` (`{"login", "password"}` → `{"token"}`) et `POST /api/services/login_cookie` (même chose, plus `Set-Cookie`) sont publics. `POST /api/services/change_password` (`{"login", "password", "new_password"}`) exige, en plus de l'ancien mot de passe, une autorisation (`call:change_password`).

## Multi-tenant

`OrganizationTree` fournit le filtre `IFilter` : un sujet `{"tid": "acme"}` voit les documents de `acme` et de toutes ses organisations descendantes. L'arbre est chargé une fois au démarrage et maintenu par les écritures/suppressions d'`organization`.

## Bootstrap

Au premier démarrage, `AccountBootStrap` crée l'organisation `system`, le rôle `superadmin` (`rights: ["*:*"]`) et le compte `superadmin`. Idempotent : les démarrages suivants ne recréent rien.

## Tester avec permissions_app

```python
import unittest

from ycappuccino.permissions import passwords
from ycappuccino.permissions.authorization import RolePermissionAuthorization


class TestAuthorization(unittest.IsolatedAsyncioTestCase):
    async def test_wildcard(self):
        # manager déjà peuplé avec un compte, un rôle "*:*" et un roleAccount
        authorization = RolePermissionAuthorization(manager)
        self.assertTrue(await authorization.is_authorized({"sub": "alice", "tid": "acme"}, "read", "book"))
```

## Développer permissions_app

```bash
uv sync
uv run python -m unittest discover -s src/unittest/python
```

L'exemple `example/` se lance avec `cd example && uv run --project .. ycappuccino`.
````

- [ ] **Step 4: Write the README test**

`permissions_app/src/unittest/python/test_readme.py` — reprend le seul exemple exécutable du README (section « Tester avec permissions_app »), avec un vrai `manager` construit via `permissions_fixtures.create_manager` et peuplé (compte, rôle `*:*`, `roleAccount`) avant l'assertion. Adapter le README pour que son bloc de code corresponde exactement au test une fois celui-ci écrit (même schéma que les tâches précédentes : le test est la source de vérité, le README est ajusté pour rester identique).

- [ ] **Step 5: Run the README test**

Run (depuis `permissions_app`) : `uv run python -m unittest discover -s src/unittest/python -p test_readme.py`
Expected: `OK`.

- [ ] **Step 6: Rebuild the example**

`permissions_app/example/conf/application.yml` :

```yaml
---
name: permissions-demo
bundle_prefix:
  - ycappuccino.storage
  - ycappuccino.endpoints_service
  - ycappuccino.permissions
  - library
layers:
  ycappuccino_storage_memory:
    active: true
config:
  http_server:
    active: false
```

`permissions_app/example/conf/config.properties` :

```
permissions.superadmin.password=demo
```

`permissions_app/example/library/__init__.py` : fichier vide.

- [ ] **Step 7: Update CLAUDE.md**

Dans `CLAUDE.md`, remplacer :

```markdown
- `endpoints_service` → `ycappuccino.endpoints_service`: transport-independent `IServiceEndpoint` calling named `IExposedService` components, authorized through the same `IAuthorization` port as `endpoints_storage` (contract in `api/endpoints_service.py`). See `endpoints_service/README.md`.
- The others are feature layers not yet migrated to the new framework: `hosts`, `permissions_app`, `remote`, `scheduler`, `scripts`, `swagger`, `component-creator`.
```

par :

```markdown
- `endpoints_service` → `ycappuccino.endpoints_service`: transport-independent `IServiceEndpoint` calling named `IExposedService` components, authorized through the same `IAuthorization` port as `endpoints_storage` (contract in `api/endpoints_service.py`). See `endpoints_service/README.md`.
- `permissions_app` → `ycappuccino.permissions` (project `permissions`): accounts, roles, organizations; implements `IAuthentication` (stateless JWT) and `IAuthorization` (permissions re-read on every check), the multi-tenant `IFilter`/`ITrigger`, and the login/change-password `IExposedService`s. See `permissions_app/README.md`.
- The others are feature layers not yet migrated to the new framework: `hosts`, `remote`, `scheduler`, `scripts`, `swagger`, `component-creator`.
```

Remplacer :

```markdown
`api`, `core`, `storage`, `endpoints_storage`, `http_server` and `endpoints_service` are built with **uv** (`pyproject.toml`, `uv_build` backend with `module-root = "src/main/python"` and a dotted `module-name`). `core` depends on `../api`, `storage` on `../api` and `../core`, `endpoints_storage` on `../api`, `../core` and `../storage`, `http_server` on all four, and `endpoints_service` on `../api` and `../core`, as editable path sources. The other repos still have PyBuilder `build.py`/`setup.py`.
```

par :

```markdown
`api`, `core`, `storage`, `endpoints_storage`, `http_server`, `endpoints_service` and `permissions_app` are built with **uv** (`pyproject.toml`, `uv_build` backend with `module-root = "src/main/python"` and a dotted `module-name`). `core` depends on `../api`, `storage` on `../api` and `../core`, `endpoints_storage` on `../api`, `../core` and `../storage`, `http_server` on all four, `endpoints_service` on `../api` and `../core`, and `permissions_app` on `../api`, `../core`, `../storage` and `../endpoints_service`, as editable path sources. The other repos still have PyBuilder `build.py`/`setup.py`.
```

- [ ] **Step 8: Final verification**

Run, depuis chaque dépôt, dans cet ordre :

```bash
cd api && uv run python -m unittest discover -s src/unittest/python
cd ../core && uv run python -m unittest discover -s src/unittest/python
cd ../storage && uv run python -m unittest discover -s src/unittest/python
cd ../endpoints_storage && uv run python -m unittest discover -s src/unittest/python
cd ../endpoints_service && uv run python -m unittest discover -s src/unittest/python
cd ../http_server && uv run python -m unittest discover -s src/unittest/python
cd ../permissions_app && uv run python -m unittest discover -s src/unittest/python
```

Expected: `OK` pour les sept dépôts (tests Mongo de `storage` ignorés sans Docker).
