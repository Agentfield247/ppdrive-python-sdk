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
        return_value=httpx.Response(400, json={"error": "missing label"})
    )

    with pytest.raises(ValidationError) as exc:
        client.create_bucket(label="")

    assert exc.value.status == 400
    assert exc.value.message == "missing label"


@respx.mock
def test_client_header_is_sent(client: PPDriveClient) -> None:
    respx.post(f"{BASE}/buckets").mock(
        return_value=httpx.Response(200, json="pid-123")
    )

    client.create_bucket(label="Docs")

    assert respx.calls[0].request.headers["x-ppdrive-client"] == "test-token"
