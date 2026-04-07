# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0

import argparse
import asyncio
import json
from typing import Any

from mcp import ClientSession, types
from mcp.client.streamable_http import streamablehttp_client


def _content_to_text(content: list[Any]) -> str:
    parts: list[str] = []
    for item in content:
        if isinstance(item, types.TextContent):
            parts.append(item.text)
        else:
            parts.append(str(item))
    return '\n'.join(parts)


async def main() -> None:
    parser = argparse.ArgumentParser(
        description='Connect to the OpenSearch MCP server and test SearchAgentsTool/ExecuteAgentTool.'
    )
    parser.add_argument(
        '--url',
        default='http://localhost:9900/mcp',
        help='Streamable HTTP MCP endpoint. Default: http://localhost:9900/mcp',
    )
    parser.add_argument(
        '--agent-id',
        default='',
        help='Optional agent ID. If provided, the script will also call ExecuteAgentTool.',
    )
    parser.add_argument(
        '--question',
        default='What tools do you have access to?',
        help='Question used when calling ExecuteAgentTool.',
    )
    args = parser.parse_args()

    async with streamablehttp_client(args.url) as (read_stream, write_stream, _):
        async with ClientSession(read_stream, write_stream) as session:
            init_result = await session.initialize()
            print('Connected to MCP server:')
            print(f'  Server: {init_result.serverInfo.name} {init_result.serverInfo.version}')

            tools_result = await session.list_tools()
            tool_names = sorted(tool.name for tool in tools_result.tools)
            print(f'Found {len(tool_names)} tool(s).')

            required_tools = {
                'GetAgentTool',
                'SearchAgentsTool',
                'RegisterAgentTool',
                'UpdateAgentTool',
                'ExecuteAgentTool',
                'DeleteAgentTool',
            }
            missing_tools = sorted(required_tools - set(tool_names))
            if missing_tools:
                print('Missing expected tools:')
                for tool_name in missing_tools:
                    print(f'  - {tool_name}')
                print('Tip: in single mode, enable `search_relevance` tools first.')
                return

            print('Found expected tools:')
            for tool_name in sorted(required_tools):
                print(f'  - {tool_name}')

            print('\nCalling SearchAgentsTool with default arguments...')
            search_result = await session.call_tool('SearchAgentsTool', arguments={})
            print(_content_to_text(search_result.content))

            if args.agent_id:
                print(f'\nCalling ExecuteAgentTool for agent {args.agent_id}...')
                execute_result = await session.call_tool(
                    'ExecuteAgentTool',
                    arguments={'agent_id': args.agent_id, 'question': args.question},
                )
                print(_content_to_text(execute_result.content))
            else:
                print('\nSkipping ExecuteAgentTool because no --agent-id was provided.')
                print('Pass --agent-id <id> to test agent execution too.')


if __name__ == '__main__':
    asyncio.run(main())
