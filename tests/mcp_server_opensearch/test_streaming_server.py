import pytest
import pytest_asyncio
from mcp.types import TextContent
from unittest.mock import AsyncMock, Mock, patch


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


class TestMCPServer:
    @pytest.fixture
    def mock_tool_registry(self):
        return {
            'test-tool': {
                'description': 'Test tool',
                'input_schema': {'type': 'object'},
                'args_model': Mock(),
                'function': AsyncMock(
                    return_value=[TextContent(type='text', text='test result')]
                ),
            }
        }

    @pytest.mark.asyncio
    @patch('mcp_server_opensearch.streaming_server.get_tools')
    async def test_create_mcp_server(self, mock_get_tools, mock_tool_registry):
        mock_get_tools.return_value = mock_tool_registry

        from mcp_server_opensearch.streaming_server import create_mcp_server

        server = await create_mcp_server()

        assert server.name == 'opensearch-agent-tools-mcp'
        mock_get_tools.assert_called_once()

    @pytest.mark.asyncio
    @patch('mcp_server_opensearch.streaming_server.get_tools')
    async def test_list_tools_shape(self, mock_get_tools, mock_tool_registry):
        mock_get_tools.return_value = mock_tool_registry

        from mcp_server_opensearch.streaming_server import create_mcp_server
        from mcp.types import Tool

        await create_mcp_server()

        tools = [
            Tool(
                name=tool_name,
                description=tool_info['description'],
                inputSchema=tool_info['input_schema'],
            )
            for tool_name, tool_info in mock_tool_registry.items()
        ]

        assert len(tools) == 1
        assert tools[0].name == 'test-tool'
        assert tools[0].description == 'Test tool'


class TestMCPStarletteApp:
    @pytest_asyncio.fixture
    async def app_handler(self):
        from mcp_server_opensearch.streaming_server import MCPStarletteApp, create_mcp_server

        with patch(
            'mcp_server_opensearch.streaming_server.get_tools',
            new_callable=AsyncMock,
            return_value={},
        ):
            server = await create_mcp_server()
            return MCPStarletteApp(server)

    def test_create_app(self, app_handler):
        app = app_handler.create_app()
        assert len(app.routes) == 5
        assert app.routes[0].path == '/sse'
        assert app.routes[1].path == '/health'
        assert app.routes[2].path == '/messages'
        assert app.routes[3].path == '/mcp'

    @pytest.mark.asyncio
    async def test_handle_sse(self, app_handler):
        mock_request = Mock()
        mock_read_stream = AsyncMock()
        mock_write_stream = AsyncMock()

        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = (mock_read_stream, mock_write_stream)
        mock_context.__aexit__.return_value = None

        app_handler.sse.connect_sse = Mock(return_value=mock_context)
        app_handler.mcp_server.run = AsyncMock(return_value=None)
        app_handler.mcp_server.create_initialization_options = Mock(return_value={})

        await app_handler.handle_sse(mock_request)

        app_handler.sse.connect_sse.assert_called_once_with(
            mock_request.scope, mock_request.receive, mock_request._send
        )
        app_handler.mcp_server.run.assert_called_once_with(mock_read_stream, mock_write_stream, {})


@pytest.mark.asyncio
async def test_serve():
    from mcp_server_opensearch.streaming_server import serve

    mock_server = AsyncMock()
    mock_config = Mock()

    with (
        patch('uvicorn.Server', return_value=mock_server) as mock_server_class,
        patch('uvicorn.Config', return_value=mock_config) as mock_config_class,
        patch('mcp_server_opensearch.streaming_server.get_tools', return_value={}),
    ):
        await serve(host='localhost', port=8000)

        config_args = mock_config_class.call_args[1]
        assert config_args['host'] == 'localhost'
        assert config_args['port'] == 8000
        mock_server_class.assert_called_once_with(mock_config)
        mock_server.serve.assert_called_once()
