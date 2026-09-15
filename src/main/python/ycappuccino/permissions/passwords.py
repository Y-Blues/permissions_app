"""
Password hashing and the shared login check used by the login services.
"""

import hashlib

from ycappuccino.api.endpoints_storage import InvalidRequest, NotFound

# password is private=True on Login: without this, Manager strips it from reads (see storage/README.md)
_READ_PASSWORD = {"content": "privateField"}


def hash_scrypt(password: str, salt: str) -> str:
    digest = hashlib.scrypt(
        password.encode(), salt=salt.encode(), n=2**14, r=8, p=1, dklen=32
    )
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
    elif not stored["password"].startswith("scrypt$") and stored[
        "password"
    ] == _hash_md5_legacy(password, salt):
        login.password(password)  # re-hash with a fresh salt in the modern scrypt format
        await manager.up_sert_model(login, subject=None)
    else:
        raise InvalidRequest("invalid credentials")

    accounts = await manager.get_many(
        "account", {"filter": {"login.ref": login_id}}, subject=None
    )
    if not accounts:
        raise NotFound(f"no account for login {login_id}")
    return accounts[0].get_storage_model()["_id"]


async def organization_of(manager, account_id: str) -> str:
    """the organization of the first RoleAccount of this account (one active role, a known simplification)"""
    role_accounts = await manager.get_many(
        "roleAccount", {"filter": {"account.ref": account_id}}, subject=None
    )
    if not role_accounts:
        raise NotFound(f"no role for account {account_id}")
    return role_accounts[0].get_storage_model()["organization"]["ref"]
