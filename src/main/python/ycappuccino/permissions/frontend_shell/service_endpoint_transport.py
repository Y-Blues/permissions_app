"""
ServiceEndpointTransport: a ycappuccino.ui.transport.Transport that calls a local IServiceEndpoint
directly in Python -- no HTTP, no JSON, no network. Deliberately NOT
ycappuccino.ui.http_transport.HttpTransport: communication between this frontend and
permissions_app's own backend must be a Python service call, not an HTTP request -- calling a
*remote* instance across a process/machine boundary is ycappuccino-remote's job, not this one, and
not ready yet (see frontend_shell/main.py's docstring).
"""

from typing import Any, Optional

from ycappuccino.api.endpoints_service import IServiceEndpoint


class ServiceEndpointTransport:

    def __init__(self, endpoint: IServiceEndpoint, subject: Optional[dict] = None):
        self._endpoint = endpoint
        self.subject = subject

    async def call(self, service: str, method: str, path: tuple, params: dict, body: Any) -> Any:
        result = await self._endpoint.call(service, method, list(path), params, body, self.subject)
        return result.body
