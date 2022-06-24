import json

from pytest import fixture

from mapi import API, Collector, hook

from .doubles import *


@fixture
def api():
    return (
        API('http://test.org')
        .add('all_users', 'users')
        .add('all_countries', 'countries')
    )


@fixture
def users():
    return [
        {'id': 1, 'nickname': 'michou'},
        {'id': 2, 'nickname': 'ernest'},
    ]


@fixture
def countries():
    return ['China', 'France', 'USA']


@fixture
def http_client(users, countries):
    client = HttpClientStub()
    client.respond_json('http://test.org/users', users)
    client.respond_json('http://test.org/countries', countries)
    return client


@fixture
def collector(db, http_client):
    return Collector(db=db, http_client=http_client)


@fixture
def db():
    return FakeDatabase()


async def test_get_one_resource(api, collector, users):
    # Act
    collector.register(api.get('all_users'))
    await collector.run()

    # Assert
    response = collector.get(api.get('all_users'))
    body = json.loads(response.body.decode('utf8'))
    assert body == users


async def test_get_many_resources(api, collector, users, countries):
    # Act
    collector.register(api.get('all_users'))
    collector.register(api.get('all_countries'))
    await collector.run()

    # Assert
    response = collector.get(api.get('all_users'))
    body = json.loads(response.body.decode('utf8'))
    assert body == users
    response = collector.get(api.get('all_countries'))
    body = json.loads(response.body.decode('utf8'))
    assert body == countries


async def test_run_resource_hook_on_request(api, http_client, collector):
    # Arrange
    def change_route_arg(request):
        request.route_args['p'] = 1
        return request

    api.add('hooked', 'hooked/{p}', hooks=[hook(handle_request=change_route_arg)])
    # register a response for modified request
    http_client.respond_json('hooked/1', 'whatever')

    # Act
    collector.register(api.get('hooked'), {'p': 0})
    await collector.run()

    # Assert
    # the request was modified so we cannot find a response
    should_be_none = collector.get(api.get('hooked'), {'p': 0})
    assert should_be_none is None
    # but we can find one for the modified response
    response = collector.get(api.get('hooked'), {'p': 1})
    assert response is not None


async def test_run_resource_hook_on_response(api, http_client, collector):
    # Arrange
    def add_header(response):
        response.headers['h'] = 1
        return response

    api.add('hooked', 'hooked', hooks=[hook(handle_response=add_header)])
    # register a response
    http_client.respond_json('hooked', 'whatever')

    # Act
    collector.register(api.get('hooked'))
    await collector.run()

    # Assert
    response = collector.get(api.get('hooked'))
    assert response.headers['h'] == 1
