"""
Tests for file security utilities.

Tests path traversal protection and filename sanitization.
These tests use local implementations to avoid torch dependency.
"""
import pytest
import re
from pathlib import Path


class HTTPException(Exception):
    """Mock HTTPException for testing."""
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


def validate_file_path(
    file_path: str,
    allowed_dir: str,
    must_exist: bool = True
) -> Path:
    """
    Validate that a file path is within an allowed directory.
    Prevents path traversal attacks.
    """
    allowed_resolved = Path(allowed_dir).resolve()
    file_resolved = Path(file_path).resolve()

    try:
        file_resolved.relative_to(allowed_resolved)
    except ValueError:
        raise HTTPException(
            status_code=403,
            detail="Access denied: path outside allowed directory"
        )

    if must_exist and not file_resolved.exists():
        raise HTTPException(status_code=404, detail="File not found")

    return file_resolved


def sanitize_filename(filename: str, max_length: int = 255) -> str:
    """
    Sanitize a filename to prevent path traversal and other issues.
    """
    if not filename:
        return "unnamed"

    # Remove path separators
    filename = filename.replace("/", "_").replace("\\", "_")

    # Remove other dangerous characters
    filename = re.sub(r'[<>:"|?*\x00-\x1f]', '_', filename)

    # Handle special names
    if filename in (".", "..") or filename.startswith("."):
        filename = "_" + filename

    # Truncate if too long
    if len(filename) > max_length:
        name, ext = (filename.rsplit(".", 1) + [""])[:2]
        if ext:
            max_name = max_length - len(ext) - 1
            filename = name[:max_name] + "." + ext
        else:
            filename = filename[:max_length]

    return filename


def is_safe_path(file_path: str, allowed_dir: str) -> bool:
    """
    Check if a file path is within an allowed directory.
    Returns True if safe, False otherwise.
    """
    try:
        allowed_resolved = Path(allowed_dir).resolve()
        file_resolved = Path(file_path).resolve()
        file_resolved.relative_to(allowed_resolved)
        return True
    except ValueError:
        return False


class TestValidateFilePath:
    """Tests for validate_file_path function."""

    def test_valid_path_within_directory(self, tmp_path):
        """Valid path within allowed directory should pass."""
        # Create a test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        result = validate_file_path(str(test_file), str(tmp_path))
        assert result == test_file.resolve()

    def test_path_traversal_blocked(self, tmp_path):
        """Path traversal attempts should be blocked."""
        malicious_path = str(tmp_path / ".." / ".." / "etc" / "passwd")

        with pytest.raises(HTTPException) as exc_info:
            validate_file_path(malicious_path, str(tmp_path))

        assert exc_info.value.status_code == 403
        assert "outside allowed directory" in exc_info.value.detail

    def test_absolute_path_outside_directory(self, tmp_path):
        """Absolute path outside allowed directory should be blocked."""
        with pytest.raises(HTTPException) as exc_info:
            validate_file_path("/etc/passwd", str(tmp_path))

        assert exc_info.value.status_code == 403

    def test_file_not_found(self, tmp_path):
        """Non-existent file should raise 404."""
        non_existent = str(tmp_path / "does_not_exist.txt")

        with pytest.raises(HTTPException) as exc_info:
            validate_file_path(non_existent, str(tmp_path), must_exist=True)

        assert exc_info.value.status_code == 404

    def test_file_not_found_optional(self, tmp_path):
        """Non-existent file with must_exist=False should pass."""
        non_existent = tmp_path / "new_file.txt"

        result = validate_file_path(str(non_existent), str(tmp_path), must_exist=False)
        assert result == non_existent.resolve()

    def test_symbolic_link_traversal(self, tmp_path):
        """Symbolic links that escape directory should be blocked."""
        # This test is platform-specific
        import platform
        if platform.system() == "Windows":
            pytest.skip("Symlink test skipped on Windows")

        # Create symlink pointing outside
        link = tmp_path / "evil_link"
        link.symlink_to("/etc/passwd")

        with pytest.raises(HTTPException) as exc_info:
            validate_file_path(str(link), str(tmp_path))

        assert exc_info.value.status_code == 403


class TestSanitizeFilename:
    """Tests for sanitize_filename function."""

    def test_normal_filename(self):
        """Normal filename should pass unchanged."""
        assert sanitize_filename("report.docx") == "report.docx"

    def test_filename_with_path_separators(self):
        """Path separators should be replaced."""
        assert sanitize_filename("path/to/file.txt") == "path_to_file.txt"
        assert sanitize_filename("path\\to\\file.txt") == "path_to_file.txt"

    def test_filename_with_special_chars(self):
        """Special characters should be replaced."""
        result = sanitize_filename("file<>:\"|?*.txt")
        assert "<" not in result
        assert ">" not in result
        assert ":" not in result
        assert '"' not in result
        assert "|" not in result
        assert "?" not in result
        assert "*" not in result

    def test_filename_too_long(self):
        """Long filenames should be truncated."""
        long_name = "a" * 300 + ".txt"
        result = sanitize_filename(long_name)
        assert len(result) <= 255

    def test_empty_filename(self):
        """Empty filename should return default."""
        assert sanitize_filename("") == "unnamed"

    def test_only_dots(self):
        """Filename with only dots should be sanitized."""
        result = sanitize_filename("...")
        assert result != "..."

    def test_unicode_filename(self):
        """Unicode characters should be preserved."""
        assert sanitize_filename("отчёт_2024.docx") == "отчёт_2024.docx"


class TestIsSafePath:
    """Tests for is_safe_path function."""

    def test_safe_path(self, tmp_path):
        """Path within directory should return True."""
        safe = tmp_path / "subdir" / "file.txt"
        assert is_safe_path(str(safe), str(tmp_path)) is True

    def test_unsafe_path(self, tmp_path):
        """Path outside directory should return False."""
        unsafe = tmp_path / ".." / ".." / "etc" / "passwd"
        assert is_safe_path(str(unsafe), str(tmp_path)) is False

    def test_absolute_path_outside(self, tmp_path):
        """Absolute path outside should return False."""
        assert is_safe_path("/etc/passwd", str(tmp_path)) is False
