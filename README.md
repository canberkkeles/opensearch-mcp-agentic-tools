# OpenSearch Agent Tools MCP

`opensearch-agent-tools-mcp` is a small MCP server focused on OpenSearch ML agent operations. It is intended for agentic search demos and containerized integrations where the MCP surface should expose only agent-related capabilities.

It supports both stdio and streamable HTTP transports, so it can be used from local MCP clients or hosted behind environments such as Amazon Bedrock AgentCore Runtime.

## Included Tools

- `GetAgentTool`
- `SearchAgentsTool`
- `RegisterAgentTool`
- `UpdateAgentTool`
- `ExecuteAgentTool`
- `DeleteAgentTool`

These tools are thin wrappers over the OpenSearch ML agent APIs:

- `GET /_plugins/_ml/agents/{agent_id}`
- `POST /_plugins/_ml/agents/_search`
- `POST /_plugins/_ml/agents/_register`
- `PUT /_plugins/_ml/agents/{agent_id}`
- `POST /_plugins/_ml/agents/{agent_id}/_execute`
- `DELETE /_plugins/_ml/agents/{agent_id}`

## Quick Start

Set your OpenSearch connection settings in PowerShell. Use one of these auth patterns:

```powershell
$env:OPENSEARCH_URL="https://your-domain.us-east-1.es.amazonaws.com"
$env:OPENSEARCH_USERNAME="your-username"
$env:OPENSEARCH_PASSWORD="your-password"
```

Or, for AWS-signed access using the runtime identity or an assumable role:

```powershell
$env:OPENSEARCH_URL="https://your-domain.aos.us-east-1.on.aws"
$env:AWS_REGION="us-east-1"
$env:AWS_IAM_ARN="arn:aws:iam::123456789012:role/YourOpenSearchAccessRole"
```

If the container already runs with the right IAM permissions, you can omit `AWS_IAM_ARN` and let the server use ambient AWS credentials from the runtime.

Run the streaming server:

```powershell
uv run python -m mcp_server_opensearch --transport stream --port 9900
```

Health check:

```powershell
curl http://localhost:9900/health
```

Connect your MCP client to:

```text
http://localhost:9900/mcp
```

Optional env vars:

- `AWS_PROFILE` to force a named local AWS profile
- `AWS_OPENSEARCH_SERVERLESS=true` for OpenSearch Serverless
- `OPENSEARCH_NO_AUTH=true` for local no-auth development
- `OPENSEARCH_SSL_VERIFY=false` for local/self-signed testing only
- `OPENSEARCH_TIMEOUT=30`
- `OPENSEARCH_MAX_RESPONSE_SIZE=5242880`
- `FASTMCP_LOG_LEVEL=INFO`

## MCP Smoke Test

After the server is running, you can verify the MCP surface with:

```powershell
uv run python scripts\test_mcp_agent_tools.py
```

To also test execution:

```powershell
uv run python scripts\test_mcp_agent_tools.py --agent-id YOUR_AGENT_ID
```

## Bedrock AgentCore Notes

This repo is designed to be a narrow MCP backend for agentic workflows. For Bedrock AgentCore Runtime, the recommended path is:

1. Package the server into a container.
2. Provide OpenSearch settings through environment variables.
3. Run the server with `--transport stream`.
4. Expose the `/mcp` endpoint from the container.
5. Let your AgentCore agent use the six MCP tools above as its OpenSearch agent control plane.

There is no YAML runtime configuration path anymore. The server is intentionally single-cluster and env-driven.
