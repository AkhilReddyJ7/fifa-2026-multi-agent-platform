"""Auth API tests — Phase 4C."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient) -> None:
    r = await client.post("/api/v1/auth/register", json={"email": "new@example.com", "password": "password123"})
    assert r.status_code == 201
    body = r.json()
    assert body["email"] == "new@example.com"
    assert "id" in body
    assert "password" not in body
    assert "hashed_password" not in body


@pytest.mark.asyncio
async def test_register_duplicate_email_returns_409(client: AsyncClient) -> None:
    payload = {"email": "dup@example.com", "password": "password123"}
    await client.post("/api/v1/auth/register", json=payload)
    r = await client.post("/api/v1/auth/register", json=payload)
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_register_short_password_returns_422(client: AsyncClient) -> None:
    r = await client.post("/api/v1/auth/register", json={"email": "short@example.com", "password": "abc"})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_register_invalid_email_returns_422(client: AsyncClient) -> None:
    r = await client.post("/api/v1/auth/register", json={"email": "not-an-email", "password": "password123"})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_login_valid_credentials_returns_token(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json={"email": "valid@example.com", "password": "password123"})
    r = await client.post("/api/v1/auth/login", json={"email": "valid@example.com", "password": "password123"})
    assert r.status_code == 200
    body = r.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"
    assert len(body["access_token"]) > 20


@pytest.mark.asyncio
async def test_login_wrong_password_returns_401(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json={"email": "wrongpw@example.com", "password": "password123"})
    r = await client.post("/api/v1/auth/login", json={"email": "wrongpw@example.com", "password": "wrongpassword"})
    assert r.status_code == 401
    assert r.json()["detail"] == "Incorrect email or password"


@pytest.mark.asyncio
async def test_login_unknown_email_returns_401(client: AsyncClient) -> None:
    r = await client.post("/api/v1/auth/login", json={"email": "ghost@example.com", "password": "password123"})
    assert r.status_code == 401
    assert r.json()["detail"] == "Incorrect email or password"


@pytest.mark.asyncio
async def test_me_with_valid_token(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json={"email": "me@example.com", "password": "password123"})
    login_r = await client.post("/api/v1/auth/login", json={"email": "me@example.com", "password": "password123"})
    token = login_r.json()["access_token"]

    r = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["email"] == "me@example.com"


@pytest.mark.asyncio
async def test_me_without_token_returns_401(client: AsyncClient) -> None:
    r = await client.get("/api/v1/auth/me")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_me_with_invalid_token_returns_401(client: AsyncClient) -> None:
    r = await client.get("/api/v1/auth/me", headers={"Authorization": "Bearer this.is.not.a.valid.token"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_chat_without_auth_returns_401(client: AsyncClient) -> None:
    r = await client.post("/api/v1/chat", json={"message": "Hello"})
    assert r.status_code == 401
