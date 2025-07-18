# AMD SMI MCP Server - Docker Setup

This directory contains Docker configuration for testing the AMD SMI MCP Server with ROCm 6.4.1.

## Quick Start

### 1. Build and Test (Recommended)

Use the provided script for an interactive build and test experience:

```bash
chmod +x build-and-test.sh
./build-and-test.sh
```

This script will:
- Build the ROCm 6.4.1 container
- Offer options to run diagnostics, tests, or interactive shell
- Provide clear feedback on each step

### 2. Manual Docker Commands

If you prefer manual control:

```bash
# Build the container
docker-compose build mcp-amdsmi

# Run diagnostics
docker-compose run --rm mcp-diagnose

# Run compatibility tests
docker-compose run --rm mcp-test

# Interactive shell
docker-compose run --rm mcp-amdsmi

# Start MCP server
docker-compose run --rm mcp-amdsmi start-mcp-server
```

## Container Features

### Base Image
- **ROCm 6.4.1** with Ubuntu 22.04
- Full ROCm development environment
- AMD SMI Python library compatibility

### Included Tools
- **diagnose** - System diagnostic tool
- **test-compatibility** - Compatibility test suite
- **start-mcp-server** - MCP server launcher
- **interactive** - Interactive shell with environment activated

### GPU Access
The container is configured to access AMD GPUs through:
- `/dev/kfd` - Kernel Fusion Driver
- `/dev/dri` - Direct Rendering Infrastructure
- ROCm runtime environment

## Expected Behavior

### With ROCm 6.4.1 Container:
✅ **AMD SMI import** - Should work without symbol errors
✅ **GPU detection** - Should find AMD Instinct MI300X
✅ **Metrics collection** - All metrics should be available
✅ **MCP server** - Should start and respond to requests

### Error Handling:
- Clear error messages for missing GPUs
- Proper failure modes instead of demo data
- Specific guidance for ROCm version issues

## Development Workflow

1. **Build once**: `./build-and-test.sh` → option 1 (build)
2. **Test changes**: Edit code, then `docker-compose run --rm mcp-test`
3. **Debug**: `docker-compose run --rm mcp-amdsmi` for interactive shell
4. **Production**: `docker-compose run --rm mcp-amdsmi start-mcp-server`

## Troubleshooting

### Container Build Issues
- Ensure Docker has sufficient memory (4GB+ recommended)
- Check internet connectivity for package downloads
- Verify base image availability: `docker pull rocm/dev-ubuntu-22.04:6.4.1`

### GPU Access Issues
- Ensure AMD GPU drivers are installed on host
- Check that `/dev/kfd` and `/dev/dri` exist on host
- Verify ROCm is working on host: `rocm-smi`

### Permission Issues
- Make sure your user is in the `docker` group
- Run with `sudo` if needed: `sudo ./build-and-test.sh`

## Container Environment

### Environment Variables
- `ROCM_PATH=/opt/rocm`
- `HIP_PATH=/opt/rocm` 
- `AMD_SMI_PATH=/opt/rocm/bin`

### Python Environment
- Python 3.11 with virtual environment
- All dependencies pre-installed
- Package installed in development mode

### File Structure
```
/app/                     # Project root
├── venv/                 # Python virtual environment
├── mcp_amdsmi/          # Main package
├── diagnose_system.py   # Diagnostic tool
├── test_compatibility.py # Test suite
└── requirements.txt     # Dependencies
```

## Performance Notes

- **Container size**: ~8GB (includes full ROCm stack)
- **Build time**: 10-15 minutes (depending on connection)
- **Memory usage**: 2-4GB during operation
- **GPU memory**: Depends on workload, typically < 1GB for monitoring

## Production Deployment

For production use, consider:
1. Multi-stage build to reduce image size
2. Specific version pinning in requirements.txt
3. Health checks for GPU availability
4. Logging configuration for container environments
5. Resource limits and security policies