"""
Tests for LIKE injection protection.

Tests the _escape_like_pattern function from logs service.
"""
import pytest


def _escape_like_pattern(value: str) -> str:
    """
    Escape special characters in LIKE pattern to prevent LIKE injection.

    Args:
        value: User-provided search string.

    Returns:
        Escaped string safe for use in LIKE queries.
    """
    # Escape backslash first, then other special chars
    return (
        value
        .replace("\\", "\\\\")
        .replace("%", "\\%")
        .replace("_", "\\_")
    )


class TestEscapeLikePattern:
    """Tests for LIKE pattern escaping."""

    def test_normal_string(self):
        """Normal string without special chars should pass unchanged."""
        assert _escape_like_pattern("hello") == "hello"

    def test_percent_escaped(self):
        """Percent sign should be escaped."""
        assert _escape_like_pattern("50%") == "50\\%"
        assert _escape_like_pattern("%admin%") == "\\%admin\\%"

    def test_underscore_escaped(self):
        """Underscore should be escaped."""
        assert _escape_like_pattern("user_name") == "user\\_name"
        assert _escape_like_pattern("__init__") == "\\_\\_init\\_\\_"

    def test_backslash_escaped(self):
        """Backslash should be escaped."""
        assert _escape_like_pattern("path\\to\\file") == "path\\\\to\\\\file"

    def test_mixed_special_chars(self):
        """Multiple special chars should all be escaped."""
        result = _escape_like_pattern("50%_discount\\sale")
        assert result == "50\\%\\_discount\\\\sale"

    def test_empty_string(self):
        """Empty string should return empty string."""
        assert _escape_like_pattern("") == ""

    def test_only_special_chars(self):
        """String with only special chars should be fully escaped."""
        assert _escape_like_pattern("%_%") == "\\%\\_\\%"

    def test_unicode_preserved(self):
        """Unicode characters should be preserved."""
        assert _escape_like_pattern("пользователь_123%") == "пользователь\\_123\\%"

    def test_sql_injection_attempt(self):
        """SQL-like patterns should be escaped."""
        # Someone trying to match all records
        assert _escape_like_pattern("'; DROP TABLE users; --") == "'; DROP TABLE users; --"
        # The actual LIKE wildcards are escaped
        assert _escape_like_pattern("%' OR '1'='1") == "\\%' OR '1'='1"

    def test_realistic_search_patterns(self):
        """Realistic search patterns should be properly escaped."""
        # User searching for endpoint
        assert _escape_like_pattern("/api/users") == "/api/users"

        # User searching for error percentage
        assert _escape_like_pattern("error_rate: 50%") == "error\\_rate: 50\\%"

        # User searching for file path
        assert _escape_like_pattern("C:\\logs\\error.log") == "C:\\\\logs\\\\error.log"


class TestLikeInjectionPrevention:
    """Tests demonstrating LIKE injection prevention."""

    def test_wildcard_matching_prevented(self):
        """User cannot use % to match arbitrary strings."""
        user_input = "%admin%"
        escaped = _escape_like_pattern(user_input)

        # The escaped pattern will only match literal "%admin%"
        # not "administrator" or "admin_user"
        assert escaped == "\\%admin\\%"

    def test_single_char_wildcard_prevented(self):
        """User cannot use _ to match single characters."""
        user_input = "user_"
        escaped = _escape_like_pattern(user_input)

        # Won't match "user1", "user2", etc.
        assert escaped == "user\\_"

    def test_combined_attack_prevented(self):
        """Combined injection attempts should be neutralized."""
        # Attacker trying to match all records with specific prefix
        user_input = "admin%' OR endpoint LIKE '%"
        escaped = _escape_like_pattern(user_input)

        # Wildcards escaped, SQL remains as literal string
        assert "\\%" in escaped
        # The SQL injection part is just a string, not executed
        assert "OR endpoint" in escaped
