import os
from unittest.mock import AsyncMock, Mock, patch

import boto3
import pytest
from opensearchpy import AWSV4SignerAsyncAuth
from starlette.requests import Request

from opensearch.client import (
    AuthenticationError,
    BufferedAsyncHttpConnection,
    ConfigurationError,
    get_opensearch_client,
    initialize_client,
)
from tools.tool_params import baseToolArgs


class TestOpenSearchClient:
    def setup_method(self):
        self.original_env = os.environ.copy()
        for key in [
            'OPENSEARCH_USERNAME',
            'OPENSEARCH_PASSWORD',
            'AWS_REGION',
            'OPENSEARCH_URL',
            'OPENSEARCH_NO_AUTH',
            'OPENSEARCH_SSL_VERIFY',
            'OPENSEARCH_TIMEOUT',
            'AWS_IAM_ARN',
            'AWS_ACCESS_KEY_ID',
            'AWS_SECRET_ACCESS_KEY',
            'AWS_SESSION_TOKEN',
            'OPENSEARCH_HEADER_AUTH',
        ]:
            os.environ.pop(key, None)

    def teardown_method(self):
        os.environ.clear()
        os.environ.update(self.original_env)

    def test_initialize_client_empty_url(self):
        with pytest.raises(ConfigurationError) as exc_info:
            initialize_client(baseToolArgs(opensearch_cluster_name=''))

        assert 'OPENSEARCH_URL environment variable is required but not set' in str(exc_info.value)

    @patch('opensearch.client.AsyncOpenSearch')
    @patch('opensearch.client.get_aws_region_single_mode')
    def test_initialize_client_basic_auth(self, mock_get_region, mock_opensearch):
        os.environ['OPENSEARCH_USERNAME'] = 'test-user'
        os.environ['OPENSEARCH_PASSWORD'] = 'test-password'
        os.environ['OPENSEARCH_URL'] = 'https://test-opensearch-domain.com'
        mock_get_region.return_value = 'us-east-1'
        mock_client = Mock()
        mock_opensearch.return_value = mock_client

        client = initialize_client(baseToolArgs(opensearch_cluster_name=''))

        assert client == mock_client
        call_kwargs = mock_opensearch.call_args.kwargs
        assert call_kwargs['hosts'] == ['https://test-opensearch-domain.com']
        assert call_kwargs['connection_class'] == BufferedAsyncHttpConnection
        assert call_kwargs['http_auth'] == ('test-user', 'test-password')
        assert call_kwargs['headers']['user-agent'].startswith('opensearch-agent-tools-mcp/')

    @patch('opensearch.client.AsyncOpenSearch')
    @patch('opensearch.client.boto3.Session')
    def test_initialize_client_aws_auth(self, mock_session, mock_opensearch):
        os.environ['AWS_REGION'] = 'us-west-2'
        os.environ['OPENSEARCH_URL'] = 'https://test-opensearch-domain.com'

        mock_credentials = Mock()
        mock_credentials.access_key = 'test-access-key'
        mock_credentials.secret_key = 'test-secret-key'
        mock_credentials.token = 'test-token'

        mock_session_instance = Mock()
        mock_session_instance.get_credentials.return_value = mock_credentials
        mock_session.return_value = mock_session_instance
        mock_client = Mock()
        mock_opensearch.return_value = mock_client

        client = initialize_client(baseToolArgs(opensearch_cluster_name=''))

        assert client == mock_client
        call_kwargs = mock_opensearch.call_args.kwargs
        assert isinstance(call_kwargs['http_auth'], AWSV4SignerAsyncAuth)

    @patch('opensearch.client.AsyncOpenSearch')
    @patch('opensearch.client.boto3.Session')
    def test_initialize_client_iam_role_auth(self, mock_session, mock_opensearch):
        os.environ['AWS_REGION'] = 'us-west-2'
        os.environ['OPENSEARCH_URL'] = 'https://test-opensearch-domain.com'
        os.environ['AWS_IAM_ARN'] = 'arn:aws:iam::123456789012:role/OpenSearchDemoRole'

        mock_sts = Mock()
        mock_sts.assume_role.return_value = {
            'Credentials': {
                'AccessKeyId': 'assumed-key',
                'SecretAccessKey': 'assumed-secret',
                'SessionToken': 'assumed-token',
            }
        }
        mock_session_instance = Mock()
        mock_session_instance.client.return_value = mock_sts
        mock_session.return_value = mock_session_instance
        mock_client = Mock()
        mock_opensearch.return_value = mock_client

        client = initialize_client(baseToolArgs(opensearch_cluster_name=''))

        assert client == mock_client
        mock_sts.assume_role.assert_called_once()
        call_kwargs = mock_opensearch.call_args.kwargs
        assert isinstance(call_kwargs['http_auth'], AWSV4SignerAsyncAuth)

    @patch('opensearch.client.AsyncOpenSearch')
    @patch('opensearch.client.get_aws_region_single_mode')
    def test_initialize_client_no_auth_enabled(self, mock_get_region, mock_opensearch):
        os.environ['OPENSEARCH_URL'] = 'https://test-opensearch-domain.com'
        os.environ['OPENSEARCH_NO_AUTH'] = 'true'
        mock_get_region.return_value = 'us-east-1'
        mock_client = Mock()
        mock_opensearch.return_value = mock_client

        client = initialize_client(baseToolArgs(opensearch_cluster_name=''))

        assert client == mock_client
        call_kwargs = mock_opensearch.call_args.kwargs
        assert 'http_auth' not in call_kwargs

    @patch('opensearch.client.AsyncOpenSearch')
    @patch('opensearch.client.boto3.Session')
    def test_initialize_client_aws_auth_error(self, mock_session, mock_opensearch):
        os.environ['AWS_REGION'] = 'us-west-2'
        os.environ['OPENSEARCH_URL'] = 'https://test-opensearch-domain.com'

        mock_session_instance = Mock()
        mock_session_instance.get_credentials.side_effect = boto3.exceptions.Boto3Error(
            'AWS credentials error'
        )
        mock_session.return_value = mock_session_instance

        with pytest.raises(AuthenticationError) as exc_info:
            initialize_client(baseToolArgs(opensearch_cluster_name=''))
        assert 'Failed to authenticate with AWS credentials' in str(exc_info.value)


class TestOpenSearchClientContextManager:
    def setup_method(self):
        self.original_env = os.environ.copy()
        for key in ['OPENSEARCH_USERNAME', 'OPENSEARCH_PASSWORD', 'AWS_REGION', 'OPENSEARCH_URL']:
            os.environ.pop(key, None)

    def teardown_method(self):
        os.environ.clear()
        os.environ.update(self.original_env)

    @pytest.mark.asyncio
    @patch('opensearch.client.AsyncOpenSearch')
    @patch('opensearch.client.get_aws_region_single_mode')
    async def test_context_manager_successful_creation_and_cleanup(
        self, mock_get_region, mock_opensearch
    ):
        os.environ['OPENSEARCH_URL'] = 'https://test-opensearch-domain.com'
        os.environ['OPENSEARCH_USERNAME'] = 'test-user'
        os.environ['OPENSEARCH_PASSWORD'] = 'test-password'
        mock_get_region.return_value = 'us-east-1'

        mock_client = Mock()
        mock_client.close = AsyncMock(return_value=None)
        mock_opensearch.return_value = mock_client

        async with get_opensearch_client(baseToolArgs(opensearch_cluster_name='')) as client:
            assert client == mock_client

        mock_client.close.assert_called_once()


class TestHeaderAuth:
    def setup_method(self):
        self.original_env = os.environ.copy()
        for key in [
            'OPENSEARCH_USERNAME',
            'OPENSEARCH_PASSWORD',
            'AWS_REGION',
            'OPENSEARCH_URL',
            'OPENSEARCH_HEADER_AUTH',
        ]:
            os.environ.pop(key, None)

    def teardown_method(self):
        os.environ.clear()
        os.environ.update(self.original_env)

    @patch('opensearch.client.request_ctx')
    @patch('opensearch.client.AsyncOpenSearch')
    def test_basic_auth_from_authorization_header(self, mock_opensearch, mock_request_ctx):
        import base64

        os.environ['OPENSEARCH_URL'] = 'https://test-opensearch-domain.com'
        os.environ['OPENSEARCH_HEADER_AUTH'] = 'true'

        username = 'header-user'
        password = 'header-password'
        encoded_credentials = base64.b64encode(f'{username}:{password}'.encode('utf-8')).decode(
            'utf-8'
        )

        mock_request = Mock(spec=Request)
        mock_request.headers = {'authorization': f'Basic {encoded_credentials}'}
        mock_context = Mock()
        mock_context.request = mock_request
        mock_request_ctx.get.return_value = mock_context
        mock_client = Mock()
        mock_opensearch.return_value = mock_client

        client = initialize_client(baseToolArgs(opensearch_cluster_name=''))

        assert client == mock_client
        assert mock_opensearch.call_args.kwargs['http_auth'] == (username, password)

    @patch('opensearch.client.request_ctx')
    @patch('opensearch.client.AsyncOpenSearch')
    def test_bearer_auth_from_authorization_header(self, mock_opensearch, mock_request_ctx):
        os.environ['OPENSEARCH_URL'] = 'https://test-opensearch-domain.com'
        os.environ['OPENSEARCH_HEADER_AUTH'] = 'true'

        mock_request = Mock(spec=Request)
        mock_request.headers = {'authorization': 'Bearer test-bearer-token'}
        mock_context = Mock()
        mock_context.request = mock_request
        mock_request_ctx.get.return_value = mock_context
        mock_client = Mock()
        mock_opensearch.return_value = mock_client

        client = initialize_client(baseToolArgs(opensearch_cluster_name=''))

        assert client == mock_client
        assert mock_opensearch.call_args.kwargs['headers'] == {
            'Authorization': 'Bearer test-bearer-token'
        }
