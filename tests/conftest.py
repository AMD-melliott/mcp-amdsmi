"""Test configuration and fixtures for AMD SMI MCP Server."""

import pytest
from unittest.mock import Mock, MagicMock
from typing import Any, Dict, List, Generator

from mcp_amdsmi.amd_smi_wrapper import AMDSMIManager
from mcp_amdsmi.business_logic import HealthAnalyzer, PerformanceInterpreter


@pytest.fixture
def mock_amdsmi():
    """Mock the AMD SMI library for testing without hardware."""
    mock = MagicMock()
    
    # Mock initialization
    mock.amdsmi_init.return_value = None
    mock.amdsmi_shut_down.return_value = None
    
    # Mock device handles - simulate 2 GPUs
    mock_handles = [MagicMock(), MagicMock()]
    mock.amdsmi_get_processor_handles.return_value = mock_handles
    
    # Mock device info
    mock.amdsmi_get_gpu_asic_info.return_value = {
        "asic_serial": "12345",
        "market_name": "AMD Instinct MI300X",
        "vendor_id": "0x1002",
        "device_id": "0x74a1",
        "subsystem_vendor_id": "0x1002",
        "subsystem_device_id": "0x0123"
    }
    
    # Mock temperature data
    mock.amdsmi_get_temp_metric.return_value = 65.0  # 65°C
    
    # Mock power data
    mock.amdsmi_get_gpu_power_info.return_value = {
        "power": 250.0,  # 250W
        "power_cap": 300.0,
        "power_cap_max": 350.0,
        "power_cap_min": 150.0
    }
    
    # Mock memory data
    mock.amdsmi_get_gpu_memory_info.return_value = {
        "vram_total": 128 * 1024 * 1024 * 1024,  # 128GB
        "vram_used": 64 * 1024 * 1024 * 1024,    # 64GB used
        "vram_vendor": "HBM3"
    }
    
    # Mock utilization data
    mock.amdsmi_get_gpu_usage_info.return_value = {
        "gfx_activity": 85.5,  # 85.5% utilization
        "memory_activity": 70.2,
        "encoder_activity": 0.0,
        "decoder_activity": 0.0
    }
    
    # Mock clock speeds
    mock.amdsmi_get_clk_freq.return_value = {
        "current": 1700,  # MHz
        "min": 500,
        "max": 2100
    }
    
    return mock


@pytest.fixture
def sample_gpu_metrics() -> Dict[str, Any]:
    """Sample GPU metrics for testing business logic."""
    return {
        "device_id": "gpu_0",
        "temperature": 65.0,
        "power": 250.0,
        "power_cap": 300.0,
        "memory_total": 128 * 1024 * 1024 * 1024,
        "vram_used": 64 * 1024 * 1024 * 1024,
        "vram_total": 128 * 1024 * 1024 * 1024,
        "utilization_gfx": 85.5,
        "utilization_memory": 70.2,
        "clock_current": 1700,
        "clock_max": 2100,
        "vendor": "AMD",
        "model": "Instinct MI300X"
    }


@pytest.fixture
def amd_smi_manager() -> AMDSMIManager:
    """Create an AMDSMIManager instance for testing."""
    return AMDSMIManager()


@pytest.fixture
def gpu_health_analyzer() -> HealthAnalyzer:
    """Create a HealthAnalyzer instance for testing."""
    return HealthAnalyzer()


@pytest.fixture
def performance_interpreter() -> PerformanceInterpreter:
    """Create a PerformanceInterpreter instance for testing."""
    return PerformanceInterpreter()


@pytest.fixture
def mcp_server(amd_smi_manager):
    """Create an MCP server instance for testing."""
    # FastMCP server doesn't need explicit instantiation for testing
    return None


@pytest.fixture
def unhealthy_gpu_metrics() -> Dict[str, Any]:
    """Sample unhealthy GPU metrics for testing edge cases."""
    return {
        "device_id": "gpu_0",
        "temperature": 95.0,  # High temperature
        "power": 320.0,       # Exceeding power cap
        "power_cap": 300.0,
        "memory_total": 128 * 1024 * 1024 * 1024,
        "vram_used": 120 * 1024 * 1024 * 1024,  # 94% memory usage
        "vram_total": 128 * 1024 * 1024 * 1024,
        "utilization_gfx": 100.0,  # Maxed out
        "utilization_memory": 100.0,
        "clock_current": 500,   # Throttled down
        "clock_max": 2100,
        "vendor": "AMD",
        "model": "Instinct MI300X"
    }


@pytest.fixture
def mock_mcp_client():
    """Mock MCP client for testing server interactions."""
    client = MagicMock()
    client.list_tools.return_value = []
    client.call_tool.return_value = {"content": [{"text": "Mock response"}]}
    return client


class AsyncContextManager:
    """Helper class for testing async context managers."""
    
    def __init__(self, return_value):
        self.return_value = return_value
        
    async def __aenter__(self):
        return self.return_value
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return None


@pytest.fixture
def mock_stdio_server():
    """Mock stdio server for testing MCP server."""
    mock_streams = (MagicMock(), MagicMock())
    return AsyncContextManager(mock_streams)