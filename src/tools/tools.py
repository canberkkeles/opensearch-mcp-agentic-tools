# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0

import json

from opensearch.helper import (
    delete_agent,
    execute_agent,
    get_agent,
    get_opensearch_version,
    register_agent,
    search_agents,
    update_agent,
)

from .tool_logging import log_tool_error
from .tool_params import (
    DeleteAgentArgs,
    ExecuteAgentArgs,
    GetAgentArgs,
    RegisterAgentArgs,
    SearchAgentsArgs,
    UpdateAgentArgs,
    baseToolArgs,
)
from .utils import is_tool_compatible


async def check_tool_compatibility(tool_name: str, args: baseToolArgs | None = None):
    opensearch_version = await get_opensearch_version(args)
    if not is_tool_compatible(opensearch_version, TOOL_REGISTRY[tool_name]):
        tool_display_name = TOOL_REGISTRY[tool_name].get('display_name', tool_name)
        min_version = TOOL_REGISTRY[tool_name].get('min_version', '')
        max_version = TOOL_REGISTRY[tool_name].get('max_version', '')

        version_info = (
            f'{min_version} to {max_version}'
            if min_version and max_version
            else f'{min_version} or later'
            if min_version
            else f'up to {max_version}'
            if max_version
            else None
        )

        error_message = f"Tool '{tool_display_name}' is not supported for this OpenSearch version (current version: {opensearch_version})."
        if version_info:
            error_message += f' Supported version: {version_info}.'
        raise Exception(error_message)


async def get_agent_tool(args: GetAgentArgs) -> list[dict]:
    try:
        await check_tool_compatibility('GetAgentTool', args)
        result = await get_agent(args)
        formatted_result = json.dumps(result, separators=(',', ':'))
        return [{'type': 'text', 'text': f'Agent {args.agent_id}:\n{formatted_result}'}]
    except Exception as e:
        return log_tool_error('GetAgentTool', e, 'retrieving agent', agent_id=args.agent_id)


async def search_agents_tool(args: SearchAgentsArgs) -> list[dict]:
    try:
        await check_tool_compatibility('SearchAgentsTool', args)
        result = await search_agents(args)
        formatted_result = json.dumps(result, separators=(',', ':'))
        return [{'type': 'text', 'text': f'Agent search results:\n{formatted_result}'}]
    except Exception as e:
        return log_tool_error('SearchAgentsTool', e, 'searching agents')


async def register_agent_tool(args: RegisterAgentArgs) -> list[dict]:
    try:
        await check_tool_compatibility('RegisterAgentTool', args)
        result = await register_agent(args)
        formatted_result = json.dumps(result, separators=(',', ':'))
        return [{'type': 'text', 'text': f'Agent registered:\n{formatted_result}'}]
    except Exception as e:
        return log_tool_error('RegisterAgentTool', e, 'registering agent')


async def update_agent_tool(args: UpdateAgentArgs) -> list[dict]:
    try:
        await check_tool_compatibility('UpdateAgentTool', args)
        result = await update_agent(args)
        formatted_result = json.dumps(result, separators=(',', ':'))
        return [{'type': 'text', 'text': f'Agent {args.agent_id} updated:\n{formatted_result}'}]
    except Exception as e:
        return log_tool_error('UpdateAgentTool', e, 'updating agent', agent_id=args.agent_id)


async def execute_agent_tool(args: ExecuteAgentArgs) -> list[dict]:
    try:
        await check_tool_compatibility('ExecuteAgentTool', args)
        result = await execute_agent(args)
        formatted_result = json.dumps(result, separators=(',', ':'))
        return [{'type': 'text', 'text': f'Agent execution result for {args.agent_id}:\n{formatted_result}'}]
    except Exception as e:
        return log_tool_error('ExecuteAgentTool', e, 'executing agent', agent_id=args.agent_id)


async def delete_agent_tool(args: DeleteAgentArgs) -> list[dict]:
    try:
        await check_tool_compatibility('DeleteAgentTool', args)
        result = await delete_agent(args)
        formatted_result = json.dumps(result, separators=(',', ':'))
        return [{'type': 'text', 'text': f'Agent {args.agent_id} deleted:\n{formatted_result}'}]
    except Exception as e:
        return log_tool_error('DeleteAgentTool', e, 'deleting agent', agent_id=args.agent_id)


TOOL_REGISTRY = {
    'GetAgentTool': {
        'display_name': 'GetAgentTool',
        'description': 'Retrieves a registered OpenSearch ML agent by ID.',
        'input_schema': GetAgentArgs.model_json_schema(),
        'function': get_agent_tool,
        'args_model': GetAgentArgs,
        'min_version': '2.13.0',
        'http_methods': 'GET',
    },
    'SearchAgentsTool': {
        'display_name': 'SearchAgentsTool',
        'description': (
            'Searches registered OpenSearch ML agents using query DSL. '
            'Returns all agents when called without a query body.'
        ),
        'input_schema': SearchAgentsArgs.model_json_schema(),
        'function': search_agents_tool,
        'args_model': SearchAgentsArgs,
        'min_version': '2.13.0',
        'http_methods': 'GET, POST',
    },
    'RegisterAgentTool': {
        'display_name': 'RegisterAgentTool',
        'description': 'Registers a new OpenSearch ML agent from a full agent definition body.',
        'input_schema': RegisterAgentArgs.model_json_schema(),
        'function': register_agent_tool,
        'args_model': RegisterAgentArgs,
        'min_version': '2.13.0',
        'http_methods': 'POST',
    },
    'UpdateAgentTool': {
        'display_name': 'UpdateAgentTool',
        'description': 'Updates an existing OpenSearch ML agent by ID.',
        'input_schema': UpdateAgentArgs.model_json_schema(),
        'function': update_agent_tool,
        'args_model': UpdateAgentArgs,
        'min_version': '2.13.0',
        'http_methods': 'PUT',
    },
    'ExecuteAgentTool': {
        'display_name': 'ExecuteAgentTool',
        'description': (
            'Executes a registered OpenSearch ML agent using either question-based or unified input.'
        ),
        'input_schema': ExecuteAgentArgs.model_json_schema(),
        'function': execute_agent_tool,
        'args_model': ExecuteAgentArgs,
        'min_version': '2.13.0',
        'http_methods': 'POST',
    },
    'DeleteAgentTool': {
        'display_name': 'DeleteAgentTool',
        'description': 'Deletes a registered OpenSearch ML agent by ID.',
        'input_schema': DeleteAgentArgs.model_json_schema(),
        'function': delete_agent_tool,
        'args_model': DeleteAgentArgs,
        'min_version': '2.13.0',
        'http_methods': 'DELETE',
    },
}
