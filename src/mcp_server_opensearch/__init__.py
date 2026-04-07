# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0

import argparse
import asyncio
import logging


def main() -> None:
    """
    Main entry point for the OpenSearch Agent Tools MCP server.
    Handles command line arguments and starts the appropriate server based on transport type.
    """
    # Set up command line argument parser
    parser = argparse.ArgumentParser(description='OpenSearch Agent Tools MCP Server')
    parser.add_argument(
        '--transport',
        choices=['stdio', 'stream'],
        default='stdio',
        help='Transport type (stdio or stream)',
    )
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to (streaming only)')
    parser.add_argument(
        '--port', type=int, default=9900, help='Port to listen on (streaming only)'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging',
    )
    parser.add_argument(
        '--log-format',
        choices=['text', 'json'],
        default='text',
        help='Log output format: text (default, human-readable) or json (structured)',
    )

    args, _ = parser.parse_known_args()

    # Configure logging with appropriate level and format
    from .logging_config import configure_logging

    log_level = logging.DEBUG if args.debug else logging.INFO
    configure_logging(level=log_level, log_format=args.log_format)
    logger = logging.getLogger(__name__)

    logger.info('Starting MCP server...')

    # Import servers lazily to avoid circular imports at module load time
    from .stdio_server import serve as serve_stdio
    from .streaming_server import serve as serve_streaming

    # Start the appropriate server based on transport type
    if args.transport == 'stdio':
        asyncio.run(serve_stdio())
    else:
        asyncio.run(serve_streaming(host=args.host, port=args.port))


if __name__ == '__main__':
    main()
