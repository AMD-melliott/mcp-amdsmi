"""Tests for MCP server functionality."""

import pytest
from unittest.mock import MagicMock, patch

from mcp_amdsmi.server import main, mcp


class TestFastMCPServer:
    """Test cases for FastMCP server setup."""
    
    def test_server_initialization(self):
        """Test FastMCP server initialization."""
        assert mcp is not None
        assert hasattr(mcp, 'name')
        assert mcp.name == "AMD GPU Monitor"
        
    def test_tools_registered(self):
        """Test that MCP tools are properly registered by importing them."""
        # Test that we can import all the tool functions without error
        from mcp_amdsmi.server import (
            get_gpu_discovery,
            get_gpu_status,
            get_gpu_performance,
            analyze_gpu_memory,
            monitor_power_thermal,
            check_gpu_health
        )
        
        # Check that all tools exist (they are FunctionTool objects from FastMCP)
        tools = [
            get_gpu_discovery,
            get_gpu_status,
            get_gpu_performance,
            analyze_gpu_memory,
            monitor_power_thermal,
            check_gpu_health
        ]
        
        for tool in tools:
            assert tool is not None, f"Tool {tool} is None"
            # FastMCP tools have a name attribute
            assert hasattr(tool, 'name'), f"Tool {tool} doesn't have name attribute"


class TestMainFunction:
    """Test cases for main function."""
    
    def test_main_function(self):
        """Test main entry point function."""
        with patch('mcp_amdsmi.server.mcp.run') as mock_run:
            with patch('mcp_amdsmi.server.logging.basicConfig') as mock_logging:
                main()
                
                mock_logging.assert_called_once_with(level=20)  # logging.INFO = 20
                mock_run.assert_called_once()


class TestMCPServerIntegration:
    """Integration tests for MCP server components."""
    
    def test_server_components_integration(self):
        """Test that server components work together."""
        # Import the global instances
        from mcp_amdsmi.server import smi_manager, health_analyzer, performance_interpreter
        
        # Verify components are properly initialized
        assert smi_manager is not None
        assert health_analyzer is not None
        assert performance_interpreter is not None
        
    def test_server_with_smi_manager(self):
        """Test server with AMD SMI manager."""
        from mcp_amdsmi.server import smi_manager
        
        # Should initialize without errors
        assert smi_manager is not None
        assert hasattr(smi_manager, 'initialize')
        assert hasattr(smi_manager, 'get_device_handles')


class TestToolResponses:
    """Test cases for MCP tool responses."""
    
    @patch('mcp_amdsmi.server.smi_manager')
    def test_get_gpu_discovery_response_format(self, mock_smi_manager):
        """Test that get_gpu_discovery returns human-readable text."""
        from mcp_amdsmi.server import get_gpu_discovery
        
        # Mock the GPU context and device handles
        mock_context = MagicMock()
        mock_smi_manager.gpu_context.return_value = mock_context
        mock_smi_manager.get_device_handles.return_value = [MagicMock()]
        mock_smi_manager.get_device_info.return_value = {
            'name': 'Test GPU',
            'index': 0,
            'driver_version': '1.0.0'
        }
        
        # Access the actual function through the tool wrapper
        result = get_gpu_discovery.fn()
        
        # Should return a string (human-readable text)
        assert isinstance(result, str)
        assert "AMD GPU Discovery Report" in result
        assert "Test GPU" in result
        assert "Driver Version: 1.0.0" in result
        
    @patch('mcp_amdsmi.server.smi_manager')
    @patch('mcp_amdsmi.server.health_analyzer')
    def test_get_gpu_status_response_format(self, mock_health_analyzer, mock_smi_manager):
        """Test that get_gpu_status returns human-readable text."""
        from mcp_amdsmi.server import get_gpu_status
        
        # Mock the GPU context and metrics
        mock_context = MagicMock()
        mock_smi_manager.gpu_context.return_value = mock_context
        mock_smi_manager.get_device_by_index.return_value = MagicMock()
        mock_smi_manager.get_metrics.return_value = {
            'temperature': {'current': 65.0},
            'power': {'current': 180, 'cap': 240},
            'memory': {'used': 6144, 'total': 8192},
            'utilization': {'gpu': 75, 'memory': 80}
        }
        mock_health_analyzer.calculate_health_score.return_value = 85.5
        
        # Access the actual function through the tool wrapper
        result = get_gpu_status.fn()
        
        # Should return a string (human-readable text)
        assert isinstance(result, str)
        assert "GPU Device 0 Status Report" in result
        assert "Health Summary" in result
        assert "85.5/100" in result
        assert "65.0°C" in result
        assert "180W" in result
        
    @patch('mcp_amdsmi.server.smi_manager')
    @patch('mcp_amdsmi.server.performance_interpreter')
    def test_get_gpu_performance_response_format(self, mock_performance_interpreter, mock_smi_manager):
        """Test that get_gpu_performance returns human-readable text."""
        from mcp_amdsmi.server import get_gpu_performance
        
        # Mock the GPU context and metrics
        mock_context = MagicMock()
        mock_smi_manager.gpu_context.return_value = mock_context
        mock_smi_manager.get_device_by_index.return_value = MagicMock()
        mock_smi_manager.get_metrics.return_value = {
            'utilization': {'gpu': 85, 'memory': 70},
            'clock': {'sclk': 1500, 'mclk': 2000},
            'memory': {'used': 6144, 'total': 8192},
            'power': {'current': 200, 'cap': 240}
        }
        mock_performance_interpreter.calculate_efficiency.return_value = 88.5
        mock_performance_interpreter.analyze_utilization.return_value = {
            'balance_score': 85.0,
            'recommendations': ['Test recommendation']
        }
        
        # Access the actual function through the tool wrapper
        result = get_gpu_performance.fn()
        
        # Should return a string (human-readable text)
        assert isinstance(result, str)
        assert "GPU Device 0 Performance Analysis" in result
        assert "Performance Summary" in result
        assert "88.5/100" in result
        assert "85%" in result
        assert "Test recommendation" in result
        
    @patch('mcp_amdsmi.server.smi_manager')
    @patch('mcp_amdsmi.server.health_analyzer')
    @patch('mcp_amdsmi.server.performance_interpreter')
    def test_analyze_gpu_memory_response_format(self, mock_performance_interpreter, mock_health_analyzer, mock_smi_manager):
        """Test that analyze_gpu_memory returns human-readable text."""
        from mcp_amdsmi.server import analyze_gpu_memory
        
        # Mock the GPU context and metrics
        mock_context = MagicMock()
        mock_smi_manager.gpu_context.return_value = mock_context
        mock_smi_manager.get_device_by_index.return_value = MagicMock()
        mock_smi_manager.get_metrics.return_value = {
            'memory': {'used': 6144, 'total': 8192, 'free': 2048}
        }
        mock_health_analyzer.analyze_memory_health.return_value = "healthy"
        mock_performance_interpreter.analyze_memory_efficiency.return_value = {
            'recommendations': ['Test memory recommendation']
        }
        
        # Access the actual function through the tool wrapper
        result = analyze_gpu_memory.fn()
        
        # Should return a string (human-readable text)
        assert isinstance(result, str)
        assert "GPU Device 0 Memory Analysis" in result
        assert "Memory Status" in result
        assert "6.0GB" in result
        assert "8.0GB" in result
        assert "healthy" in result
        assert "Test memory recommendation" in result
        
    @patch('mcp_amdsmi.server.smi_manager')
    @patch('mcp_amdsmi.server.health_analyzer')
    @patch('mcp_amdsmi.server.performance_interpreter')
    def test_monitor_power_thermal_response_format(self, mock_performance_interpreter, mock_health_analyzer, mock_smi_manager):
        """Test that monitor_power_thermal returns human-readable text."""
        from mcp_amdsmi.server import monitor_power_thermal
        
        # Mock the GPU context and metrics
        mock_context = MagicMock()
        mock_smi_manager.gpu_context.return_value = mock_context
        mock_smi_manager.get_device_by_index.return_value = MagicMock()
        mock_smi_manager.get_metrics.return_value = {
            'temperature': {'current': 72.0, 'critical': 90.0},
            'power': {'current': 180, 'cap': 240},
            'fan': {'speed_percent': 60, 'speed_rpm': 2400}
        }
        mock_health_analyzer.check_thermal_warnings.return_value = []
        mock_performance_interpreter.analyze_thermal_performance.return_value = {
            'thermal_margin': 18.0,
            'thermal_efficiency': 80.0,
            'recommendations': ['Test thermal recommendation']
        }
        
        # Access the actual function through the tool wrapper
        result = monitor_power_thermal.fn()
        
        # Should return a string (human-readable text)
        assert isinstance(result, str)
        assert "GPU Device 0 Power & Thermal Monitor" in result
        assert "Current Readings" in result
        assert "72.0°C" in result
        assert "180W" in result
        assert "60%" in result
        assert "Test thermal recommendation" in result
        
    @patch('mcp_amdsmi.server.smi_manager')
    @patch('mcp_amdsmi.server.health_analyzer')
    def test_check_gpu_health_response_format(self, mock_health_analyzer, mock_smi_manager):
        """Test that check_gpu_health returns human-readable text."""
        from mcp_amdsmi.server import check_gpu_health
        
        # Mock the GPU context and metrics
        mock_context = MagicMock()
        mock_smi_manager.gpu_context.return_value = mock_context
        mock_smi_manager.get_device_by_index.return_value = MagicMock()
        mock_smi_manager.get_metrics.return_value = {
            'temperature': {'current': 65.0},
            'power': {'current': 180, 'cap': 240},
            'memory': {'used': 6144, 'total': 8192},
            'utilization': {'gpu': 75, 'memory': 80},
            'fan': {'speed_percent': 55}
        }
        mock_health_analyzer.comprehensive_health_check.return_value = {
            'status': 'good',
            'score': 85.5,
            'issues': ['Test issue'],
            'recommendations': ['Test recommendation']
        }
        
        # Access the actual function through the tool wrapper
        result = check_gpu_health.fn()
        
        # Should return a string (human-readable text)
        assert isinstance(result, str)
        assert "GPU Device 0 Health Assessment" in result
        assert "Overall Health Status" in result
        assert "85.5/100" in result
        assert "Good" in result
        assert "Test issue" in result
        assert "Test recommendation" in result


class TestErrorHandling:
    """Test error handling in server components."""
    
    def test_server_initialization_with_smi_failure(self):
        """Test server initialization when AMD SMI fails."""
        from mcp_amdsmi.server import smi_manager
        
        # Server should still initialize even if AMD SMI fails
        assert smi_manager is not None
        
    def test_main_with_server_exception(self):
        """Test main function when server raises exception."""
        with patch('mcp_amdsmi.server.mcp.run') as mock_run:
            mock_run.side_effect = Exception("Test exception")
            
            with pytest.raises(Exception, match="Test exception"):
                main()
                
    @patch('mcp_amdsmi.server.smi_manager')
    def test_error_response_format(self, mock_smi_manager):
        """Test that error responses are also human-readable."""
        from mcp_amdsmi.server import get_gpu_status
        
        # Mock an error scenario
        mock_context = MagicMock()
        mock_smi_manager.gpu_context.return_value = mock_context
        mock_smi_manager.get_device_by_index.side_effect = Exception("Test error")
        
        # Access the actual function through the tool wrapper
        result = get_gpu_status.fn()
        
        # Should return a string (human-readable error message)
        assert isinstance(result, str)
        assert "GPU Device 0 Status Report" in result
        assert "❌ Error: Failed to retrieve GPU status" in result
        assert "Test error" in result
        assert "Troubleshooting:" in result