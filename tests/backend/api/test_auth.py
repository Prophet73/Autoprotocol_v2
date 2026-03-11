"""Tests for /auth endpoints."""


async def test_login_invalid_credentials_returns_401(async_client):
    """POST /auth/login with wrong credentials should return 401."""
    response = await async_client.post(
        "/auth/login",
        data={"username": "nonexistent@test.com", "password": "wrongpassword"},
    )
    assert response.status_code == 401


async def test_login_missing_fields_returns_422(async_client):
    """POST /auth/login without required fields should return 422."""
    response = await async_client.post("/auth/login", data={})
    assert response.status_code == 422
