"""MCP Server implementation for AMD GPU monitoring.

This module implements the main MCP server that exposes AMD SMI functionality
as conversational tools for infrastructure management using FastMCP framework.
"""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

from fastmcp import FastMCP

from .amd_smi_wrapper import AMDSMIManager, safe_divide
from .business_logic import HealthAnalyzer, PerformanceInterpreter
from .text_formatting import (
    format_header,
    format_timestamp,
    format_health_score,
    format_temperature,
    format_power,
    format_memory,
    format_utilization,
    format_clock_speeds,
    format_fan_info,
    format_device_summary,
    format_warnings,
    format_recommendations,
    format_issues,
    format_summary_table,
    format_efficiency_score,
    format_bullet_list,
)


# Initialize FastMCP server
mcp = FastMCP("AMD GPU Monitor")

# Global AMD SMI manager instance
smi_manager = AMDSMIManager()
health_analyzer = HealthAnalyzer()
performance_interpreter = PerformanceInterpreter()


@mcp.tool()
def get_gpu_discovery() -> str:
    """Discover and enumerate all available AMD GPU devices.
    
    Returns comprehensive information about all GPU devices including
    device names, IDs, driver versions, and hardware specifications.
    """
    try:
        with smi_manager.gpu_context():
            devices = []
            device_handles = smi_manager.get_device_handles()
            
            for i, device_handle in enumerate(device_handles):
                try:
                    device_info = smi_manager.get_device_info(device_handle)
                    device_info['index'] = i
                    devices.append(device_info)
                except Exception as e:
                    logging.error(f"Failed to get info for device {i}: {e}")
                    devices.append({
                        'index': i,
                        'name': 'Unknown GPU',
                        'error': str(e)
                    })
            
            # Format human-readable response
            response = format_header("AMD GPU Discovery Report")
            response += f"Scan completed at: {format_timestamp(time.time())}\n"
            response += f"Total devices found: {len(devices)}\n\n"
            
            if not devices:
                response += "No AMD GPU devices were detected on this system.\n"
                response += "Please ensure AMD SMI library is installed and GPUs are properly configured.\n"
            else:
                response += format_header("Detected Devices", level=2)
                for device in devices:
                    response += f"{format_device_summary(device)}\n"
                    if 'driver_version' in device:
                        response += f"  Driver Version: {device['driver_version']}\n"
                    if 'vbios_version' in device:
                        response += f"  VBIOS Version: {device['vbios_version']}\n"
                    response += "\n"
            
            return response
            
    except Exception as e:
        logging.error(f"GPU discovery failed: {e}")
        response = format_header("AMD GPU Discovery Report")
        response += f"Scan completed at: {format_timestamp(time.time())}\n"
        response += f"❌ Error: Failed to discover GPU devices\n"
        response += f"Details: {str(e)}\n\n"
        response += "Please ensure:\n"
        response += "• AMD SMI library is installed\n"
        response += "• AMD GPU drivers are properly configured\n"
        response += "• You have sufficient permissions to access GPU resources\n"
        return response


@mcp.tool()
def get_gpu_status(device_id: str = "0") -> str:
    """Get comprehensive current status of a specific GPU device.
    
    Args:
        device_id: GPU device identifier (default: "0")
        
    Returns current status including temperature, power, utilization,
    and overall health assessment.
    """
    try:
        with smi_manager.gpu_context():
            device_handle = smi_manager.get_device_by_index(int(device_id))
            if not device_handle:
                raise ValueError(f"Invalid device ID: {device_id}")
            
            # Collect comprehensive status metrics
            metrics = smi_manager.get_metrics(device_handle, [
                'temperature', 'power', 'utilization', 'memory', 'clock'
            ])
            
            # Calculate health score using business logic
            health_score = health_analyzer.calculate_health_score(metrics)
            
            # Format human-readable response
            response = format_header(f"GPU Device {device_id} Status Report")
            response += f"Report generated at: {format_timestamp(time.time())}\n\n"
            
            # Health summary
            response += format_header("Health Summary", level=2)
            response += f"Overall Health: {format_health_score(health_score)}\n\n"
            
            # Current metrics
            response += format_header("Current Metrics", level=2)
            response += f"{format_temperature(metrics.get('temperature', {}))}\n"
            response += f"{format_power(metrics.get('power', {}))}\n"
            response += f"{format_memory(metrics.get('memory', {}))}\n"
            response += f"{format_utilization(metrics.get('utilization', {}))}\n"
            response += f"{format_clock_speeds(metrics.get('clock', {}))}\n"
            response += f"{format_fan_info(metrics.get('fan', {}))}\n\n"
            
            # Status interpretation
            response += format_header("Status Interpretation", level=2)
            if health_score >= 90:
                response += "✅ Your GPU is operating excellently with optimal performance and temperatures.\n"
            elif health_score >= 75:
                response += "✅ Your GPU is in good condition with stable performance.\n"
            elif health_score >= 50:
                response += "⚠️ Your GPU is showing moderate stress - monitor for potential issues.\n"
            elif health_score >= 25:
                response += "⚠️ Your GPU is experiencing performance degradation - attention needed.\n"
            else:
                response += "🔴 Your GPU is in critical condition - immediate action required.\n"
            
            return response
            
    except Exception as e:
        logging.error(f"Failed to get GPU status for device {device_id}: {e}")
        response = format_header(f"GPU Device {device_id} Status Report")
        response += f"Report generated at: {format_timestamp(time.time())}\n\n"
        response += f"❌ Error: Failed to retrieve GPU status\n"
        response += f"Details: {str(e)}\n\n"
        response += "Troubleshooting:\n"
        response += f"• Verify device ID '{device_id}' is valid\n"
        response += "• Check if GPU is properly connected and recognized\n"
        response += "• Ensure AMD SMI library has access to the device\n"
        return response


@mcp.tool()
def get_gpu_performance(device_id: str = "0") -> str:
    """Analyze GPU performance metrics and efficiency.
    
    Args:
        device_id: GPU device identifier (default: "0")
        
    Returns performance metrics, utilization rates, and efficiency analysis.
    """
    try:
        with smi_manager.gpu_context():
            device_handle = smi_manager.get_device_by_index(int(device_id))
            if not device_handle:
                raise ValueError(f"Invalid device ID: {device_id}")
            
            # Collect performance-related metrics
            metrics = smi_manager.get_metrics(device_handle, [
                'utilization', 'clock', 'memory', 'power'
            ])
            
            # Calculate efficiency score
            efficiency_score = performance_interpreter.calculate_efficiency(metrics)
            
            # Analyze utilization patterns
            utilization_analysis = performance_interpreter.analyze_utilization(
                metrics.get('utilization', {})
            )
            
            # Format human-readable response
            response = format_header(f"GPU Device {device_id} Performance Analysis")
            response += f"Analysis completed at: {format_timestamp(time.time())}\n\n"
            
            # Performance summary
            response += format_header("Performance Summary", level=2)
            response += f"Efficiency Score: {format_efficiency_score(efficiency_score)}\n"
            response += f"Balance Score: {utilization_analysis.get('balance_score', 0):.1f}/100\n\n"
            
            # Current performance metrics
            response += format_header("Current Performance Metrics", level=2)
            response += f"{format_utilization(metrics.get('utilization', {}))}\n"
            response += f"{format_clock_speeds(metrics.get('clock', {}))}\n"
            response += f"{format_memory(metrics.get('memory', {}))}\n"
            response += f"{format_power(metrics.get('power', {}))}\n\n"
            
            # Performance insights
            response += format_header("Performance Insights", level=2)
            gpu_util = metrics.get('utilization', {}).get('gpu', 0)
            memory_util = metrics.get('utilization', {}).get('memory', 0)
            
            if gpu_util > 95:
                response += "🔥 GPU is under heavy load - excellent utilization for compute tasks\n"
            elif gpu_util > 80:
                response += "🚀 GPU is actively processing with high utilization\n"
            elif gpu_util > 50:
                response += "⚡ GPU is moderately active\n"
            elif gpu_util > 20:
                response += "💤 GPU is lightly loaded\n"
            else:
                response += "😴 GPU is mostly idle\n"
            
            if memory_util > 90:
                response += "⚠️ Memory is heavily utilized - consider batch size optimization\n"
            elif memory_util > 75:
                response += "📊 Memory usage is high but manageable\n"
            elif memory_util < 30:
                response += "💾 Memory is underutilized - could handle larger workloads\n"
            
            # Recommendations
            recommendations = utilization_analysis.get('recommendations', [])
            if recommendations:
                response += "\n" + format_recommendations(recommendations)
            
            return response
            
    except Exception as e:
        logging.error(f"Failed to get GPU performance for device {device_id}: {e}")
        response = format_header(f"GPU Device {device_id} Performance Analysis")
        response += f"Analysis completed at: {format_timestamp(time.time())}\n\n"
        response += f"❌ Error: Failed to analyze GPU performance\n"
        response += f"Details: {str(e)}\n\n"
        response += "Troubleshooting:\n"
        response += f"• Verify device ID '{device_id}' is valid\n"
        response += "• Check if performance metrics are accessible\n"
        response += "• Ensure GPU is not in power-saving mode\n"
        return response


@mcp.tool()
def analyze_gpu_memory(device_id: str = "0") -> str:
    """Analyze GPU memory usage and health.
    
    Args:
        device_id: GPU device identifier (default: "0")
        
    Returns detailed memory usage analysis and health assessment.
    """
    try:
        with smi_manager.gpu_context():
            device_handle = smi_manager.get_device_by_index(int(device_id))
            if not device_handle:
                raise ValueError(f"Invalid device ID: {device_id}")
            
            # Collect memory-specific metrics
            metrics = smi_manager.get_metrics(device_handle, ['memory'])
            memory_data = metrics.get('memory', {})
            
            # Analyze memory health
            memory_health = health_analyzer.analyze_memory_health(memory_data)
            
            # Get detailed memory analysis
            memory_analysis = performance_interpreter.analyze_memory_efficiency(memory_data)
            
            # Format human-readable response
            response = format_header(f"GPU Device {device_id} Memory Analysis")
            response += f"Analysis completed at: {format_timestamp(time.time())}\n\n"
            
            # Memory status
            response += format_header("Memory Status", level=2)
            response += f"{format_memory(memory_data)}\n"
            response += f"Health Assessment: {memory_health}\n\n"
            
            # Detailed memory breakdown
            if memory_data:
                response += format_header("Memory Breakdown", level=2)
                used_gb = memory_data.get('used', 0) / 1024
                total_memory = memory_data.get('total', 0)
                total_gb = total_memory / 1024 if total_memory > 0 else 0
                free_gb = memory_data.get('free', 0) / 1024
                
                response += f"Used Memory:  {used_gb:.2f} GB\n"
                response += f"Free Memory:  {free_gb:.2f} GB\n"
                response += f"Total Memory: {total_gb:.2f} GB\n"
                
                # Safe division to prevent division by zero
                usage_percent = safe_divide(
                    memory_data.get('used', 0),
                    total_memory,
                    default="N/A (total memory unavailable)",
                    context=f"GPU device {device_id} memory usage calculation"
                )
                
                if isinstance(usage_percent, float):
                    response += f"Usage Percentage: {usage_percent * 100:.1f}%\n\n"
                else:
                    response += f"Usage Percentage: {usage_percent}\n\n"
            
            # Memory health analysis
            response += format_header("Memory Health Analysis", level=2)
            if memory_health == "healthy":
                response += "✅ Memory usage is optimal with plenty of available capacity.\n"
            elif memory_health == "moderate":
                response += "⚠️ Memory usage is elevated but manageable.\n"
            elif memory_health == "high":
                response += "⚠️ Memory usage is high - consider optimizing allocation.\n"
            elif memory_health == "critical":
                response += "🔴 Memory usage is critical - immediate optimization needed.\n"
            else:
                response += "❓ Memory health status could not be determined.\n"
            
            # Recommendations
            recommendations = memory_analysis.get('recommendations', [])
            if recommendations:
                response += "\n" + format_recommendations(recommendations)
            
            return response
            
    except Exception as e:
        logging.error(f"Failed to analyze GPU memory for device {device_id}: {e}")
        response = format_header(f"GPU Device {device_id} Memory Analysis")
        response += f"Analysis completed at: {format_timestamp(time.time())}\n\n"
        response += f"❌ Error: Failed to analyze GPU memory\n"
        response += f"Details: {str(e)}\n\n"
        response += "Troubleshooting:\n"
        response += f"• Verify device ID '{device_id}' is valid\n"
        response += "• Check if memory metrics are accessible\n"
        response += "• Ensure GPU memory is not corrupted\n"
        return response


@mcp.tool()
def monitor_power_thermal(device_id: str = "0") -> str:
    """Monitor GPU power consumption and thermal status.
    
    Args:
        device_id: GPU device identifier (default: "0")
        
    Returns power consumption data, thermal information, and warnings.
    """
    try:
        with smi_manager.gpu_context():
            device_handle = smi_manager.get_device_by_index(int(device_id))
            if not device_handle:
                raise ValueError(f"Invalid device ID: {device_id}")
            
            # Collect power and thermal metrics
            metrics = smi_manager.get_metrics(device_handle, [
                'power', 'temperature', 'fan'
            ])
            
            # Check for warnings
            warnings = health_analyzer.check_thermal_warnings(
                metrics.get('temperature', {}),
                metrics.get('power', {})
            )
            
            # Analyze thermal performance
            thermal_analysis = performance_interpreter.analyze_thermal_performance(
                metrics.get('temperature', {})
            )
            
            # Format human-readable response
            response = format_header(f"GPU Device {device_id} Power & Thermal Monitor")
            response += f"Monitoring data collected at: {format_timestamp(time.time())}\n\n"
            
            # Current readings
            response += format_header("Current Readings", level=2)
            response += f"{format_temperature(metrics.get('temperature', {}))}\n"
            response += f"{format_power(metrics.get('power', {}))}\n"
            response += f"{format_fan_info(metrics.get('fan', {}))}\n\n"
            
            # Thermal analysis
            response += format_header("Thermal Analysis", level=2)
            temp_data = metrics.get('temperature', {})
            current_temp = temp_data.get('current', 0)
            
            if current_temp > 0:
                thermal_margin = thermal_analysis.get('thermal_margin', 0)
                thermal_efficiency = thermal_analysis.get('thermal_efficiency', 0)
                
                response += f"Thermal Margin: {thermal_margin:.1f}°C\n"
                response += f"Thermal Efficiency: {thermal_efficiency:.1f}%\n\n"
                
                if current_temp < 60:
                    response += "❄️ GPU is running cool - excellent thermal performance\n"
                elif current_temp < 75:
                    response += "🌡️ GPU temperature is normal for active workloads\n"
                elif current_temp < 85:
                    response += "🔥 GPU is warm but within acceptable limits\n"
                else:
                    response += "⚠️ GPU is running hot - monitor cooling system\n"
            
            # Power analysis
            response += format_header("Power Analysis", level=2)
            power_data = metrics.get('power', {})
            current_power = power_data.get('current', 0)
            power_cap = power_data.get('cap', 0)
            
            if current_power > 0 and power_cap > 0:
                power_efficiency = (current_power / power_cap) * 100
                response += f"Power Efficiency: {power_efficiency:.1f}% of capacity\n"
                
                if power_efficiency < 50:
                    response += "🔋 Power consumption is low - GPU is idle or lightly loaded\n"
                elif power_efficiency < 75:
                    response += "⚡ Power consumption is moderate for current workload\n"
                elif power_efficiency < 90:
                    response += "🔥 Power consumption is high - GPU is under heavy load\n"
                else:
                    response += "⚠️ Power consumption is very high - monitor thermal conditions\n"
            
            # Warnings
            if warnings:
                response += "\n" + format_warnings(warnings)
            
            # Recommendations
            recommendations = thermal_analysis.get('recommendations', [])
            if recommendations:
                response += "\n" + format_recommendations(recommendations)
            
            return response
            
    except Exception as e:
        logging.error(f"Failed to monitor power/thermal for device {device_id}: {e}")
        response = format_header(f"GPU Device {device_id} Power & Thermal Monitor")
        response += f"Monitoring data collected at: {format_timestamp(time.time())}\n\n"
        response += f"❌ Error: Failed to monitor power and thermal status\n"
        response += f"Details: {str(e)}\n\n"
        response += "Troubleshooting:\n"
        response += f"• Verify device ID '{device_id}' is valid\n"
        response += "• Check if thermal sensors are accessible\n"
        response += "• Ensure power monitoring is enabled\n"
        return response


@mcp.tool()
def check_gpu_health(device_id: str = "0") -> str:
    """Perform comprehensive GPU health assessment with recommendations.
    
    Args:
        device_id: GPU device identifier (default: "0")
        
    Returns detailed health assessment, detected issues, and recommendations.
    """
    try:
        with smi_manager.gpu_context():
            device_handle = smi_manager.get_device_by_index(int(device_id))
            if not device_handle:
                raise ValueError(f"Invalid device ID: {device_id}")
            
            # Collect all relevant metrics for health assessment
            metrics = smi_manager.get_metrics(device_handle, [
                'temperature', 'power', 'utilization', 'memory', 'clock', 'fan'
            ])
            
            # Perform comprehensive health analysis
            health_result = health_analyzer.comprehensive_health_check(metrics)
            
            # Format human-readable response
            response = format_header(f"GPU Device {device_id} Health Assessment")
            response += f"Health check completed at: {format_timestamp(time.time())}\n\n"
            
            # Overall health status
            response += format_header("Overall Health Status", level=2)
            response += f"Health Score: {format_health_score(health_result['score'])}\n"
            response += f"Status: {health_result['status'].title()}\n\n"
            
            # Current vital signs
            response += format_header("Current Vital Signs", level=2)
            response += f"{format_temperature(metrics.get('temperature', {}))}\n"
            response += f"{format_power(metrics.get('power', {}))}\n"
            response += f"{format_memory(metrics.get('memory', {}))}\n"
            response += f"{format_utilization(metrics.get('utilization', {}))}\n"
            response += f"{format_fan_info(metrics.get('fan', {}))}\n\n"
            
            # Health assessment details
            response += format_header("Health Assessment Details", level=2)
            status = health_result['status']
            
            if status == "excellent":
                response += "🌟 Your GPU is in excellent condition!\n"
                response += "• All systems are operating optimally\n"
                response += "• Temperature and power consumption are ideal\n"
                response += "• No issues detected\n"
            elif status == "good":
                response += "✅ Your GPU is in good health.\n"
                response += "• Systems are stable and performing well\n"
                response += "• Minor variations are within normal ranges\n"
                response += "• Continue monitoring for optimal performance\n"
            elif status == "moderate":
                response += "⚠️ Your GPU shows signs of moderate stress.\n"
                response += "• Some metrics are elevated but manageable\n"
                response += "• Increased monitoring recommended\n"
                response += "• Consider workload optimization\n"
            elif status == "poor":
                response += "⚠️ Your GPU health is concerning.\n"
                response += "• Multiple metrics indicate stress\n"
                response += "• Immediate attention recommended\n"
                response += "• Performance may be impacted\n"
            else:  # critical
                response += "🔴 Your GPU is in critical condition!\n"
                response += "• Immediate action required\n"
                response += "• Risk of hardware damage or failure\n"
                response += "• Reduce workload immediately\n"
            
            # Issues detected
            issues = health_result.get('issues', [])
            if issues:
                response += "\n" + format_issues(issues)
            
            # Recommendations
            recommendations = health_result.get('recommendations', [])
            if recommendations:
                response += "\n" + format_recommendations(recommendations)
            else:
                response += "\n" + format_header("💡 Recommendations", level=2)
                response += "• Continue regular monitoring\n"
                response += "• Maintain current operating conditions\n"
                response += "• No immediate action required\n"
            
            return response
            
    except Exception as e:
        logging.error(f"Failed to check GPU health for device {device_id}: {e}")
        response = format_header(f"GPU Device {device_id} Health Assessment")
        response += f"Health check completed at: {format_timestamp(time.time())}\n\n"
        response += f"❌ Error: Failed to perform health assessment\n"
        response += f"Details: {str(e)}\n\n"
        response += "Troubleshooting:\n"
        response += f"• Verify device ID '{device_id}' is valid\n"
        response += "• Check if all sensors are accessible\n"
        response += "• Ensure GPU drivers are functioning properly\n"
        response += "\n" + format_header("💡 Recommendations", level=2)
        response += "• Verify GPU connectivity and drivers\n"
        response += "• Check system logs for hardware errors\n"
        response += "• Consider restarting the monitoring service\n"
        return response


def main():
    """Main entry point for the MCP server."""
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Run the FastMCP server
    mcp.run()


if __name__ == "__main__":
    main()