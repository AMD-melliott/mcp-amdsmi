# AMD SMI MCP Server

> **⚠️ DEMONSTRATION ONLY ⚠️**
> 
> This is a demonstration project created for PEARC25. It is **NOT intended for production use**. This server is designed for educational, research, and demonstration purposes only. For production GPU monitoring, please use enterprise-grade monitoring solutions with proper security, reliability, and support guarantees.
> 
> **Security Notice:** This server may expose system information and should only be used in trusted environments.

A Model Context Protocol (MCP) server created for PEARC25 that provides conversational access to AMD GPU monitoring capabilities. Designed for infrastructure monitoring demonstrations and basic performance analysis.

## Features

- **Six Core Monitoring Tools**: Device discovery, status monitoring, performance analysis, memory analysis, power/thermal monitoring, and health assessment
- **Intelligent Health Analysis**: AI-powered health scoring with contextual recommendations
- **N/A Value Handling**: Robust handling of missing or unavailable metrics without failures
- **FastMCP Integration**: Modern MCP implementation with proper tool registration and error handling
- **Demo Mode Support**: Works on development systems without enterprise GPUs

## Quick Start

### Prerequisites

- Python 3.11+
- AMD GPU with ROCm 5.0+ and AMD SMI installed (for hardware monitoring)
- Git

**Note:** The server includes demo mode functionality and will work on systems without AMD hardware for testing purposes.

### Installation

**Option 1: Install as a Package (Recommended)**

1. **Clone the repository:**
   ```bash
   git clone https://github.com/AMD-melliott/mcp-amdsmi.git
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
   git clone https://github.com/AMD-melliott/mcp-amdsmi.git
   cd mcp-amdsmi
   python3 -m venv venv
   source venv/bin/activate
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
python3 -m mcp_amdsmi.unified_server --transport http

# Custom host and port
python3 -m mcp_amdsmi.unified_server --transport http --host 0.0.0.0 --port 8080

# With custom session timeout (default: 3600 seconds)
python3 -m mcp_amdsmi.unified_server --transport http --session-timeout 7200
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
      "url": "http://127.0.0.1:8000/mcp"
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

Once integrated with an MCP client (such as Claude Desktop), you can use natural language queries:

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
├── mcp_amdsmi/
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
black mcp_amdsmi/             # Code formatting
flake8 mcp_amdsmi/            # Linting
mypy mcp_amdsmi/              # Type checking
```
## Troubleshooting

### Common Issues

*"amdsmi library not available"*
- Install ROCm and AMD SMI library
- Server will automatically use demo mode if unavailable

*"No AMD GPU devices found"*
- Check GPU hardware installation
- Verify driver installation
- Server continues in demo mode

*"Permission denied" errors*
- Ensure user has GPU access permissions
- May require adding user to appropriate groups

*Import errors in MCP clients*
- Verify `cwd` and `PYTHONPATH` in MCP configuration
- Ensure virtual environment activation if using venv

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
