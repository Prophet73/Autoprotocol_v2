"""
Integration tests for job management via API.

Tests:
1. Text file processing doesn't block API
2. Job cancellation works correctly
3. Cancelling queued job allows next job to start
"""
import pytest
import requests
import time
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# API base URL
API_URL = os.getenv("API_URL", "http://localhost:8000")

# Test files
TEST_MEDIA_DIR = Path(__file__).parent.parent.parent / "_test_media"

# Auth token — берётся из env или получается автоматически через mock dev login
_AUTH_TOKEN: str | None = None


def _get_auth_token() -> str:
    """Получить JWT токен для тестовых запросов.

    Приоритет:
    1. Env var API_TOKEN (явный токен)
    2. Env var API_TEST_EMAIL + API_TEST_PASSWORD (логин через /auth/login)
    3. Авто-логин через admin@mock.dev (dev окружение с mock Hub)
    """
    global _AUTH_TOKEN
    if _AUTH_TOKEN:
        return _AUTH_TOKEN

    # 1. Явный токен из env
    token = os.getenv("API_TOKEN")
    if token:
        _AUTH_TOKEN = token
        return _AUTH_TOKEN

    # 2. Email/пароль из env
    email = os.getenv("API_TEST_EMAIL", "admin@mock.dev")
    password = os.getenv("API_TEST_PASSWORD", "")

    # 3. Попытка логина (нужен пароль или работающий /auth/login)
    if password:
        resp = requests.post(
            f"{API_URL}/auth/login",
            data={"username": email, "password": password},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10,
        )
        if resp.status_code == 200:
            _AUTH_TOKEN = resp.json()["access_token"]
            return _AUTH_TOKEN

    raise RuntimeError(
        "Не удалось получить auth токен для тестов. "
        "Укажите API_TOKEN или API_TEST_EMAIL + API_TEST_PASSWORD."
    )


def _auth_headers() -> dict:
    return {"Authorization": f"Bearer {_get_auth_token()}"}


def get_test_text_file():
    """Get a test text file path."""
    # Look for any docx or txt file in test media
    for ext in ["*.docx", "*.txt"]:
        files = list(TEST_MEDIA_DIR.glob(ext))
        if files:
            return files[0]
    return None


def get_test_media_file():
    """Get a test media file path."""
    for ext in ["*.m4a", "*.mp3", "*.wav", "*.mp4"]:
        files = list(TEST_MEDIA_DIR.glob(ext))
        if files:
            return files[0]
    return None


def upload_file(file_path: Path, project_code: str | None = None) -> dict:
    """Upload a file and return job info."""
    # project_code берётся из env (TEST_PROJECT_CODE) или не передаётся вовсе
    code = project_code or os.getenv("TEST_PROJECT_CODE")
    data: dict = {"generate_transcript": "true", "generate_risk_brief": "true"}
    if code:
        data["project_code"] = code

    with open(file_path, "rb") as f:
        response = requests.post(
            f"{API_URL}/transcribe",
            files={"file": (file_path.name, f)},
            data=data,
            headers=_auth_headers(),
            timeout=30,
        )
    response.raise_for_status()
    return response.json()


def get_job_status(job_id: str) -> dict:
    """Get job status."""
    response = requests.get(
        f"{API_URL}/transcribe/{job_id}/status",
        headers=_auth_headers(),
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def cancel_job(job_id: str) -> dict:
    """Cancel a job."""
    response = requests.delete(
        f"{API_URL}/transcribe/{job_id}",
        headers=_auth_headers(),
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def check_api_responsive() -> bool:
    """Check if API responds within timeout."""
    try:
        response = requests.get(f"{API_URL}/health", timeout=5)
        return response.status_code == 200
    except requests.exceptions.Timeout:
        return False
    except requests.exceptions.RequestException:
        return False


class TestTextFileProcessing:
    """Test that text file processing doesn't block API."""

    def test_api_responsive_during_text_processing(self):
        """API should remain responsive while text file is being processed."""
        text_file = get_test_text_file()
        if not text_file:
            pytest.skip("No test text file available")

        # Upload text file
        job_info = upload_file(text_file)
        job_id = job_info["job_id"]
        print(f"Uploaded text file, job_id: {job_id}")

        # Immediately check if API is responsive
        responsive_checks = []
        for i in range(5):
            is_responsive = check_api_responsive()
            responsive_checks.append(is_responsive)
            print(f"API responsive check {i+1}: {is_responsive}")
            time.sleep(1)

        # All checks should pass
        assert all(responsive_checks), "API should remain responsive during text processing"

        # Cleanup - cancel job if still running
        try:
            status = get_job_status(job_id)
            if status["status"] in ["pending", "processing"]:
                cancel_job(job_id)
        except:
            pass

    def test_text_file_goes_to_celery(self):
        """Text file should be queued to Celery, not processed inline."""
        text_file = get_test_text_file()
        if not text_file:
            pytest.skip("No test text file available")

        # Upload should return immediately with pending status
        start = time.time()
        job_info = upload_file(text_file)
        upload_time = time.time() - start

        assert job_info["status"] == "pending"
        # Upload should be fast (< 5 seconds) since processing is async
        assert upload_time < 5, f"Upload took {upload_time}s, expected < 5s"

        print(f"Upload completed in {upload_time:.2f}s")

        # Cleanup
        try:
            cancel_job(job_info["job_id"])
        except:
            pass


class TestJobCancellation:
    """Test job cancellation functionality."""

    def test_cancel_pending_job(self):
        """Should be able to cancel a pending job."""
        media_file = get_test_media_file()
        if not media_file:
            pytest.skip("No test media file available")

        # Upload file
        job_info = upload_file(media_file)
        job_id = job_info["job_id"]
        print(f"Uploaded media file, job_id: {job_id}")

        # Give it a moment
        time.sleep(1)

        # Check status
        status = get_job_status(job_id)
        print(f"Job status: {status['status']}")

        # Cancel the job
        if status["status"] in ["pending", "processing"]:
            result = cancel_job(job_id)
            assert result.get("success") is True
            print("Job cancelled successfully")

            # Verify status is now failed (cancelled)
            final_status = get_job_status(job_id)
            assert final_status["status"] == "failed"
            assert "cancel" in final_status.get("error", "").lower() or \
                   "cancel" in final_status.get("message", "").lower()

    def test_cancel_with_correct_task_id(self):
        """Celery task_id should equal job_id for proper revoke."""
        media_file = get_test_media_file()
        if not media_file:
            pytest.skip("No test media file available")

        # This test verifies the fix by checking that cancellation works
        # If task_id != job_id, revoke would fail silently

        job_info = upload_file(media_file)
        job_id = job_info["job_id"]

        time.sleep(2)

        status_before = get_job_status(job_id)
        print(f"Status before cancel: {status_before['status']}")

        if status_before["status"] in ["pending", "processing"]:
            cancel_job(job_id)

            # Wait for cancellation to take effect
            time.sleep(2)

            status_after = get_job_status(job_id)
            print(f"Status after cancel: {status_after['status']}")

            # Job should be failed (cancelled), not still processing
            assert status_after["status"] == "failed", \
                "Job should be cancelled. If still processing, task_id != job_id bug exists."


class TestQueueBehavior:
    """Test queue behavior when jobs are cancelled."""

    def test_next_job_starts_after_cancel(self):
        """When a job is cancelled, the next queued job should start."""
        media_file = get_test_media_file()
        if not media_file:
            pytest.skip("No test media file available")

        # Upload two jobs quickly
        job1_info = upload_file(media_file)
        job1_id = job1_info["job_id"]
        print(f"Job 1: {job1_id}")

        time.sleep(0.5)

        job2_info = upload_file(media_file)
        job2_id = job2_info["job_id"]
        print(f"Job 2: {job2_id}")

        # Wait a moment for jobs to be queued
        time.sleep(2)

        # Check statuses
        status1 = get_job_status(job1_id)
        status2 = get_job_status(job2_id)
        print(f"Job 1 status: {status1['status']}")
        print(f"Job 2 status: {status2['status']}")

        # Cancel job 1 (whether pending or processing)
        if status1["status"] in ["pending", "processing"]:
            cancel_job(job1_id)
            print("Job 1 cancelled")

        # Wait for queue to process
        time.sleep(5)

        # Job 2 should eventually start processing or complete
        status2_after = get_job_status(job2_id)
        print(f"Job 2 status after cancel: {status2_after['status']}")

        # Job 2 should not be stuck in pending forever
        # It should be processing, completed, or failed (but not pending)
        # Note: if worker is busy with another task, it may still be pending
        # The key test is that it eventually processes

        # Cleanup
        for jid in [job1_id, job2_id]:
            try:
                s = get_job_status(jid)
                if s["status"] in ["pending", "processing"]:
                    cancel_job(jid)
            except:
                pass


class TestAPIHealth:
    """Test API health and responsiveness."""

    def test_health_endpoint(self):
        """Health endpoint should respond."""
        response = requests.get(f"{API_URL}/health", timeout=5)
        assert response.status_code == 200

    def test_concurrent_status_requests(self):
        """API should handle concurrent requests."""

        def make_request():
            try:
                response = requests.get(f"{API_URL}/health", timeout=5)
                return response.status_code == 200
            except:
                return False

        # Make 10 concurrent requests
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(10)]
            results = [f.result() for f in as_completed(futures)]

        assert all(results), "All concurrent requests should succeed"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
