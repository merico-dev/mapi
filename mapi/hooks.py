import logging
import sys
import json

from mapi import Hook, Abort
from mapi.core import Request, Response


class SetHeader(Hook):
    def __init__(self, header: str, val: str):
        self.header = header
        self.val = val

    def handle_request(self, response, **kwargs):
        response.headers[self.header] = self.val


class SetQueryParams(Hook):
    def __init__(self, **params):
        self.params = params

    def handle_request(self, response, **kwargs):
        for param, val in self.params.items():
            response.query_args[param] = val


class RateLimit(Hook):
    def handle_response(response, collector, **kwargs):
        if response.status == 427:
            timestamp = response.headers['X-retry-by']
            date = timestamp
            collector.pause_until(timestamp)
            request = response.request
            collector.register(request.resource, request.route_args, request.query_args)
            return Abort


class HeaderPagination(Hook):
    def __init__(self, next_page_header='x-next-page'):
        self.next_page_header = next_page_header

    def handle_response(self, response, collector, **kwargs):
        next_page = response.headers.get(self.next_page_header)
        if next_page:
            request = response.request
            query_args = request.query_args
            query_args['page'] = next_page
            collector.register(request.resource, request.route_args, query_args)


class FetchAllPagesWeirdApi(Hook):
    def handle_response(self, response, collector, **kwargs):
        request = response.request
        query_args = dict(request.query_args)
        query_args['page'] += 1
        collector.register(request.resource, request.route_args, query_args)


class EtagConditionalRequest(Hook):
    def handle_request(self, request, collector, **kwargs):
        previous_response = collector.get(request.resource, request.route_args, request.query_args)
        if previous_response:
            etag = previous_response.headers.get('ETag')
            if etag:
                request.headers['If-None-Match'] = etag

    def handle_response(self, response):
        if response.status == 304:
            return Abort


class LastModifiedConditionalRequest(Hook):
    def handle_request(self, request, collector, **kwargs):
        previous_response = collector.get(request.resource, request.route_args, request.query_args)
        if previous_response:
            timestamp = previous_response.headers.get('Last-Modified')
            if timestamp:
                request.headers['If-Modified-Since'] = timestamp

    def handle_response(self, response):
        if response.status == 304:
            return Abort


class Log(Hook):
    def __init__(self, log_name: str = None):
        self.logger = logging.getLogger(log_name or 'mapi')
        self.logger.addHandler(logging.StreamHandler(sys.stdout))
        self.logger.setLevel(logging.INFO)

    def handle_request(self, request: Request, **kwargs):
        self.logger.info(f'Handling request {request}')

    def handle_response(self, response: Response, **kwargs):
        self.logger.info(f'Handling response {response}')


class ParseJson(Hook):
    def handle_response(self, response: Response, **kwargs):
        if response.status == 200:
            response.body = json.loads(response.body)
