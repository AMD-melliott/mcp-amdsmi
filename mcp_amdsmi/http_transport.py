"""HTTP transport implementation for MCP Streamable HTTP.

This module implements the HTTP transport layer for MCP Streamable HTTP
as specified in MCP 2025-03-26, including session management, unified
endpoint handling, and SSE streaming capabilities.
"""

import asyncio
import json
import logging
import time
from typing import Any, Dict, Optional, Tuple
from urllib.parse import parse_qs, urlparse
from asyncio import Queue

from fastapi import FastAPI, Request, Response, HTTPException, Depends
from fastapi.responses import StreamingResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware

from .session_manager import SessionManager, Session


class MCPSessionMiddleware(BaseHTTPMiddleware):
    """Middleware to handle MCP session management for HTTP requests."""
    
    def __init__(self, app, session_manager: SessionManager):
        super().__init__(app)
        self.session_manager = session_manager
        self.logger = logging.getLogger(__name__)
    
    async def dispatch(self, request: Request, call_next):
        """Process request and handle session management."""
        # Skip session management for health and metrics endpoints
        if request.url.path in ["/health", "/metrics"]:
            return await call_next(request)
        
        # For /mcp endpoint, check if method is supported
        if request.url.path == "/mcp":
            if request.method not in ["GET", "POST", "DELETE"]:
                return JSONResponse(
                    status_code=405,
                    content={
                        "error": "Method not allowed",
                        "allowed_methods": ["GET", "POST", "DELETE"]
                    }
                )
        
        # Extract session ID from header
        session_id = request.headers.get("Mcp-Session-Id")
        
        # Check if this is an SSE request for legacy HTTP+SSE transport
        is_legacy_sse = self._is_legacy_sse_request(request)
        
        if is_legacy_sse:
            # For legacy SSE requests, create a temporary session
            client_info = self._extract_client_info_sync(request)
            session = self.session_manager.create_session(client_info=client_info)
            request.state.mcp_session = session
            
            # Process request
            response = await call_next(request)
            
            return response
        
        # Check if this is an initialization request
        is_initialization = self._is_initialization_request(request)
        
        if is_initialization:
            # For initialization, create new session
            response = await call_next(request)
            
            # If initialization was successful, add session header
            if response.status_code == 200:
                # Create new session
                client_info = self._extract_client_info_sync(request)
                session = self.session_manager.create_session(client_info=client_info)
                
                # Add session ID to response header
                response.headers["Mcp-Session-Id"] = session.session_id
                self.logger.info(f"Created session {session.session_id[:8]}... for initialization")
                
            return response
        else:
            # For non-initialization requests, validate session
            if not session_id:
                # Allow GET requests to /mcp without session for SSE
                if request.method == "GET" and request.url.path == "/mcp":
                    # Check if it's a valid SSE request
                    accept_header = request.headers.get("Accept", "")
                    if "text/event-stream" in accept_header:
                        # Create a temporary session for SSE /mcp requests
                        client_info = self._extract_client_info_sync(request)
                        session = self.session_manager.create_session(client_info=client_info)
                        request.state.mcp_session = session
                        response = await call_next(request)
                        return response
                    else:
                        # GET /mcp without SSE header should return 405
                        return JSONResponse(
                            status_code=405,
                            content={
                                "jsonrpc": "2.0",
                                "error": {
                                    "code": -32600,
                                    "message": "Method not allowed. Use POST for MCP requests or add Accept: text/event-stream header for SSE."
                                }
                            }
                        )
                
                # For all other requests, require session
                self.logger.warning("Request missing Mcp-Session-Id header")
                return JSONResponse(
                    status_code=400,
                    content={
                        "jsonrpc": "2.0",
                        "error": {
                            "code": -32600,
                            "message": "Missing Mcp-Session-Id header"
                        }
                    }
                )
            
            # Validate session
            session = self.session_manager.get_session(session_id)
            if not session:
                self.logger.warning(f"Invalid or expired session: {session_id[:8]}...")
                return JSONResponse(
                    status_code=400,
                    content={
                        "jsonrpc": "2.0",
                        "error": {
                            "code": -32600,
                            "message": "Invalid or expired session ID"
                        }
                    }
                )
            
            # Add session to request state
            request.state.mcp_session = session
            
            # Process request
            response = await call_next(request)
            
            # Update session access time
            session.update_access_time()
            
            return response
    
    def _is_legacy_sse_request(self, request: Request) -> bool:
        """Check if this is a legacy HTTP+SSE transport request."""
        # Legacy SSE requests are GET requests to /sse endpoint
        # with Accept: text/event-stream header and no session ID
        return (
            request.method == "GET" and
            request.url.path == "/sse" and
            "text/event-stream" in request.headers.get("Accept", "") and
            "Mcp-Session-Id" not in request.headers
        )
    
    def _is_initialization_request(self, request: Request) -> bool:
        """Check if this is an MCP initialization request."""
        # For GET requests, don't treat as initialization even without session
        # since they might be for SSE streams
        if request.method == "GET":
            return False
        
        # For initialization, we need to check if there's no session header
        # OR if the request body contains an "initialize" method
        if "Mcp-Session-Id" not in request.headers:
            return True
        
        # Could also check request body for "initialize" method, but that would
        # require reading the body which might interfere with downstream processing
        return False
    
    def _extract_client_info_sync(self, request: Request) -> Dict[str, Any]:
        """Extract client information from request (sync version)."""
        client_info = {}
        
        # Extract user agent
        user_agent = request.headers.get("User-Agent")
        if user_agent:
            client_info["user_agent"] = user_agent
        
        # Extract client IP
        if request.client:
            client_info["client_ip"] = request.client.host
        
        # Extract any other relevant headers
        origin = request.headers.get("Origin")
        if origin:
            client_info["origin"] = origin
        
        return client_info
    
    async def _extract_client_info(self, request: Request) -> Dict[str, Any]:
        """Extract client information from request."""
        client_info = {}
        
        # Extract user agent
        user_agent = request.headers.get("User-Agent")
        if user_agent:
            client_info["user_agent"] = user_agent
        
        # Extract client IP
        if request.client:
            client_info["client_ip"] = request.client.host
        
        # Extract any other relevant headers
        origin = request.headers.get("Origin")
        if origin:
            client_info["origin"] = origin
        
        return client_info


class HTTPTransport:
    """HTTP transport implementation for MCP Streamable HTTP."""
    
    def __init__(self, session_timeout: float = 3600):
        """Initialize HTTP transport.
        
        Args:
            session_timeout: Session timeout in seconds
        """
        self.session_manager = SessionManager(session_timeout=session_timeout)
        self.app = FastAPI(title="MCP AMD SMI Server", version="1.0.0")
        self.logger = logging.getLogger(__name__)
        
        # Message queues for SSE streaming - maps session_id to queue
        self.message_queues: Dict[str, Queue] = {}
        
        # Add CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # In production, restrict this
            allow_credentials=True,
            allow_methods=["GET", "POST", "OPTIONS", "DELETE"],
            allow_headers=["*"],
        )
        
        # Add session middleware
        self.app.add_middleware(MCPSessionMiddleware, session_manager=self.session_manager)
        
        # Set up routes
        self._setup_routes()
    
    def _setup_routes(self):
        """Set up HTTP routes for MCP transport."""
        
        @self.app.post("/mcp")
        async def mcp_post_endpoint(request: Request):
            """Handle POST requests to /mcp endpoint."""
            return await self._handle_mcp_request(request)
        
        @self.app.get("/mcp")
        async def mcp_get_endpoint(request: Request):
            """Handle GET requests to /mcp endpoint for SSE streams."""
            return await self._handle_mcp_get_request(request)
        
        @self.app.get("/sse")
        async def sse_endpoint(request: Request):
            """Handle SSE requests for streaming MCP messages."""
            return await self._handle_sse_request(request)
        
        @self.app.post("/sse")
        async def sse_post_endpoint(request: Request):
            """Handle POST requests to /sse endpoint (legacy HTTP+SSE support)."""
            return await self._handle_legacy_sse_post(request)
        
        @self.app.delete("/mcp")
        async def mcp_delete_endpoint(request: Request):
            """Handle DELETE requests to /mcp endpoint (session termination)."""
            return await self._handle_session_termination(request)
        
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint."""
            return {
                "status": "healthy",
                "timestamp": time.time(),
                "sessions": self.session_manager.get_session_count()
            }
        
        @self.app.get("/metrics")
        async def metrics_endpoint():
            """Basic metrics endpoint for VS Code compatibility."""
            return {
                "status": "ok",
                "timestamp": time.time(),
                "sessions": self.session_manager.get_session_count(),
                "uptime": time.time() - self.session_manager.created_at if hasattr(self.session_manager, 'created_at') else 0
            }
    
    def _validate_jsonrpc_request(self, json_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Validate JSON-RPC request format according to MCP spec.
        
        Returns error response if validation fails, None if valid.
        """
        # Check required fields
        if not isinstance(json_data, dict):
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32600,
                    "message": "Invalid Request: must be a JSON object"
                }
            }
        
        if json_data.get("jsonrpc") != "2.0":
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32600,
                    "message": "Invalid Request: jsonrpc must be '2.0'"
                }
            }
        
        method = json_data.get("method")
        if not method or not isinstance(method, str):
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32600,
                    "message": "Invalid Request: method is required and must be a string"
                }
            }
        
        # For non-notification requests, id is required
        if not method.startswith("notifications/") and "id" not in json_data:
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32600,
                    "message": "Invalid Request: id is required for non-notification requests"
                }
            }
        
        # Validate params if present
        params = json_data.get("params")
        if params is not None and not isinstance(params, (dict, list)):
            return {
                "jsonrpc": "2.0",
                "id": json_data.get("id"),
                "error": {
                    "code": -32600,
                    "message": "Invalid Request: params must be an object or array"
                }
            }
        
        return None  # Valid request
    
    async def _handle_mcp_get_request(self, request: Request) -> Response:
        """Handle GET requests to /mcp endpoint for SSE streams.
        
        According to MCP spec, GET requests to /mcp should establish SSE streams
        for server-to-client communication.
        """
        try:
            # Check if client accepts SSE
            accept_header = request.headers.get("Accept", "")
            if "text/event-stream" not in accept_header:
                raise HTTPException(
                    status_code=405, 
                    detail="Method Not Allowed - GET /mcp requires Accept: text/event-stream"
                )
            
            # Get session from request state (middleware should have created one)
            session = getattr(request.state, "mcp_session", None)
            if not session:
                # If no session, create one for this SSE stream
                # This allows VS Code to establish SSE connections
                client_info = await self._extract_client_info(request)
                session = self.session_manager.create_session(client_info=client_info)
                self.logger.info(f"Created session {session.session_id[:8]}... for GET /mcp SSE stream")
            
            # Create message queue for this session if it doesn't exist
            if session.session_id not in self.message_queues:
                self.message_queues[session.session_id] = Queue()
            
            # Create SSE response
            return StreamingResponse(
                self._sse_generator(session),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Headers": "Cache-Control",
                    "Mcp-Session-Id": session.session_id,  # Include session ID in response
                }
            )
            
        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"Error handling GET /mcp request: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def _extract_client_info(self, request: Request) -> Dict[str, Any]:
        """Extract client information from request."""
        client_info = {}
        
        # Extract user agent
        user_agent = request.headers.get("User-Agent")
        if user_agent:
            client_info["user_agent"] = user_agent
        
        # Extract client IP
        if request.client:
            client_info["client_ip"] = request.client.host
        
        # Extract any other relevant headers
        origin = request.headers.get("Origin")
        if origin:
            client_info["origin"] = origin
        
        return client_info
    
    async def _handle_mcp_request(self, request: Request) -> Response:
        """Handle POST requests to MCP endpoint."""
        try:
            # Parse JSON-RPC request
            body = await request.body()
            if not body:
                return JSONResponse(
                    status_code=400,
                    content={
                        "jsonrpc": "2.0",
                        "error": {
                            "code": -32700,
                            "message": "Parse error: Empty request body"
                        }
                    }
                )
            
            try:
                json_data = json.loads(body)
            except json.JSONDecodeError as e:
                return JSONResponse(
                    status_code=400,
                    content={
                        "jsonrpc": "2.0",
                        "error": {
                            "code": -32700,
                            "message": f"Parse error: {str(e)}"
                        }
                    }
                )
            
            # Validate JSON-RPC format
            validation_error = self._validate_jsonrpc_request(json_data)
            if validation_error:
                return JSONResponse(status_code=400, content=validation_error)
            
            # Get session from request state (added by middleware)
            session = getattr(request.state, "mcp_session", None)
            
            # Process the MCP request
            response_data = await self._process_mcp_request(json_data, session)
            
            # Handle notifications that don't return a response
            if response_data is None:
                return Response(status_code=204)  # No Content
            
            return JSONResponse(content=response_data)
            
        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"Error handling MCP request: {e}")
            return JSONResponse(
                status_code=500,
                content={
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32603,
                        "message": "Internal server error"
                    }
                }
            )
    
    async def _handle_sse_request(self, request: Request) -> Response:
        """Handle SSE requests for streaming MCP messages."""
        try:
            # Get session from request state
            session = getattr(request.state, "mcp_session", None)
            if not session:
                raise HTTPException(status_code=400, detail="Valid session required for SSE")
            
            # Check if client accepts SSE
            accept_header = request.headers.get("Accept", "")
            if "text/event-stream" not in accept_header:
                raise HTTPException(
                    status_code=400, 
                    detail="SSE requires Accept: text/event-stream"
                )
            
            # Create message queue for this session if it doesn't exist
            if session.session_id not in self.message_queues:
                self.message_queues[session.session_id] = Queue()
            
            # Create SSE response
            return StreamingResponse(
                self._sse_generator(session),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Headers": "Cache-Control",
                }
            )
            
        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"Error handling SSE request: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def _send_sse_message(self, session_id: str, message: Dict[str, Any]):
        """Send a message to an SSE stream for the given session."""
        if session_id in self.message_queues:
            try:
                await self.message_queues[session_id].put(message)
            except Exception as e:
                self.logger.error(f"Failed to send SSE message to session {session_id[:8]}...: {e}")
    
    async def _cleanup_session_queue(self, session_id: str):
        """Clean up message queue for a session."""
        if session_id in self.message_queues:
            del self.message_queues[session_id]
            self.logger.debug(f"Cleaned up message queue for session {session_id[:8]}...")
    
    async def _handle_legacy_sse_post(self, request: Request) -> Response:
        """Handle POST requests to /sse endpoint for legacy HTTP+SSE transport."""
        try:
            # Parse JSON-RPC request
            body = await request.body()
            if not body:
                return JSONResponse(
                    status_code=400,
                    content={
                        "jsonrpc": "2.0",
                        "error": {
                            "code": -32700,
                            "message": "Parse error: Empty request body"
                        }
                    }
                )
            
            try:
                json_data = json.loads(body)
            except json.JSONDecodeError as e:
                return JSONResponse(
                    status_code=400,
                    content={
                        "jsonrpc": "2.0",
                        "error": {
                            "code": -32700,
                            "message": f"Parse error: {str(e)}"
                        }
                    }
                )
            
            # Validate JSON-RPC format
            validation_error = self._validate_jsonrpc_request(json_data)
            if validation_error:
                return JSONResponse(status_code=400, content=validation_error)
            
            # Get or create session from request state
            session = getattr(request.state, "mcp_session", None)
            
            # Process the MCP request
            response_data = await self._process_mcp_request(json_data, session)
            
            # Handle notifications that don't return a response
            if response_data is None:
                return Response(status_code=204)  # No Content
            
            return JSONResponse(content=response_data)
            
        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"Error handling legacy SSE POST: {e}")
            return JSONResponse(
                status_code=500,
                content={
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32603,
                        "message": "Internal server error"
                    }
                }
            )
    
    async def _handle_session_termination(self, request: Request) -> Response:
        """Handle DELETE requests for session termination."""
        try:
            session_id = request.headers.get("Mcp-Session-Id")
            if not session_id:
                raise HTTPException(status_code=400, detail="Missing Mcp-Session-Id header")
            
            # Clean up message queue
            await self._cleanup_session_queue(session_id)
            
            # Remove session
            removed = self.session_manager.remove_session(session_id)
            if not removed:
                raise HTTPException(status_code=404, detail="Session not found")
            
            return JSONResponse(
                content={
                    "jsonrpc": "2.0",
                    "result": {
                        "message": "Session terminated successfully"
                    }
                }
            )
            
        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"Error terminating session: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def _process_mcp_request(self, json_data: Dict[str, Any], 
                                 session: Optional[Session]) -> Optional[Dict[str, Any]]:
        """Process MCP JSON-RPC request according to MCP 2025-03-26 spec.
        
        This method handles the full MCP protocol including initialization,
        tool calls, and resource management.
        """
        method = json_data.get("method")
        params = json_data.get("params", {})
        request_id = json_data.get("id")
        
        self.logger.info(f"Processing MCP request: {method}")
        
        # Handle different MCP methods
        if method == "initialize":
            return await self._handle_initialize(params, request_id, session)
        elif method == "notifications/initialized":
            # Notification - no response needed
            return None
        elif method == "tools/list":
            return await self._handle_tools_list(params, request_id)
        elif method == "tools/call":
            return await self._handle_tools_call(params, request_id, session)
        elif method == "resources/list":
            return await self._handle_resources_list(params, request_id)
        elif method == "resources/read":
            return await self._handle_resources_read(params, request_id)
        elif method == "prompts/list":
            return await self._handle_prompts_list(params, request_id)
        elif method == "prompts/get":
            return await self._handle_prompts_get(params, request_id)
        elif method == "logging/setLevel":
            return await self._handle_logging_set_level(params, request_id)
        elif method.startswith("notifications/"):
            # Other notifications - no response needed
            return None
        else:
            # For other methods, return method not found error
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                }
            }
    
    async def _handle_initialize(self, params: Dict[str, Any], request_id: Any, 
                               session: Optional[Session]) -> Dict[str, Any]:
        """Handle MCP initialize request with feature negotiation."""
        client_info = params.get("clientInfo", {})
        client_capabilities = params.get("capabilities", {})
        
        # Store client info in session if available
        if session:
            session.client_info.update(client_info)
            session.capabilities = client_capabilities
        
        # Determine server capabilities based on client capabilities
        server_capabilities = {
            "tools": {
                "listChanged": False
            },
            "resources": {},
            "prompts": {},
            "logging": {
                "supportedLevels": ["debug", "info", "warning", "error", "critical"]
            }
        }
        
        # Add sampling capability if client supports it
        if client_capabilities.get("sampling"):
            server_capabilities["sampling"] = {}
        
        # Add experimental features for testing
        if client_capabilities.get("experimental"):
            server_capabilities["experimental"] = {
                "progress": True  # We support progress notifications via SSE
            }
        
        self.logger.info(f"Negotiated capabilities with client: {client_info.get('name', 'unknown')}")
        self.logger.debug(f"Client capabilities: {client_capabilities}")
        self.logger.debug(f"Server capabilities: {server_capabilities}")
        
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "2025-03-26",
                "capabilities": server_capabilities,
                "serverInfo": {
                    "name": "AMD SMI MCP Server",
                    "version": "1.0.0"
                }
            }
        }
    
    async def _handle_tools_list(self, params: Dict[str, Any], request_id: Any) -> Dict[str, Any]:
        """Handle tools/list request."""
        try:
            # Get tools from FastMCP server
            from .server import mcp as fastmcp_server
            
            tools = []
            # Access the tool manager properly
            tool_manager = fastmcp_server._tool_manager
            
            # Get all tools from the tool manager's _tools dictionary
            # The tools are stored in tool_manager._tools as a dict
            fastmcp_tools = tool_manager._tools
            
            for tool_name, tool_obj in fastmcp_tools.items():
                # Extract tool information from the Tool object
                tool_def = {
                    "name": tool_obj.name,
                    "description": tool_obj.description or f"Execute {tool_name}",
                    "inputSchema": tool_obj.parameters or {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
                tools.append(tool_def)
            
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "tools": tools
                }
            }
        except Exception as e:
            self.logger.error(f"Error listing tools: {e}")
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32603,
                    "message": f"Internal server error: {str(e)}"
                }
            }
    
    async def _handle_tools_call(self, params: Dict[str, Any], request_id: Any, session: Optional[Session] = None) -> Dict[str, Any]:
        """Handle tools/call request with SSE streaming support."""
        tool_name = params.get("name")
        tool_args = params.get("arguments", {})
        
        if not tool_name:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32602,
                    "message": "Tool name is required"
                }
            }
        
        # Get tools from FastMCP server
        from .server import mcp as fastmcp_server
        tool_manager = fastmcp_server._tool_manager
        
        if not await tool_manager.has_tool(tool_name):
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32601,
                    "message": f"Tool '{tool_name}' not found"
                }
            }
        
        try:
            # Send progress notification via SSE if session exists
            if session:
                progress_message = {
                    "jsonrpc": "2.0",
                    "method": "notifications/progress",
                    "params": {
                        "progressToken": f"tool_{request_id}",
                        "value": {
                            "kind": "begin",
                            "title": f"Executing {tool_name}",
                            "message": "Starting tool execution..."
                        }
                    }
                }
                await self._send_sse_message(session.session_id, progress_message)
            
            # Call the tool through the tool manager
            result = await tool_manager.call_tool(tool_name, tool_args)
            
            # Convert result to text if it's a ToolResult object
            if hasattr(result, 'content'):
                # FastMCP ToolResult object
                content_text = "\n".join(str(item) for item in result.content)
            else:
                # Plain result
                content_text = str(result)
            
            # Send completion notification via SSE if session exists
            if session:
                completion_message = {
                    "jsonrpc": "2.0",
                    "method": "notifications/progress",
                    "params": {
                        "progressToken": f"tool_{request_id}",
                        "value": {
                            "kind": "end",
                            "message": "Tool execution completed"
                        }
                    }
                }
                await self._send_sse_message(session.session_id, completion_message)
            
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": content_text
                        }
                    ]
                }
            }
        except Exception as e:
            self.logger.error(f"Error calling tool {tool_name}: {e}")
            
            # Send error notification via SSE if session exists
            if session:
                error_message = {
                    "jsonrpc": "2.0",
                    "method": "notifications/progress",
                    "params": {
                        "progressToken": f"tool_{request_id}",
                        "value": {
                            "kind": "end",
                            "message": f"Tool execution failed: {str(e)}"
                        }
                    }
                }
                await self._send_sse_message(session.session_id, error_message)
            
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32603,
                    "message": f"Tool execution failed: {str(e)}"
                }
            }
    
    async def _handle_resources_list(self, params: Dict[str, Any], request_id: Any) -> Dict[str, Any]:
        """Handle resources/list request."""
        # For now, we don't have resources implemented
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "resources": []
            }
        }
    
    async def _handle_resources_read(self, params: Dict[str, Any], request_id: Any) -> Dict[str, Any]:
        """Handle resources/read request."""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": -32601,
                "message": "Resources not implemented"
            }
        }
    
    async def _handle_prompts_list(self, params: Dict[str, Any], request_id: Any) -> Dict[str, Any]:
        """Handle prompts/list request."""
        # For now, we don't have prompts implemented
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "prompts": []
            }
        }
    
    async def _handle_prompts_get(self, params: Dict[str, Any], request_id: Any) -> Dict[str, Any]:
        """Handle prompts/get request."""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": -32601,
                "message": "Prompts not implemented"
            }
        }
    
    async def _handle_logging_set_level(self, params: Dict[str, Any], request_id: Any) -> Dict[str, Any]:
        """Handle logging/setLevel request."""
        level = params.get("level")
        
        if level not in ["debug", "info", "warning", "error", "critical"]:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32602,
                    "message": f"Invalid logging level: {level}"
                }
            }
        
        # Set logging level
        numeric_level = getattr(logging, level.upper())
        logging.getLogger().setLevel(numeric_level)
        
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {}
        }
    
    def _extract_tool_schema(self, tool_func) -> Dict[str, Any]:
        """Extract JSON schema from tool function signature."""
        import inspect
        
        sig = inspect.signature(tool_func)
        properties = {}
        required = []
        
        for param_name, param in sig.parameters.items():
            param_info = {"type": "string"}  # Default to string
            
            if param.annotation != inspect.Parameter.empty:
                if param.annotation == str:
                    param_info["type"] = "string"
                elif param.annotation == int:
                    param_info["type"] = "integer"
                elif param.annotation == float:
                    param_info["type"] = "number"
                elif param.annotation == bool:
                    param_info["type"] = "boolean"
                elif hasattr(param.annotation, '__origin__'):
                    # Handle generic types like List, Dict, etc.
                    if param.annotation.__origin__ == list:
                        param_info["type"] = "array"
                    elif param.annotation.__origin__ == dict:
                        param_info["type"] = "object"
            
            if param.default == inspect.Parameter.empty:
                required.append(param_name)
            else:
                param_info["default"] = param.default
            
            properties[param_name] = param_info
        
        return {
            "type": "object",
            "properties": properties,
            "required": required
        }
    
    async def _sse_generator(self, session: Session):
        """Generate SSE events for streaming MCP messages."""
        session_id = session.session_id
        message_queue = self.message_queues[session_id]
        
        # Send initial connection event
        yield f"data: {json.dumps({'type': 'connection', 'session_id': session_id})}\n\n"
        
        try:
            while True:
                # Wait for messages with timeout for heartbeat
                try:
                    # Wait for message with timeout
                    message = await asyncio.wait_for(message_queue.get(), timeout=30.0)
                    
                    # Format message as SSE event
                    event_data = {
                        'type': 'message',
                        'timestamp': time.time(),
                        'data': message
                    }
                    
                    yield f"data: {json.dumps(event_data)}\n\n"
                    
                except asyncio.TimeoutError:
                    # Send heartbeat if no messages received
                    if not self.session_manager.get_session(session_id):
                        break
                    
                    heartbeat = {
                        'type': 'heartbeat',
                        'timestamp': time.time(),
                        'session_id': session_id
                    }
                    
                    yield f"data: {json.dumps(heartbeat)}\n\n"
                    
        except Exception as e:
            self.logger.error(f"SSE stream error for session {session_id[:8]}...: {e}")
            error_event = {
                'type': 'error',
                'timestamp': time.time(),
                'message': str(e)
            }
            yield f"data: {json.dumps(error_event)}\n\n"
        finally:
            # Clean up when SSE connection closes
            await self._cleanup_session_queue(session_id)
            self.logger.info(f"SSE stream closed for session {session_id[:8]}...")
    
    def get_app(self) -> FastAPI:
        """Get the FastAPI application."""
        return self.app