"""Transport calling a local IServiceEndpoint directly (no HTTP) -- see main.py's docstring."""

from typing import Any, Optional

from ycappuccino.api.endpoints_service import IServiceEndpoint


class ServiceEndpointTransport:

    def __init__(self, endpoint: IServiceEndpoint, subject: Optional[dict] = None):
        self._endpoint = endpoint
        self.subject = subject

    async def call(self, service: str, method: str, path: tuple, params: dict, body: Any) -> Any:
        result = await self._endpoint.call(service, method, list(path), params, body, self.subject)
        return result.body
