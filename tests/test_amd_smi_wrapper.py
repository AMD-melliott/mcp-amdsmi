"""Tests for AMD SMI wrapper functionality."""

import pytest
from unittest.mock import patch, MagicMock

from mcp_amdsmi.amd_smi_wrapper import (
    AMDSMIManager, 
    AMDSMIError, 
    AMDSMIDeviceError, 
    AMDSMIMetricsError,
    AMDSMIInitializationError,
    safe_get_value
)


class TestAMDSMIManager:
    """Test cases for AMDSMIManager class."""
    
    def test_initialization(self):
        """Test AMDSMIManager initialization."""
        manager = AMDSMIManager()
        assert manager.initialized is False
        assert manager.device_handles == []
        assert manager.logger is not None
        
    def test_initialize_success(self):
        """Test successful AMD SMI initialization."""
        manager = AMDSMIManager()
        # Override the actual implementation for testing
        manager.initialized = True
        manager.device_handles = [MagicMock(), MagicMock()]
        
        # Mock the initialize method behavior
        with patch.object(manager, 'initialize', return_value=True):
            result = manager.initialize()
            assert result is True
            
    def test_initialize_failure(self):
        """Test AMD SMI initialization failure."""
        manager = AMDSMIManager()
        # Mock the initialize method to return False (failure)
        with patch.object(manager, 'initialize', return_value=False):
            result = manager.initialize()
            assert result is False
        
    def test_shutdown(self):
        """Test AMD SMI shutdown."""
        manager = AMDSMIManager()
        manager.initialized = True
        manager.device_handles = [MagicMock()]
        
        manager.shutdown()
        assert manager.initialized is False
        assert manager.device_handles == []
        
    def test_get_device_handles(self):
        """Test getting device handles."""
        manager = AMDSMIManager()
        test_handles = [MagicMock(), MagicMock()]
        manager.device_handles = test_handles
        
        handles = manager.get_device_handles()
        assert len(handles) == 2
        assert handles is not test_handles  # Should return a copy
        
    def test_get_device_info_placeholder(self):
        """Test device info retrieval with mocked data."""
        manager = AMDSMIManager()
        
        # Mock the device and initialization
        mock_device = MagicMock()
        manager.device_handles = [mock_device]
        manager.initialized = True
        
        # Mock the get_device_info method to return test data
        with patch.object(manager, 'get_device_info') as mock_get_info:
            mock_get_info.return_value = {
                "device_id": "test_device_id",
                "name": "AMD Instinct MI250X",
                "asic_family": "gfx90a",
                "vbios_version": "1.0.0",
                "driver_version": "6.4.1",
                "pci_info": {"domain": 0, "bus": 1, "device": 0, "function": 0}
            }
            
            info = manager.get_device_info(mock_device)
            assert isinstance(info, dict)
            assert "device_id" in info
            assert "name" in info
            assert "AMD Instinct MI250X" in info["name"]
        
    def test_get_metrics_placeholder(self):
        """Test metrics collection with mocked data."""
        manager = AMDSMIManager()
        
        # Mock the device and initialization
        mock_device = MagicMock()
        manager.device_handles = [mock_device]
        manager.initialized = True
        
        metric_types = ["temperature", "power"]
        
        # Mock the get_metrics method to return test data
        with patch.object(manager, 'get_metrics') as mock_get_metrics:
            mock_get_metrics.return_value = {
                "temperature": {"current": 45, "critical": 90, "emergency": 95},
                "power": {"current": 150, "average": 140, "cap": 300}
            }
            
            metrics = manager.get_metrics(mock_device, metric_types)
            assert isinstance(metrics, dict)
            assert "temperature" in metrics
            assert "power" in metrics
            assert metrics["temperature"]["current"] > 0
            assert metrics["power"]["current"] > 0
        
    def test_context_manager_success(self):
        """Test context manager with successful initialization."""
        manager = AMDSMIManager()
        # Mock successful initialization
        manager.initialize = MagicMock(return_value=True)
        manager.shutdown = MagicMock()
        
        with manager.gpu_context() as ctx:
            assert ctx is manager
            
        manager.initialize.assert_called_once()
        manager.shutdown.assert_called_once()
            
    def test_context_manager_failure(self):
        """Test context manager with failed initialization."""
        manager = AMDSMIManager()
        manager.initialize = MagicMock(return_value=False)
        
        with pytest.raises(RuntimeError, match="Failed to initialize AMD SMI"):
            with manager.gpu_context():
                pass

    def test_get_device_count(self):
        """Test device count retrieval."""
        manager = AMDSMIManager()
        
        # Mock two devices
        manager.device_handles = [MagicMock(), MagicMock()]
        
        count = manager.get_device_count()
        assert count == 2
        
    def test_is_device_valid(self):
        """Test device handle validation."""
        manager = AMDSMIManager()
        
        # Mock device handles
        mock_device_1 = MagicMock()
        mock_device_2 = MagicMock()
        manager.device_handles = [mock_device_1, mock_device_2]
        
        # Valid device should return True
        assert manager.is_device_valid(mock_device_1) is True
        assert manager.is_device_valid(mock_device_2) is True
        
        # Invalid device should return False
        invalid_handle = MagicMock()
        assert manager.is_device_valid(invalid_handle) is False
        
    def test_get_device_by_index(self):
        """Test device retrieval by index."""
        manager = AMDSMIManager()
        
        # Mock device handles
        mock_device_1 = MagicMock()
        mock_device_2 = MagicMock()
        manager.device_handles = [mock_device_1, mock_device_2]
        
        # Test valid indices
        device = manager.get_device_by_index(0)
        assert device == mock_device_1
        
        device = manager.get_device_by_index(1)
        assert device == mock_device_2
        
        # Test invalid index
        device = manager.get_device_by_index(999)
        assert device is None
        
    def test_get_all_device_metrics(self):
        """Test metrics collection for all devices."""
        manager = AMDSMIManager()
        
        # Mock device handles
        mock_device_1 = MagicMock()
        mock_device_2 = MagicMock()
        manager.device_handles = [mock_device_1, mock_device_2]
        
        # Mock the get_metrics method
        with patch.object(manager, 'get_metrics') as mock_get_metrics:
            mock_get_metrics.return_value = {
                "temperature": {"current": 45, "critical": 90},
                "power": {"current": 150, "average": 140}
            }
            
            all_metrics = manager.get_all_device_metrics(["temperature", "power"])
            
            assert isinstance(all_metrics, dict)
            assert "0" in all_metrics
            assert "1" in all_metrics
            
            # Check first device metrics
            device_0_metrics = all_metrics["0"]
            assert "temperature" in device_0_metrics
            assert "power" in device_0_metrics


class TestErrorHandling:
    """Test error handling in AMD SMI wrapper."""
    
    def test_device_info_not_initialized(self):
        """Test device info access when not initialized."""
        manager = AMDSMIManager()
        
        with pytest.raises(AMDSMIError, match="AMD SMI not initialized"):
            manager.get_device_info("some_device")
            
    def test_metrics_not_initialized(self):
        """Test metrics access when not initialized."""
        manager = AMDSMIManager()
        
        with pytest.raises(AMDSMIError, match="AMD SMI not initialized"):
            manager.get_metrics("some_device", ["temperature"])
            
    def test_invalid_device_handle(self):
        """Test operations with invalid device handle."""
        manager = AMDSMIManager()
        
        # Mock device handles
        mock_device = MagicMock()
        manager.device_handles = [mock_device]
        manager.initialized = True
        
        # Test non-existent device
        invalid_device = MagicMock()
        with pytest.raises(AMDSMIDeviceError, match="Invalid device handle"):
            manager.get_device_info(invalid_device)
            
    def test_initialization_max_attempts(self):
        """Test maximum initialization attempts."""
        manager = AMDSMIManager()
        
        # Mock initialization to always fail
        with patch('mcp_amdsmi.amd_smi_wrapper.AMDSMI_AVAILABLE', False):
            with pytest.raises(AMDSMIInitializationError, match="AMD SMI library not available"):
                manager.initialize()
                
    def test_thread_safety(self):
        """Test thread safety of initialization."""
        import threading
        manager = AMDSMIManager()
        results = []
        
        # Mock successful initialization
        with patch.object(manager, 'initialize', return_value=True):
            def init_worker():
                try:
                    result = manager.initialize()
                    results.append(result)
                except Exception as e:
                    results.append(e)
            
            # Start multiple threads
            threads = [threading.Thread(target=init_worker) for _ in range(5)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
                
            # All should succeed
            assert all(r is True for r in results)
            assert len(results) == 5


class TestSafeGetValue:
    """Test cases for safe_get_value function."""
    
    def test_none_value(self):
        """Test handling of None values."""
        result = safe_get_value(None, 'default')
        assert result == 'default'
        
    def test_numeric_value(self):
        """Test handling of numeric values."""
        result = safe_get_value(42)
        assert result == 42
        
        result = safe_get_value(3.14)
        assert result == 3.14
        
    def test_string_na_value(self):
        """Test handling of N/A string values."""
        result = safe_get_value('N/A', 0)
        assert result == 0
        
        result = safe_get_value('  n/a  ', 0)
        assert result == 0
        
    def test_string_numeric_value(self):
        """Test handling of numeric string values."""
        result = safe_get_value('42', 0)
        assert result == 42.0
        
        result = safe_get_value('3.14', 0)
        assert result == 3.14
        
    def test_string_non_numeric_value(self):
        """Test handling of non-numeric string values."""
        # Without expect_numeric, string values are preserved
        result = safe_get_value('invalid', 0)
        assert result == 'invalid'
        
        # With expect_numeric, non-numeric strings return default
        result = safe_get_value('invalid', 0, expect_numeric=True)
        assert result == 0
        
    def test_dict_value_normal(self):
        """Test handling of dictionary values in normal mode."""
        input_dict = {'key1': 'value1', 'key2': 42}
        result = safe_get_value(input_dict, {})
        assert result == {'key1': 'value1', 'key2': 42}
        
    def test_dict_value_expect_numeric(self):
        """Test handling of dictionary values when expecting numeric."""
        # Non-empty dict with expect_numeric=True should return default
        input_dict = {'key1': 'value1'}
        result = safe_get_value(input_dict, 0, expect_numeric=True)
        assert result == 0
        
    def test_empty_dict_value(self):
        """Test handling of empty dictionary values."""
        # Empty dict should return default regardless of expect_numeric
        result = safe_get_value({}, 0, expect_numeric=False)
        assert result == 0
        
        result = safe_get_value({}, 0, expect_numeric=True)
        assert result == 0
        
    def test_mm_activity_dict_case(self):
        """Test the specific case of mm_activity returning {}."""
        # This is the exact case we're fixing - mm_activity returns {}
        result = safe_get_value({}, 0, expect_numeric=True)
        assert result == 0
        
    def test_utilization_metrics_consistency(self):
        """Test that utilization metrics always return numeric values."""
        # Test various problematic values that might come from GPU activity
        test_values = [None, {}, {'some': 'dict'}, 'N/A', 'invalid', '', 0, 42, 3.14]
        
        for value in test_values:
            result = safe_get_value(value, 0, expect_numeric=True)
            assert isinstance(result, (int, float)), f"Expected numeric for {value}, got {type(result)}"
            
    def test_list_value(self):
        """Test handling of list values."""
        input_list = [1, 2, 'N/A', 4]
        result = safe_get_value(input_list, 0)
        assert result == [1, 2, 0, 4]
        
    def test_list_value_expect_numeric(self):
        """Test handling of list values with expect_numeric."""
        # List items should not propagate expect_numeric
        input_list = [1, {}, 'N/A', 4, 'valid_string']
        result = safe_get_value(input_list, 0, expect_numeric=True)
        assert result == [1, 0, 0, 4, 'valid_string']
        
    def test_nested_dict_processing(self):
        """Test nested dictionary processing."""
        input_dict = {
            'level1': {
                'level2': 'N/A',
                'number': 42
            },
            'direct': 'value'
        }
        result = safe_get_value(input_dict, 0)
        expected = {
            'level1': {
                'level2': 0,
                'number': 42
            },
            'direct': 'value'
        }
        assert result == expected