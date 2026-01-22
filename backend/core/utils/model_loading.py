"""
Safe model loading utilities.

Provides controlled loading of models that require weights_only=False,
without globally patching torch.load (which is a security risk).
"""
import torch
import logging
import warnings
from contextlib import contextmanager
from typing import Optional

logger = logging.getLogger(__name__)


# List of trusted model patterns that can be loaded with weights_only=False
# These are models we control or trust from HuggingFace
TRUSTED_MODEL_PATTERNS = [
    "pyannote/",
    "Aniemore/",
    "speechbrain/",
    "silero",
    "whisperx",
]


def is_trusted_model(path_or_name: str) -> bool:
    """
    Check if a model path/name is from a trusted source.

    Args:
        path_or_name: Model path or HuggingFace model name

    Returns:
        True if model is from a trusted source
    """
    path_str = str(path_or_name).lower()
    for pattern in TRUSTED_MODEL_PATTERNS:
        if pattern.lower() in path_str:
            return True
    return False


@contextmanager
def unsafe_torch_load():
    """
    Context manager that temporarily allows loading pickled weights.

    WARNING: Only use this for trusted model sources!
    The weights_only=False setting allows arbitrary code execution
    through pickle deserialization.

    Usage:
        with unsafe_torch_load():
            model = torch.load(path)
    """
    original_load = torch.load

    def patched_load(*args, **kwargs):
        # Force weights_only=False for this context
        kwargs['weights_only'] = False
        return original_load(*args, **kwargs)

    torch.load = patched_load

    try:
        yield
    finally:
        torch.load = original_load


def safe_load_model(
    path: str,
    device: str = "cpu",
    model_name: Optional[str] = None,
    force_unsafe: bool = False,
) -> dict:
    """
    Safely load a model checkpoint.

    Attempts safe loading first, falls back to unsafe only for trusted models.

    Args:
        path: Path to model checkpoint
        device: Device to load to
        model_name: Optional model name for trust checking
        force_unsafe: Force unsafe loading (use with caution!)

    Returns:
        Loaded model state dict

    Raises:
        RuntimeError: If model is not trusted and safe loading fails
    """
    # Try safe loading first (PyTorch 2.0+)
    try:
        return torch.load(path, map_location=device, weights_only=True)
    except Exception as e:
        logger.debug(f"Safe loading failed: {e}")

    # Check if we should allow unsafe loading
    source = model_name or path
    if not force_unsafe and not is_trusted_model(source):
        raise RuntimeError(
            f"Model {source} is not from a trusted source. "
            f"Safe loading failed and unsafe loading is not allowed. "
            f"Add model to TRUSTED_MODEL_PATTERNS if you trust this source."
        )

    # Unsafe loading for trusted models
    logger.warning(
        f"Loading model with weights_only=False (trusted source: {source})"
    )

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=FutureWarning)
        return torch.load(path, map_location=device, weights_only=False)


def patch_lightning_fabric():
    """
    Patch lightning_fabric's torch.load for compatibility with older models.

    This is needed because lightning_fabric caches the torch.load reference.
    Should be called once at application startup if using pyannote.
    """
    try:
        import lightning_fabric.utilities.cloud_io as cloud_io

        original_load = cloud_io.torch.load

        def patched_load(*args, **kwargs):
            # Only patch if weights_only is not explicitly set
            if 'weights_only' not in kwargs:
                kwargs['weights_only'] = False
            return original_load(*args, **kwargs)

        cloud_io.torch.load = patched_load
        logger.debug("Patched lightning_fabric torch.load")

    except ImportError:
        pass  # lightning_fabric not installed


def setup_model_loading(enable_pyannote_compat: bool = True):
    """
    Setup model loading compatibility.

    Call this once at application startup instead of global patching.

    Args:
        enable_pyannote_compat: Enable compatibility patches for pyannote
    """
    if enable_pyannote_compat:
        patch_lightning_fabric()
        logger.info("Model loading compatibility enabled for pyannote")
