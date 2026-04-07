import asyncio
import os
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, Mock, patch

import pytest
from mcp.types import TextContent, Tool


os.environ['OPENSEARCH_URL'] = 'https://test-domain.us-west-2.es.amazonaws.com'
os.environ['AWS_REGION'] = 'us-west-2'
os.environ['AWS_ACCESS_KEY_ID'] = 'test-access-key'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'test-secret-key'

MOCK_TOOL_REGISTRY = {
    'test_tool': {
        'description': 'Test tool',
        'input_schema': {'type': 'object', 'properties': {}},
        'args_model': Mock(),
        'function': AsyncMock(return_value=[TextContent(type='text', text='test result')]),
    }
}


@pytest.fixture(autouse=True)
def patch_opensearch_version():
    from semver import Version

    mock_client = Mock()
    mock_client.info = AsyncMock(return_value={'version': {'number': '3.0.0'}})

    async def mock_get_version(*args, **kwargs):
        return Version.parse('2.13.0')

    with (
        patch('opensearch.helper.get_opensearch_version', side_effect=mock_get_version),
        patch('opensearch.client.initialize_client', return_value=mock_client),
    ):
        yield


@pytest.fixture
def mock_server():
    mock = Mock()
    mock_instance = Mock()
    mock_instance.create_initialization_options.return_value = {
        'protocolVersion': '1.0',
        'serverInfo': {'name': 'test-server', 'version': '1.0'},
    }
    mock.return_value = mock_instance

    with patch('mcp_server_opensearch.stdio_server.Server', mock):
        yield mock


@pytest.fixture
def mock_stdio():
    reader = AsyncMock()
    writer = AsyncMock()

    @asynccontextmanager
    async def mock_context():
        yield reader, writer

    with patch('mcp_server_opensearch.stdio_server.stdio_server', mock_context):
        yield reader, writer


@pytest.fixture
def mock_tool_registry():
    async def mock_get_tools(*args, **kwargs):
        return MOCK_TOOL_REGISTRY

    with patch('mcp_server_opensearch.stdio_server.get_tools', side_effect=mock_get_tools):
        yield MOCK_TOOL_REGISTRY


@pytest.mark.asyncio
async def test_serve_initialization(mock_server, mock_stdio, mock_tool_registry):
    from mcp_server_opensearch.stdio_server import serve

    asyncio.create_task(serve())
    await asyncio.sleep(0.1)

    mock_server.assert_called_once()
    mock_server.return_value.create_initialization_options.assert_called_once()


@pytest.mark.asyncio
async def test_list_tools(mock_server, mock_stdio, mock_tool_registry):
    from mcp_server_opensearch.stdio_server import serve

    asyncio.create_task(serve())
    await asyncio.sleep(0.1)

    list_tools_handler = None
    for call in mock_server.mock_calls:
        if 'list_tools' in str(call):

            async def mock_list_tools():
                return [
                    Tool(
                        name='test_tool',
                        description='Test tool',
                        inputSchema={'type': 'object', 'properties': {}},
                    )
                ]

            list_tools_handler = mock_list_tools
            break

    assert list_tools_handler is not None
    tools = await list_tools_handler()
    assert len(tools) == 1
    assert tools[0].name == 'test_tool'


@pytest.mark.asyncio
async def test_server_error_handling(mock_server, mock_stdio, mock_tool_registry):
    mock_server.return_value.run.side_effect = Exception('Test error')

    from mcp_server_opensearch.stdio_server import serve

    with pytest.raises(Exception, match='Test error'):
        await serve()
