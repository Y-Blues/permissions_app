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

Au premier démarrage, `AccountBootStrap` crée l'organisation `system`, le rôle `superadmin` (`rights: ["*:*"]`) et le compte `superadmin`. Idempotent : les démarrages suivants ne recréent rien. Ces enregistrements sont écrits par le superadmin dans l'organisation `system` : ils portent leur
organisation (`_tid`) comme ceux de n'importe quel utilisateur, et le filtre multi-tenant les montre donc aux
membres de `system`. De même, un login créé par `create_login` appartient à l'organisation de celui qui le
crée.

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
README de [ui](../ui/README.md)) : écran de connexion, puis une barre avec un menu déroulant par section
(« My account », « Organizations », « Roles and permissions », « Users »), l'utilisateur connecté et
« Sign out », au-dessus des écrans enchaînés et pré-remplis et du message « Saved. ». Les écrans sont les templates YAML du même dossier.
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

`frontend_web/` (`PermissionsWebApp`) : la même console dans un navigateur. Son thème ne fait pas partie du
paquet : c'est la configuration du déploiement, `example/web/style.css` (une page de site : barre expresso
pleine largeur, contenu sans cadre, clair et sombre, mobile), liée par `ycappuccino.json`
(`components: PyodidePage: stylesheets`). Elle tourne dans le `Framework` client de [`client`](../client/README.md) (Pyodide) et ne dépend que
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
 "components": {"PyodidePage": {"mount_selector": "#app", "stylesheets": "style.css"}}}
```

Les wheels se construisent avec `uv build --wheel` dans `api`, `core`, `client`, `ui`, `ui_web` et
`permissions_app`.

**Vérifié le 2026-09-17** dans Chromium (Playwright, Pyodide 0.28.3), devant un vrai backend : mauvais mot
de passe affiché sur l'écran, connexion, création d'une organisation (relue ensuite par l'API REST),
création d'un utilisateur en trois écrans puis connexion de cet utilisateur, déconnexion.  Vérifié aussi
par `example/web/run.sh` : page, wheels et `/api` servis par le même backend via `hosts`.

## Trois processus : stockage, backend, frontend

`example/three_processes/run.sh` lance la même application répartie sur trois processus Python, qui se
parlent par les appels JSON-RPC signés de [`remote`](../remote/README.md) :

| Processus | Contient | Appelle |
|---|---|---|
| `storage` (http://localhost:8201) | `MemoryStorage` (`IStorage`) | — |
| `backend` (http://localhost:8202) | `Manager`, use cases CRUD et services, permissions (connexion, JWT, autorisation), API HTTP | `IStorage` du stockage |
| `frontend` (ce terminal) | la console d'administration (`FrontendShell`) | `ILoginService`, `IServiceEndpoint`, `ICrud` du backend |

Login `admin` / `admin`. Quitter la console arrête les deux autres ; leurs journaux sont dans
`example/three_processes/logs/`.

- **La frontière du stockage est `IStorage`** et non `IManager` : les méthodes d'`IManager` prennent et
  rendent des `Model`, qu'un appel JSON ne transporte pas ; celles d'`IStorage` n'échangent que des
  documents. Le `Manager` (items, filtres, triggers) reste donc dans le backend.
- **Aucun stockage partagé pour se trouver** : chaque processus déclare ses pairs dans son
  `application.yml` (`ConfiguredPeers`, avec un secret partagé qui signe chaque appel). Le frontend n'a
  ni stockage ni serveur HTTP : il est déclaré sans adresse chez le backend, seulement pour authentifier
  ses appels.
- **Les proxies** sont créés par `ComponentDirectory`, limités aux interfaces utiles (`specifications`) et
  redécouverts toutes les deux secondes : l'ordre de démarrage est libre, un composant qui en dépend
  (le `Manager`, la console) devient valide dès que son proxy existe.
- **Le sujet** de l'utilisateur connecté sur la console accompagne chaque appel vers le backend, signé ;
  le backend applique ses autorisations comme pour une requête HTTP.

`test_three_processes_example.py` lance le stockage et le backend en sous-processus depuis ces mêmes
fichiers de configuration, pilote la vraie console (connexion, création d'un rôle) et relit le rôle
directement dans l'`IStorage` du processus de stockage.

## Quatre processus : stockage, use cases, adaptateur HTTP, front web

`example/four_processes/run.sh` découpe le backend par rôle, chaque processus n'embarquant que ses
composants, et sert la console web. Ouvrir http://localhost:8304, login `admin` / `admin` ; `Ctrl+C` arrête
les quatre, leurs journaux sont dans `example/four_processes/logs/`.

| Processus | Contient | Prend en proxy |
|---|---|---|
| `storage` (8301) | `MemoryStorage` | — |
| `usecases` (8302) | `Manager`, use cases CRUD et services, permissions (connexion, autorisation, bootstrap) | `IStorage` ← storage |
| `http` (8303) | l'API publique : `ApiServlet`, `JwtAuthentication`, `__remote_dispatch__`/`__remote_capabilities__` pour le navigateur, `FederatedServiceEndpoint` | `ICrud`, `IDrafts`, `IItemCatalog`, `ILoginService` ← usecases |
| `web` (8304) | le front web : la page générique de `client`, `ycappuccino.json`, le thème, les wheels (`hosts`) | — |

- **Le navigateur** charge la page depuis `web` et appelle l'API de `http` (`client.base_url` dans
  `ycappuccino.json`). Deux origines : `http` autorise celle de `web` et elle seule (`ApiServlet`
  `allowed_origins`, CORS).
- **L'adaptateur HTTP ne contient aucun use case** : il authentifie le jeton de l'utilisateur, puis relaie
  chaque appel, signé et pour le compte de cet utilisateur, au processus `usecases` ; un service nommé
  (`change_password`, `create_login`...) est relayé par `FederatedServiceEndpoint`.
- **Chaque processus appelé a son petit serveur HTTP** : `remote` voyage en HTTP (`__remote_dispatch__`).
  Seul `http` est l'API de l'application ; `storage` et `usecases` n'acceptent que les appels signés de
  leurs pairs déclarés (`ConfiguredPeers`).

`test_four_processes_example.py` lance les quatre processus depuis ces mêmes fichiers de configuration,
joue le navigateur contre `http` (découverte, pré-vol CORS, connexion, création d'un rôle et d'un login,
refus d'un appel anonyme) et relit le rôle et le login dans l'`IStorage` du processus `storage`.

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
