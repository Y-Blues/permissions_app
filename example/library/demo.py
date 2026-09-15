"""
Logs in as the superadmin created by AccountBootStrap and checks its permissions, without HTTP.
"""

from ycappuccino.api.core import IActivityLogger
from ycappuccino.api.core_base import YCappuccinoComponent, YCappuccinoType
from ycappuccino.api.endpoints_service import IServiceEndpoint
from ycappuccino.api.endpoints_storage import IAuthorization
from ycappuccino.permissions.bootstrap import AccountBootStrap


class PermissionsDemo(YCappuccinoComponent):

    def __init__(
        self,
        endpoint: IServiceEndpoint,
        authorization: IAuthorization,
        # depending on the bootstrap: it is published once its start() created the superadmin
        bootstrap: AccountBootStrap,
        logger: YCappuccinoType(IActivityLogger, "(name=main)"),
    ):
        self._endpoint = endpoint
        self._authorization = authorization
        self._logger = logger

    async def start(self):
        result = await self._endpoint.call(
            "login", "POST", [], {}, {"login": "superadmin", "password": "demo"}, None
        )
        self._logger.info(f"superadmin token: {result.body['token']}")

        subject = {"sub": "superadmin", "tid": "system"}
        allowed = await self._authorization.is_authorized(subject, "read", "book")
        self._logger.info(f"superadmin may read a book: {allowed}")

    async def stop(self):
        pass
