"""Test utilities and helper functions."""

from typing import Any, Dict, List
from unittest.mock import MagicMock


def create_mock_gpu_device(device_id: str = "gpu_0", **kwargs: Any) -> MagicMock:
    """Create a mock GPU device handle with default properties.
    
    Args:
        device_id: Identifier for the mock GPU device
        **kwargs: Additional properties to set on the mock device
        
    Returns:
        MagicMock: Mock GPU device handle
    """
    device = MagicMock()
    device.device_id = device_id
    
    # Set default properties
    defaults = {
        "temperature": 65.0,
        "power": 250.0,
        "power_cap": 300.0,
        "memory_total": 128 * 1024 * 1024 * 1024,  # 128GB
        "memory_used": 64 * 1024 * 1024 * 1024,    # 64GB
        "utilization_gfx": 85.5,
        "utilization_memory": 70.2,
        "clock_current": 1700,
        "clock_max": 2100,
        "vendor": "AMD",
        "model": "Instinct MI300X"
    }
    
    # Override defaults with provided kwargs
    for key, value in {**defaults, **kwargs}.items():
        setattr(device, key, value)
        
    return device


def create_sample_metrics(device_id: str = "gpu_0", **overrides: Any) -> Dict[str, Any]:
    """Create sample GPU metrics for testing.
    
    Args:
        device_id: Identifier for the GPU device
        **overrides: Values to override in the default metrics
        
    Returns:
        Dict[str, Any]: Sample metrics dictionary
    """
    metrics = {
        "device_id": device_id,
        "timestamp": "2024-01-01T12:00:00Z",
        "temperature": 65.0,
        "power": 250.0,
        "power_cap": 300.0,
        "power_efficiency": 0.83,  # 250/300
        "memory_total": 128 * 1024 * 1024 * 1024,
        "memory_used": 64 * 1024 * 1024 * 1024,
        "memory_utilization": 50.0,
        "utilization_gfx": 85.5,
        "utilization_memory": 70.2,
        "utilization_encoder": 0.0,
        "utilization_decoder": 0.0,
        "clock_current": 1700,
        "clock_max": 2100,
        "clock_min": 500,
        "thermal_throttling": False,
        "power_throttling": False,
        "vendor": "AMD",
        "model": "Instinct MI300X",
        "driver_version": "6.1.0",
        "firmware_version": "1.2.3"
    }
    
    # Apply overrides
    metrics.update(overrides)
    return metrics


def create_unhealthy_metrics(device_id: str = "gpu_0") -> Dict[str, Any]:
    """Create metrics representing an unhealthy GPU state.
    
    Args:
        device_id: Identifier for the GPU device
        
    Returns:
        Dict[str, Any]: Unhealthy metrics dictionary
    """
    return create_sample_metrics(
        device_id=device_id,
        temperature=95.0,           # High temperature
        power=350.0,               # Exceeding power cap
        power_cap=300.0,
        power_efficiency=1.17,     # Over limit
        memory_used=120 * 1024 * 1024 * 1024,  # 94% memory usage
        memory_utilization=94.0,
        utilization_gfx=100.0,     # Maxed out
        utilization_memory=100.0,
        clock_current=500,         # Throttled down
        thermal_throttling=True,
        power_throttling=True
    )


def create_idle_metrics(device_id: str = "gpu_0") -> Dict[str, Any]:
    """Create metrics representing an idle GPU state.
    
    Args:
        device_id: Identifier for the GPU device
        
    Returns:
        Dict[str, Any]: Idle metrics dictionary
    """
    return create_sample_metrics(
        device_id=device_id,
        temperature=45.0,           # Low temperature
        power=50.0,                # Low power
        power_efficiency=0.17,     # Very efficient
        memory_used=1 * 1024 * 1024 * 1024,   # 1GB used
        memory_utilization=0.8,
        utilization_gfx=0.0,       # No graphics workload
        utilization_memory=0.0,    # No memory workload
        clock_current=500,         # Base clock
        thermal_throttling=False,
        power_throttling=False
    )


class MockAMDSMIResponse:
    """Helper class for creating consistent AMD SMI mock responses."""
    
    @staticmethod
    def device_info() -> Dict[str, Any]:
        """Standard device information response."""
        return {
            "asic_serial": "12345",
            "market_name": "AMD Instinct MI300X",
            "vendor_id": "0x1002",
            "device_id": "0x74a1",
            "subsystem_vendor_id": "0x1002",
            "subsystem_device_id": "0x0123",
            "driver_version": "6.1.0",
            "firmware_version": "1.2.3"
        }
    
    @staticmethod
    def temperature_response(temp: float = 65.0) -> float:
        """Temperature metric response."""
        return temp
    
    @staticmethod
    def power_response(power: float = 250.0, cap: float = 300.0) -> Dict[str, float]:
        """Power information response."""
        return {
            "power": power,
            "power_cap": cap,
            "power_cap_max": cap + 50.0,
            "power_cap_min": cap - 150.0
        }
    
    @staticmethod
    def memory_response(used: int = 64 * 1024**3, total: int = 128 * 1024**3) -> Dict[str, Any]:
        """Memory information response."""
        return {
            "vram_total": total,
            "vram_used": used,
            "vram_vendor": "HBM3",
            "vram_type": "HBM3"
        }
    
    @staticmethod
    def utilization_response(gfx: float = 85.5, memory: float = 70.2) -> Dict[str, float]:
        """GPU utilization response."""
        return {
            "gfx_activity": gfx,
            "memory_activity": memory,
            "encoder_activity": 0.0,
            "decoder_activity": 0.0
        }


def assert_metrics_valid(metrics: Dict[str, Any]) -> None:
    """Assert that metrics dictionary contains required fields.
    
    Args:
        metrics: Metrics dictionary to validate
        
    Raises:
        AssertionError: If required fields are missing
    """
    required_fields = [
        "device_id", "temperature", "power", "memory_total", 
        "memory_used", "utilization_gfx", "vendor", "model"
    ]
    
    for field in required_fields:
        assert field in metrics, f"Required field '{field}' missing from metrics"
        
    # Validate data types
    assert isinstance(metrics["temperature"], (int, float))
    assert isinstance(metrics["power"], (int, float))
    assert isinstance(metrics["memory_total"], int)
    assert isinstance(metrics["memory_used"], int)
    assert isinstance(metrics["utilization_gfx"], (int, float))


def assert_health_assessment_valid(assessment: Dict[str, Any]) -> None:
    """Assert that health assessment contains required fields.
    
    Args:
        assessment: Health assessment dictionary to validate
        
    Raises:
        AssertionError: If required fields are missing or invalid
    """
    required_fields = ["health_score", "status", "issues", "recommendations"]
    
    for field in required_fields:
        assert field in assessment, f"Required field '{field}' missing from assessment"
        
    # Validate data types and ranges
    assert isinstance(assessment["health_score"], (int, float))
    assert 0.0 <= assessment["health_score"] <= 10.0
    assert isinstance(assessment["status"], str)
    assert isinstance(assessment["issues"], list)
    assert isinstance(assessment["recommendations"], list)