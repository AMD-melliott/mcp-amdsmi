"""Tests for business logic components."""

import pytest
from mcp_amdsmi.business_logic import HealthAnalyzer, PerformanceInterpreter


class TestHealthAnalyzer:
    """Test cases for HealthAnalyzer class."""
    
    def test_initialization(self, gpu_health_analyzer):
        """Test HealthAnalyzer initialization."""
        assert gpu_health_analyzer.logger is not None
        
    def test_calculate_health_score(self, gpu_health_analyzer, sample_gpu_metrics):
        """Test health score calculation."""
        # Convert sample metrics to expected format
        formatted_metrics = {
            'temperature': {'current': sample_gpu_metrics['temperature']},
            'power': {'current': sample_gpu_metrics['power'], 'cap': sample_gpu_metrics['power_cap']},
            'memory': {'used': sample_gpu_metrics['vram_used'], 'total': sample_gpu_metrics['vram_total']},
            'utilization': {'gpu': sample_gpu_metrics['utilization_gfx']}
        }
        
        result = gpu_health_analyzer.calculate_health_score(formatted_metrics)
        
        assert isinstance(result, float)
        assert 0.0 <= result <= 100.0
        
    def test_health_score_with_zero_values(self, gpu_health_analyzer):
        """Test health score calculation with N/A data (zero values)."""
        na_metrics = {
            'temperature': {'current': 0, 'critical': 90, 'emergency': 95},
            'power': {'current': 0, 'average': 0, 'cap': 0},
            'memory': {'used': 0, 'total': 0, 'free': 0},
            'utilization': {'gpu': 0, 'memory': 0},
            'fan': {'speed_percent': 0, 'speed_rpm': 0}
        }
        
        result = gpu_health_analyzer.calculate_health_score(na_metrics)
        
        # Should handle N/A values gracefully
        assert isinstance(result, float)
        assert 0.0 <= result <= 100.0
        
    def test_health_check_with_realistic_enterprise_data(self, gpu_health_analyzer):
        """Test health check with realistic enterprise GPU data."""
        realistic_metrics = {
            'temperature': {'current': 75, 'critical': 90, 'emergency': 95},
            'power': {'current': 250, 'average': 240, 'cap': 300},
            'memory': {'used': 32768, 'total': 65536, 'free': 32768},
            'utilization': {'gpu': 85, 'memory': 70},
            'fan': {'speed_percent': 65, 'speed_rpm': 2800}
        }
        
        result = gpu_health_analyzer.comprehensive_health_check(realistic_metrics)
        
        assert isinstance(result, dict)
        assert "score" in result
        assert "status" in result
        assert "issues" in result
        assert "recommendations" in result
        assert isinstance(result["score"], float)
        assert result["status"] in ["excellent", "good", "moderate", "poor", "critical"]
        assert isinstance(result["issues"], list)
        assert isinstance(result["recommendations"], list)
        
    def test_health_check_with_high_temperature_scenario(self, gpu_health_analyzer):
        """Test health check with high temperature scenario."""
        hot_metrics = {
            'temperature': {'current': 85, 'critical': 90, 'emergency': 95},
            'power': {'current': 290, 'average': 285, 'cap': 300},
            'memory': {'used': 60000, 'total': 65536, 'free': 5536},
            'utilization': {'gpu': 95, 'memory': 90},
            'fan': {'speed_percent': 85, 'speed_rpm': 3500}
        }
        
        result = gpu_health_analyzer.comprehensive_health_check(hot_metrics)
        
        assert isinstance(result, dict)
        assert "score" in result
        assert "status" in result
        assert "issues" in result
        assert "recommendations" in result
        
        # Should detect thermal issues
        assert result["score"] < 80.0  # Should be lower score for hot GPU
        assert len(result["issues"]) > 0  # Should have identified issues
        
    def test_comprehensive_health_check(self, gpu_health_analyzer, sample_gpu_metrics):
        """Test comprehensive health assessment."""
        # Convert sample metrics to expected format
        formatted_metrics = {
            'temperature': {'current': sample_gpu_metrics['temperature']},
            'power': {'current': sample_gpu_metrics['power'], 'cap': sample_gpu_metrics['power_cap']},
            'memory': {'used': sample_gpu_metrics['vram_used'], 'total': sample_gpu_metrics['vram_total']}
        }
        
        result = gpu_health_analyzer.comprehensive_health_check(formatted_metrics)
        
        assert isinstance(result, dict)
        assert "score" in result
        assert "status" in result
        assert "issues" in result
        assert "recommendations" in result
        assert isinstance(result["score"], float)
        assert result["status"] in ["excellent", "good", "moderate", "poor", "critical"]
        assert isinstance(result["issues"], list)
        assert isinstance(result["recommendations"], list)
        
    def test_analyze_memory_health(self, gpu_health_analyzer, sample_gpu_metrics):
        """Test memory health analysis."""
        memory_data = {
            'used': sample_gpu_metrics['vram_used'],
            'total': sample_gpu_metrics['vram_total']
        }
        
        result = gpu_health_analyzer.analyze_memory_health(memory_data)
        
        assert isinstance(result, str)
        assert result in ["unknown", "healthy", "moderate", "high", "critical"]


class TestPerformanceInterpreter:
    """Test cases for PerformanceInterpreter class."""
    
    def test_initialization(self, performance_interpreter):
        """Test PerformanceInterpreter initialization."""
        assert performance_interpreter.logger is not None
        
    def test_analyze_utilization(self, performance_interpreter):
        """Test utilization analysis."""
        utilization_data = {
            "gpu": 85.5,
            "memory": 70.2
        }
        
        result = performance_interpreter.analyze_utilization(utilization_data)
        assert isinstance(result, dict)
        assert "gpu_utilization" in result
        assert "memory_utilization" in result
        assert "balance_score" in result
        assert "recommendations" in result
        assert isinstance(result["recommendations"], list)
        
    def test_efficiency_calculation_scenarios(self, performance_interpreter):
        """Test efficiency calculation with different utilization scenarios."""
        # Test low utilization scenario
        low_util_metrics = {
            'utilization': {'gpu': 20, 'memory': 15},
            'memory': {'used': 2048, 'total': 65536, 'free': 63488},
            'power': {'current': 100, 'cap': 300},
            'clock': {'sclk': 800, 'mclk': 900, 'fclk': 850}
        }
        
        low_efficiency = performance_interpreter.calculate_efficiency(low_util_metrics)
        assert isinstance(low_efficiency, float)
        assert 0.0 <= low_efficiency <= 100.0
        
        # Test high utilization scenario
        high_util_metrics = {
            'utilization': {'gpu': 90, 'memory': 85},
            'memory': {'used': 50000, 'total': 65536, 'free': 15536},
            'power': {'current': 280, 'cap': 300},
            'clock': {'sclk': 1700, 'mclk': 1600, 'fclk': 1800}
        }
        
        high_efficiency = performance_interpreter.calculate_efficiency(high_util_metrics)
        assert isinstance(high_efficiency, float)
        assert 0.0 <= high_efficiency <= 100.0
        
        # High utilization should generally be more efficient
        assert high_efficiency > low_efficiency
        
    def test_efficiency_calculation_with_na_data(self, performance_interpreter):
        """Test efficiency calculation with N/A data (zero values)."""
        na_metrics = {
            'utilization': {'gpu': 0, 'memory': 0},
            'memory': {'used': 0, 'total': 0, 'free': 0},
            'power': {'current': 0, 'cap': 0},
            'clock': {'sclk': 0, 'mclk': 0, 'fclk': 0}
        }
        
        efficiency = performance_interpreter.calculate_efficiency(na_metrics)
        
        # Should handle N/A values gracefully
        assert isinstance(efficiency, float)
        assert 0.0 <= efficiency <= 100.0
        
    def test_utilization_analysis_scenarios(self, performance_interpreter):
        """Test utilization analysis with different scenarios."""
        # Test low utilization
        low_util = {'gpu': 20, 'memory': 15}
        low_analysis = performance_interpreter.analyze_utilization(low_util)
        assert isinstance(low_analysis, dict)
        assert "gpu_utilization" in low_analysis
        assert "memory_utilization" in low_analysis
        assert "balance_score" in low_analysis
        assert "recommendations" in low_analysis
        
        # Test high utilization
        high_util = {'gpu': 90, 'memory': 85}
        high_analysis = performance_interpreter.analyze_utilization(high_util)
        assert isinstance(high_analysis, dict)
        assert "gpu_utilization" in high_analysis
        assert "memory_utilization" in high_analysis
        assert "balance_score" in high_analysis
        assert "recommendations" in high_analysis
        
        # Test N/A data
        na_util = {'gpu': 0, 'memory': 0}
        na_analysis = performance_interpreter.analyze_utilization(na_util)
        assert isinstance(na_analysis, dict)
        assert "gpu_utilization" in na_analysis
        assert "memory_utilization" in na_analysis
        assert "balance_score" in na_analysis
        assert "recommendations" in na_analysis
        
    def test_analyze_memory_efficiency(self, performance_interpreter):
        """Test memory efficiency analysis."""
        memory_data = {
            "total": 128 * 1024 * 1024 * 1024,
            "used": 64 * 1024 * 1024 * 1024,
            "free": 64 * 1024 * 1024 * 1024
        }
        
        result = performance_interpreter.analyze_memory_efficiency(memory_data)
        assert isinstance(result, dict)
        assert "used_memory_mb" in result
        assert "total_memory_mb" in result
        assert "usage_ratio" in result
        assert "efficiency_score" in result
        assert "recommendations" in result
        assert isinstance(result["recommendations"], list)
        
    def test_analyze_thermal_performance(self, performance_interpreter):
        """Test thermal performance analysis."""
        thermal_data = {
            "current": 65.0,
            "critical": 90.0
        }
        
        result = performance_interpreter.analyze_thermal_performance(thermal_data)
        assert isinstance(result, dict)
        assert "current_temperature" in result
        assert "critical_temperature" in result
        assert "thermal_margin" in result
        assert "thermal_efficiency" in result
        assert "recommendations" in result
        assert isinstance(result["recommendations"], list)


class TestBusinessLogicIntegration:
    """Integration tests for business logic components."""
    
    def test_health_analyzer_with_healthy_metrics(self, gpu_health_analyzer, sample_gpu_metrics):
        """Test health analyzer with normal GPU metrics."""
        formatted_metrics = {
            'temperature': {'current': sample_gpu_metrics['temperature']},
            'power': {'current': sample_gpu_metrics['power'], 'cap': sample_gpu_metrics['power_cap']},
            'memory': {'used': sample_gpu_metrics['vram_used'], 'total': sample_gpu_metrics['vram_total']}
        }
        
        result = gpu_health_analyzer.comprehensive_health_check(formatted_metrics)
        
        # Should not raise any exceptions
        assert isinstance(result, dict)
        assert "score" in result
        assert "status" in result
        
    def test_health_analyzer_with_unhealthy_metrics(self, gpu_health_analyzer, unhealthy_gpu_metrics):
        """Test health analyzer with problematic GPU metrics."""
        formatted_metrics = {
            'temperature': {'current': unhealthy_gpu_metrics['temperature']},
            'power': {'current': unhealthy_gpu_metrics['power'], 'cap': unhealthy_gpu_metrics['power_cap']},
            'memory': {'used': unhealthy_gpu_metrics['vram_used'], 'total': unhealthy_gpu_metrics['vram_total']}
        }
        
        result = gpu_health_analyzer.comprehensive_health_check(formatted_metrics)
        
        # Should not raise any exceptions
        assert isinstance(result, dict)
        assert "score" in result
        assert "status" in result
        
        # Should detect issues with unhealthy metrics
        assert result["score"] < 75.0  # Should be lower score for unhealthy metrics
        
    def test_calculate_efficiency(self, performance_interpreter, sample_gpu_metrics):
        """Test efficiency calculation."""
        # Convert sample metrics to expected format
        formatted_metrics = {
            'utilization': {'gpu': sample_gpu_metrics['utilization_gfx'], 'memory': sample_gpu_metrics['utilization_memory']},
            'memory': {'used': sample_gpu_metrics['vram_used'], 'total': sample_gpu_metrics['vram_total']},
            'power': {'current': sample_gpu_metrics['power'], 'cap': sample_gpu_metrics['power_cap']}
        }
        
        result = performance_interpreter.calculate_efficiency(formatted_metrics)
        
        assert isinstance(result, float)
        assert 0.0 <= result <= 100.0