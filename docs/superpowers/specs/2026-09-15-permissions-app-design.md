# permissions_app natif : design

Date : 2026-09-15. Sous-projet 3 de la reprise des dépôts YCappuccino, après `core`, `api`, `storage`, `endpoints_storage`, `http_server`, `endpoints_service`.

## Objectif

`permissions_app` fournit les modèles et services de gestion des comptes, rôles, permissions et organisations (tenants), et implémente les ports `IAuthentication` (`http_server`) et `IAuthorization` (`endpoints_storage`) que les sous-projets précédents attendent déjà sans implémentation concrète.

## Décisions

| Sujet | Décision |
|---|---|
| Style | Composants natifs, aucun décorateur ; modèles `@Item` inchangés dans leur principe |
| Modèles conservés | `Organization`, `Login`, `Account`, `Role`, `RoleAccount`, `RolePermission` |
| Modèles supprimés | `Permission` (jamais réellement utilisé : `RolePermission.rights` porte déjà les motifs directement) ; `Media` (hors sujet, `endpoints_storage` gère déjà l'upload) |
| Format des permissions | `"<action>:<item_id>"` avec `*` en joker (ex. `"read:book"`, `"call:login"`, `"*:*"`), aligné sur le vocabulaire d'`endpoints_storage`/`endpoints_service`, plus le format legacy fondé sur les URL |
| Fraîcheur des permissions | Relues à chaque `is_authorized` via `IManager` (pas embarquées dans le JWT) ; le JWT ne porte que `{"sub", "tid", "exp"}` |
| Hachage des mots de passe | `hashlib.scrypt` ; un hash legacy (MD5) est transparently re-haché à la prochaine connexion réussie |
| Cache des jetons | Aucun : vérification sans état, `jwt.decode` gère déjà l'expiration ; pas de purge par thread |
| Connexion | `LoginService` (jeton dans le corps) et `LoginCookieService` (cookie `Set-Cookie`) sont deux services distincts, non sécurisés (le mot de passe est la preuve d'identité) |
| Changement de mot de passe | `ChangePasswordService` est sécurisé (`secure=True`), en plus de la vérification de l'ancien mot de passe |
| Mot de passe superadmin | Depuis la configuration, ou généré aléatoirement et journalisé une fois au démarrage — jamais de valeur en dur |

## 1. Modèles (`permissions_app/.../models/`)

```python
@App(name="ycappuccino_permissions")
@Item(collection="organizations", name="organization", plural="organizations", secure_read=True, secure_write=True)
class Organization(Model):
    # name: str, father: str | None (id d'une autre organisation, propriété simple, pas de référence)

@App(name="ycappuccino_permissions")
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
        """sets a fresh salt and stores its scrypt hash — never call _stored_password directly"""
        self.salt(secrets.token_hex(32))
        self._stored_password(passwords.hash_scrypt(cleartext, self._salt))

@App(name="ycappuccino_permissions")
@Item(collection="accounts", name="account", plural="accounts", secure_read=True, secure_write=True)
@ItemReference(from_name="account", field="login", item="login")
@ItemReference(from_name="account", field="role", item="role")
class Account(Model):
    # name: str, login: ref, role: ref

@App(name="ycappuccino_permissions")
@Item(collection="roles", name="role", plural="roles", secure_read=True, secure_write=True)
class Role(Model):
    # name: str

@App(name="ycappuccino_permissions")
@Item(collection="role_accounts", name="roleAccount", plural="role-accounts", secure_read=True, secure_write=True)
@ItemReference(from_name="roleAccount", field="account", item="account")
@ItemReference(from_name="roleAccount", field="role", item="role")
@ItemReference(from_name="roleAccount", field="organization", item="organization")
class RoleAccount(Model):
    # role: ref, account: ref, organization: ref — le rôle d'un compte dans un tenant

@App(name="ycappuccino_permissions")
@Item(collection="role_permissions", name="rolePermission", plural="role-permissions", secure_read=True, secure_write=True)
@ItemReference(from_name="rolePermission", field="role", item="role")
class RolePermission(Model):
    # role: ref, rights: list[str] — motifs "action:item_id"
```

`id` de `Login` égale son `login` (comme le legacy : `w_admin_login.id("superadmin"); w_admin_login.login("superadmin")`), ce qui permet `manager.get_one("login", identifiant_saisi)` directement.

## 2. Authentification et autorisation

### 2.1 `jwt_codec.py` (module partagé, sans composant)

```python
def encode(payload: dict, key: str, timeout_seconds: int) -> str:
    now = int(time.time())
    return jwt.encode({**payload, "iat": now, "exp": now + timeout_seconds}, key, algorithm="HS256")

def decode(token: str, key: str) -> Optional[dict]:
    try:
        return jwt.decode(token, key, algorithms=["HS256"])
    except jwt.PyJWTError:
        return None


DEFAULT_KEY = "YCap"        # valeur du legacy, conservée comme défaut de développement uniquement
DEFAULT_TIMEOUT = 15 * 60   # 15 minutes, en secondes — le legacy calculait 15 * 60 * 1000 (millisecondes) et
                            # l'ajoutait directement à un timestamp Unix en secondes, un bug qui rendait les
                            # jetons valides ~10 jours au lieu de 15 minutes ; corrigé ici, pas reproduit
```

`encode` est utilisé par `LoginService`/`LoginCookieService` (section 3), `decode` par `JwtAuthentication`. `DEFAULT_KEY`/`DEFAULT_TIMEOUT` vivent ici, dans le module partagé, puisque `JwtAuthentication` (section 2.2) et les services de connexion (section 3) sont dans des fichiers différents et en ont tous les deux besoin.

### 2.2 `JwtAuthentication(IAuthentication)`

```python
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
        token = _token_from_headers(headers)  # Bearer <token> ou cookie _ycappuccino=<token>
        if token is None:
            return None
        return jwt_codec.decode(token, self._key)
```

`_token_from_headers` reprend exactement `get_token_from_header` du legacy (`api.endpoints`), déplacée ici puisque ce module sera retiré à terme.

### 2.3 `RolePermissionAuthorization(IAuthorization)`

```python
def __init__(self, manager: IManager):
    self._manager = manager

async def is_authorized(self, subject: dict, action: str, item_id: str) -> bool:
    role_accounts = await self._manager.get_many(
        "roleAccount", {"filter": {"account.ref": subject["sub"], "organization.ref": subject["tid"]}}
    )
    if not role_accounts:
        return False
    role_id = role_accounts[0].get_storage_model()["role"]["ref"]
    permissions = await self._manager.get_many("rolePermission", {"filter": {"role.ref": role_id}})
    rights = [right for model in permissions for right in model.get_storage_model().get("rights", [])]
    return any(_matches(pattern, action, item_id) for pattern in rights)
```

- Les appels à `IManager` ne portent **pas** de sujet (lectures système, non filtrées) : voir section 4 pour la justification (évite une récursion avec le filtre de tenant).
- `_matches(pattern, action, item_id)` : `re.fullmatch(re.escape(pattern).replace(r"\*", ".*"), f"{action}:{item_id}")`.
- Ces deux composants (`JwtAuthentication`, `RolePermissionAuthorization`) ne dépendent que de `storage`/`api`, jamais d'`endpoints_storage` (dépendance circulaire sinon, puisqu'`endpoints_storage` dépend d'`IAuthorization`).

## 3. Services de connexion (`IExposedService`)

```python
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
        account_id = await passwords.check_login(self._manager, body["login"], body["password"])
        organization_id = await passwords.organization_of(self._manager, account_id)
        token = jwt_codec.encode({"sub": account_id, "tid": organization_id}, self._key, self._timeout)
        return ServiceResult(body={"token": token})
```

`LoginCookieService` (`name = "login_cookie"`) : identique, renvoie `ServiceResult(body={"token": token}, headers={"set-cookie": f"_ycappuccino={token};Path=/;HttpOnly"})`.

```python
class ChangePasswordService(IExposedService):
    name = "change_password"
    secure = True   # en plus de la vérification de l'ancien mot de passe, contrôlé par IAuthorization comme n'importe quel service

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

**Format du hash stocké** (`permissions/passwords.py`, module partagé par `models/login.py` et les services de connexion) : `Login.password(cleartext)` écrit toujours `"scrypt$" + hexdigest`, préfixe qui rend le format explicite et distingue sans ambiguïté un hash natif d'un hash legacy (MD5 nu, sans préfixe, 32 caractères hexadécimaux) :

```python
def hash_scrypt(password: str, salt: str) -> str:
    digest = hashlib.scrypt(password.encode(), salt=salt.encode(), n=2**14, r=8, p=1, dklen=32)
    return "scrypt$" + digest.hex()


def _hash_md5_legacy(password: str, salt: str) -> str:
    return hashlib.md5(f"{salt}{password}".encode()).hexdigest()


# password est private=True : sans "content": "privateField", Manager le retire des lectures (voir storage/README.md)
_READ_PASSWORD = {"content": "privateField"}


async def check_login(manager: IManager, login_id: str, password: str) -> str:
    """returns the account id matching login_id/password, or raises NotFound / InvalidRequest"""
    login = await manager.get_one("login", login_id, _READ_PASSWORD, subject=None)
    if login is None:
        raise NotFound(f"unknown login {login_id}")
    stored = login.get_storage_model()
    salt = stored["salt"]

    if stored["password"] == hash_scrypt(password, salt):
        pass
    elif not stored["password"].startswith("scrypt$") and stored["password"] == _hash_md5_legacy(password, salt):
        login.password(password)  # re-hash with a fresh salt in the modern scrypt format
        await manager.up_sert_model(login, subject=None)
    else:
        raise InvalidRequest("invalid credentials")

    accounts = await manager.get_many("account", {"filter": {"login.ref": login_id}}, subject=None)
    if not accounts:
        raise NotFound(f"no account for login {login_id}")
    return accounts[0].get_storage_model()["_id"]


async def organization_of(manager: IManager, account_id: str) -> str:
    """the organization of the first RoleAccount found for this account (known simplification: one active role)"""
    role_accounts = await manager.get_many("roleAccount", {"filter": {"account.ref": account_id}}, subject=None)
    if not role_accounts:
        raise NotFound(f"no role for account {account_id}")
    return role_accounts[0].get_storage_model()["organization"]["ref"]
```

`check_login`/`organization_of`/`hash_scrypt` vivent dans `permissions/passwords.py`, importé par `models/login.py` (seulement `hash_scrypt`) et par les trois services de connexion. Toutes les lectures/écritures se font sans sujet (mêmes raisons qu'en section 4). `ChangePasswordService.call`'s propre lecture de `login` (pour appeler `login.password(...)`) doit elle aussi passer `subject=None`, déjà le cas dans le code de la section précédente ; elle n'a pas besoin de `_READ_PASSWORD` puisqu'elle réécrit le mot de passe sans le relire.

## 4. `OrganizationTree(ITrigger, IFilter)`

```python
class OrganizationTree(ITrigger, IFilter):
    item_id = "organization"
    actions = ("upsert", "delete")
    post = True

    def __init__(self, manager: IManager):
        self._manager = manager
        self._children: dict[str, set[str]] = {}

    async def start(self):
        await self._load_tree()   # get_many paginé, sans sujet

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

    def _descendants(self, root_id):
        result = [root_id]
        for child in self._children.get(root_id, ()):
            result.extend(self._descendants(child))
        return result
```

Chargé une seule fois à `start()`. Les lectures internes (`_load_tree`, et celles de `RolePermissionAuthorization`) n'utilisent jamais de sujet, pour deux raisons : (1) elles portent sur les données de contrôle d'accès elles-mêmes, à traiter comme des lectures système ; (2) passer un sujet réappliquerait ce même filtre de tenant de façon récursive, ce qui n'a pas de sens ici et casserait le cas du compte superadmin dont l'organisation (`system`) n'a pas de parent.

## 5. `AccountBootStrap`

```python
class AccountBootStrap(YCappuccinoComponent):
    def __init__(self, manager: IManager, config: IConfiguration, logger: YCappuccinoType(IActivityLogger, "(name=main)")):
        self._manager, self._config, self._logger = manager, config, logger

    async def stop(self):
        pass

    async def start(self):
        if await self._manager.get_one("login", "superadmin") is not None:
            return  # déjà initialisé
        password = self._config.get("permissions.superadmin.password", None)
        if password is None:
            password = secrets.token_urlsafe(16)
            self._logger.warning(f"generated superadmin password: {password}")
        # crée, dans l'ordre : organization "system", role "superadmin", login "superadmin",
        # account "superadmin", roleAccount (organization="system"), rolePermission (rights=["*:*"])
```

Toutes les écritures se font sans sujet (bootstrap système). Idempotent : le test de `get_one("login", "superadmin")` évite de régénérer un mot de passe à chaque démarrage.

## 6. Packaging et exemple

```
permissions_app/
  pyproject.toml
  README.md
  example/conf/application.yml
  example/library/__init__.py
  src/main/python/ycappuccino/permissions/
    __init__.py
    jwt_codec.py           encode, decode, DEFAULT_KEY, DEFAULT_TIMEOUT
    passwords.py           hash_scrypt, check_login, organization_of
    authentication.py      JwtAuthentication
    authorization.py       RolePermissionAuthorization
    organization_tree.py   OrganizationTree
    bootstrap.py           AccountBootStrap
    services/
      login.py             LoginService, LoginCookieService
      change_password.py   ChangePasswordService
    models/
      organization.py, login.py, account.py, role.py, role_account.py, role_permission.py
  src/unittest/python/...
```

- **`pyproject.toml`** (uv, `uv_build`) : projet `ycappuccino-permissions`, module `ycappuccino.permissions`, racine `src/main/python`. Dépendances : `ycappuccino-api`, `ycappuccino-core`, `ycappuccino-storage`, `ycappuccino-endpoints-service` (pour `IExposedService`/`ServiceResult`), **pas** `ycappuccino-endpoints-storage` (dépendance circulaire évitée, voir section 2.3). `pyjwt` en dépendance externe.
- Nom de projet legacy `permissions`, paquet legacy `ycappuccino.permissions` — le paquet ne change pas, seul le contenu est réécrit.
- **Supprimés** : `build.py`, `setup.py`, les bundles legacy (`bundles/jwt.py`), `permissions/models/media.py`, `permissions/models/permission.py`, `permissions/services/login_services.py`, `permissions/services/tenant_service.py`, `permissions/bootstrap.py` (remplacés), les tests vides.
- **Exemple** : couche mémoire de `storage`, `permissions.superadmin.password: demo` dans la config pour un mot de passe prévisible en local. Un composant de démarrage appelle `LoginService` directement (sans HTTP) pour montrer le jeton obtenu, puis vérifie qu'`is_authorized` accepte l'action `"*:*"` du superadmin.
- **README** : mise en place, modèles, format des permissions, services de connexion, organisation multi-tenant, bootstrap, avertissement sur la clé JWT par défaut.

## 7. Tests

| Fichier | Contenu |
|---|---|
| `jwt_codec` : encode/decode, jeton expiré, clé invalide |
| `authentication` : en-tête `Bearer`, cookie `_ycappuccino`, absent, jeton invalide |
| `authorization` : motif exact, joker `*`, plusieurs `RolePermission`, tenant sans `RoleAccount`, action refusée |
| `organization_tree` : filtre sur une organisation sans enfant, avec enfants, avec petits-enfants ; mise à jour incrémentale par `execute` (ajout, suppression) |
| `bootstrap` : première exécution crée tout ; seconde exécution ne recrée rien ; mot de passe fourni vs généré (journalisé) |
| `login`/`change_password` : connexion réussie, mauvais mot de passe, compte inconnu, repli MD5 avec ré-hachage, cookie posé, `change_password` refusé sans autorisation, accepté avec `call:change_password` |
| `test_permissions_framework.py` | démarrage du framework, `IAuthentication`/`IAuthorization` publiés, un vrai cycle bootstrap → login → appel autorisé, en mémoire |
| `test_readme.py` | les exemples du README s'exécutent |

## 8. Hors périmètre

- La révocation de jeton avant expiration (liste noire) : la fraîcheur des permissions couvre déjà les changements de rôle ; une vraie révocation de session nécessiterait un état côté serveur, explicitement écarté par la section 2 (stateless).
- La génération swagger de ces services (`swagger`, sous-projet suivant).
- L'inscription libre de nouveaux comptes (self-service signup) : non demandée, seuls la connexion et le changement de mot de passe existent.

## 9. Risques

- **Deux requêtes `IManager` par contrôle d'autorisation** (`RoleAccount` puis `RolePermission`), à chaque appel de route protégée : accepté par choix explicite (fraîcheur), acceptable pour les volumes visés ; un cache à courte durée de vie serait une évolution possible si le coût se révèle réel.
- **Un compte a un seul rôle actif** (le premier `RoleAccount` trouvé pour un tenant donné) : reprend la simplification du legacy, pas une régression.
- **Clé JWT par défaut** : si `jwt.token.key` n'est pas surchargée, toute installation partage la même clé de signature. Un avertissement est journalisé au démarrage si la valeur par défaut est utilisée (voir README) ; il n'y a pas de blocage au démarrage, cohérent avec le reste du framework (avertir plutôt qu'interrompre).
