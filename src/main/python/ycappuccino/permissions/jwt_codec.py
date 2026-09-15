"""
Stateless JWT encode/decode, shared by JwtAuthentication and the login services.
"""

import time
from typing import Optional

import jwt

DEFAULT_KEY = "YCap"  # legacy value, kept only as a development default
DEFAULT_TIMEOUT = 15 * 60  # 15 minutes, in seconds


def encode(payload: dict, key: str, timeout_seconds: int) -> str:
    now = int(time.time())
    return jwt.encode(
        {**payload, "iat": now, "exp": now + timeout_seconds}, key, algorithm="HS256"
    )


def decode(token: str, key: str) -> Optional[dict]:
    try:
        return jwt.decode(token, key, algorithms=["HS256"])
    except jwt.PyJWTError:
        return None
