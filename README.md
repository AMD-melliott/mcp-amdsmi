## HTTP Transport Usage Examples

### Basic HTTP Client Example

```python
import requests
import json

# Initialize session
response = requests.post('http://localhost:8000/mcp', json={
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2025-03-26",
        "capabilities": {},
        "clientInfo": {
            "name": "Python Client",
            "version": "1.0.0"
        }
    }
})

# Extract session ID from response header
session_id = response.headers.get('Mcp-Session-Id')
print(f"Session ID: {session_id}")

# Send initialized notification
requests.post('http://localhost:8000/mcp', 
    json={
        "jsonrpc": "2.0",
        "method": "notifications/initialized"
    },
    headers={'Mcp-Session-Id': session_id}
)

# List available tools
tools_response = requests.post('http://localhost:8000/mcp',
    json={
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list"
    },
    headers={'Mcp-Session-Id': session_id}
)

print("Available tools:", tools_response.json())

# Call a tool
gpu_discovery = requests.post('http://localhost:8000/mcp',
    json={
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "get_gpu_discovery",
            "arguments": {}
        }
    },
    headers={'Mcp-Session-Id': session_id}
)

print("GPU Discovery:", gpu_discovery.json())
```

### SSE Streaming Example

```python
import requests
import json

# Initialize session first (same as above)
# ...

# Connect to SSE stream
sse_response = requests.get('http://localhost:8000/mcp',
    headers={
        'Mcp-Session-Id': session_id,
        'Accept': 'text/event-stream'
    },
    stream=True
)

# Process SSE events
for line in sse_response.iter_lines():
    if line:
        if line.startswith(b'data:'):
            data = json.loads(line[5:])  # Remove 'data:' prefix
            print(f"SSE Event: {data}")
```

### cURL Examples

```bash
# Initialize session
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
      "protocolVersion": "2025-03-26",
      "capabilities": {},
      "clientInfo": {
        "name": "curl",
        "version": "1.0.0"
      }
    }
  }' -v

# Extract session ID from response header and use it
# Replace {SESSION_ID} with the actual session ID

# List tools
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -H "Mcp-Session-Id: {SESSION_ID}" \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/list"
  }'

# Call GPU discovery tool
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -H "Mcp-Session-Id: {SESSION_ID}" \
  -d '{
    "jsonrpc": "2.0",
    "id": 3,
    "method": "tools/call",
    "params": {
      "name": "get_gpu_discovery",
      "arguments": {}
    }
  }'

# Health check
curl -X GET http://localhost:8000/health

# Terminate session
curl -X DELETE http://localhost:8000/mcp \
  -H "Mcp-Session-Id: {SESSION_ID}"
```

# AMD SMI MCP Server

A Model Context Protocol (MCP) server created for PEARC25 that provides conversational access to AMD GPU monitoring capabilities. Designed for infrastructure monitoring, and basic performance analysis.

## Features

- **Six Core Monitoring Tools**: Device discovery, status monitoring, performance analysis, memory analysis, power/thermal monitoring, and health assessment
- **Intelligent Health Analysis**: AI-powered health scoring with contextual recommendations
- **N/A Value Handling**: Robust handling of missing or unavailable metrics without failures
- **FastMCP Integration**: Modern MCP implementation with proper tool registration and error handling
- **Demo Mode Support**: Works on development systems without enterprise GPUs

## Quick Start

### Prerequisites

- Python 3.11+
- AMD GPU with ROCm/AMD SMI installed (or any system for demo mode)
- Git

### Installation

**Option 1: Install as a Package (Recommended)**

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd mcp-amdsmi
   ```

2. **Install the package:**
   ```bash
   pip install -e .
   ```

3. **Test the installation:**
   ```bash
   mcp-amdsmi --help
   ```

**Option 2: Development Installation**

1. **Clone and create virtual environment:**
   ```bash
   git clone <repository-url>
   cd mcp-amdsmi
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install in development mode:**
   ```bash
   pip install -e .
   ```

3. **Test the installation:**
   ```bash
   python test_monitoring.py
   ```

### Running the MCP Server

#### STDIO Transport (Default)

Add this simplified configuration to your MCP client:

```json
{
  "mcpServers": {
    "mcp-amdsmi": {
      "command": "mcp-amdsmi"
    }
  }
}
```

Or if you want to use a specific installation:

```json
{
  "mcpServers": {
    "mcp-amdsmi": {
      "command": "/path/to/venv/bin/mcp-amdsmi"
    }
  }
}
```

#### HTTP Transport

For remote deployments or when you need HTTP access, run the server in HTTP mode:

```bash
# Start HTTP server (default: localhost:8000)
mcp-amdsmi --transport http

# Custom host and port
mcp-amdsmi --transport http --host 0.0.0.0 --port 8080

# With custom session timeout (default: 3600 seconds)
mcp-amdsmi --transport http --session-timeout 7200
```

**HTTP Transport Features:**
- **MCP Streamable HTTP**: Compliant with MCP 2025-03-26 specification
- **Session Management**: Automatic session creation and management via `Mcp-Session-Id` headers
- **Unified Endpoint**: Single `/mcp` endpoint for all MCP operations
- **SSE Support**: Server-Sent Events for real-time streaming
- **RESTful Health Checks**: `/health` endpoint for monitoring
- **CORS Support**: Cross-origin requests enabled for web clients
- **Backward Compatibility**: Maintains compatibility with STDIO transport

**HTTP Client Configuration:**

For MCP clients that support HTTP transport:

```json
{
  "mcpServers": {
    "mcp-amdsmi": {
      "transport": "http",
      "url": "http://localhost:8000/mcp",
      "headers": {
        "Content-Type": "application/json"
      }
    }
  }
}
```

**Available HTTP Endpoints:**
- `POST /mcp` - Main MCP JSON-RPC endpoint
- `GET /mcp` - SSE streaming endpoint (requires `Accept: text/event-stream`)
- `DELETE /mcp` - Session termination endpoint
- `GET /health` - Health check endpoint

**Session Management:**
- Sessions are automatically created during initialization
- Session IDs are returned in `Mcp-Session-Id` response headers
- Clients must include `Mcp-Session-Id` header in subsequent requests
- Sessions automatically expire after the configured timeout
- Sessions can be explicitly terminated via `DELETE /mcp`

## Command Line Options

The MCP server supports various command-line options for both STDIO and HTTP transport modes:

```bash
# Display help
mcp-amdsmi --help

# Transport options
mcp-amdsmi --transport stdio          # Default STDIO transport
mcp-amdsmi --transport http           # HTTP transport mode

# HTTP-specific options
mcp-amdsmi --transport http --host 0.0.0.0 --port 8080
mcp-amdsmi --transport http --session-timeout 7200

# Logging options
mcp-amdsmi --log-level DEBUG          # Enable debug logging
mcp-amdsmi --log-level INFO           # Default info logging
mcp-amdsmi --log-level WARNING        # Warning level only
mcp-amdsmi --log-level ERROR          # Error level only
mcp-amdsmi --log-level CRITICAL       # Critical level only

# Combined example
mcp-amdsmi --transport http --host 0.0.0.0 --port 8080 --session-timeout 7200 --log-level DEBUG
```

**Available Options:**
- `--transport {stdio,http}`: Choose transport mode (default: stdio)
- `--host HOST`: Host to bind to for HTTP mode (default: 127.0.0.1)
- `--port PORT`: Port to bind to for HTTP mode (default: 8000)
- `--session-timeout SECONDS`: Session timeout for HTTP mode (default: 3600)
- `--log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}`: Set logging level (default: INFO)

## Available Tools

### 1. `get_gpu_discovery`
Discovers and enumerates all available AMD GPU devices.
- Returns device information, driver versions, and hardware specifications
- Works in both real hardware and demo modes

### 2. `get_gpu_status`
Provides comprehensive current status of a specific GPU.
- Temperature, power, utilization, memory, clock speeds, and fan data
- Includes overall health score (0-100)
- **Parameters:** `device_id` (string, default: "0")

### 3. `get_gpu_performance`
Analyzes GPU performance metrics and efficiency.
- Performance analysis with efficiency scoring
- Utilization patterns and bottleneck identification
- **Parameters:** `device_id` (string, default: "0")

### 4. `analyze_gpu_memory`
Detailed GPU memory usage analysis.
- Memory health assessment
- Usage patterns and recommendations
- **Parameters:** `device_id` (string, default: "0")

### 5. `monitor_power_thermal`
Monitors GPU power consumption and thermal status.
- Real-time power and temperature data
- Thermal warnings and power efficiency metrics
- **Parameters:** `device_id` (string, default: "0")

### 6. `check_gpu_health`
Comprehensive GPU health assessment with recommendations.
- Overall health status and scoring
- Issue detection and actionable recommendations
- **Parameters:** `device_id` (string, default: "0")

## Example Usage

Once integrated with Claude Code, you can use natural language queries:

- *"What GPUs are available in the system?"*
- *"Check the health of GPU 0"*
- *"Show me the performance metrics for all GPUs"*
- *"Is GPU 0 running too hot?"*
- *"Analyze memory usage patterns"*

## Architecture

The system consists of three main layers:

1. **AMD SMI Interface Layer** (`AMDSMIManager`) - Abstracts AMD SMI Python API with robust error handling
2. **Business Logic Layer** (`HealthAnalyzer`, `PerformanceInterpreter`) - Provides intelligent analysis and recommendations
3. **MCP Server Layer** (FastMCP-based) - Exposes functionality as conversational tools

## Demo Mode

The server automatically falls back to demo mode when:
- No AMD GPUs are detected
- AMD SMI library is unavailable
- Hardware access fails

Demo mode provides realistic mock data for development and testing.

## N/A Value Handling

The server gracefully handles missing or "N/A" values common in:
- Development environments
- Limited hardware access scenarios
- Partial metric availability

Missing values receive neutral health scores (80.0) and don't cause failures.

## Development

### Project Structure
```
mcp-amdsmi/
├── src/amd_smi_mcp/
│   ├── server.py              # FastMCP server with tool definitions
│   ├── amd_smi_wrapper.py     # AMD SMI library abstraction
│   └── business_logic.py      # Health analysis and performance interpretation
├── tests/                     # Unit and integration tests
├── test_monitoring.py         # Comprehensive test script
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

### Running Tests
```bash
source venv/bin/activate
python test_monitoring.py      # Comprehensive functionality test
pytest                         # Unit tests (if available)
```

### Code Quality
```bash
source venv/bin/activate
black src/                     # Code formatting
flake8 src/                    # Linting
mypy src/                      # Type checking
```

## Workshop Integration

Designed for PEARC25 workshop demonstrations:
- 30-second response times for single GPU queries
- Support for 30 concurrent users
- Educational explanations and visual indicators
- Fallback modes for demonstration reliability

## Troubleshooting

### Common Issues

**1. "amdsmi library not available"**
- Install ROCm and AMD SMI library
- Server will automatically use demo mode if unavailable

**2. "No AMD GPU devices found"**
- Check GPU hardware installation
- Verify driver installation
- Server continues in demo mode

**3. "Permission denied" errors**
- Ensure user has GPU access permissions
- May require adding user to appropriate groups

**4. Import errors in Claude Code**
- Verify `cwd` and `PYTHONPATH` in MCP configuration
- Ensure virtual environment activation if using venv

**5. HTTP Transport Issues**

*Connection refused or server not responding:*
- Verify server is running in HTTP mode: `mcp-amdsmi --transport http`
- Check host and port configuration
- Ensure firewall allows connections on the specified port

*"Missing Mcp-Session-Id header" errors:*
- Always initialize session first using the `initialize` method
- Include the session ID from the response header in all subsequent requests
- Sessions expire after the configured timeout (default: 3600 seconds)

*"Invalid or expired session ID" errors:*
- Session may have expired - initialize a new session
- Verify session ID is correctly extracted from headers
- Check for any special characters or encoding issues

*CORS errors in web browsers:*
- Server includes CORS headers by default
- For production, configure allowed origins appropriately
- Ensure `Content-Type: application/json` header is set

*SSE connection issues:*
- Verify `Accept: text/event-stream` header is set
- Ensure session is valid and active
- Check network connectivity and proxy settings

*Tool execution failures:*
- Verify tool name is correct (use `tools/list` to check available tools)
- Check tool arguments match the expected schema
- Review server logs for detailed error information

### Logging

Enable debug logging by setting environment variable:
```bash
export PYTHONPATH=/path/to/mcp-amdsmi
export LOG_LEVEL=DEBUG
```

## License

[License information to be added]

## Contributing

[Contributing guidelines to be added]