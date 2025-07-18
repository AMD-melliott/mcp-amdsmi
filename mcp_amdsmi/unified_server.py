"""Unified MCP server supporting both STDIO and HTTP transport.

This module provides a unified entry point for running the MCP server with support
for both STDIO transport (for local/development use) and HTTP transport (for remote
deployments with MCP Streamable HTTP as per MCP 2025-03-26 specification).
"""

import argparse
import asyncio
import logging
import os
import sys
from typing import Optional

import uvicorn
from fastmcp import FastMCP

from .server import mcp as fastmcp_server
from .http_transport import HTTPTransport


class UnifiedMCPServer:
    """Unified MCP server that supports both STDIO and HTTP transport modes."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.http_transport: Optional[HTTPTransport] = None
        
    def run_stdio(self):
        """Run the MCP server in STDIO mode (default FastMCP behavior)."""
        self.logger.info("Starting MCP server in STDIO mode")
        # Use the existing FastMCP server
        fastmcp_server.run()
    
    def run_http(self, host: str = "127.0.0.1", port: int = 8000, 
                 session_timeout: float = 3600):
        """Run the MCP server in HTTP mode with Streamable HTTP support.
        
        Args:
            host: Host to bind to
            port: Port to bind to
            session_timeout: Session timeout in seconds
        """
        self.logger.info(f"Starting MCP server in HTTP mode on {host}:{port}")
        
        # Create HTTP transport
        self.http_transport = HTTPTransport(session_timeout=session_timeout)
        
        # Get the FastAPI app
        app = self.http_transport.get_app()
        
        # Add FastMCP integration routes
        self._integrate_fastmcp_with_http(app)
        
        # Run with uvicorn
        uvicorn.run(
            app,
            host=host,
            port=port,
            log_level="info"
        )
    
    def _integrate_fastmcp_with_http(self, app):
        """Integrate FastMCP tools with HTTP transport."""
        # No additional integration needed - the HTTP transport now handles
        # MCP protocol directly through the unified /mcp endpoint
        pass


def main():
    """Main entry point with command-line argument support."""
    parser = argparse.ArgumentParser(description="AMD SMI MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default="stdio",
        help="Transport mode (default: stdio)"
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind to for HTTP mode (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind to for HTTP mode (default: 8000)"
    )
    parser.add_argument(
        "--session-timeout",
        type=float,
        default=3600,
        help="Session timeout in seconds for HTTP mode (default: 3600)"
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Logging level (default: INFO)"
    )
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create server instance
    server = UnifiedMCPServer()
    
    try:
        if args.transport == "stdio":
            server.run_stdio()
        elif args.transport == "http":
            server.run_http(
                host=args.host,
                port=args.port,
                session_timeout=args.session_timeout
            )
    except KeyboardInterrupt:
        logging.info("Server stopped by user")
    except Exception as e:
        logging.error(f"Server error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()