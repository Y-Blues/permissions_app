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
    key: une-vraie-cle-secrete-d-au-moins-32-octets
  LoginService:
    key: une-vraie-cle-secrete-d-au-moins-32-octets
  LoginCookieService:
    key: une-vraie-cle-secrete-d-au-moins-32-octets
```

`conf/config.properties` :

```
permissions.superadmin.password=un-mot-de-passe-initial
```

Sans ces deux valeurs, un avertissement est journalisé au démarrage : une clé JWT par défaut partagée entre toutes les installations, et un mot de passe superadmin généré aléatoirement (visible dans le journal). La clé doit être la même pour `JwtAuthentication`, qui vérifie les jetons, et pour les services de connexion, qui les signent ; `pyjwt` avertit si elle fait moins de 32 octets.

## Modèles

`Organization` (name, father), `Login` (login, mot de passe haché en `scrypt`), `Account` (name, login, role), `Role` (name), `RoleAccount` (role, account, organization — le rôle d'un compte dans un tenant), `RolePermission` (role, rights).

L'`id` d'un `Login` est l'identifiant saisi à la connexion. Le champ `password` est privé : il n'est jamais renvoyé par une lecture ordinaire, et `Login.password(cleartext)` est le seul point d'entrée pour l'écrire (il tire un nouveau sel et stocke `scrypt$<empreinte>`). Un mot de passe legacy haché en MD5 est accepté une dernière fois, puis ré-haché en `scrypt` à la première connexion réussie.

## Format des permissions

`RolePermission.rights` est une liste de motifs `"<action>:<item_id>"`, `*` en joker :

```python
["read:book", "call:login", "*:*"]
```

`action` reprend le vocabulaire d'`endpoints_storage` (`read`, `write`, `delete`, `private`) et d'`endpoints_service` (`call`).

Les droits sont relus à chaque contrôle : le JWT ne porte que `{"sub", "tid", "exp"}`, donc un changement de rôle prend effet immédiatement, sans attendre l'expiration du jeton.

## Connexion

`POST /api/services/login` (`{"login", "password"}` → `{"token"}`) et `POST /api/services/login_cookie` (même chose, plus `Set-Cookie`) sont publics. `POST /api/services/change_password` (`{"login", "password", "new_password"}`) exige, en plus de l'ancien mot de passe, une autorisation (`call:change_password`).

Le jeton est présenté soit en en-tête `Authorization: Bearer <jeton>`, soit dans le cookie `_ycappuccino`. Il expire au bout de 15 minutes ; il n'y a pas de révocation avant expiration.

## Multi-tenant

`OrganizationTree` fournit le filtre `IFilter` : un sujet `{"tid": "acme"}` voit les documents de `acme` et de toutes ses organisations descendantes. L'arbre est chargé une fois au démarrage et maintenu par les écritures/suppressions d'`organization`.

## Bootstrap

Au premier démarrage, `AccountBootStrap` crée l'organisation `system`, le rôle `superadmin` (`rights: ["*:*"]`) et le compte `superadmin`. Idempotent : les démarrages suivants ne recréent rien.

## Tester avec permissions_app

```python
import unittest

from ycappuccino.storage.files import LocalFileStore
from ycappuccino.storage.items import ItemManager
from ycappuccino.storage.manager import Manager
from ycappuccino.storage.memory import MemoryStorage

from ycappuccino.permissions.authorization import RolePermissionAuthorization
from ycappuccino.permissions.models.role_account import RoleAccount
from ycappuccino.permissions.models.role_permission import RolePermission


class TestAuthorization(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.manager = Manager(
            MemoryStorage(), ItemManager(), [], [], LocalFileStore("/tmp/files")
        )

        role_account = RoleAccount()
        role_account.id("ra-alice")
        role_account.account("alice")
        role_account.role("admin")
        role_account.organization("acme")
        await self.manager.up_sert_model(role_account)

        role_permission = RolePermission()
        role_permission.id("rp-admin")
        role_permission.role("admin")
        role_permission.rights(["*:*"])
        await self.manager.up_sert_model(role_permission)

    async def test_the_admin_role_may_read_a_book(self):
        authorization = RolePermissionAuthorization(self.manager)

        subject = {"sub": "alice", "tid": "acme"}
        self.assertTrue(await authorization.is_authorized(subject, "read", "book"))
```

## Frontend shell

`frontend_shell/` (`FrontendShell`, `ycappuccino.permissions.frontend_shell.main`) : connexion puis
changement de mot de passe, deux écrans chargés depuis des templates YAML (`frontend_shell/screens/`, pas
construits à la main), rendus en terminal par `ycappuccino-ui-shell`. Voir le README de
[ui](../ui/README.md) pour le modèle d'écran et [ui_shell](../ui_shell/README.md) pour le rendu.

**Choix explicite : la communication entre ce frontend et le backend `permissions_app` est un appel de
service Python (`ServiceEndpointTransport`, un vrai `IServiceEndpoint` injecté), jamais du HTTP.**
`FrontendShell` ne s'installe donc que dans le **même** process/`Framework` que le backend — le sujet
décodé du jeton de connexion (`jwt_codec.decode`) est transmis directement au deuxième appel, sans
en-tête `Authorization` puisqu'il n'y a aucune requête HTTP. Faire tourner ce frontend comme un vrai
client séparé (un autre process, une autre machine) demande le dispatch typé et authentifié entre pairs
que `remote` est censé fournir — conçu mais **pas encore implémenté**
(`remote/docs/superpowers/specs/2026-09-16-transparent-rpc-design.md`, plan à
`remote/docs/superpowers/plans/2026-09-16-transparent-rpc.md`) : tant que ce n'est pas prêt, ce frontend
reste un outil mono-process, voir la docstring de `main.py` pour le détail.

## Développer permissions_app

```bash
uv sync
uv run python -m unittest discover -s src/unittest/python
```

L'exemple `example/` se lance avec `cd example && uv run --project .. ycappuccino`.
