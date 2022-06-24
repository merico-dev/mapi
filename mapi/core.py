from __future__ import annotations

from typing import Callable, Dict, List, Optional, Union
from string import Formatter


RouteArgs = Union[List[str], Dict[str, str]]
QueryArgs = Dict[str, str]
Headers = Dict[str, str]


class API:
    def __init__(self, host: str):
        self.host = host
        self._resources = {}
        self.hooks = []

    def add(self,
            name: str,
            route_template: str,
            query_params: Optional[List[str]] = None,
            hooks: Optional[List[Hook]] = None):
        assert name not in self._resources, \
            f"Resource {name} already exist"

        resource = Resource(
            self,
            name,
            route_template,
            query_params,
            hooks
        )
        self._resources[name] = resource
        return self

    def hook(self, hook):
        self.hooks.append(hook)
        return self

    def get(self, resource_name):
        try:
            return self._resources[resource_name]
        except KeyError:
            raise Exception(f'Unknown resource {resource_name}')


class Resource:
    """
    Represents a REST resource of an API.
    A resource describe the different handlers.
    """
    def __init__(self,
                 api: API,
                 name: str,
                 route_template: str,
                 query_params: List[str] = None,
                 hooks: List[Hook] = None):
        self.api = api
        self.name = name
        self.route_template = route_template
        self.query_params = query_params or []
        self.hooks = hooks or []

    @property
    def route_params(self):
        return [name for _, name, _, _ in Formatter().parse(self.route_template) if name]

    def as_request(self,
                   route_args: Optional[RouteArgs] = None,
                   query_args: Optional[QueryArgs] = None):
        return Request(
            resource=self,
            route_args=route_args,
            query_args=query_args
        )


class Request:
    def __init__(self,
                 resource: Resource,
                 route_args: Optional[RouteArgs] = None,
                 query_args: Optional[QueryArgs] = None,
                 headers: Optional[Headers] = None):
        self.resource = resource
        self.route_args = route_args or {}
        self.query_args = query_args or {}
        self.headers = headers or {}
        self._validate_route_args()

    @property
    def route(self) -> str:
        return self.resource.route_template.format(**self.route_args)

    @property
    def uri(self) -> str:
        return self.resource.api.host.strip('/') + '/' + self.route.strip('/')

    def run_hooks(self, hooks: List[Hook], **kwargs) -> Optional[Request]:
        request = self
        for hook in hooks:
            result = hook.handle_request(request, **kwargs)
            if result is Abort:
                break
            if isinstance(result, Request):
                request = result
        return request

    def __eq__(self, other):
        """
        Equality between two requests ignores headers.
        """
        if not isinstance(other, Request):
            return False

        return self.uri == other.uri and self.query_args == other.query_args

    def __hash__(self):
        return hash((self.uri, tuple(self.query_args.items())))

    def __str__(self):
        if self.query_args:
            query_str = '&'.join(f'{k}={v}' for k, v in self.query_args.items())
            return f'{self.uri}?{query_str}'
        return self.uri

    def _validate_route_args(self):
        params = set(self.resource.route_params)
        args = set(self.route_args.keys())

        missing_args = params.difference(args)
        if missing_args:
            raise ValueError(f'Missing route argument for parameter {list(missing_args)[0]}')

        unknown_params = args.difference(params)
        if unknown_params:
            raise ValueError(f'Unknown route parameter {list(unknown_params)[0]}')


class Response:
    def __init__(self,
                 request: Request,
                 status: int,
                 body: bytes = None,
                 headers: Headers = None):
        self.request = request
        self.status = status
        self.body = body
        self.headers = headers or {}

    def run_hooks(self, hooks: List[Hook], **kwargs) -> Optional[Response]:
        response = self
        for hook in reversed(hooks):
            result = hook.handle_response(response, **kwargs)
            if result is Abort:
                break
            if isinstance(result, Response):
                response = result
        return response

    def __str__(self):
        return f'{self.request}: {self.status}'


# Sentinel object to signal abortion of request or response in hooks
Abort = object()


class Hook:
    """
    A hook can be registered for a whole API or for individual Resources.
    It allows to customize requests before sending them and responses
    before storing them.

    A hook must implement two methods:
    - handle_request: updates the request or return Abort, in which case
      the request is not sent.
    - handle_response: updates the response or return Abort, in which case
      the response is not further processed.
    """
    def handle_request(self, request, **kwargs):
        pass

    def handle_response(self, response, **kwargs):
        pass


class CustomHook(Hook):
    """
    A convenience class to create hooks from two user-supplied functions.
    """
    def __init__(self, handle_request_fn = None, handle_response_fn = None):
        self.handle_request_fn = handle_request_fn
        self.handle_response_fn = handle_response_fn

    def handle_request(self, request, **kwargs):
        if self.handle_request_fn:
            return self.handle_request_fn(request, **kwargs)
        return request

    def handle_response(self, response, **kwargs):
        if self.handle_response_fn:
            return self.handle_response_fn(response, **kwargs)
        return response


def hook(handle_request: Callable = None, handle_response: Callable = None):
    """
    Create a hook from optional user supplied functions
    """
    return CustomHook(handle_request, handle_response)
