"""
File security utilities.

Provides protection against path traversal and other file-related vulnerabilities.
"""
import os
import re
from pathlib import Path
from typing import Union
from urllib.parse import quote

from fastapi import HTTPException


class PathTraversalError(Exception):
    """Raised when path traversal attempt is detected."""
    pass


def validate_file_path(
    file_path: Union[str, Path],
    allowed_dir: Union[str, Path],
    must_exist: bool = True,
) -> Path:
    """
    Validate that a file path is within an allowed directory.

    Prevents path traversal attacks (e.g., ../../etc/passwd).

    Args:
        file_path: The file path to validate (can be relative or absolute).
        allowed_dir: The directory that file_path must be within.
        must_exist: If True, raise error if file doesn't exist.

    Returns:
        Resolved absolute Path object.

    Raises:
        HTTPException 403: If path is outside allowed directory.
        HTTPException 404: If must_exist=True and file doesn't exist.

    Example:
        >>> validate_file_path("/data/output/job123/file.docx", "/data/output")
        PosixPath('/data/output/job123/file.docx')

        >>> validate_file_path("../../etc/passwd", "/data/output")
        # Raises HTTPException 403
    """
    # Resolve to absolute paths
    allowed_resolved = Path(allowed_dir).resolve()
    file_resolved = Path(file_path).resolve()

    # Check that file is within allowed directory
    try:
        file_resolved.relative_to(allowed_resolved)
    except ValueError:
        # file_resolved is not relative to allowed_resolved
        raise HTTPException(
            status_code=403,
            detail="Access denied: path outside allowed directory"
        )

    # Check existence if required
    if must_exist and not file_resolved.exists():
        raise HTTPException(
            status_code=404,
            detail="File not found"
        )

    return file_resolved


def sanitize_filename(filename: str, max_length: int = 255) -> str:
    """
    Sanitize a filename to prevent directory traversal and other issues.

    Args:
        filename: The original filename.
        max_length: Maximum allowed length for filename.

    Returns:
        Sanitized filename safe for filesystem use.

    Example:
        >>> sanitize_filename("../../../etc/passwd")
        'etc_passwd'
        >>> sanitize_filename("my file<script>.txt")
        'my file_script_.txt'
    """
    # Remove null bytes
    filename = filename.replace('\x00', '')

    # Remove path separators
    filename = filename.replace('/', '_').replace('\\', '_')

    # Remove path traversal patterns
    filename = re.sub(r'\.\.+', '.', filename)

    # Remove leading dots (hidden files on Unix)
    filename = filename.lstrip('.')

    # Replace dangerous characters
    dangerous_chars = '<>:"|?*'
    for char in dangerous_chars:
        filename = filename.replace(char, '_')

    # Remove control characters
    filename = ''.join(c for c in filename if ord(c) >= 32)

    # Truncate to max length
    if len(filename) > max_length:
        # Preserve extension if possible
        name, ext = os.path.splitext(filename)
        if len(ext) < max_length - 10:
            filename = name[:max_length - len(ext)] + ext
        else:
            filename = filename[:max_length]

    # If filename is empty after sanitization, use default
    if not filename:
        filename = 'unnamed_file'

    return filename


def is_safe_path(file_path: Union[str, Path], allowed_dir: Union[str, Path]) -> bool:
    """
    Check if a file path is within an allowed directory (non-raising version).

    Args:
        file_path: The file path to check.
        allowed_dir: The directory that file_path must be within.

    Returns:
        True if path is safe, False otherwise.

    Example:
        >>> is_safe_path("/data/output/file.txt", "/data/output")
        True
        >>> is_safe_path("../../etc/passwd", "/data/output")
        False
    """
    try:
        allowed_resolved = Path(allowed_dir).resolve()
        file_resolved = Path(file_path).resolve()
        file_resolved.relative_to(allowed_resolved)
        return True
    except (ValueError, OSError):
        return False


def make_content_disposition(filename: str, disposition: str = "attachment") -> str:
    """Build Content-Disposition header with RFC 5987 encoding for non-ASCII filenames.

    Always includes both plain `filename` (ASCII fallback) and `filename*` (UTF-8)
    so all browsers can pick the best option.

    Example:
        >>> make_content_disposition("Отчёт.docx")
        'attachment; filename="Otchyot.docx"; filename*=UTF-8\'\'%D0%9E%D1%82%D1%87%D1%91%D1%82.docx'
    """
    # ASCII-safe fallback: replace non-ASCII chars with underscores
    ascii_name = filename.encode("ascii", "replace").decode("ascii").replace("?", "_")
    # RFC 5987 UTF-8 encoded version
    utf8_name = quote(filename, safe="")
    return f'{disposition}; filename="{ascii_name}"; filename*=UTF-8\'\'{utf8_name}'
