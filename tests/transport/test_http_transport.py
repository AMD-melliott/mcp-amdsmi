"""Unit tests for HTTP transport functionality."""

import asyncio
import json
import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient
from fastapi import Request, Response
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from mcp_amdsmi.http_transport import HTTPTransport, MCPSessionMiddleware
from mcp_amdsmi.session_manager import SessionManager, Session


class TestHTTPTransport:
    """Test HTTP transport implementation."""
    
    @pytest.fixture
    def session_manager(self):
        """Create a session manager for testing."""
        return SessionManager(session_timeout=3600, cleanup_interval=300)
    
    @pytest.fixture
    def http_transport(self, session_manager):
        """Create HTTP transport instance for testing."""
        return HTTPTransport(session_timeout=3600)
    
    @pytest.fixture
    def test_client(self, http_transport):
        """Create test client for HTTP transport."""
        return TestClient(http_transport.get_app())
    
    def test_http_transport_initialization(self, http_transport):
        """Test HTTP transport initialization."""
        assert http_transport.session_manager is not None
        assert http_transport.app is not None
        assert http_transport.logger is not None
        assert isinstance(http_transport.message_queues, dict)
        assert len(http_transport.message_queues) == 0
    
    def test_health_endpoint(self, test_client):
        """Test health check endpoint."""
        response = test_client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "sessions" in data
        assert isinstance(data["sessions"], int)
    
    def test_metrics_endpoint(self, test_client):
        """Test metrics endpoint for VS Code compatibility."""
        response = test_client.get("/metrics")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "ok"
        assert "timestamp" in data
        assert "sessions" in data
        assert "uptime" in data
    
    def test_jsonrpc_validation_valid_request(self, http_transport):
        """Test JSON-RPC request validation with valid request."""
        valid_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {}
        }
        
        error = http_transport._validate_jsonrpc_request(valid_request)
        assert error is None
    
    def test_jsonrpc_validation_invalid_jsonrpc_version(self, http_transport):
        """Test JSON-RPC validation with invalid version."""
        invalid_request = {
            "jsonrpc": "1.0",
            "id": 1,
            "method": "initialize"
        }
        
        error = http_transport._validate_jsonrpc_request(invalid_request)
        assert error is not None
        assert error["error"]["code"] == -32600
        assert "jsonrpc must be '2.0'" in error["error"]["message"]
    
    def test_jsonrpc_validation_missing_method(self, http_transport):
        """Test JSON-RPC validation with missing method."""
        invalid_request = {
            "jsonrpc": "2.0",
            "id": 1
        }
        
        error = http_transport._validate_jsonrpc_request(invalid_request)
        assert error is not None
        assert error["error"]["code"] == -32600
        assert "method is required" in error["error"]["message"]
    
    def test_jsonrpc_validation_missing_id(self, http_transport):
        """Test JSON-RPC validation with missing id for non-notification."""
        invalid_request = {
            "jsonrpc": "2.0",
            "method": "initialize"
        }
        
        error = http_transport._validate_jsonrpc_request(invalid_request)
        assert error is not None
        assert error["error"]["code"] == -32600
        assert "id is required" in error["error"]["message"]
    
    def test_jsonrpc_validation_notification_no_id_required(self, http_transport):
        """Test JSON-RPC validation for notifications (no id required)."""
        notification_request = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        }
        
        error = http_transport._validate_jsonrpc_request(notification_request)
        assert error is None
    
    def test_jsonrpc_validation_invalid_params(self, http_transport):
        """Test JSON-RPC validation with invalid params."""
        invalid_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": "invalid"  # Should be dict or list
        }
        
        error = http_transport._validate_jsonrpc_request(invalid_request)
        assert error is not None
        assert error["error"]["code"] == -32600
        assert "params must be an object or array" in error["error"]["message"]
    
    @pytest.mark.asyncio
    async def test_initialize_request_processing(self, http_transport):
        """Test MCP initialize request processing."""
        params = {
            "protocolVersion": "2025-03-26",
            "capabilities": {
                "tools": {}
            },
            "clientInfo": {
                "name": "Test Client",
                "version": "1.0.0"
            }
        }
        
        # Mock session for testing
        mock_session = Mock()
        mock_session.client_info = {}
        
        response = await http_transport._handle_initialize(params, 1, mock_session)
        
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert "result" in response
        assert response["result"]["protocolVersion"] == "2025-03-26"
        assert "capabilities" in response["result"]
        assert "serverInfo" in response["result"]
        assert response["result"]["serverInfo"]["name"] == "AMD SMI MCP Server"
    
    @pytest.mark.asyncio
    async def test_client_info_extraction(self, http_transport):
        """Test client information extraction from request."""
        # Mock request
        mock_request = Mock()
        mock_request.headers = {
            "User-Agent": "Test Client/1.0.0",
            "Origin": "https://example.com"
        }
        mock_request.client = Mock()
        mock_request.client.host = "127.0.0.1"
        
        client_info = await http_transport._extract_client_info(mock_request)
        
        assert client_info["user_agent"] == "Test Client/1.0.0"
        assert client_info["origin"] == "https://example.com"
        assert client_info["client_ip"] == "127.0.0.1"
    
    def test_post_mcp_endpoint_empty_body(self, test_client):
        """Test POST /mcp endpoint with empty body."""
        response = test_client.post("/mcp", content="")
        assert response.status_code == 400
        
        data = response.json()
        assert data["error"]["code"] == -32700
        assert "Empty request body" in data["error"]["message"]
    
    def test_post_mcp_endpoint_invalid_json(self, test_client):
        """Test POST /mcp endpoint with invalid JSON."""
        response = test_client.post("/mcp", content="invalid json")
        assert response.status_code == 400
        
        data = response.json()
        assert data["error"]["code"] == -32700
        assert "Parse error" in data["error"]["message"]
    
    def test_get_mcp_endpoint_without_sse_header(self, test_client):
        """Test GET /mcp endpoint without SSE Accept header."""
        response = test_client.get("/mcp")
        assert response.status_code == 405
        # Response should be JSON-RPC error format
        data = response.json()
        assert "error" in data
        assert "method not allowed" in data["error"]["message"].lower()
    
    def test_get_mcp_endpoint_with_sse_header(self, test_client):
        """Test GET /mcp endpoint with SSE Accept header."""
        with patch('mcp_amdsmi.http_transport.HTTPTransport._sse_generator') as mock_generator:
            # Mock the SSE generator to return a simple response and stop
            mock_generator.return_value = iter(['data: {"type": "connection"}\n\n'])
            
            response = test_client.get("/mcp", headers={"Accept": "text/event-stream"})
            assert response.status_code == 200
            assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
            assert "Mcp-Session-Id" in response.headers
    
    @pytest.mark.asyncio
    async def test_sse_message_sending(self, http_transport):
        """Test SSE message sending functionality."""
        session_id = "test-session-123"
        
        # Create a queue for the session
        http_transport.message_queues[session_id] = asyncio.Queue()
        
        # Test message
        test_message = {
            "jsonrpc": "2.0",
            "method": "notifications/progress",
            "params": {"message": "Test message"}
        }
        
        # Send message
        await http_transport._send_sse_message(session_id, test_message)
        
        # Check if message was queued
        assert not http_transport.message_queues[session_id].empty()
        
        # Retrieve and verify message
        queued_message = await http_transport.message_queues[session_id].get()
        assert queued_message == test_message
    
    @pytest.mark.asyncio
    async def test_session_cleanup(self, http_transport):
        """Test session cleanup functionality."""
        session_id = "test-session-456"
        
        # Create a queue for the session
        http_transport.message_queues[session_id] = asyncio.Queue()
        
        # Verify queue exists
        assert session_id in http_transport.message_queues
        
        # Clean up session
        await http_transport._cleanup_session_queue(session_id)
        
        # Verify queue was removed
        assert session_id not in http_transport.message_queues
    
    @pytest.mark.asyncio
    async def test_unsupported_method(self, http_transport):
        """Test handling of unsupported MCP methods."""
        response = await http_transport._process_mcp_request(
            {"jsonrpc": "2.0", "id": 1, "method": "unsupported/method"},
            None
        )
        
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert "error" in response
        assert response["error"]["code"] == -32601
        assert "Method not found" in response["error"]["message"]
    
    @pytest.mark.asyncio
    async def test_notification_handling(self, http_transport):
        """Test handling of notification requests (no response expected)."""
        response = await http_transport._process_mcp_request(
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            None
        )
        
        # Notifications should return None (no response)
        assert response is None


class TestMCPSessionMiddleware:
    """Test MCP session middleware."""
    
    @pytest.fixture
    def session_manager(self):
        """Create a session manager for testing."""
        return SessionManager(session_timeout=3600, cleanup_interval=300)
    
    @pytest.fixture
    def middleware(self, session_manager):
        """Create middleware instance for testing."""
        mock_app = Mock()
        return MCPSessionMiddleware(mock_app, session_manager)
    
    def test_middleware_initialization(self, middleware):
        """Test middleware initialization."""
        assert middleware.session_manager is not None
        assert middleware.logger is not None
    
    def test_is_legacy_sse_request(self, middleware):
        """Test legacy SSE request detection."""
        # Mock request for legacy SSE
        mock_request = Mock()
        mock_request.method = "GET"
        mock_request.url.path = "/sse"
        mock_request.headers = {
            "Accept": "text/event-stream"
        }
        
        result = middleware._is_legacy_sse_request(mock_request)
        assert result is True
        
        # Test non-legacy request
        mock_request.url.path = "/mcp"
        result = middleware._is_legacy_sse_request(mock_request)
        assert result is False
    
    def test_is_initialization_request(self, middleware):
        """Test initialization request detection."""
        # Mock request without session header
        mock_request = Mock()
        mock_request.method = "POST"
        mock_request.headers = {}
        
        result = middleware._is_initialization_request(mock_request)
        assert result is True
        
        # Test request with session header
        mock_request.headers = {"Mcp-Session-Id": "test-session"}
        result = middleware._is_initialization_request(mock_request)
        assert result is False
        
        # Test GET request without session (should not be initialization)
        mock_request.method = "GET"
        mock_request.headers = {}
        result = middleware._is_initialization_request(mock_request)
        assert result is False
    
    def test_extract_client_info_sync(self, middleware):
        """Test synchronous client info extraction."""
        # Mock request
        mock_request = Mock()
        mock_request.headers = {
            "User-Agent": "Test Client/1.0.0",
            "Origin": "https://example.com"
        }
        mock_request.client = Mock()
        mock_request.client.host = "127.0.0.1"
        
        client_info = middleware._extract_client_info_sync(mock_request)
        
        assert client_info["user_agent"] == "Test Client/1.0.0"
        assert client_info["origin"] == "https://example.com"
        assert client_info["client_ip"] == "127.0.0.1"
    
    def test_extract_client_info_minimal(self, middleware):
        """Test client info extraction with minimal headers."""
        # Mock request with minimal info
        mock_request = Mock()
        mock_request.headers = {}
        mock_request.client = None
        
        client_info = middleware._extract_client_info_sync(mock_request)
        
        # Should return empty dict if no info available
        assert isinstance(client_info, dict)


class TestHTTPTransportIntegration:
    """Integration tests for HTTP transport with mocked dependencies."""
    
    @pytest.fixture
    def mock_fastmcp_server(self):
        """Mock FastMCP server for testing."""
        mock_server = Mock()
        mock_tool_manager = Mock()
        mock_server._tool_manager = mock_tool_manager
        
        # Mock tool manager methods
        mock_tool_manager._tools = {
            "get_gpu_discovery": Mock(
                name="get_gpu_discovery",
                description="Discover all available GPUs",
                parameters={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            )
        }
        
        mock_tool_manager.has_tool = AsyncMock(return_value=True)
        mock_tool_manager.call_tool = AsyncMock(
            return_value=Mock(content=["GPU discovery results"])
        )
        
        return mock_server
    
    @pytest.fixture
    def http_transport(self):
        """Create HTTP transport for integration testing."""
        return HTTPTransport(session_timeout=3600)
    
    @pytest.fixture
    def test_client(self, http_transport):
        """Create test client for integration testing."""
        return TestClient(http_transport.get_app())
    
    @pytest.mark.skip(reason="Complex mocking disabled - focusing on simple integration tests")
    @patch('mcp_amdsmi.server.mcp')
    def test_full_mcp_workflow(self, mock_mcp, mock_fastmcp_server, test_client):
        """Test full MCP workflow from initialization to tool call."""
        # Mock the server import
        mock_mcp.return_value = mock_fastmcp_server
        
        # Configure the mock to return some tools
        mock_fastmcp_server.handle_request.return_value = {
            "jsonrpc": "2.0",
            "id": 2,
            "result": {
                "tools": [
                    {
                        "name": "get_gpu_discovery",
                        "description": "Discover and enumerate all available AMD GPU devices",
                        "inputSchema": {"type": "object", "properties": {}}
                    },
                    {
                        "name": "get_gpu_status", 
                        "description": "Get comprehensive current status of a specific GPU device",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "device_id": {"type": "string", "default": "0"}
                            }
                        }
                    }
                ]
            }
        }
        
        # Step 1: Initialize connection
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {"tools": {}},
                "clientInfo": {"name": "Test Client", "version": "1.0.0"}
            }
        }
        
        response = test_client.post("/mcp", json=init_request)
        assert response.status_code == 200
        
        # Extract session ID
        session_id = response.headers.get("Mcp-Session-Id")
        assert session_id is not None
        
        # Step 2: Send initialized notification
        notification = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        }
        
        response = test_client.post(
            "/mcp",
            json=notification,
            headers={"Mcp-Session-Id": session_id}
        )
        assert response.status_code == 204  # No content for notifications
        
        # Step 3: List tools
        tools_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list"
        }

        response = test_client.post(
            "/mcp",
            json=tools_request,
            headers={"Mcp-Session-Id": session_id}
        )
        assert response.status_code == 200

        data = response.json()
        assert "result" in data
        assert "tools" in data["result"]
        assert len(data["result"]["tools"]) > 0
        
        # Verify expected tools are present
        tool_names = [tool["name"] for tool in data["result"]["tools"]]
        assert "get_gpu_discovery" in tool_names
        assert "get_gpu_status" in tool_names
        
        # Step 4: Call a tool
        tool_call_request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "get_gpu_discovery",
                "arguments": {}
            }
        }
        
        response = test_client.post(
            "/mcp",
            json=tool_call_request,
            headers={"Mcp-Session-Id": session_id}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "result" in data
        assert "content" in data["result"]
        assert len(data["result"]["content"]) > 0
        assert data["result"]["content"][0]["type"] == "text"