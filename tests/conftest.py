"""
Pytest configuration and fixtures.
"""
import os
import sys
from pathlib import Path

import pytest

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Set test environment
os.environ["ENVIRONMENT"] = "test"
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only"


@pytest.fixture
def sample_email():
    """Sample valid email."""
    return "test@example.com"


@pytest.fixture
def sample_emails():
    """Sample list of valid emails."""
    return ["user1@example.com", "user2@example.com"]


@pytest.fixture
def malicious_path():
    """Sample path traversal attempt."""
    return "../../../etc/passwd"


@pytest.fixture
def safe_filename():
    """Sample safe filename."""
    return "report_20240101_120000.docx"
