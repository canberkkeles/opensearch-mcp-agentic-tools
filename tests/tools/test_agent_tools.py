# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0

import json
from unittest.mock import AsyncMock, Mock, patch

import pytest


class TestAgentTools:
    def setup_method(self):
        """Setup that runs before each test method."""
        self.mock_client = Mock()
        self.mock_client.info = AsyncMock(return_value={'version': {'number': '3.5.0'}})
        self.mock_client.transport = Mock()
        self.mock_client.transport.perform_request = AsyncMock(return_value={})

        self.init_client_patcher = patch(
            'opensearch.client.initialize_client', return_value=self.mock_client
        )
        self.init_client_patcher.start()

        import sys

        for module in ['tools.tools']:
            if module in sys.modules:
                del sys.modules[module]

        from tools.tools import (
            DeleteAgentArgs,
            ExecuteAgentArgs,
            GetAgentArgs,
            RegisterAgentArgs,
            SearchAgentsArgs,
            UpdateAgentArgs,
            delete_agent_tool,
            execute_agent_tool,
            get_agent_tool,
            register_agent_tool,
            search_agents_tool,
            update_agent_tool,
        )

        self.DeleteAgentArgs = DeleteAgentArgs
        self.ExecuteAgentArgs = ExecuteAgentArgs
        self.GetAgentArgs = GetAgentArgs
        self.RegisterAgentArgs = RegisterAgentArgs
        self.SearchAgentsArgs = SearchAgentsArgs
        self.UpdateAgentArgs = UpdateAgentArgs
        self._delete_agent_tool = delete_agent_tool
        self._execute_agent_tool = execute_agent_tool
        self._get_agent_tool = get_agent_tool
        self._register_agent_tool = register_agent_tool
        self._search_agents_tool = search_agents_tool
        self._update_agent_tool = update_agent_tool

    def teardown_method(self):
        """Cleanup after each test method."""
        self.init_client_patcher.stop()

    @pytest.mark.asyncio
    async def test_get_agent_success(self):
        self.mock_client.transport.perform_request.return_value = {'_id': 'agent-123'}

        result = await self._get_agent_tool(
            self.GetAgentArgs(opensearch_cluster_name='', agent_id='agent-123')
        )

        assert len(result) == 1
        assert 'Agent agent-123' in result[0]['text']
        call_kwargs = self.mock_client.transport.perform_request.call_args
        assert call_kwargs.kwargs['method'] == 'GET'
        assert call_kwargs.kwargs['url'] == '/_plugins/_ml/agents/agent-123'

    @pytest.mark.asyncio
    async def test_search_agents_default_query(self):
        self.mock_client.transport.perform_request.return_value = {
            'hits': {'total': {'value': 2}, 'hits': []}
        }

        result = await self._search_agents_tool(
            self.SearchAgentsArgs(opensearch_cluster_name='')
        )

        assert len(result) == 1
        assert result[0]['type'] == 'text'
        assert 'Agent search results' in result[0]['text']

        call_kwargs = self.mock_client.transport.perform_request.call_args
        assert call_kwargs.kwargs['method'] == 'POST'
        assert call_kwargs.kwargs['url'] == '/_plugins/_ml/agents/_search'
        body = json.loads(call_kwargs.kwargs['body'])
        assert body == {'query': {'match_all': {}}, 'size': 1000}

    @pytest.mark.asyncio
    async def test_register_agent_success(self):
        self.mock_client.transport.perform_request.return_value = {'_id': 'agent-new'}

        result = await self._register_agent_tool(
            self.RegisterAgentArgs(
                opensearch_cluster_name='',
                agent_definition={
                    'name': 'demo-agent',
                    'type': 'flow',
                    'description': 'Demo agent',
                },
            )
        )

        assert len(result) == 1
        assert 'Agent registered' in result[0]['text']
        call_kwargs = self.mock_client.transport.perform_request.call_args
        assert call_kwargs.kwargs['method'] == 'POST'
        assert call_kwargs.kwargs['url'] == '/_plugins/_ml/agents/_register'

    @pytest.mark.asyncio
    async def test_update_agent_success(self):
        self.mock_client.transport.perform_request.return_value = {'result': 'updated'}

        result = await self._update_agent_tool(
            self.UpdateAgentArgs(
                opensearch_cluster_name='',
                agent_id='agent-123',
                agent_update={'description': 'Updated demo agent'},
            )
        )

        assert len(result) == 1
        assert 'Agent agent-123 updated' in result[0]['text']
        call_kwargs = self.mock_client.transport.perform_request.call_args
        assert call_kwargs.kwargs['method'] == 'PUT'
        assert call_kwargs.kwargs['url'] == '/_plugins/_ml/agents/agent-123'

    @pytest.mark.asyncio
    async def test_execute_agent_with_question(self):
        self.mock_client.transport.perform_request.return_value = {
            'inference_results': [{'output': [{'result': 'ok'}]}]
        }

        result = await self._execute_agent_tool(
            self.ExecuteAgentArgs(
                opensearch_cluster_name='',
                agent_id='agent-123',
                question='List all the flowers present',
                verbose=True,
                memory_id='memory-1',
            )
        )

        assert len(result) == 1
        assert 'Agent execution result for agent-123' in result[0]['text']

        call_kwargs = self.mock_client.transport.perform_request.call_args
        assert call_kwargs.kwargs['method'] == 'POST'
        assert call_kwargs.kwargs['url'] == '/_plugins/_ml/agents/agent-123/_execute'
        body = json.loads(call_kwargs.kwargs['body'])
        assert body == {
            'parameters': {
                'question': 'List all the flowers present',
                'verbose': True,
                'memory_id': 'memory-1',
            }
        }

    @pytest.mark.asyncio
    async def test_execute_agent_with_input_and_async(self):
        self.mock_client.transport.perform_request.return_value = {'task_id': 'task-123'}

        await self._execute_agent_tool(
            self.ExecuteAgentArgs(
                opensearch_cluster_name='',
                agent_id='agent-456',
                input='What tools do you have access to?',
                parameters={'tool_choice': 'auto'},
                async_execution=True,
            )
        )

        call_kwargs = self.mock_client.transport.perform_request.call_args
        body = json.loads(call_kwargs.kwargs['body'])
        assert body == {
            'input': 'What tools do you have access to?',
            'parameters': {'tool_choice': 'auto'},
        }
        assert call_kwargs.kwargs['params'] == {'async': 'true'}

    @pytest.mark.asyncio
    async def test_delete_agent_success(self):
        self.mock_client.transport.perform_request.return_value = {'result': 'deleted'}

        result = await self._delete_agent_tool(
            self.DeleteAgentArgs(opensearch_cluster_name='', agent_id='agent-123')
        )

        assert len(result) == 1
        assert 'Agent agent-123 deleted' in result[0]['text']
        call_kwargs = self.mock_client.transport.perform_request.call_args
        assert call_kwargs.kwargs['method'] == 'DELETE'
        assert call_kwargs.kwargs['url'] == '/_plugins/_ml/agents/agent-123'

    @pytest.mark.asyncio
    async def test_execute_agent_requires_input(self):
        result = await self._execute_agent_tool(
            self.ExecuteAgentArgs(opensearch_cluster_name='', agent_id='agent-789')
        )

        assert 'Error executing agent' in result[0]['text']
        assert 'Provide at least one of question, input, or parameters' in result[0]['text']

    @pytest.mark.asyncio
    async def test_agent_tools_registered_in_registry(self):
        import sys

        for module in ['tools.tools']:
            if module in sys.modules:
                del sys.modules[module]

        from tools.tools import TOOL_REGISTRY

        for tool_name in [
            'GetAgentTool',
            'SearchAgentsTool',
            'RegisterAgentTool',
            'UpdateAgentTool',
            'ExecuteAgentTool',
            'DeleteAgentTool',
        ]:
            assert tool_name in TOOL_REGISTRY
            tool = TOOL_REGISTRY[tool_name]
            assert 'description' in tool
            assert 'input_schema' in tool
            assert 'function' in tool
            assert 'args_model' in tool
            assert tool.get('min_version') == '2.13.0'
