"""AMD SMI wrapper for abstracting GPU interactions.

This module provides a high-level interface to the AMD SMI library,
handling initialization, error management, and data formatting.
"""

import logging
import time
from contextlib import contextmanager
from functools import wraps
from typing import Any, Callable, Dict, Generator, List, Optional
import threading

# AMD SMI import with proper error handling
def _try_import_amdsmi():
    """Attempt to import AMD SMI with clear error reporting."""
    try:
        import amdsmi  # type: ignore
        return amdsmi, True
    except (ImportError, KeyError, OSError, AttributeError) as e:
        error_str = str(e)
        
        raise ImportError(
            f"Failed to import AMD SMI: {e}. "
        ) from e

# Import AMD SMI - will raise ImportError if not compatible
amdsmi, AMDSMI_AVAILABLE = _try_import_amdsmi()

# Function availability tracking for version compatibility
AMDSMI_FUNCTION_AVAILABILITY = {}

def _check_function_availability(func_name: str) -> bool:
    """Check if a specific AMD SMI function is available.
    
    Args:
        func_name: Name of the AMD SMI function to check
        
    Returns:
        bool: True if function is available, False otherwise
    """
    if not AMDSMI_AVAILABLE or amdsmi is None:
        return False
        
    if func_name in AMDSMI_FUNCTION_AVAILABILITY:
        return AMDSMI_FUNCTION_AVAILABILITY[func_name]
    
    try:
        # Check if the function exists in the module
        func = getattr(amdsmi, func_name, None)
        available = func is not None and callable(func)
        AMDSMI_FUNCTION_AVAILABILITY[func_name] = available
        return available
    except (AttributeError, ImportError):
        AMDSMI_FUNCTION_AVAILABILITY[func_name] = False
        return False

def _safe_call_amdsmi_function(func_name: str, *args, **kwargs):
    """Safely call an AMD SMI function with fallback handling.
    
    Args:
        func_name: Name of the AMD SMI function to call
        *args: Positional arguments for the function
        **kwargs: Keyword arguments for the function
        
    Returns:
        Function result or None if function is not available
        
    Raises:
        Exception: If function is available but call fails
    """
    if not _check_function_availability(func_name):
        raise AttributeError(f"AMD SMI function '{func_name}' not available in this ROCm version")
    
    func = getattr(amdsmi, func_name)
    return func(*args, **kwargs)


class AMDSMIError(Exception):
    """Base exception for AMD SMI related errors."""
    pass


class AMDSMIInitializationError(AMDSMIError):
    """Raised when AMD SMI initialization fails."""
    pass


class AMDSMIDeviceError(AMDSMIError):
    """Raised when device operations fail."""
    pass


class AMDSMIMetricsError(AMDSMIError):
    """Raised when metrics collection fails."""
    pass


def safe_divide(numerator: float, denominator: float, default: Any = 0.0, log_warning: bool = True, context: str = "") -> Any:
    """Safely perform division with zero-check and logging.
    
    Args:
        numerator: Value to divide
        denominator: Value to divide by
        default: Default value to return if division by zero (default: 0.0)
        log_warning: Whether to log a warning on division by zero (default: True)
        context: Context string for logging (default: "")
        
    Returns:
        Result of division or default value if denominator is zero
    """
    if denominator == 0:
        if log_warning:
            logger = logging.getLogger(__name__)
            context_msg = f" in {context}" if context else ""
            logger.warning(f"Division by zero prevented{context_msg}: {numerator} / {denominator}, returning {default}")
        return default
    
    return numerator / denominator


def safe_get_value(data: Any, default: Any = None, expect_numeric: bool = False) -> Any:
    """Safely extract value from AMD SMI data, handling N/A values.
    
    Args:
        data: Raw value from AMD SMI library
        default: Default value to return if data is N/A or invalid
        expect_numeric: If True, convert non-numeric values (like dicts) to default
        
    Returns:
        Processed value or default
    """
    if data is None:
        return default
    
    # Handle string "N/A" values
    if isinstance(data, str) and data.strip().upper() == "N/A":
        return default
    
    # Handle numeric values that might be returned as strings
    if isinstance(data, str):
        try:
            # Try to convert to float first
            converted = float(data)
            # Return as int if it's a whole number and expecting numeric
            if expect_numeric and converted.is_integer():
                return int(converted)
            return converted
        except (ValueError, TypeError):
            return default if expect_numeric else data
    
    # Handle dictionary values - if expecting numeric, return default for dicts
    if isinstance(data, dict):
        # For utilization metrics, empty dicts or when expecting numeric should return default
        if expect_numeric or len(data) == 0:
            return default
        # Otherwise, process dictionary recursively (don't propagate expect_numeric)
        cleaned_dict = {}
        for key, value in data.items():
            cleaned_dict[key] = safe_get_value(value, default, expect_numeric=False)
        return cleaned_dict
    
    # Handle list/tuple values
    if isinstance(data, (list, tuple)):
        return [safe_get_value(item, default, expect_numeric=False) for item in data]
    
    # Handle numeric values - ensure they are reasonable
    if isinstance(data, (int, float)):
        # Check for unreasonable values that might indicate errors
        if expect_numeric and (data < 0 or data > 1e12):  # Very large numbers might be errors
            return default
        return data
    
    return data


def retry_on_failure(max_retries: int = 3, delay: float = 0.1, backoff: float = 2.0) -> Callable:
    """Decorator to retry operations on transient failures.
    
    Args:
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff: Multiplier for delay on each retry
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            retry_delay = delay
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except (ConnectionError, OSError, RuntimeError) as e:
                    last_exception = e
                    if attempt < max_retries:
                        time.sleep(retry_delay)
                        retry_delay *= backoff
                        continue
                    raise last_exception
            
        return wrapper
    return decorator


class AMDSMIManager:
    """Manages AMD SMI library lifecycle and provides abstracted GPU access."""

    def __init__(self) -> None:
        """Initialize the AMD SMI manager.
        
        Raises:
            ImportError: If AMD SMI is not available or incompatible
        """
        if not AMDSMI_AVAILABLE:
            raise ImportError(
                "AMD SMI is not available. This MCP server requires ROCm 6.4.1+ with AMD SMI Python library."
            )
        
        self.initialized = False
        self.device_handles: List[Any] = []
        self.logger = logging.getLogger(__name__)
        self._lock = threading.RLock()  # For thread safety
        self._initialization_attempts = 0
        self._max_init_attempts = 3

    @retry_on_failure(max_retries=2, delay=0.5)
    def initialize(self) -> bool:
        """Initialize AMD SMI library and discover devices.

        Returns:
            bool: True if initialization successful, False otherwise
        """
        with self._lock:
            if self.initialized:
                return True
                
            self._initialization_attempts += 1
            
            if self._initialization_attempts > self._max_init_attempts:
                self.logger.error(f"Exceeded maximum initialization attempts ({self._max_init_attempts})")
                raise AMDSMIInitializationError("Maximum initialization attempts exceeded")
            
            try:
                if self.initialized:
                    return True
                    
                self._initialization_attempts += 1
                
                if self._initialization_attempts > self._max_init_attempts:
                    self.logger.error(f"Exceeded maximum initialization attempts ({self._max_init_attempts})")
                    raise AMDSMIInitializationError("Maximum initialization attempts exceeded")
                
                if not AMDSMI_AVAILABLE:
                    raise AMDSMIInitializationError("AMD SMI library not available")
                    
                # Initialize AMD SMI library
                _safe_call_amdsmi_function('amdsmi_init')
                
                # Get all available GPU devices
                self.device_handles = _safe_call_amdsmi_function('amdsmi_get_processor_handles')
                
                if not self.device_handles:
                    self.logger.warning("No AMD GPU devices found")
                    raise AMDSMIInitializationError("No AMD GPU devices found")
                    
                self.initialized = True
                self.logger.info(
                    f"AMD SMI initialized successfully with {len(self.device_handles)} devices"
                )
                return True
                
            except AMDSMIInitializationError:
                # Don't catch our own exceptions for retry
                raise
            except Exception as e:
                self.logger.error(f"Failed to initialize AMD SMI (attempt {self._initialization_attempts}): {e}")
                raise AMDSMIInitializationError(f"Failed to initialize AMD SMI: {e}") from e

    def shutdown(self) -> None:
        """Clean shutdown of AMD SMI library."""
        with self._lock:
            if self.initialized:
                try:
                    if AMDSMI_AVAILABLE:
                        _safe_call_amdsmi_function('amdsmi_shut_down')
                        
                    self.initialized = False
                    self.device_handles = []
                    self._initialization_attempts = 0  # Reset for next initialization
                    self.logger.info("AMD SMI shutdown completed")
                except Exception as e:
                    self.logger.error(f"Error during AMD SMI shutdown: {e}")
                    # Always clean up state even if shutdown fails
                    self.initialized = False
                    self.device_handles = []
                    self._initialization_attempts = 0

    def get_device_handles(self) -> List[Any]:
        """Return list of available GPU device handles.

        Returns:
            List[Any]: List of device handles
        """
        return self.device_handles.copy()

    @retry_on_failure(max_retries=2, delay=0.1)
    def get_device_info(self, device_handle: Any) -> Dict[str, Any]:
        """Get comprehensive device information.

        Args:
            device_handle: AMD SMI device handle

        Returns:
            Dict[str, Any]: Device information dictionary
        """
        if not self.initialized:
            raise AMDSMIDeviceError("AMD SMI not initialized")
            
        if not self.is_device_valid(device_handle):
            raise AMDSMIDeviceError(f"Invalid device handle: {device_handle}")
            
        try:
            # Real AMD SMI device info collection
            info = {}
            
            # Get device ID
            try:
                device_id = _safe_call_amdsmi_function('amdsmi_get_gpu_device_uuid', device_handle)
                info['device_id'] = safe_get_value(device_id, 'Unknown')
            except Exception:
                info['device_id'] = 'Unknown'
            
            # Get device name
            try:
                device_name = _safe_call_amdsmi_function('amdsmi_get_gpu_asic_info', device_handle)
                if isinstance(device_name, dict):
                    info['name'] = device_name.get('market_name', 'Unknown GPU')
                    info['asic_family'] = device_name.get('family', 'Unknown')
                else:
                    info['name'] = safe_get_value(device_name, 'Unknown GPU')
                    info['asic_family'] = 'Unknown'
            except Exception:
                info['name'] = 'Unknown GPU'
                info['asic_family'] = 'Unknown'
            
            # Get VBIOS version
            try:
                vbios_info = _safe_call_amdsmi_function('amdsmi_get_gpu_vbios_info', device_handle)
                if isinstance(vbios_info, dict):
                    info['vbios_version'] = vbios_info.get('version', 'Unknown')
                else:
                    info['vbios_version'] = safe_get_value(vbios_info, 'Unknown')
            except Exception:
                info['vbios_version'] = 'Unknown'
            
            # Get driver version
            try:
                driver_info = _safe_call_amdsmi_function('amdsmi_get_gpu_driver_info', device_handle)
                if isinstance(driver_info, dict):
                    info['driver_version'] = driver_info.get('driver_version', 'Unknown')
                else:
                    info['driver_version'] = safe_get_value(driver_info, 'Unknown')
            except Exception:
                info['driver_version'] = 'Unknown'
            
            # Get PCI information
            try:
                pci_info = _safe_call_amdsmi_function('amdsmi_get_gpu_device_bdf', device_handle)
                if isinstance(pci_info, dict):
                    info['pci_info'] = {
                        'domain': pci_info.get('domain', 0),
                        'bus': pci_info.get('bus', 0),
                        'device': pci_info.get('device', 0),
                        'function': pci_info.get('function', 0)
                    }
                else:
                    info['pci_info'] = {'domain': 0, 'bus': 0, 'device': 0, 'function': 0}
            except Exception:
                info['pci_info'] = {'domain': 0, 'bus': 0, 'device': 0, 'function': 0}
            
            return info
            
        except Exception as e:
            self.logger.error(f"Failed to get device info for {device_handle}: {e}")
            raise AMDSMIDeviceError(f"Failed to get device info: {e}") from e

    @retry_on_failure(max_retries=2, delay=0.1)
    def get_metrics(
        self, device_handle: Any, metric_types: List[str]
    ) -> Dict[str, Any]:
        """Collect specified metrics from device.

        Args:
            device_handle: AMD SMI device handle
            metric_types: List of metric types to collect

        Returns:
            Dict[str, Any]: Collected metrics
        """
        if not self.initialized:
            raise AMDSMIMetricsError("AMD SMI not initialized")
            
        if not self.is_device_valid(device_handle):
            raise AMDSMIMetricsError(f"Invalid device handle: {device_handle}")
            
        metrics = {}
        
        try:
            # Real AMD SMI metrics collection
            for metric_type in metric_types:
                try:
                    if metric_type == 'temperature':
                        # Try different temperature types available on AMD GPUs
                        # Priority order: HOTSPOT -> VRAM -> EDGE -> HBM_0
                        temp_types_to_try = [
                            ('HOTSPOT', amdsmi.AmdSmiTemperatureType.HOTSPOT),
                            ('VRAM', amdsmi.AmdSmiTemperatureType.VRAM),
                            ('EDGE', amdsmi.AmdSmiTemperatureType.EDGE),
                            ('HBM_0', amdsmi.AmdSmiTemperatureType.HBM_0)
                        ]
                        
                        temp_current = 0
                        temp_critical = 90
                        temp_emergency = 95
                        temp_type_used = None
                        
                        # Try each temperature type until we find one that works
                        for temp_name, temp_type in temp_types_to_try:
                            try:
                                # Try to get current temperature
                                # Note: Despite documentation saying millidegrees, the API returns degrees Celsius directly
                                temp_current_raw = _safe_call_amdsmi_function('amdsmi_get_temp_metric', device_handle, temp_type, amdsmi.AmdSmiTemperatureMetric.CURRENT)
                                temp_current_processed = safe_get_value(temp_current_raw, 0)
                                if temp_current_processed and temp_current_processed > 0:
                                    # Temperature is already in degrees Celsius, no conversion needed
                                    temp_current = temp_current_processed
                                    temp_type_used = temp_name
                                    
                                    # Try to get critical temperature for this type
                                    try:
                                        temp_critical_raw = safe_get_value(_safe_call_amdsmi_function('amdsmi_get_temp_metric', device_handle, temp_type, amdsmi.AmdSmiTemperatureMetric.CRITICAL), 90)
                                        temp_critical = temp_critical_raw if temp_critical_raw else 90
                                    except:
                                        temp_critical = 90
                                    
                                    # Try to get emergency temperature for this type
                                    try:
                                        temp_emergency_raw = safe_get_value(_safe_call_amdsmi_function('amdsmi_get_temp_metric', device_handle, temp_type, amdsmi.AmdSmiTemperatureMetric.EMERGENCY), 95)
                                        temp_emergency = temp_emergency_raw if temp_emergency_raw else 95
                                    except:
                                        temp_emergency = 95
                                    
                                    # Successfully got temperature, break out of loop
                                    break
                                    
                            except Exception as e:
                                # This temperature type is not supported, try next one
                                continue
                        
                        if temp_type_used:
                            self.logger.debug(f"Temperature monitoring using {temp_type_used} type: {temp_current}°C")
                        else:
                            self.logger.warning("Temperature monitoring not supported on this device - tried all available types")
                        
                        metrics['temperature'] = {
                            'current': temp_current,
                            'critical': temp_critical,
                            'emergency': temp_emergency,
                            'type': temp_type_used or 'N/A'
                        }
                    
                    elif metric_type == 'power':
                        try:
                            power_info = _safe_call_amdsmi_function('amdsmi_get_power_info', device_handle)
                            power_info = safe_get_value(power_info, {})
                        except Exception:
                            power_info = {}
                        
                        metrics['power'] = {
                            'current': safe_get_value(power_info.get('current_socket_power'), 0),
                            'average': safe_get_value(power_info.get('average_socket_power'), 0),
                            'cap': safe_get_value(power_info.get('power_cap'), 0)
                        }
                    
                    elif metric_type == 'utilization':
                        try:
                            # Use amdsmi_get_gpu_activity for all utilization metrics
                            if _check_function_availability('amdsmi_get_gpu_activity'):
                                util_info = _safe_call_amdsmi_function('amdsmi_get_gpu_activity', device_handle)
                                util_info = safe_get_value(util_info, {})
                            else:
                                # If amdsmi_get_gpu_activity is not available, provide zero values
                                util_info = {}
                        except Exception:
                            util_info = {}
                        
                        metrics['utilization'] = {
                            'gpu': safe_get_value(util_info.get('gfx_activity'), 0, expect_numeric=True),
                            'memory': safe_get_value(util_info.get('umc_activity'), 0, expect_numeric=True),
                            'multimedia': safe_get_value(util_info.get('mm_activity'), 0, expect_numeric=True)
                        }
                    
                    elif metric_type == 'memory':
                        try:
                            mem_info = _safe_call_amdsmi_function('amdsmi_get_gpu_vram_usage', device_handle)
                            mem_info = safe_get_value(mem_info, {})
                        except Exception:
                            mem_info = {}
                        
                        # Handle different return types from AMD SMI
                        if isinstance(mem_info, dict):
                            memory_used = safe_get_value(mem_info.get('vram_used'), 0)
                            memory_total = safe_get_value(mem_info.get('vram_total'), 0)
                        elif isinstance(mem_info, (int, float)):
                            # Some versions return just the used memory as a number
                            memory_used = mem_info
                            memory_total = 0  # Total not available in this format
                        else:
                            memory_used = 0
                            memory_total = 0
                        
                        # Values are already in MB from AMD SMI, no conversion needed
                        memory_used_mb = int(memory_used) if memory_used else 0
                        memory_total_mb = int(memory_total) if memory_total else 0
                        memory_free_mb = max(0, memory_total_mb - memory_used_mb)
                        
                        metrics['memory'] = {
                            'used': memory_used_mb,
                            'total': memory_total_mb,
                            'free': memory_free_mb
                        }
                    
                    elif metric_type == 'clock':
                        try:
                            sclk_raw = safe_get_value(_safe_call_amdsmi_function('amdsmi_get_clk_freq', device_handle, amdsmi.AmdSmiClkType.SYS), {})
                            mclk_raw = safe_get_value(_safe_call_amdsmi_function('amdsmi_get_clk_freq', device_handle, amdsmi.AmdSmiClkType.MEM), {})
                            # Try to get fabric clock or use system clock as fallback
                            try:
                                fclk_raw = safe_get_value(_safe_call_amdsmi_function('amdsmi_get_clk_freq', device_handle, amdsmi.AmdSmiClkType.DF), {})
                            except:
                                fclk_raw = sclk_raw  # Use system clock as fallback
                        except Exception:
                            sclk_raw = mclk_raw = fclk_raw = {}
                        
                        # Handle amdsmi_get_clk_freq return format: dict with 'num_supported', 'current', 'frequency'
                        def extract_clock_value(clock_data):
                            if isinstance(clock_data, dict):
                                # Get the current frequency index
                                current_idx = safe_get_value(clock_data.get('current'), 0)
                                frequency_list = safe_get_value(clock_data.get('frequency'), [])
                                if isinstance(frequency_list, list) and len(frequency_list) > current_idx:
                                    # Return current frequency in Hz, convert to MHz
                                    return frequency_list[current_idx] / 1000000
                                return 0
                            elif isinstance(clock_data, (int, float)):
                                # If returned as number directly (fallback), assume it's in Hz
                                return clock_data / 1000000
                            else:
                                return 0
                        
                        sclk_mhz = int(extract_clock_value(sclk_raw))
                        mclk_mhz = int(extract_clock_value(mclk_raw))
                        fclk_mhz = int(extract_clock_value(fclk_raw))
                        
                        metrics['clock'] = {
                            'sclk': sclk_mhz,  # System clock in MHz
                            'mclk': mclk_mhz,  # Memory clock in MHz
                            'fclk': fclk_mhz   # Fabric clock in MHz
                        }
                    
                    elif metric_type == 'fan':
                        try:
                            # Get fan speed in RPMs (integer)
                            fan_rpm_raw = _safe_call_amdsmi_function('amdsmi_get_gpu_fan_rpms', device_handle, 0)
                            self.logger.debug(f"Raw fan RPM value: {fan_rpm_raw}, type: {type(fan_rpm_raw)}")
                            fan_rpm = safe_get_value(fan_rpm_raw, 0, expect_numeric=True)
                            self.logger.debug(f"Processed fan RPM value: {fan_rpm}")
                            
                            # Get fan speed as percentage relative to MAX (0-100)
                            fan_speed_raw = _safe_call_amdsmi_function('amdsmi_get_gpu_fan_speed', device_handle, 0)
                            self.logger.debug(f"Raw fan speed value: {fan_speed_raw}, type: {type(fan_speed_raw)}")
                            fan_speed = safe_get_value(fan_speed_raw, 0, expect_numeric=True)
                            self.logger.debug(f"Processed fan speed value: {fan_speed}")
                        except Exception:
                            fan_rpm = fan_speed = 0
                        
                        # Ensure values are integers and within reasonable ranges
                        fan_rpm = int(fan_rpm) if isinstance(fan_rpm, (int, float)) and fan_rpm > 0 else 0
                        fan_speed = int(fan_speed) if isinstance(fan_speed, (int, float)) and 0 <= fan_speed <= 100 else 0
                        
                        metrics['fan'] = {
                            'speed_rpm': fan_rpm,      # Fan speed in RPM
                            'speed_percent': fan_speed  # Fan speed as percentage (0-100)
                        }
                        
                except Exception as e:
                    self.logger.warning(f"Failed to collect {metric_type} metric: {e}")
                    # Continue with other metrics even if one fails
                    
            return metrics
            
        except Exception as e:
            self.logger.error(f"Failed to collect metrics for {device_handle}: {e}")
            raise AMDSMIMetricsError(f"Failed to collect metrics: {e}") from e

    @contextmanager
    def gpu_context(self) -> Generator["AMDSMIManager", None, None]:
        """Context manager for automatic initialization and cleanup."""
        try:
            if not self.initialize():
                raise RuntimeError("Failed to initialize AMD SMI")
            yield self
        finally:
            self.shutdown()

    def get_device_count(self) -> int:
        """Get the number of available GPU devices.
        
        Returns:
            int: Number of GPU devices
        """
        return len(self.device_handles)

    def is_device_valid(self, device_handle: Any) -> bool:
        """Check if a device handle is valid.
        
        Args:
            device_handle: Device handle to validate
            
        Returns:
            bool: True if device handle is valid
        """
        return device_handle in self.device_handles

    def get_device_by_index(self, index: int) -> Optional[Any]:
        """Get device handle by index.
        
        Args:
            index: Device index (0-based)
            
        Returns:
            Device handle or None if index is invalid
        """
        if 0 <= index < len(self.device_handles):
            return self.device_handles[index]
        return None

    def get_all_device_metrics(self, metric_types: List[str]) -> Dict[str, Dict[str, Any]]:
        """Get metrics for all available devices.
        
        Args:
            metric_types: List of metric types to collect
            
        Returns:
            Dict mapping device indices to their metrics
        """
        all_metrics = {}
        
        for i, device_handle in enumerate(self.device_handles):
            try:
                metrics = self.get_metrics(device_handle, metric_types)
                all_metrics[str(i)] = metrics
            except Exception as e:
                self.logger.error(f"Failed to get metrics for device {i}: {e}")
                all_metrics[str(i)] = {}
                
        return all_metrics
