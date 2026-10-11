from __future__ import annotations

import httpx
import pytest
import respx

from ppdrive import PPDriveClient, ValidationError


BASE = "http://localhost:8000"


@pytest.fixture
def client() -> PPDriveClient:
    return PPDriveClient(BASE, "test-token")


@respx.mock
def test_upload_file_sends_no_null_fields(client: PPDriveClient) -> None:
    respx.post(f"{BASE}/upload/session").mock(
        return_value=httpx.Response(200, json="session-token")
    )
    respx.post(f"{BASE}/upload/session/play/session-token").mock(
        return_value=httpx.Response(200)
    )

    client.upload_file("docs/report.pdf", b"hello")

    session_call = respx.calls[0]
    body = session_call.request.content.decode()
    assert "null" not in body
    assert '"asset_type":"File"' in body
    assert '"target_filesize":5' in body


@respx.mock
def test_error_maps_to_validation_error(client: PPDriveClient) -> None:
    respx.post(f"{BASE}/buckets").mock(
        return_value=httpx.Response(400, json={"error": "missing name"})
    )

    with pytest.raises(ValidationError) as exc:
        client.create_bucket(name="", path="")

    assert exc.value.status == 400
    assert exc.value.message == "missing name"


@respx.mock
def test_client_header_is_sent(client: PPDriveClient) -> None:
    respx.post(f"{BASE}/buckets").mock(
        return_value=httpx.Response(201, json="pid-123")
    )

    client.create_bucket(name="Docs", path="storage/docs")

    assert respx.calls[0].request.headers["x-ppdrive-client"] == "test-token"

@respx.mock
def test_create_bucket_sends_correct_fields(client: PPDriveClient) -> None:
    respx.post(f"{BASE}/buckets").mock(
        return_value=httpx.Response(201, json="pid-abc")
    )

    pid = client.create_bucket(name="Docs", path="storage/docs")

    assert pid == "pid-abc"
    body = respx.calls[0].request.content.decode()
    assert '"name":"Docs"' in body
    assert '"path":"storage/docs"' in body
    assert "null" not in body


@respx.mock
def test_login_sends_email_and_password(client: PPDriveClient) -> None:
    respx.post(f"{BASE}/auth/login").mock(
        return_value=httpx.Response(200, json={"token": "abc"})
    )

    client.login(email="test@example.com", password="secret")

    body = respx.calls[0].request.content.decode()
    assert '"email":"test@example.com"' in body
    assert '"password":"secret"' in body
