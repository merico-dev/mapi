from typing import Optional
import asyncio as aio

from .core import Abort, Resource, Request, Response, Hook, RouteArgs, QueryArgs
from .http_client import HttpClient, AioHttpClient
from .db import ResponseDatabase
# TODO: use a real db
from tests.doubles import FakeDatabase



class Collector:
    def __init__(self,
                 db: Optional[ResponseDatabase] = None,
                 http_client: Optional[HttpClient] = None,
                 num_workers: Optional[int] = 3):
        self._db = db or FakeDatabase()
        self._http_client = http_client or AioHttpClient()
        self._num_workers = num_workers
        self._queue = []
        # asyncio.Queue must be created in the same event loop
        # than its consumers
        self._async_queue = None

    def register(self,
                 resource: Resource,
                 route_args: Optional[RouteArgs] = None,
                 query_args: Optional[QueryArgs] = None):
        """
        Register API collection for a given Resource.
        The resource can be a Resource object or identified by name.
        Route parameters must be supplied in order if the resource requires it.
        Query parameters are optional.
        """
        request = resource.as_request(route_args, query_args)
        if self._async_queue:
            self._async_queue.put_nowait(request)
        else:
            self._queue.append(request)
        return self

    def get(self,
            resource: Resource,
            route_args: Optional[RouteArgs] = None,
            query_args: Optional[QueryArgs] = None):
        request = resource.as_request(route_args, query_args)
        return self._db.get(request)

    def iter_responses(self):
        yield from self._db.iter_responses()

    def run(self):
        aio.run(self._run())

    async def _run(self):
        self._async_queue = aio.Queue()

        self._fill_async_queue()
        tasks = [aio.create_task(self._worker(), name=f'Task-{i}') for i in range(self._num_workers)]
        # Wait until the queue is fully processed.
        await self._async_queue.join()
        # Cancel worker tasks.
        for task in tasks:
            task.cancel()
        # Wait until all worker tasks are cancelled.
        await aio.gather(*tasks, return_exceptions=True)
        self._async_queue = None

    async def _worker(self):
        while True:
            try:
                request = await self._async_queue.get()
                resource = request.resource
                hooks = resource.hooks + resource.api.hooks
                request = request.run_hooks(hooks, collector=self)
                if request is Abort:
                    continue
                response = await self._http_client.send(request)
                response = response.run_hooks(hooks, collector=self)
                if response is not Abort:
                    self._db.put(request, response)
            finally:
                self._async_queue.task_done()

    def _fill_async_queue(self):
        # We have a sync queue and an async queue
        # because aio.Queue must be created in the same
        # loop context than its consumers
        for request in self._queue:
            self._async_queue.put_nowait(request)
        self._queue.clear()