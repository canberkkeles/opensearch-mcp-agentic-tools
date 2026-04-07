# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0

import logging
import os

from opensearch.helper import get_opensearch_version

from .tool_params import baseToolArgs
from .utils import is_tool_compatible


AGENT_ONLY_TOOL_NAMES = [
    'GetAgentTool',
    'SearchAgentsTool',
    'RegisterAgentTool',
    'UpdateAgentTool',
    'ExecuteAgentTool',
    'DeleteAgentTool',
]

_resolved_allow_write_setting = None


def set_allow_write_setting(allow_write: bool) -> None:
    global _resolved_allow_write_setting
    _resolved_allow_write_setting = allow_write


def get_allow_write_setting() -> bool:
    global _resolved_allow_write_setting
    if _resolved_allow_write_setting is not None:
        return _resolved_allow_write_setting
    return os.getenv('OPENSEARCH_SETTINGS_ALLOW_WRITE', 'true').lower() == 'true'


def _resolve_allow_write_setting(config_file_path: str = None) -> bool:
    return os.getenv('OPENSEARCH_SETTINGS_ALLOW_WRITE', 'true').lower() == 'true'


def process_tool_filter(
    enabled_tools: str = None,
    disabled_tools: str = None,
    tool_categories: str = None,
    enabled_categories: str = None,
    disabled_categories: str = None,
    enabled_tools_regex: str = None,
    disabled_tools_regex: str = None,
    allow_write: bool = None,
    filter_path: str = None,
    tool_registry: dict = None,
) -> None:
    """Keep the server surface focused on agent tools only."""
    del enabled_tools, disabled_tools, tool_categories, enabled_categories
    del enabled_tools_regex, disabled_tools_regex, allow_write, filter_path

    allowed = set(AGENT_ONLY_TOOL_NAMES)
    if disabled_categories and 'agent_tools' in disabled_categories:
        allowed = set()

    for tool_name in list(tool_registry.keys()):
        if tool_name not in allowed:
            tool_registry.pop(tool_name, None)


async def get_tools(tool_registry: dict, config_file_path: str = '') -> dict:
    """Return the agent-only tool set for the single-cluster runtime."""
    resolved_allow_write = _resolve_allow_write_setting(config_file_path)
    set_allow_write_setting(resolved_allow_write)

    filtered_registry = {k: v for k, v in tool_registry.items() if k in AGENT_ONLY_TOOL_NAMES}

    enabled = {}
    version = await get_opensearch_version(baseToolArgs(opensearch_cluster_name=''))
    logging.info(f'Connected OpenSearch version: {version}')

    process_tool_filter(tool_registry=filtered_registry)

    for name, info in filtered_registry.items():
        if not is_tool_compatible(version, info):
            continue

        tool_info = info.copy()
        schema = tool_info['input_schema'].copy()
        if 'properties' in schema:
            for field in baseToolArgs.model_fields.keys():
                schema['properties'].pop(field, None)
                if 'required' in schema and field in schema['required']:
                    schema['required'].remove(field)
        tool_info['input_schema'] = schema
        enabled[name] = tool_info

    return enabled
