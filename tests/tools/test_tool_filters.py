import copy
from unittest.mock import MagicMock, patch

import pytest
from semver import Version

from tools.tool_filter import AGENT_ONLY_TOOL_NAMES, get_tools, process_tool_filter
from tools.utils import is_tool_compatible


MOCK_TOOL_REGISTRY = {
    'GetAgentTool': {
        'display_name': 'GetAgentTool',
        'description': 'Get an agent',
        'input_schema': {
            'type': 'object',
            'properties': {
                'opensearch_cluster_name': {'type': 'string'},
                'agent_id': {'type': 'string'},
            },
        },
        'function': MagicMock(),
        'args_model': MagicMock(),
        'min_version': '2.13.0',
    },
    'SearchAgentsTool': {
        'display_name': 'SearchAgentsTool',
        'description': 'Search agents',
        'input_schema': {
            'type': 'object',
            'properties': {
                'opensearch_cluster_name': {'type': 'string'},
                'query_body': {'type': 'object'},
            },
        },
        'function': MagicMock(),
        'args_model': MagicMock(),
        'min_version': '2.13.0',
    },
    'ExecuteAgentTool': {
        'display_name': 'ExecuteAgentTool',
        'description': 'Execute an agent',
        'input_schema': {
            'type': 'object',
            'properties': {
                'opensearch_cluster_name': {'type': 'string'},
                'agent_id': {'type': 'string'},
                'question': {'type': 'string'},
            },
        },
        'function': MagicMock(),
        'args_model': MagicMock(),
        'min_version': '2.13.0',
    },
    'ListIndexTool': {
        'display_name': 'ListIndexTool',
        'description': 'Legacy tool that should not be exposed',
        'input_schema': {'type': 'object', 'properties': {'index': {'type': 'string'}}},
        'function': MagicMock(),
        'args_model': MagicMock(),
        'min_version': '1.0.0',
    },
}


class TestIsToolCompatible:
    def test_version_within_range(self):
        tool_info = {'min_version': '1.0.0', 'max_version': '3.0.0'}
        assert is_tool_compatible(Version.parse('2.0.0'), tool_info) is True


class TestGetTools:
    @pytest.fixture
    def mock_tool_registry(self):
        return copy.deepcopy(MOCK_TOOL_REGISTRY)

    @pytest.mark.asyncio
    async def test_get_tools_filters_and_removes_base_fields(self, mock_tool_registry):
        with (
            patch('tools.tool_filter.get_opensearch_version', return_value=Version.parse('2.13.0')),
            patch('tools.tool_filter.is_tool_compatible', return_value=True),
        ):
            result = await get_tools(mock_tool_registry)

        assert set(result.keys()) == {'GetAgentTool', 'SearchAgentsTool', 'ExecuteAgentTool'}
        assert 'opensearch_cluster_name' not in result['GetAgentTool']['input_schema']['properties']

    @pytest.mark.asyncio
    async def test_get_tools_excludes_non_agent_tools(self, mock_tool_registry):
        with (
            patch('tools.tool_filter.get_opensearch_version', return_value=Version.parse('2.13.0')),
            patch('tools.tool_filter.is_tool_compatible', return_value=True),
        ):
            result = await get_tools(mock_tool_registry)

        assert 'ListIndexTool' not in result

    @pytest.mark.asyncio
    async def test_get_tools_logs_version_info(self, mock_tool_registry, caplog):
        with (
            patch('tools.tool_filter.get_opensearch_version', return_value=Version.parse('2.13.0')),
            patch('tools.tool_filter.is_tool_compatible', return_value=True),
            caplog.at_level('INFO'),
        ):
            await get_tools(mock_tool_registry)

        assert 'Connected OpenSearch version: 2.13.0' in caplog.text


class TestProcessToolFilter:
    def test_process_tool_filter_defaults_to_agent_tools(self):
        registry = copy.deepcopy(MOCK_TOOL_REGISTRY)
        process_tool_filter(tool_registry=registry, allow_write=True)
        assert set(registry.keys()) == {'GetAgentTool', 'SearchAgentsTool', 'ExecuteAgentTool'}

    def test_process_tool_filter_can_disable_agent_tools(self):
        registry = copy.deepcopy(MOCK_TOOL_REGISTRY)
        process_tool_filter(
            tool_registry=registry,
            disabled_categories='agent_tools',
            allow_write=True,
        )
        assert registry == {}

    def test_agent_only_tool_list_contains_expected_names(self):
        assert AGENT_ONLY_TOOL_NAMES == [
            'GetAgentTool',
            'SearchAgentsTool',
            'RegisterAgentTool',
            'UpdateAgentTool',
            'ExecuteAgentTool',
            'DeleteAgentTool',
        ]
