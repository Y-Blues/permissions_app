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
  PasswordLogin:
    key: une-vraie-cle-secrete-d-au-moins-32-octets
```

`conf/config.properties` :

```
# optionnel, « superadmin » par défaut
permissions.superadmin.login=superadmin
permissions.superadmin.password=un-mot-de-passe-initial
```

Sans ces deux valeurs, un avertissement est journalisé au démarrage : une clé JWT par défaut partagée entre toutes les installations, et un mot de passe superadmin généré aléatoirement (visible dans le journal). La clé doit être la même pour `JwtAuthentication`, qui vérifie les jetons, et pour `PasswordLogin`, qui les signe ; `pyjwt` avertit si elle fait moins de 32 octets.

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

`PasswordLogin` implémente `ycappuccino.api.permissions.ILoginService` : `login(login, password)` renvoie le jeton. Un composant, local ou dans un navigateur via `ycappuccino.client`, en dépend par cette interface.

Côté HTTP, `LoginService` et `LoginCookieService` s'appuient sur `ILoginService` : `POST /api/services/login` (`{"login", "password"}` → `{"token"}`) et `POST /api/services/login_cookie` (même chose, plus `Set-Cookie`) sont publics. `POST /api/services/change_password` (`{"login", "password", "new_password"}`) et `POST /api/services/create_login` (`{"login", "password"}`) exigent, en plus, une autorisation (`call:change_password`, `call:create_login`). Chacun de ces services répond par une méthode `@rpc_method` (voir le README d'`endpoints_service`).

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

## Une console, deux rendus

Le layout de la console d'admin est décrit une seule fois,
`src/main/python/ycappuccino/permissions/screens/application.yml` (voir « Une console entière » dans le
README de [ui](../ui/README.md)) : écran de connexion, menu (changer son mot de passe, créer une
organisation, un rôle, une permission, un utilisateur, attribuer un rôle), écrans enchaînés et
pré-remplis, message « Enregistré. », déconnexion. Les écrans sont les templates YAML du même dossier.
La console terminal le rend avec `ShellApplication` (`ui_shell`), la console web avec `WebApplication`
(`ui_web`) : modifier ce fichier change les deux.

Les étapes nomment l'un des trois transports que chaque console fournit : `login` (`ILoginService`),
`services` (`IServiceEndpoint`), `crud` (`ICrud`).

## Frontend shell

`frontend_shell/` (`FrontendShell`) : la console en terminal, une App textual (`run_menu()`).

L'essayer : `example/console/run.sh` (login `admin` / `admin`, stockage en mémoire).

`FrontendShell` ne connaît que des interfaces : `ILoginService` (écran de connexion, par
`ComponentTransport`), `IServiceEndpoint` (`change_password`, `create_login`) et `ICrud` (le reste). Il
tourne dans le process du backend et transmet aux appels suivants le sujet décodé du jeton
(`jwt_codec.decode`), d'où son paramètre `key`.

## Frontend web

`frontend_web/` (`PermissionsWebApp`) : la même console dans un navigateur. Elle tourne dans le `Framework` client de [`client`](../client/README.md) (Pyodide) et ne dépend que
d'interfaces : `ILoginService`, `IServiceEndpoint` et `ICrud` (les proxies générés), `ISession` (le jeton)
et `IWebPage` ([`ui_web`](../ui_web/README.md), la page où elle dessine). Elle n'envoie jamais de sujet :
le backend le déduit du jeton.

L'essayer : `example/web/run.sh`, puis ouvrir http://localhost:8180 (login `admin` / `admin`, stockage en
mémoire). Le script construit les wheels dans `example/web/site/`, y copie la page générique de `client` et
`ycappuccino.json`, puis démarre un seul process : le backend, qui sert aussi `site/` par `hosts` (composant
`WebSite`, `example/web/webhost/site.py`), donc la page et l'`/api` partagent la même origine.

**Déployer.** Le backend charge, en plus de ses modules habituels, `ycappuccino.remote.dispatch` et
`ycappuccino.remote.capabilities`. La page générique `client/static/index.html` est servie sur la même
origine que son `/api`, à côté des wheels et de `example/web/ycappuccino.json` :

```json
{"name": "permissions-admin",
 "wheels": ["wheels/ycappuccino_api-0.1.0-py3-none-any.whl", "...", "wheels/ycappuccino_permissions-0.1.0-py3-none-any.whl"],
 "bundles": ["ycappuccino.ui_web.page", "ycappuccino.permissions.frontend_web"],
 "components": {"PyodidePage": {"mount_selector": "#app"}}}
```

Les wheels se construisent avec `uv build --wheel` dans `api`, `core`, `client`, `ui`, `ui_web` et
`permissions_app`.

**Vérifié le 2026-09-17** dans Chromium (Playwright, Pyodide 0.28.3), devant un vrai backend : mauvais mot
de passe affiché sur l'écran, connexion, création d'une organisation (relue ensuite par l'API REST),
création d'un utilisateur en trois écrans puis connexion de cet utilisateur, déconnexion.  Vérifié aussi
par `example/web/run.sh` : page, wheels et `/api` servis par le même backend via `hosts`.

**Modèle de tenancy** (voir « Multi-tenant » plus haut) : `Role`/`RolePermission` ne sont **pas** eux-mêmes
liés à un tenant — leur définition est la même partout. C'est `RoleAccount` (écran « Attribuer un rôle »,
`FrontendShell.grant_role()`) qui scope réellement une attribution à une organisation. Un rôle « global »
(ex. `admin`) n'est pas un cas particulier du modèle de données : on l'attribue simplement à
l'organisation racine (`system`) — le filtre par descendance d'`OrganizationTree` (voir plus haut) fait
alors qu'un sujet scopé à la racine voit tout en dessous, exactement comme le `superadmin` de
`AccountBootStrap`.

**Créer un utilisateur** (`FrontendShell.create_user()`) enchaîne 3 écrans, jamais un seul : identifiants
(`create_login`, un appel de service Python vers `CreateLoginService` — seul point d'entrée sûr pour un
mot de passe haché, une écriture CRUD générique sur `login` écrirait le mot de passe en clair, voir la
docstring de ce service), profil (`account`, CRUD), puis attribution du rôle dans un tenant
(`role_account`, CRUD) — les mêmes trois enregistrements qu'`AccountBootStrap` crée à la main pour le
superadmin.

**Connexion : locale aujourd'hui, fournisseur d'identité externe non construit.**
`PasswordLogin`/`JwtAuthentication` n'authentifient que des comptes `permissions_app` locaux. Brancher un
fournisseur externe (OIDC/SAML/...) est une direction réelle mais **volontairement pas commencée** : côté
backend il faudrait son propre `IExposedService`/`IAuthentication`, côté frontend un tout autre type
d'écran (un flux de redirection/device-code ne rentre pas dans le modèle actuel de `Screen`, « un
formulaire, une action ») — non ébauché ici pour éviter une abstraction à moitié construite, voir la
docstring de `main.py`.

## Développer permissions_app

```bash
uv sync
uv run python -m unittest discover -s src/unittest/python
```

L'exemple `example/` se lance avec `cd example && uv run --project .. ycappuccino`.
