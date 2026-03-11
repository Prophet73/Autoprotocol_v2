"""
Tests for cleanup tasks (backend/tasks/cleanup.py).

Verifies that:
1. Old audio/video files in uploads/ are deleted after retention period
2. Text reports and transcripts are preserved
3. Empty job directories are removed after cleanup
4. Recent files are not deleted regardless of type
5. dry_run mode reports but does not delete
"""
import os
import pytest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch, AsyncMock

from backend.tasks.cleanup import _cleanup_directory, _async_cleanup


def _create_file(path: Path, age_days: int = 0, size: int = 1024) -> Path:
    """Create a test file and backdate its mtime."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\x00" * size)
    if age_days > 0:
        old_ts = (datetime.now(timezone.utc) - timedelta(days=age_days)).timestamp()
        os.utime(path, (old_ts, old_ts))
        # Also backdate parent dir so _cleanup_directory doesn't skip it
        os.utime(path.parent, (old_ts, old_ts))
    return path


@pytest.fixture
def upload_dir(tmp_path):
    """Create a temporary uploads directory."""
    d = tmp_path / "uploads"
    d.mkdir()
    return d


class TestCleanupDirectory:
    """Tests for _cleanup_directory."""

    @pytest.mark.asyncio
    async def test_deletes_old_audio_files(self, upload_dir):
        """Old audio/video files should be deleted."""
        job_dir = upload_dir / "job-001"
        _create_file(job_dir / "recording.wav", age_days=10, size=2048)
        _create_file(job_dir / "video.mp4", age_days=10, size=4096)

        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        stats = await _cleanup_directory(upload_dir, cutoff, dry_run=False, cleanup_audio_only=True)

        assert stats["deleted"] == 2
        assert stats["bytes"] == 2048 + 4096
        assert not (job_dir / "recording.wav").exists()
        assert not (job_dir / "video.mp4").exists()

    @pytest.mark.asyncio
    async def test_preserves_text_reports(self, upload_dir):
        """Text files (reports, transcripts, JSON) must NOT be deleted."""
        job_dir = upload_dir / "job-002"
        _create_file(job_dir / "report.pdf", age_days=10)
        _create_file(job_dir / "transcript.json", age_days=10)
        _create_file(job_dir / "notes.txt", age_days=10)

        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        stats = await _cleanup_directory(upload_dir, cutoff, dry_run=False, cleanup_audio_only=True)

        assert stats["deleted"] == 0
        assert (job_dir / "report.pdf").exists()
        assert (job_dir / "transcript.json").exists()
        assert (job_dir / "notes.txt").exists()

    @pytest.mark.asyncio
    async def test_preserves_recent_files(self, upload_dir):
        """Files younger than retention period should not be deleted."""
        job_dir = upload_dir / "job-003"
        _create_file(job_dir / "fresh.wav", age_days=0, size=5000)

        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        stats = await _cleanup_directory(upload_dir, cutoff, dry_run=False, cleanup_audio_only=True)

        assert stats["deleted"] == 0
        assert (job_dir / "fresh.wav").exists()

    @pytest.mark.asyncio
    async def test_removes_empty_job_directory(self, upload_dir):
        """Job dir should be removed when all files are cleaned."""
        job_dir = upload_dir / "job-004"
        _create_file(job_dir / "audio.mp3", age_days=10)

        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        stats = await _cleanup_directory(upload_dir, cutoff, dry_run=False, cleanup_audio_only=True)

        assert stats["deleted"] == 1
        assert stats["dirs"] == 1
        assert not job_dir.exists()

    @pytest.mark.asyncio
    async def test_keeps_dir_with_remaining_reports(self, upload_dir):
        """Dir with remaining text files should NOT be removed."""
        job_dir = upload_dir / "job-005"
        _create_file(job_dir / "audio.wav", age_days=10)
        _create_file(job_dir / "report.pdf", age_days=10)

        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        stats = await _cleanup_directory(upload_dir, cutoff, dry_run=False, cleanup_audio_only=True)

        assert stats["deleted"] == 1
        assert stats["dirs"] == 0
        assert job_dir.exists()
        assert (job_dir / "report.pdf").exists()

    @pytest.mark.asyncio
    async def test_dry_run_does_not_delete(self, upload_dir):
        """dry_run should report stats but not actually delete files."""
        job_dir = upload_dir / "job-006"
        _create_file(job_dir / "big.flac", age_days=10, size=8192)

        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        stats = await _cleanup_directory(upload_dir, cutoff, dry_run=True, cleanup_audio_only=True)

        assert stats["deleted"] == 1  # Counted as "would delete"
        assert stats["bytes"] == 8192
        assert (job_dir / "big.flac").exists()  # File still there


class TestAsyncCleanup:
    """Integration test for the full _async_cleanup flow."""

    @pytest.mark.asyncio
    async def test_full_cleanup_with_retention(self, tmp_path):
        """End-to-end: old audio deleted, reports kept, stats correct."""
        uploads = tmp_path / "uploads"
        output = tmp_path / "output"

        # Old job with mixed files
        _create_file(uploads / "job-100" / "call.wav", age_days=15, size=10000)
        _create_file(uploads / "job-100" / "result.json", age_days=15, size=500)

        # Recent job
        _create_file(uploads / "job-101" / "fresh.mp4", age_days=1, size=20000)

        # Old output audio
        _create_file(output / "job-100" / "converted.ogg", age_days=15, size=3000)

        with patch("backend.tasks.cleanup.UPLOAD_DIR", uploads), \
             patch("backend.tasks.cleanup.OUTPUT_DIR", output):
            stats = await _async_cleanup(retention_days=7, dry_run=False)

        assert stats["files_deleted"] == 2  # call.wav + converted.ogg
        assert stats["bytes_freed"] == 10000 + 3000
        assert stats["mb_freed"] == round(13000 / (1024 * 1024), 2)
        assert stats["errors"] == []

        # Reports preserved
        assert (uploads / "job-100" / "result.json").exists()
        # Recent files preserved
        assert (uploads / "job-101" / "fresh.mp4").exists()
