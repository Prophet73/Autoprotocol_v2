"""
GPU Memory Management utilities.

Provides controlled loading/unloading of models to prevent VRAM fragmentation
and optimize memory usage.
"""
import gc
import torch
import logging
import threading
from typing import Dict, Optional, Any, Callable
from contextlib import contextmanager
from functools import wraps

logger = logging.getLogger(__name__)


class GPUMemoryManager:
    """
    Singleton manager for GPU memory and model lifecycle.

    Features:
    - Aggressive VRAM cleanup between stages
    - Model caching for repeated use
    - Memory usage tracking
    - Automatic cleanup on low memory
    """

    _instance = None
    _lock = threading.Lock()

    # Memory thresholds (fraction of total VRAM)
    CLEANUP_THRESHOLD = 0.85  # Cleanup when >85% used
    CRITICAL_THRESHOLD = 0.95  # Force cleanup when >95% used

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model_cache: Dict[str, Any] = {}
        self._initialized = True

        if self.device == "cuda":
            self.total_memory = torch.cuda.get_device_properties(0).total_memory
            logger.info(
                f"GPU Manager initialized: {torch.cuda.get_device_name(0)}, "
                f"{self.total_memory / 1e9:.1f}GB VRAM"
            )
        else:
            self.total_memory = 0
            logger.info("GPU Manager initialized: CPU mode")

    def get_memory_usage(self) -> Dict[str, float]:
        """
        Get current GPU memory usage.

        Returns:
            Dict with memory stats in GB and percentage
        """
        if self.device != "cuda":
            return {"allocated_gb": 0, "reserved_gb": 0, "free_gb": 0, "percent": 0}

        allocated = torch.cuda.memory_allocated(0)
        reserved = torch.cuda.memory_reserved(0)
        free = self.total_memory - reserved

        return {
            "allocated_gb": allocated / 1e9,
            "reserved_gb": reserved / 1e9,
            "free_gb": free / 1e9,
            "percent": reserved / self.total_memory if self.total_memory > 0 else 0,
        }

    def log_memory(self, label: str = ""):
        """Log current memory usage."""
        if self.device != "cuda":
            return

        stats = self.get_memory_usage()
        logger.debug(
            f"[{label}] GPU Memory: "
            f"{stats['allocated_gb']:.2f}GB allocated, "
            f"{stats['reserved_gb']:.2f}GB reserved, "
            f"{stats['percent']*100:.1f}% used"
        )

    def cleanup(self, aggressive: bool = False):
        """
        Clean up GPU memory.

        Args:
            aggressive: If True, forces garbage collection and synchronization
        """
        if self.device != "cuda":
            return

        # Clear model cache if aggressive
        if aggressive and self.model_cache:
            logger.info(f"Clearing {len(self.model_cache)} cached models")
            self.model_cache.clear()

        # Standard cleanup
        gc.collect()
        torch.cuda.empty_cache()

        if aggressive:
            # Force synchronization to ensure all operations complete
            torch.cuda.synchronize()
            gc.collect()
            torch.cuda.empty_cache()

        self.log_memory("after_cleanup")

    def check_and_cleanup(self) -> bool:
        """
        Check memory usage and cleanup if necessary.

        Returns:
            True if cleanup was performed
        """
        if self.device != "cuda":
            return False

        stats = self.get_memory_usage()

        if stats["percent"] > self.CRITICAL_THRESHOLD:
            logger.warning(
                f"GPU memory critical ({stats['percent']*100:.1f}%), "
                f"forcing aggressive cleanup"
            )
            self.cleanup(aggressive=True)
            return True

        if stats["percent"] > self.CLEANUP_THRESHOLD:
            logger.info(
                f"GPU memory high ({stats['percent']*100:.1f}%), cleaning up"
            )
            self.cleanup(aggressive=False)
            return True

        return False

    def cache_model(self, key: str, model: Any):
        """
        Cache a model for reuse.

        Args:
            key: Unique key for the model
            model: Model to cache
        """
        # Check memory before caching
        self.check_and_cleanup()

        self.model_cache[key] = model
        logger.debug(f"Cached model: {key}")

    def get_cached_model(self, key: str) -> Optional[Any]:
        """
        Get a cached model.

        Args:
            key: Model key

        Returns:
            Cached model or None
        """
        return self.model_cache.get(key)

    def remove_cached_model(self, key: str):
        """
        Remove a model from cache and free memory.

        Args:
            key: Model key
        """
        if key in self.model_cache:
            del self.model_cache[key]
            self.cleanup()
            logger.debug(f"Removed cached model: {key}")

    @contextmanager
    def model_context(self, cleanup_after: bool = True):
        """
        Context manager for model operations.

        Ensures cleanup after operations complete.

        Args:
            cleanup_after: Whether to cleanup after context exits

        Usage:
            with gpu_manager.model_context():
                model = load_model()
                result = model.predict()
        """
        self.check_and_cleanup()

        try:
            yield
        finally:
            if cleanup_after:
                self.cleanup()


def gpu_cleanup(func: Callable) -> Callable:
    """
    Decorator to cleanup GPU memory after function execution.

    Usage:
        @gpu_cleanup
        def process_audio(audio):
            ...
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        finally:
            get_gpu_manager().cleanup()

    return wrapper


def get_gpu_manager() -> GPUMemoryManager:
    """Get the global GPU memory manager instance."""
    return GPUMemoryManager()


def clean_cuda_cache():
    """
    Aggressive CUDA memory cleanup.

    Standalone function for backward compatibility.
    """
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.synchronize()


# Convenience functions
def log_gpu_memory(label: str = ""):
    """Log current GPU memory usage."""
    get_gpu_manager().log_memory(label)


def ensure_gpu_memory(required_gb: float = 2.0) -> bool:
    """
    Ensure enough GPU memory is available.

    Args:
        required_gb: Required free memory in GB

    Returns:
        True if enough memory is available (after cleanup if needed)
    """
    manager = get_gpu_manager()

    if manager.device != "cuda":
        return True

    stats = manager.get_memory_usage()

    if stats["free_gb"] >= required_gb:
        return True

    # Try cleanup
    manager.cleanup(aggressive=True)
    stats = manager.get_memory_usage()

    if stats["free_gb"] >= required_gb:
        return True

    logger.warning(
        f"Insufficient GPU memory: need {required_gb:.1f}GB, "
        f"have {stats['free_gb']:.1f}GB free"
    )
    return False
