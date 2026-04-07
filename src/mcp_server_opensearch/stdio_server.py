# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0

import asyncio
import logging
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool
from tools.tool_filter import get_tools
from tools.tools import TOOL_REGISTRY


# --- Server setup ---
async def serve() -> None:
    server = Server('opensearch-agent-tools-mcp')
    enabled_tools = await get_tools(tool_registry=TOOL_REGISTRY)
    logging.info(f'Enabled tools: {list(enabled_tools.keys())}')

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        tools = []
        for tool_name, tool_info in enabled_tools.items():
            tools.append(
                Tool(
                    name=tool_info.get('display_name', tool_name),
                    description=tool_info['description'],
                    inputSchema=tool_info['input_schema'],
                )
            )
        return tools

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        from mcp_server_opensearch.tool_executor import execute_tool

        return await execute_tool(name, arguments, enabled_tools)

    # Start stdio-based MCP server
    from mcp_server_opensearch.logging_config import start_memory_monitor

    options = server.create_initialization_options()
    async with stdio_server() as (reader, writer):
        monitor_task = start_memory_monitor()
        try:
            await server.run(reader, writer, options, raise_exceptions=True)
        finally:
            monitor_task.cancel()
            try:
                await monitor_task
            except (asyncio.CancelledError, Exception):
                pass
