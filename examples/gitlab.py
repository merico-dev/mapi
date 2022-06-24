import os

from mapi import API, Collector
from mapi.hooks import HeaderPagination, SetHeader, SetQueryParams, Log, ParseJson


token = os.environ['GITLAB_ACCESS_TOKEN']
if not token:
    raise Exception('Set GITLAB_ACCESS_TOKEN env var')

auth = SetHeader('PRIVATE-TOKEN', token)
paged_hooks = [
    SetQueryParams(scope='all', per_page='100'),
    HeaderPagination()
]

api = (
    API('https://www.gitlab.com/api/v4')
    .add(
        name='project_issues',
        route_template='projects/{project}/issues',
        hooks=paged_hooks
    )
    .add(
        name='projects_merge_requests',
        route_template='projects/{project}/merge_requests',
        hooks=paged_hooks
    )
    .hook(Log('gitlab'))
    .hook(auth)
    .hook(ParseJson())
)

project = 11624398 # meta-analytics id

collector = (
    Collector()
    .register(api.get('project_issues'), route_args={'project': project})
    .register(api.get('projects_merge_requests'), route_args={'project': project})
)

collector.run()

for response in collector.iter_responses():
    print(response)
    print(response.body)
