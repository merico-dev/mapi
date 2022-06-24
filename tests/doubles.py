from typing import Optional

import json

from mapi import Request, Response
from mapi.db import ResponseDatabase
from mapi.http_client import HttpClient


class FakeDatabase(ResponseDatabase):
    def __init__(self):
        self._entries = {}

    def put(self, request, response):
        self._entries[request] = response

    def get(self, request):
        return self._entries.get(request)

    def iter_responses(self):
        yield from self._entries.values()


class HttpClientStub(HttpClient):
    def __init__(self):
        self.responses_map = {}

    def stub(self, request_url: str, response: Response):
        self.responses_map[request_url] = response

    def respond_json(self, request_url: str, json_body: object):
        json_str = json.dumps(json_body)
        json_bytes = json_str.encode('utf8')
        status=200,
        body=json_bytes,
        headers={'Content-type': 'application/json; charset=utf-8'}
        self.stub(request_url, (status, body, headers))

    async def send(self, request: Request):
        if request.uri in self.responses_map:
            status, body, headers = self.responses_map.get(request.uri)
            return Response(request, status, body, headers)
        else:
            return Response(request, status=404)
