# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0

import json
import logging

from semver import Version

from tools.tool_params import (
    DeleteAgentArgs,
    ExecuteAgentArgs,
    GetAgentArgs,
    RegisterAgentArgs,
    SearchAgentsArgs,
    UpdateAgentArgs,
    baseToolArgs,
)


logger = logging.getLogger(__name__)


def validate_json_string(value: str) -> None:
    """Validate that a string is valid JSON."""
    try:
        json.loads(value)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"query is not valid JSON: {e.msg} (line {e.lineno}, col {e.colno})"
        ) from e


async def get_agent(args: GetAgentArgs) -> json:
    """Retrieve a registered ML agent by ID."""
    from .client import get_opensearch_client

    async with get_opensearch_client(args) as client:
        return await client.transport.perform_request(
            method='GET', url=f'/_plugins/_ml/agents/{args.agent_id}'
        )


async def search_agents(args: SearchAgentsArgs) -> json:
    """Search registered ML agents using OpenSearch query DSL."""
    from .client import get_opensearch_client

    if args.query_body is None:
        body = {'query': {'match_all': {}}, 'size': 1000}
    elif isinstance(args.query_body, str):
        validate_json_string(args.query_body)
        body = json.loads(args.query_body)
    else:
        body = args.query_body

    async with get_opensearch_client(args) as client:
        return await client.transport.perform_request(
            method='POST', url='/_plugins/_ml/agents/_search', body=json.dumps(body)
        )


async def register_agent(args: RegisterAgentArgs) -> json:
    """Register a new ML agent."""
    from .client import get_opensearch_client

    agent_definition = args.agent_definition
    if isinstance(agent_definition, str):
        validate_json_string(agent_definition)
        agent_definition = json.loads(agent_definition)

    async with get_opensearch_client(args) as client:
        return await client.transport.perform_request(
            method='POST',
            url='/_plugins/_ml/agents/_register',
            body=json.dumps(agent_definition),
        )


async def update_agent(args: UpdateAgentArgs) -> json:
    """Update an existing ML agent."""
    from .client import get_opensearch_client

    agent_update = args.agent_update
    if isinstance(agent_update, str):
        validate_json_string(agent_update)
        agent_update = json.loads(agent_update)

    async with get_opensearch_client(args) as client:
        return await client.transport.perform_request(
            method='PUT',
            url=f'/_plugins/_ml/agents/{args.agent_id}',
            body=json.dumps(agent_update),
        )


async def execute_agent(args: ExecuteAgentArgs) -> json:
    """Execute an ML agent using either the regular or unified execution format."""
    from .client import get_opensearch_client

    if not args.question and args.input is None and args.parameters is None:
        raise ValueError(
            'Provide at least one of question, input, or parameters when executing an agent'
        )

    parameters = args.parameters
    if isinstance(parameters, str):
        validate_json_string(parameters)
        parameters = json.loads(parameters)

    if parameters is not None and not isinstance(parameters, dict):
        raise ValueError('parameters must be a JSON object when provided')

    body: dict = {}
    if args.input is not None:
        body['input'] = args.input

    if (
        args.question is not None
        or parameters is not None
        or args.verbose
        or args.memory_id
        or args.memory_container_id
    ):
        merged_parameters = dict(parameters or {})
        if args.question is not None:
            merged_parameters['question'] = args.question
        if args.verbose:
            merged_parameters['verbose'] = True
        if args.memory_id:
            merged_parameters['memory_id'] = args.memory_id
        if args.memory_container_id:
            merged_parameters['memory_container_id'] = args.memory_container_id
        body['parameters'] = merged_parameters

    async with get_opensearch_client(args) as client:
        request_params = {
            'method': 'POST',
            'url': f'/_plugins/_ml/agents/{args.agent_id}/_execute',
            'body': json.dumps(body),
        }
        if args.async_execution:
            request_params['params'] = {'async': 'true'}
        return await client.transport.perform_request(**request_params)


async def delete_agent(args: DeleteAgentArgs) -> json:
    """Delete a registered ML agent."""
    from .client import get_opensearch_client

    async with get_opensearch_client(args) as client:
        return await client.transport.perform_request(
            method='DELETE', url=f'/_plugins/_ml/agents/{args.agent_id}'
        )


async def get_opensearch_version(args: baseToolArgs) -> Version:
    """Get the version of the connected OpenSearch cluster."""
    from .client import get_opensearch_client

    try:
        async with get_opensearch_client(args) as client:
            response = await client.info()
            return Version.parse(response['version']['number'])
    except Exception as e:
        logger.error(f'Error getting OpenSearch version: {e}')
        return None
