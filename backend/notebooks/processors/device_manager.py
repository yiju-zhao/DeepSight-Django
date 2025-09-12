"""
Device Manager - Handle device detection and configuration for ML models.
"""
import os
import logging
from typing import Dict, Optional


class DeviceManager:
    """Handle device detection and configuration for ML models."""
    
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)
    
    def log_operation(self, operation: str, details: str = "", level: str = "info"):
        """Log operations with consistent formatting."""
        message = f"[device_manager] {operation}"
        if details:
            message += f": {details}"
        getattr(self.logger, level)(message)

    def detect_device(self) -> str:
        """
        Detect the best available device for acceleration.

        Returns:
            str: Device string ('cuda', 'mps', or 'cpu')
        """
        try:
            import torch
            if torch.cuda.is_available():
                return 'cuda'
            elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                return 'mps'
            else:
                return 'cpu'
        except ImportError:
            return 'cpu'

    def get_device_info_detailed(self) -> Dict:
        """
        Get detailed information about available devices.

        Returns:
            dict: Device information including type, count, and memory
        """
        device_info = {
            'device_type': 'cpu',
            'device_count': 0,
            'memory_info': None,
            'device_name': None
        }

        try:
            import torch
            if torch.cuda.is_available():
                device_info['device_type'] = 'cuda'
                device_info['device_count'] = torch.cuda.device_count()
                device_info['device_name'] = torch.cuda.get_device_name(0)
                if torch.cuda.device_count() > 0:
                    device_info['memory_info'] = {
                        'total': torch.cuda.get_device_properties(0).total_memory,
                        'allocated': torch.cuda.memory_allocated(0),
                        'cached': torch.cuda.memory_reserved(0)
                    }
            elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                device_info['device_type'] = 'mps'
                device_info['device_count'] = 1  # MPS typically has one device
                device_info['device_name'] = 'Apple Silicon GPU'
                # MPS doesn't have memory info API like CUDA
                device_info['memory_info'] = {'note': 'MPS memory info not available via PyTorch API'}
        except ImportError:
            pass

        return device_info

    def setup_device_environment(self, device_type: str, gpu_id: Optional[int] = None):
        """
        Set up environment variables and configurations for the specified device.

        Args:
            device_type: Type of device ('cuda', 'mps', or 'cpu')
            gpu_id: Specific GPU ID for CUDA (ignored for MPS)
        """
        if device_type == 'cuda':
            if gpu_id is not None:
                os.environ["CUDA_VISIBLE_DEVICES"] = str(gpu_id)
                self.log_operation("cuda_device_setup", f"Set CUDA_VISIBLE_DEVICES to {gpu_id}")
            # Set TORCH_DEVICE for models that use it
            os.environ["TORCH_DEVICE"] = "cuda"
        elif device_type == 'mps':
            # Set TORCH_DEVICE for models to use MPS
            os.environ["TORCH_DEVICE"] = "mps"
            self.log_operation("mps_device_setup", "Configured environment for MPS acceleration")
        else:
            # CPU mode
            os.environ["TORCH_DEVICE"] = "cpu"
            self.log_operation("cpu_device_setup", "Configured environment for CPU processing")

