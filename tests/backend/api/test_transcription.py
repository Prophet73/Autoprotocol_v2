"""Tests for POST /transcribe endpoint with mocked dependencies."""
import io
from unittest.mock import patch, MagicMock

from backend.core.auth.dependencies import get_optional_user
from backend.api.main import app
from backend.shared.models import User


def _make_mock_user():
    """Create a fake authenticated user."""
    user = MagicMock(spec=User)
    user.id = 1
    user.email = "test@example.com"
    user.username = "testuser"
    user.role = "user"
    user.is_active = True
    user.is_superuser = False
    user.domains = []
    user.active_domain = None
    return user


async def test_transcribe_unauthenticated_returns_401(async_client):
    """POST /transcribe without auth token should return 401."""
    fake_file = io.BytesIO(b"fake audio content")
    response = await async_client.post(
        "/transcribe",
        files={"file": ("test.mp3", fake_file, "audio/mpeg")},
        data={"languages": "ru"},
    )
    assert response.status_code == 401


async def test_transcribe_authorized_returns_200(async_client, tmp_path):
    """POST /transcribe with auth and mocked Celery should return 200 with job_id."""
    mock_user = _make_mock_user()

    # Override auth dependency to return mock user
    app.dependency_overrides[get_optional_user] = lambda: mock_user

    mock_store = MagicMock()

    try:
        fake_file = io.BytesIO(b"fake audio content for testing")

        with patch("backend.api.routes.transcription.get_store", return_value=mock_store), \
             patch("backend.api.routes.transcription.UPLOAD_DIR", tmp_path / "uploads"), \
             patch("backend.api.routes.transcription.OUTPUT_DIR", tmp_path / "output"), \
             patch("backend.api.routes.transcription.process_transcription_task") as mock_task:

            mock_task.apply_async = MagicMock()

            response = await async_client.post(
                "/transcribe",
                files={"file": ("test.mp3", fake_file, "audio/mpeg")},
                data={"languages": "ru"},
            )

        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        assert "status" in data
    finally:
        app.dependency_overrides.pop(get_optional_user, None)
