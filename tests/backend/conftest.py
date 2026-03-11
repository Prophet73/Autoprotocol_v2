"""
Backend test fixtures: async database session and HTTP client.

Mocks heavy GPU/ML dependencies that aren't installed in test environments.
"""
import sys
from unittest.mock import MagicMock

# Mock heavy dependencies before any app imports.
# torch needs deep sub-module mocks because code does `import torch.nn.functional as F`.
_torch_mock = MagicMock()
# Health endpoint checks torch.cuda.is_available() and torch.cuda.get_device_name(0)
_torch_mock.cuda.is_available.return_value = False
_MOCK_MODULES = {
    "torch": _torch_mock,
    "torch.nn": _torch_mock.nn,
    "torch.nn.functional": _torch_mock.nn.functional,
    "torch.cuda": _torch_mock.cuda,
    "torch.hub": _torch_mock.hub,
    "torchaudio": MagicMock(),
    "whisperx": MagicMock(),
    "pyannote": MagicMock(),
    "pyannote.audio": MagicMock(),
    "pyannote.audio.pipelines": MagicMock(),
    "transformers": MagicMock(),
    "nemo": MagicMock(),
    "nemo.collections": MagicMock(),
    "nemo.collections.asr": MagicMock(),
    "soundfile": MagicMock(),
    "librosa": MagicMock(),
}
for mod_name, mock_obj in _MOCK_MODULES.items():
    if mod_name not in sys.modules:
        sys.modules[mod_name] = mock_obj

import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from httpx import AsyncClient, ASGITransport

from backend.shared.database import Base, get_db
from backend.api.main import app


@pytest.fixture
async def db_engine():
    """Create an in-memory SQLite async engine for tests."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(db_engine):
    """Provide a transactional async database session for tests."""
    session_factory = async_sessionmaker(
        db_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_factory() as session:
        yield session


@pytest.fixture
async def async_client(db_session):
    """
    HTTP client for testing FastAPI endpoints.

    Overrides the get_db dependency to use the test SQLite session.
    """
    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()
