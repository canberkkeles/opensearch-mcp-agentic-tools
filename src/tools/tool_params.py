# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0

from typing import Any, Dict, Optional, Type, TypeVar

from pydantic import BaseModel, Field

T = TypeVar('T', bound=BaseModel)


def validate_args_for_mode(args_dict: Dict[str, Any], args_model_class: Type[T]) -> T:
    """Validate tool arguments while keeping cluster selection internal only."""
    args_dict = args_dict.copy()
    args_dict.setdefault('opensearch_cluster_name', '')

    try:
        return args_model_class(**args_dict)
    except Exception as e:
        import re

        error_str = str(e)
        missing_fields = re.findall(r'^(\w+)\n  Field required', error_str, re.MULTILINE)
        if missing_fields:
            field_list = ', '.join(f"'{field}'" for field in missing_fields)
            error_msg = (
                f'Missing required field: {field_list}'
                if len(missing_fields) == 1
                else f'Missing required fields: {field_list}'
            )
            user_input = {k: v for k, v in args_dict.items() if k != 'opensearch_cluster_name'}
            error_msg += f'\n\nProvided: {user_input}'
            raise ValueError(error_msg) from e
        raise


class baseToolArgs(BaseModel):
    """Base class for tool arguments."""

    opensearch_cluster_name: str = Field(description='The name of the OpenSearch cluster')


class GetAgentArgs(baseToolArgs):
    """Arguments for the GetAgentTool."""

    agent_id: str = Field(description='ID of the agent to retrieve')

    class Config:
        json_schema_extra = {'examples': [{'agent_id': '879v9YwBjWKCe6Kg12Tx'}]}


class SearchAgentsArgs(baseToolArgs):
    """Arguments for the SearchAgentsTool."""

    query_body: Optional[Any] = Field(
        default=None,
        description=(
            'OpenSearch query DSL body used to search registered ML agents. '
            'Defaults to {"query": {"match_all": {}}, "size": 1000} if not provided.'
        ),
    )

    class Config:
        json_schema_extra = {
            'examples': [
                {},
                {'query_body': {'query': {'match_all': {}}, 'size': 1000}},
                {'query_body': {'query': {'match': {'name': 'agentic search'}}, 'size': 10}},
            ]
        }


class RegisterAgentArgs(baseToolArgs):
    """Arguments for the RegisterAgentTool."""

    agent_definition: Any = Field(
        description='Full OpenSearch agent registration body as a JSON object or JSON string.'
    )

    class Config:
        json_schema_extra = {
            'examples': [
                {
                    'agent_definition': {
                        'name': 'demo-agent',
                        'type': 'flow',
                        'description': 'Demo agent for agentic search',
                        'tools': [],
                    }
                }
            ]
        }


class UpdateAgentArgs(baseToolArgs):
    """Arguments for the UpdateAgentTool."""

    agent_id: str = Field(description='ID of the agent to update')
    agent_update: Any = Field(
        description='Partial OpenSearch agent update body as a JSON object or JSON string.'
    )

    class Config:
        json_schema_extra = {
            'examples': [
                {
                    'agent_id': '879v9YwBjWKCe6Kg12Tx',
                    'agent_update': {
                        'name': 'demo-agent-updated',
                        'description': 'Updated demo agent',
                    },
                }
            ]
        }


class ExecuteAgentArgs(baseToolArgs):
    """Arguments for the ExecuteAgentTool."""

    agent_id: str = Field(description='ID of the agent to execute')
    question: Optional[str] = Field(
        default=None,
        description='Question to ask the agent using the regular execution API.',
    )
    input: Optional[Any] = Field(
        default=None,
        description='Unified agent input for newer OpenSearch agent execution APIs.',
    )
    parameters: Optional[Any] = Field(
        default=None,
        description='Optional JSON object of execution parameters to merge into the request body.',
    )
    verbose: bool = Field(default=False, description='Whether to request verbose execution output.')
    memory_id: Optional[str] = Field(
        default=None,
        description='Conversation memory ID used to continue an existing conversational agent session.',
    )
    memory_container_id: Optional[str] = Field(
        default=None,
        description='Optional memory container override for agents using agentic memory.',
    )
    async_execution: bool = Field(
        default=False,
        description='If true, executes the agent asynchronously and returns a task ID when supported.',
    )

    class Config:
        json_schema_extra = {
            'examples': [
                {
                    'agent_id': '879v9YwBjWKCe6Kg12Tx',
                    'question': "what's the population increase of Seattle from 2021 to 2023",
                },
                {
                    'agent_id': '879v9YwBjWKCe6Kg12Tx',
                    'question': 'List all the flowers present',
                    'memory_id': 'iEgpJZwBZx9B0F4spD5v',
                    'verbose': True,
                },
                {
                    'agent_id': '879v9YwBjWKCe6Kg12Tx',
                    'input': 'What tools do you have access to?',
                },
            ]
        }


class DeleteAgentArgs(baseToolArgs):
    """Arguments for the DeleteAgentTool."""

    agent_id: str = Field(description='ID of the agent to delete')

    class Config:
        json_schema_extra = {'examples': [{'agent_id': '879v9YwBjWKCe6Kg12Tx'}]}
