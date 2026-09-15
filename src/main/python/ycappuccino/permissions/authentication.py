"""
JwtAuthentication: stateless JWT verification for the IAuthentication port (http_server).
"""

import logging
from typing import Optional

from ycappuccino.api.http_server import IAuthentication
from ycappuccino.permissions import jwt_codec

_logger = logging.getLogger(__name__)

_BEARER = "Bearer "
_COOKIE = "_ycappuccino"


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
    """the token of an Authorization header or of the _ycappuccino cookie, or None"""
    authorization = headers.get("authorization")
    if authorization is not None and authorization.startswith(_BEARER):
        return authorization[len(_BEARER) :]
    cookie = headers.get("cookie")
    if cookie is not None:
        for part in cookie.split(";"):
            name, separator, value = part.strip().partition("=")
            if separator and name == _COOKIE:
                return value
    return None
