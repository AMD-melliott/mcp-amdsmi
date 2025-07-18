"""Business logic for intelligent GPU analysis and recommendations.

This module implements health assessment algorithms, performance analysis,
and contextual recommendations for AMD GPU monitoring.
"""

import logging
from typing import Any, Dict, List

from .amd_smi_wrapper import safe_divide


class HealthAnalyzer:
    """Provides intelligent analysis of GPU metrics and health assessment."""

    def __init__(self) -> None:
        """Initialize the health analyzer."""
        self.logger = logging.getLogger(__name__)
        
        # Health thresholds for different metrics
        self.temp_thresholds = {
            'good': 70,      # < 70°C is good
            'warning': 80,   # 70-80°C is warning
            'critical': 90   # > 80°C is critical
        }
        
        self.power_thresholds = {
            'normal': 0.85,  # < 85% of power cap is normal
            'high': 0.95     # > 95% of power cap is high
        }
        
        self.memory_thresholds = {
            'good': 0.75,    # < 75% memory usage is good
            'warning': 0.85, # 75-85% is warning
            'critical': 0.95 # > 95% is critical
        }

    def calculate_health_score(self, metrics: Dict[str, Any]) -> float:
        """Calculate overall health score from metrics.

        Args:
            metrics: Dictionary of GPU metrics

        Returns:
            float: Health score from 0-100
        """
        scores = []
        
        # Temperature score
        if 'temperature' in metrics:
            temp_score = self._calculate_temperature_score(metrics['temperature'])
            scores.append(temp_score)
        
        # Power score
        if 'power' in metrics:
            power_score = self._calculate_power_score(metrics['power'])
            scores.append(power_score)
        
        # Memory score
        if 'memory' in metrics:
            memory_score = self._calculate_memory_score(metrics['memory'])
            scores.append(memory_score)
        
        # Utilization score (healthy utilization indicates good performance)
        if 'utilization' in metrics:
            util_score = self._calculate_utilization_score(metrics['utilization'])
            scores.append(util_score)
        
        # Fan score
        if 'fan' in metrics:
            fan_score = self._calculate_fan_score(metrics['fan'])
            scores.append(fan_score)
        
        # Return average score, or 0 if no metrics available
        return sum(scores) / len(scores) if scores else 0.0

    def _calculate_temperature_score(self, temp_data: Dict[str, Any]) -> float:
        """Calculate temperature-based health score."""
        current_temp = temp_data.get('current', 0)
        
        # If temperature is 0 or N/A, return neutral score
        if current_temp <= 0:
            return 80.0  # Neutral score for missing temperature data
        
        if current_temp < self.temp_thresholds['good']:
            return 100.0
        elif current_temp < self.temp_thresholds['warning']:
            # Linear interpolation between 100 and 70
            ratio = (current_temp - self.temp_thresholds['good']) / (self.temp_thresholds['warning'] - self.temp_thresholds['good'])
            return 100.0 - (30.0 * ratio)
        elif current_temp < self.temp_thresholds['critical']:
            # Linear interpolation between 70 and 30
            ratio = (current_temp - self.temp_thresholds['warning']) / (self.temp_thresholds['critical'] - self.temp_thresholds['warning'])
            return 70.0 - (40.0 * ratio)
        else:
            return 30.0  # Critical temperature

    def _calculate_power_score(self, power_data: Dict[str, Any]) -> float:
        """Calculate power consumption-based health score."""
        current_power = power_data.get('current', 0)
        power_cap = power_data.get('cap', 0)
        
        # If no power data available, return neutral score
        if current_power <= 0 or power_cap <= 0:
            return 80.0  # Neutral score for missing power data
        
        power_ratio = safe_divide(current_power, power_cap, default=0.0, context="power score calculation")
        
        if power_ratio < self.power_thresholds['normal']:
            return 100.0
        elif power_ratio < self.power_thresholds['high']:
            # Linear interpolation between 100 and 60
            ratio = (power_ratio - self.power_thresholds['normal']) / (self.power_thresholds['high'] - self.power_thresholds['normal'])
            return 100.0 - (40.0 * ratio)
        else:
            return 60.0  # High power consumption

    def _calculate_memory_score(self, memory_data: Dict[str, Any]) -> float:
        """Calculate memory usage-based health score."""
        used_memory = memory_data.get('used', 0)
        total_memory = memory_data.get('total', 0)
        
        # If no memory data available, return neutral score
        if total_memory <= 0:
            return 80.0  # Neutral score for missing memory data
        
        memory_ratio = safe_divide(used_memory, total_memory, default=0.0, context="memory score calculation")
        
        if memory_ratio < self.memory_thresholds['good']:
            return 100.0
        elif memory_ratio < self.memory_thresholds['warning']:
            # Linear interpolation between 100 and 75
            ratio = (memory_ratio - self.memory_thresholds['good']) / (self.memory_thresholds['warning'] - self.memory_thresholds['good'])
            return 100.0 - (25.0 * ratio)
        elif memory_ratio < self.memory_thresholds['critical']:
            # Linear interpolation between 75 and 40
            ratio = (memory_ratio - self.memory_thresholds['warning']) / (self.memory_thresholds['critical'] - self.memory_thresholds['warning'])
            return 75.0 - (35.0 * ratio)
        else:
            return 40.0  # Critical memory usage

    def _calculate_utilization_score(self, util_data: Dict[str, Any]) -> float:
        """Calculate utilization-based health score."""
        gpu_util = util_data.get('gpu', 0)
        
        # If no utilization data, return neutral score
        if gpu_util <= 0:
            return 80.0  # Neutral score for missing utilization data
        
        # High utilization is generally good for performance
        if gpu_util > 80:
            return 100.0
        elif gpu_util > 50:
            return 80.0 + (20.0 * (gpu_util - 50) / 30)
        else:
            return 50.0 + (30.0 * gpu_util / 50)

    def _calculate_fan_score(self, fan_data: Dict[str, Any]) -> float:
        """Calculate fan-based health score."""
        fan_speed = fan_data.get('speed_percent', 0)
        
        # If no fan data, return neutral score
        if fan_speed <= 0:
            return 80.0  # Neutral score for missing fan data
        
        # Moderate fan speed is healthy
        if fan_speed < 60:
            return 100.0
        elif fan_speed < 80:
            return 100.0 - (20.0 * (fan_speed - 60) / 20)
        else:
            return 80.0 - (30.0 * (fan_speed - 80) / 20)

    def analyze_memory_health(self, memory_data: Dict[str, Any]) -> str:
        """Analyze memory health status.

        Args:
            memory_data: Memory usage metrics

        Returns:
            str: Memory health status
        """
        if not memory_data:
            return "unknown"
        
        used_memory = memory_data.get('used', 0)
        total_memory = memory_data.get('total', 1)
        
        if total_memory <= 0:
            return "unknown"
        
        memory_ratio = safe_divide(used_memory, total_memory, default=0.0, context="memory health analysis")
        
        if memory_ratio < self.memory_thresholds['good']:
            return "healthy"
        elif memory_ratio < self.memory_thresholds['warning']:
            return "moderate"
        elif memory_ratio < self.memory_thresholds['critical']:
            return "high"
        else:
            return "critical"

    def check_thermal_warnings(self, temp_data: Dict[str, Any], power_data: Dict[str, Any]) -> List[str]:
        """Check for thermal and power warnings.

        Args:
            temp_data: Temperature metrics
            power_data: Power consumption metrics

        Returns:
            List[str]: List of warnings
        """
        warnings = []
        
        # Temperature warnings
        if temp_data:
            current_temp = temp_data.get('current', 0)
            if current_temp > self.temp_thresholds['critical']:
                warnings.append(f"⚠️ Critical temperature: {current_temp}°C")
            elif current_temp > self.temp_thresholds['warning']:
                warnings.append(f"⚠️ High temperature: {current_temp}°C")
        
        # Power warnings
        if power_data:
            current_power = power_data.get('current', 0)
            power_cap = power_data.get('cap', 1)
            if power_cap > 0:
                power_ratio = safe_divide(current_power, power_cap, default=0.0, context="thermal warnings power calculation")
                if power_ratio > self.power_thresholds['high']:
                    warnings.append(f"⚠️ High power consumption: {current_power}W ({power_ratio:.1%} of cap)")
        
        return warnings

    def comprehensive_health_check(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Perform comprehensive health assessment.

        Args:
            metrics: All available GPU metrics

        Returns:
            Dict[str, Any]: Comprehensive health assessment
        """
        health_score = self.calculate_health_score(metrics)
        issues = []
        recommendations = []
        
        # Determine overall status
        if health_score >= 90:
            status = "excellent"
        elif health_score >= 75:
            status = "good"
        elif health_score >= 50:
            status = "moderate"
        elif health_score >= 25:
            status = "poor"
        else:
            status = "critical"
        
        # Check for specific issues and recommendations
        if 'temperature' in metrics:
            temp_issues, temp_recs = self._analyze_temperature_issues(metrics['temperature'])
            issues.extend(temp_issues)
            recommendations.extend(temp_recs)
        
        if 'power' in metrics:
            power_issues, power_recs = self._analyze_power_issues(metrics['power'])
            issues.extend(power_issues)
            recommendations.extend(power_recs)
        
        if 'memory' in metrics:
            mem_issues, mem_recs = self._analyze_memory_issues(metrics['memory'])
            issues.extend(mem_issues)
            recommendations.extend(mem_recs)
        
        return {
            'status': status,
            'score': health_score,
            'issues': issues,
            'recommendations': recommendations
        }

    def _analyze_temperature_issues(self, temp_data: Dict[str, Any]) -> tuple[List[str], List[str]]:
        """Analyze temperature-related issues."""
        issues = []
        recommendations = []
        
        current_temp = temp_data.get('current', 0)
        
        if current_temp > self.temp_thresholds['critical']:
            issues.append(f"Critical temperature: {current_temp}°C")
            recommendations.append("Check cooling system and reduce workload immediately")
        elif current_temp > self.temp_thresholds['warning']:
            issues.append(f"High temperature: {current_temp}°C")
            recommendations.append("Monitor cooling system and consider workload optimization")
        
        return issues, recommendations

    def _analyze_power_issues(self, power_data: Dict[str, Any]) -> tuple[List[str], List[str]]:
        """Analyze power-related issues."""
        issues = []
        recommendations = []
        
        current_power = power_data.get('current', 0)
        power_cap = power_data.get('cap', 1)
        
        if power_cap > 0:
            power_ratio = safe_divide(current_power, power_cap, default=0.0, context="power consumption health calculation")
            if power_ratio > self.power_thresholds['high']:
                issues.append(f"High power consumption: {current_power}W ({power_ratio:.1%} of cap)")
                recommendations.append("Consider reducing workload or optimizing power settings")
        
        return issues, recommendations

    def _analyze_memory_issues(self, memory_data: Dict[str, Any]) -> tuple[List[str], List[str]]:
        """Analyze memory-related issues."""
        issues = []
        recommendations = []
        
        used_memory = memory_data.get('used', 0)
        total_memory = memory_data.get('total', 1)
        
        if total_memory > 0:
            memory_ratio = safe_divide(used_memory, total_memory, default=0.0, context="memory usage health calculation")
            if memory_ratio > self.memory_thresholds['critical']:
                issues.append(f"Critical memory usage: {used_memory}MB ({memory_ratio:.1%} of total)")
                recommendations.append("Free up memory or reduce batch size")
            elif memory_ratio > self.memory_thresholds['warning']:
                issues.append(f"High memory usage: {used_memory}MB ({memory_ratio:.1%} of total)")
                recommendations.append("Monitor memory usage and consider optimization")
        
        return issues, recommendations


class PerformanceInterpreter:
    """Interprets performance metrics and provides contextual insights."""

    def __init__(self) -> None:
        """Initialize the performance interpreter."""
        self.logger = logging.getLogger(__name__)

    def calculate_efficiency(self, metrics: Dict[str, Any]) -> float:
        """Calculate overall performance efficiency score.

        Args:
            metrics: Performance metrics

        Returns:
            float: Efficiency score from 0-100
        """
        scores = []
        
        # Utilization efficiency
        if 'utilization' in metrics:
            util_score = self._calculate_utilization_efficiency(metrics['utilization'])
            scores.append(util_score)
        
        # Memory efficiency
        if 'memory' in metrics:
            mem_score = self._calculate_memory_efficiency(metrics['memory'])
            scores.append(mem_score)
        
        # Power efficiency
        if 'power' in metrics and 'utilization' in metrics:
            power_score = self._calculate_power_efficiency(metrics['power'], metrics['utilization'])
            scores.append(power_score)
        
        # Clock efficiency
        if 'clock' in metrics:
            clock_score = self._calculate_clock_efficiency(metrics['clock'])
            scores.append(clock_score)
        
        return sum(scores) / len(scores) if scores else 0.0

    def _calculate_utilization_efficiency(self, util_data: Dict[str, Any]) -> float:
        """Calculate utilization efficiency score."""
        gpu_util = util_data.get('gpu', 0)
        memory_util = util_data.get('memory', 0)
        
        # High utilization is generally good for efficiency
        avg_util = (gpu_util + memory_util) / 2
        
        if avg_util > 80:
            return 100.0
        elif avg_util > 60:
            return 80.0 + (20.0 * (avg_util - 60) / 20)
        else:
            return 60.0 * (avg_util / 60)

    def _calculate_memory_efficiency(self, memory_data: Dict[str, Any]) -> float:
        """Calculate memory efficiency score."""
        used_memory = memory_data.get('used', 0)
        total_memory = memory_data.get('total', 1)
        
        if total_memory <= 0:
            return 50.0  # Neutral score if no data
        
        memory_ratio = safe_divide(used_memory, total_memory, default=0.0, context="memory efficiency calculation")
        
        # Moderate memory usage is most efficient
        if 0.4 <= memory_ratio <= 0.8:
            return 100.0
        elif memory_ratio < 0.4:
            return 50.0 + (50.0 * memory_ratio / 0.4)
        else:
            return 100.0 - (50.0 * (memory_ratio - 0.8) / 0.2)

    def _calculate_power_efficiency(self, power_data: Dict[str, Any], util_data: Dict[str, Any]) -> float:
        """Calculate power efficiency score."""
        current_power = power_data.get('current', 0)
        power_cap = power_data.get('cap', 1)
        gpu_util = util_data.get('gpu', 0)
        
        if power_cap <= 0 or gpu_util <= 0:
            return 50.0  # Neutral score if no data
        
        power_ratio = safe_divide(current_power, power_cap, default=0.0, context="power efficiency calculation")
        
        # Efficiency is utilization per unit power
        efficiency = safe_divide(gpu_util, (power_ratio * 100), default=0.0, context="power efficiency calculation")
        
        return min(100.0, efficiency * 100)

    def _calculate_clock_efficiency(self, clock_data: Dict[str, Any]) -> float:
        """Calculate clock efficiency score."""
        sclk = clock_data.get('sclk', 0)
        mclk = clock_data.get('mclk', 0)
        
        # This is a simplified efficiency calculation
        # In practice, this would compare against optimal clock speeds
        if sclk > 1000 and mclk > 1000:
            return 90.0
        elif sclk > 500 and mclk > 500:
            return 70.0
        else:
            return 50.0

    def analyze_utilization(self, utilization_data: Dict[str, float]) -> Dict[str, Any]:
        """Analyze GPU utilization patterns.

        Args:
            utilization_data: GPU utilization metrics

        Returns:
            Dict[str, Any]: Utilization analysis
        """
        gpu_util = utilization_data.get('gpu', 0)
        memory_util = utilization_data.get('memory', 0)
        
        analysis = {
            'gpu_utilization': gpu_util,
            'memory_utilization': memory_util,
            'balance_score': self._calculate_utilization_balance(gpu_util, memory_util),
            'recommendations': []
        }
        
        # Add recommendations based on utilization patterns
        if gpu_util < 50:
            analysis['recommendations'].append("GPU utilization is low - consider increasing workload")
        elif gpu_util > 95:
            analysis['recommendations'].append("GPU utilization is very high - monitor for performance bottlenecks")
        
        if memory_util < 30:
            analysis['recommendations'].append("Memory utilization is low - consider larger batch sizes")
        elif memory_util > 90:
            analysis['recommendations'].append("Memory utilization is very high - consider reducing batch size")
        
        return analysis

    def _calculate_utilization_balance(self, gpu_util: float, memory_util: float) -> float:
        """Calculate how balanced GPU and memory utilization are."""
        if gpu_util == 0 and memory_util == 0:
            return 0.0
        
        # Perfect balance is when both are equally utilized
        balance_diff = abs(gpu_util - memory_util)
        balance_score = max(0, 100 - balance_diff)
        
        return balance_score

    def analyze_memory_efficiency(self, memory_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze memory usage efficiency.

        Args:
            memory_data: Memory usage metrics

        Returns:
            Dict[str, Any]: Memory efficiency analysis
        """
        used_memory = memory_data.get('used', 0)
        total_memory = memory_data.get('total', 1)
        free_memory = memory_data.get('free', 0)
        
        if total_memory <= 0:
            return {'efficiency_score': 0, 'recommendations': []}
        
        memory_ratio = safe_divide(used_memory, total_memory, default=0.0, context="memory efficiency analysis")
        
        analysis = {
            'used_memory_mb': used_memory,
            'total_memory_mb': total_memory,
            'free_memory_mb': free_memory,
            'usage_ratio': memory_ratio,
            'efficiency_score': self._calculate_memory_efficiency(memory_data),
            'recommendations': []
        }
        
        # Add recommendations based on memory usage
        if memory_ratio < 0.3:
            analysis['recommendations'].append("Memory usage is low - consider increasing batch size or data size")
        elif memory_ratio > 0.9:
            analysis['recommendations'].append("Memory usage is very high - consider reducing batch size or optimizing memory usage")
        
        return analysis

    def analyze_thermal_performance(self, thermal_data: Dict[str, float]) -> Dict[str, Any]:
        """Analyze thermal performance and efficiency.

        Args:
            thermal_data: Temperature and thermal metrics

        Returns:
            Dict[str, Any]: Thermal analysis
        """
        current_temp = thermal_data.get('current', 0)
        critical_temp = thermal_data.get('critical', 90)
        
        analysis = {
            'current_temperature': current_temp,
            'critical_temperature': critical_temp,
            'thermal_margin': critical_temp - current_temp,
            'thermal_efficiency': self._calculate_thermal_efficiency(current_temp, critical_temp),
            'recommendations': []
        }
        
        # Add thermal recommendations
        if current_temp > critical_temp * 0.9:
            analysis['recommendations'].append("Temperature is approaching critical levels - check cooling system")
        elif current_temp > critical_temp * 0.8:
            analysis['recommendations'].append("Temperature is high - monitor cooling and consider workload optimization")
        
        return analysis

    def _calculate_thermal_efficiency(self, current_temp: float, critical_temp: float) -> float:
        """Calculate thermal efficiency score."""
        if critical_temp <= 0:
            return 50.0  # Neutral score if no data
        
        temp_ratio = safe_divide(current_temp, critical_temp, default=0.0, context="thermal efficiency calculation")
        
        # Lower temperatures are more efficient
        if temp_ratio < 0.7:
            return 100.0
        elif temp_ratio < 0.9:
            return 100.0 - (50.0 * (temp_ratio - 0.7) / 0.2)
        else:
            return 50.0 - (50.0 * (temp_ratio - 0.9) / 0.1)
