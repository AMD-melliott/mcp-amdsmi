"""Tests for text formatting utilities."""

import pytest
from datetime import datetime
from mcp_amdsmi.text_formatting import (
    format_header,
    format_timestamp,
    format_health_score,
    format_temperature,
    format_power,
    format_memory,
    format_utilization,
    format_clock_speeds,
    format_fan_info,
    format_bullet_list,
    format_numbered_list,
    format_key_value_table,
    format_device_summary,
    format_warnings,
    format_recommendations,
    format_issues,
    format_summary_table,
    format_efficiency_score,
)


class TestHeaderFormatting:
    """Test cases for header formatting functions."""
    
    def test_format_header_level_1(self):
        """Test level 1 header formatting."""
        result = format_header("Test Header", level=1)
        expected = "Test Header\n===========\n"
        assert result == expected
        
    def test_format_header_level_2(self):
        """Test level 2 header formatting."""
        result = format_header("Test Header", level=2)
        expected = "Test Header\n-----------\n"
        assert result == expected
        
    def test_format_header_level_3(self):
        """Test level 3 header formatting."""
        result = format_header("Test Header", level=3)
        expected = "### Test Header\n"
        assert result == expected
        
    def test_format_header_default_level(self):
        """Test default header level."""
        result = format_header("Test Header")
        expected = "Test Header\n===========\n"
        assert result == expected


class TestTimestampFormatting:
    """Test cases for timestamp formatting."""
    
    def test_format_timestamp(self):
        """Test timestamp formatting."""
        # Use a known timestamp
        timestamp = 1640995200.0  # 2022-01-01 00:00:00
        result = format_timestamp(timestamp)
        
        # Should return a formatted date string
        assert isinstance(result, str)
        assert "2022-01-01" in result
        assert "00:00:00" in result


class TestHealthScoreFormatting:
    """Test cases for health score formatting."""
    
    def test_format_health_score_excellent(self):
        """Test excellent health score formatting."""
        result = format_health_score(95.0)
        assert "🟢" in result
        assert "95.0/100" in result
        assert "Excellent" in result
        
    def test_format_health_score_good(self):
        """Test good health score formatting."""
        result = format_health_score(80.0)
        assert "🟢" in result
        assert "80.0/100" in result
        assert "Good" in result
        
    def test_format_health_score_moderate(self):
        """Test moderate health score formatting."""
        result = format_health_score(60.0)
        assert "🟡" in result
        assert "60.0/100" in result
        assert "Moderate" in result
        
    def test_format_health_score_poor(self):
        """Test poor health score formatting."""
        result = format_health_score(30.0)
        assert "🟠" in result
        assert "30.0/100" in result
        assert "Poor" in result
        
    def test_format_health_score_critical(self):
        """Test critical health score formatting."""
        result = format_health_score(10.0)
        assert "🔴" in result
        assert "10.0/100" in result
        assert "Critical" in result


class TestTemperatureFormatting:
    """Test cases for temperature formatting."""
    
    def test_format_temperature_normal(self):
        """Test normal temperature formatting."""
        temp_data = {'current': 65.0, 'critical': 90.0}
        result = format_temperature(temp_data)
        
        assert "Temperature: 65.0°C" in result
        assert "Critical: 90.0°C" in result
        assert "✅ Normal" in result
        
    def test_format_temperature_high(self):
        """Test high temperature formatting."""
        temp_data = {'current': 85.0, 'critical': 90.0}
        result = format_temperature(temp_data)
        
        assert "Temperature: 85.0°C" in result
        assert "⚠️ High" in result
        
    def test_format_temperature_critical(self):
        """Test critical temperature formatting."""
        temp_data = {'current': 95.0, 'critical': 90.0}
        result = format_temperature(temp_data)
        
        assert "Temperature: 95.0°C" in result
        assert "⚠️ Critical" in result
        
    def test_format_temperature_empty(self):
        """Test temperature formatting with empty data."""
        result = format_temperature({})
        assert result == "Temperature: N/A"
        
    def test_format_temperature_zero(self):
        """Test temperature formatting with zero value."""
        temp_data = {'current': 0.0}
        result = format_temperature(temp_data)
        assert result == "Temperature: N/A"


class TestPowerFormatting:
    """Test cases for power formatting."""
    
    def test_format_power_normal(self):
        """Test normal power formatting."""
        power_data = {'current': 180, 'cap': 240}
        result = format_power(power_data)
        
        assert "Power: 180W" in result
        assert "240W" in result
        assert "75.0%" in result
        assert "✅ Normal" in result
        
    def test_format_power_high(self):
        """Test high power formatting."""
        power_data = {'current': 220, 'cap': 240}
        result = format_power(power_data)
        
        assert "Power: 220W" in result
        assert "⚠️ High" in result
        
    def test_format_power_very_high(self):
        """Test very high power formatting."""
        power_data = {'current': 230, 'cap': 240}
        result = format_power(power_data)
        
        assert "Power: 230W" in result
        assert "⚠️ Very High" in result
        
    def test_format_power_empty(self):
        """Test power formatting with empty data."""
        result = format_power({})
        assert result == "Power: N/A"


class TestMemoryFormatting:
    """Test cases for memory formatting."""
    
    def test_format_memory_normal(self):
        """Test normal memory formatting."""
        memory_data = {'used': 6144, 'total': 8192}  # MB
        result = format_memory(memory_data)
        
        assert "Memory: 6.0GB / 8.0GB" in result
        assert "75.0%" in result
        assert "✅ Normal" in result
        
    def test_format_memory_high(self):
        """Test high memory formatting."""
        memory_data = {'used': 7168, 'total': 8192}  # MB
        result = format_memory(memory_data)
        
        assert "Memory: 7.0GB / 8.0GB" in result
        assert "⚠️ Moderate" in result
        
    def test_format_memory_critical(self):
        """Test critical memory formatting."""
        memory_data = {'used': 7864, 'total': 8192}  # MB
        result = format_memory(memory_data)
        
        assert "Memory: 7.7GB / 8.0GB" in result
        assert "⚠️ Critical" in result
        
    def test_format_memory_empty(self):
        """Test memory formatting with empty data."""
        result = format_memory({})
        assert result == "Memory: N/A"


class TestUtilizationFormatting:
    """Test cases for utilization formatting."""
    
    def test_format_utilization_high(self):
        """Test high utilization formatting."""
        util_data = {'gpu': 95, 'memory': 80}
        result = format_utilization(util_data)
        
        assert "Utilization: GPU 95%, Memory 80%" in result
        assert "🔥 Very High" in result
        
    def test_format_utilization_moderate(self):
        """Test moderate utilization formatting."""
        util_data = {'gpu': 60, 'memory': 70}
        result = format_utilization(util_data)
        
        assert "Utilization: GPU 60%, Memory 70%" in result
        assert "⚡ Moderate" in result
        
    def test_format_utilization_idle(self):
        """Test idle utilization formatting."""
        util_data = {'gpu': 5, 'memory': 10}
        result = format_utilization(util_data)
        
        assert "Utilization: GPU 5%, Memory 10%" in result
        assert "😴 Idle" in result
        
    def test_format_utilization_empty(self):
        """Test utilization formatting with empty data."""
        result = format_utilization({})
        assert result == "Utilization: N/A"


class TestClockSpeedsFormatting:
    """Test cases for clock speeds formatting."""
    
    def test_format_clock_speeds_both(self):
        """Test clock speeds formatting with both values."""
        clock_data = {'sclk': 1500, 'mclk': 2000}
        result = format_clock_speeds(clock_data)
        
        assert "Clock Speeds: GPU 1500MHz, Memory 2000MHz" in result
        
    def test_format_clock_speeds_gpu_only(self):
        """Test clock speeds formatting with GPU only."""
        clock_data = {'sclk': 1500, 'mclk': 0}
        result = format_clock_speeds(clock_data)
        
        assert "Clock Speeds: GPU 1500MHz" in result
        
    def test_format_clock_speeds_memory_only(self):
        """Test clock speeds formatting with memory only."""
        clock_data = {'sclk': 0, 'mclk': 2000}
        result = format_clock_speeds(clock_data)
        
        assert "Clock Speeds: Memory 2000MHz" in result
        
    def test_format_clock_speeds_empty(self):
        """Test clock speeds formatting with empty data."""
        result = format_clock_speeds({})
        assert result == "Clock Speeds: N/A"


class TestFanInfoFormatting:
    """Test cases for fan information formatting."""
    
    def test_format_fan_info_with_percentage(self):
        """Test fan info formatting with percentage."""
        fan_data = {'speed_percent': 60, 'speed_rpm': 2400}
        result = format_fan_info(fan_data)
        
        assert "Fan: 60%" in result
        assert "2400 RPM" in result
        assert "🌬️ Moderate" in result
        
    def test_format_fan_info_high_speed(self):
        """Test fan info formatting with high speed."""
        fan_data = {'speed_percent': 90, 'speed_rpm': 3600}
        result = format_fan_info(fan_data)
        
        assert "Fan: 90%" in result
        assert "🌪️ Maximum" in result
        
    def test_format_fan_info_low_speed(self):
        """Test fan info formatting with low speed."""
        fan_data = {'speed_percent': 30, 'speed_rpm': 1200}
        result = format_fan_info(fan_data)
        
        assert "Fan: 30%" in result
        assert "🍃 Low" in result
        
    def test_format_fan_info_empty(self):
        """Test fan info formatting with empty data."""
        result = format_fan_info({})
        assert result == "Fan: N/A"


class TestListFormatting:
    """Test cases for list formatting functions."""
    
    def test_format_bullet_list(self):
        """Test bullet list formatting."""
        items = ["Item 1", "Item 2", "Item 3"]
        result = format_bullet_list(items)
        
        assert "• Item 1" in result
        assert "• Item 2" in result
        assert "• Item 3" in result
        
    def test_format_bullet_list_custom_bullet(self):
        """Test bullet list formatting with custom bullet."""
        items = ["Item 1", "Item 2"]
        result = format_bullet_list(items, bullet="▪")
        
        assert "▪ Item 1" in result
        assert "▪ Item 2" in result
        
    def test_format_bullet_list_empty(self):
        """Test bullet list formatting with empty list."""
        result = format_bullet_list([])
        assert result == ""
        
    def test_format_numbered_list(self):
        """Test numbered list formatting."""
        items = ["First item", "Second item", "Third item"]
        result = format_numbered_list(items)
        
        assert "1. First item" in result
        assert "2. Second item" in result
        assert "3. Third item" in result
        
    def test_format_numbered_list_empty(self):
        """Test numbered list formatting with empty list."""
        result = format_numbered_list([])
        assert result == ""


class TestDeviceSummaryFormatting:
    """Test cases for device summary formatting."""
    
    def test_format_device_summary_complete(self):
        """Test device summary formatting with complete info."""
        device_info = {
            'name': 'AMD Radeon RX 6800 XT',
            'index': 0,
            'driver_version': '21.50.2'
        }
        result = format_device_summary(device_info)
        
        assert "Device 0: AMD Radeon RX 6800 XT" in result
        assert "Driver: 21.50.2" in result
        
    def test_format_device_summary_with_error(self):
        """Test device summary formatting with error."""
        device_info = {
            'name': 'Unknown GPU',
            'index': 1,
            'error': 'Device not accessible'
        }
        result = format_device_summary(device_info)
        
        assert "Device 1: Unknown GPU" in result
        assert "⚠️ Error: Device not accessible" in result
        
    def test_format_device_summary_empty(self):
        """Test device summary formatting with empty info."""
        result = format_device_summary({})
        assert result == "Device: Unknown"


class TestSectionFormatting:
    """Test cases for section formatting functions."""
    
    def test_format_warnings(self):
        """Test warnings section formatting."""
        warnings = ["High temperature detected", "Power consumption elevated"]
        result = format_warnings(warnings)
        
        assert "⚠️ Warnings" in result
        assert "⚠️ High temperature detected" in result
        assert "⚠️ Power consumption elevated" in result
        
    def test_format_warnings_empty(self):
        """Test warnings section formatting with empty list."""
        result = format_warnings([])
        assert result == ""
        
    def test_format_recommendations(self):
        """Test recommendations section formatting."""
        recommendations = ["Check cooling system", "Reduce workload"]
        result = format_recommendations(recommendations)
        
        assert "💡 Recommendations" in result
        assert "💡 Check cooling system" in result
        assert "💡 Reduce workload" in result
        
    def test_format_recommendations_empty(self):
        """Test recommendations section formatting with empty list."""
        result = format_recommendations([])
        assert result == ""
        
    def test_format_issues(self):
        """Test issues section formatting."""
        issues = ["Memory usage critical", "Temperature too high"]
        result = format_issues(issues)
        
        assert "🔍 Issues Detected" in result
        assert "🔍 Memory usage critical" in result
        assert "🔍 Temperature too high" in result
        
    def test_format_issues_empty(self):
        """Test issues section formatting with empty list."""
        result = format_issues([])
        assert result == ""


class TestTableFormatting:
    """Test cases for table formatting functions."""
    
    def test_format_summary_table(self):
        """Test summary table formatting."""
        data = {
            "GPU": "AMD Radeon RX 6800 XT",
            "Temperature": "65°C",
            "Power": "180W",
            "Memory": "6.0GB / 8.0GB"
        }
        result = format_summary_table(data)
        
        assert "GPU        : AMD Radeon RX 6800 XT" in result
        assert "Temperature: 65°C" in result
        assert "Power      : 180W" in result
        assert "Memory     : 6.0GB / 8.0GB" in result
        
    def test_format_summary_table_empty(self):
        """Test summary table formatting with empty data."""
        result = format_summary_table({})
        assert result == ""
        
    def test_format_key_value_table(self):
        """Test key-value table formatting."""
        data = {
            "temperature": 65.0,
            "power": {"current": 180, "cap": 240},
            "utilization": {"gpu": 75, "memory": 80}
        }
        result = format_key_value_table(data)
        
        assert "temperature: 65.0" in result
        assert "power:" in result
        assert "  current: 180" in result
        assert "  cap: 240" in result
        assert "utilization:" in result
        assert "  gpu: 75" in result
        assert "  memory: 80" in result


class TestEfficiencyScoreFormatting:
    """Test cases for efficiency score formatting."""
    
    def test_format_efficiency_score_excellent(self):
        """Test excellent efficiency score formatting."""
        result = format_efficiency_score(95.0)
        assert "🏆" in result
        assert "95.0/100" in result
        assert "Excellent" in result
        
    def test_format_efficiency_score_good(self):
        """Test good efficiency score formatting."""
        result = format_efficiency_score(80.0)
        assert "⚡" in result
        assert "80.0/100" in result
        assert "Good" in result
        
    def test_format_efficiency_score_moderate(self):
        """Test moderate efficiency score formatting."""
        result = format_efficiency_score(60.0)
        assert "⚖️" in result
        assert "60.0/100" in result
        assert "Moderate" in result
        
    def test_format_efficiency_score_poor(self):
        """Test poor efficiency score formatting."""
        result = format_efficiency_score(30.0)
        assert "⚠️" in result
        assert "30.0/100" in result
        assert "Poor" in result
        
    def test_format_efficiency_score_critical(self):
        """Test critical efficiency score formatting."""
        result = format_efficiency_score(10.0)
        assert "🔴" in result
        assert "10.0/100" in result
        assert "Critical" in result