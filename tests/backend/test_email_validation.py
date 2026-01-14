"""
Tests for email validation.

Tests email format validation and header injection protection.
"""
import pytest
import re

# Email validation regex from transcription.py
_EMAIL_REGEX = re.compile(
    r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
)


def validate_email(email: str) -> bool:
    """Validate single email address."""
    if not email or len(email) > 254:
        return False
    # Check for header injection attempts
    if any(c in email for c in ['\n', '\r', '\x00']):
        return False
    return bool(_EMAIL_REGEX.match(email))


def validate_email_list(emails_str: str) -> list[str]:
    """Parse and validate comma-separated email list."""
    if not emails_str:
        return []

    emails = []
    for email in emails_str.split(','):
        email = email.strip()
        if email and validate_email(email):
            emails.append(email)

    return emails


class TestEmailValidation:
    """Tests for email validation."""

    def test_valid_email(self):
        """Standard email should pass."""
        assert validate_email("user@example.com") is True

    def test_valid_email_with_subdomain(self):
        """Email with subdomain should pass."""
        assert validate_email("user@mail.example.com") is True

    def test_valid_email_with_plus(self):
        """Email with plus addressing should pass."""
        assert validate_email("user+tag@example.com") is True

    def test_valid_email_with_dots(self):
        """Email with dots in local part should pass."""
        assert validate_email("first.last@example.com") is True

    def test_invalid_email_no_at(self):
        """Email without @ should fail."""
        assert validate_email("userexample.com") is False

    def test_invalid_email_no_domain(self):
        """Email without domain should fail."""
        assert validate_email("user@") is False

    def test_invalid_email_no_tld(self):
        """Email without TLD should fail."""
        assert validate_email("user@example") is False

    def test_invalid_email_short_tld(self):
        """Email with single-char TLD should fail."""
        assert validate_email("user@example.c") is False

    def test_empty_email(self):
        """Empty string should fail."""
        assert validate_email("") is False

    def test_email_too_long(self):
        """Email over 254 chars should fail."""
        long_email = "a" * 250 + "@example.com"
        assert validate_email(long_email) is False


class TestHeaderInjection:
    """Tests for header injection protection."""

    def test_newline_injection(self):
        """Email with newline should be rejected."""
        assert validate_email("user@example.com\nBcc: victim@example.com") is False

    def test_carriage_return_injection(self):
        """Email with carriage return should be rejected."""
        assert validate_email("user@example.com\rBcc: victim@example.com") is False

    def test_null_byte_injection(self):
        """Email with null byte should be rejected."""
        assert validate_email("user@example.com\x00Bcc: victim@example.com") is False

    def test_crlf_injection(self):
        """Email with CRLF should be rejected."""
        assert validate_email("user@example.com\r\nBcc: victim@example.com") is False


class TestEmailListValidation:
    """Tests for email list validation."""

    def test_single_email(self):
        """Single email should return list with one item."""
        result = validate_email_list("user@example.com")
        assert result == ["user@example.com"]

    def test_multiple_emails(self):
        """Multiple emails should all be returned."""
        result = validate_email_list("a@example.com, b@example.com, c@example.com")
        assert result == ["a@example.com", "b@example.com", "c@example.com"]

    def test_mixed_valid_invalid(self):
        """Invalid emails should be filtered out."""
        result = validate_email_list("valid@example.com, invalid, another@example.com")
        assert result == ["valid@example.com", "another@example.com"]

    def test_empty_string(self):
        """Empty string should return empty list."""
        assert validate_email_list("") == []

    def test_whitespace_handling(self):
        """Whitespace around emails should be trimmed."""
        result = validate_email_list("  user1@example.com  ,  user2@example.com  ")
        assert result == ["user1@example.com", "user2@example.com"]

    def test_all_invalid(self):
        """All invalid emails should return empty list."""
        result = validate_email_list("invalid1, invalid2, invalid3")
        assert result == []
