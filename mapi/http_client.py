from abc import ABC, abstractmethod

import aiohttp

from mapi import Request, Response


class HttpClient(ABC):
    @abstractmethod
    async def send(self, request: Request) -> Response:
        pass


class AioHttpClient(HttpClient):
    async def send(self, request):
        async with aiohttp.ClientSession() as session:
            async with session.get(
                request.uri,
                params=request.query_args,
                headers=request.headers) as aio_response:
                return Response(
                    request = request,
                    status = aio_response.status,
                    body = await aio_response.read(),
                    headers = aio_response.headers
                )
