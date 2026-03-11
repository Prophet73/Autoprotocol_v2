"""Tests for GET /health endpoint."""


async def test_health_returns_200(async_client):
    """Health endpoint should return 200 with status key."""
    response = await async_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] == "healthy"


async def test_health_has_version(async_client):
    """Health endpoint should include version info."""
    response = await async_client.get("/health")
    data = response.json()
    assert "version" in data


async def test_health_has_gpu_info(async_client):
    """Health endpoint should include gpu_available field."""
    response = await async_client.get("/health")
    data = response.json()
    assert "gpu_available" in data
