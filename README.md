# ppdrive-python-sdk

Python SDK for [PPDRIVE](https://github.com/dududaa/ppdrive) — a self-hosted, open-source object storage service.

- Sync client built on `httpx`
- Full coverage of the PPDRIVE client API
- Typed exceptions for every HTTP error
- Resumable uploads and range downloads
- Zero runtime dependencies beyond `httpx`

## Installation

```bash
pip install ppdrive
```

## Quick Start

```python
from ppdrive import PPDriveClient

with PPDriveClient("http://localhost:8000", "YOUR_CLIENT_TOKEN") as client:
    # Create a bucket
    bucket = client.create_bucket(
        label="Documents",
        root_path="storage/docs",
        public=False,
    )
    
    # Upload a file
    with open("report.pdf", "rb") as f:
        client.upload_file(
            "report.pdf",
            f,
            bucket=bucket,
            content_type="application/pdf",
        )
        
    # Download it back
    data = client.download_file(bucket, "report.pdf", expires=300)
    with open("report_copy.pdf", "wb") as f:
        f.write(data)
```

## Authentication

Every request sends your client token in the `x-ppdrive-client` header. If your server uses a custom header key (see `client_header_key` in the server config), pass it explicitly:

```python
client = PPDriveClient(
    "http://localhost:8000",
    "YOUR_CLIENT_TOKEN",
    client_header_key="x-my-custom-header",
)
```

## Resumable Uploads

For files ≥ 2 MB, pass `resumable=True`. Chunk size defaults to 1 MB:

```python
with open("large.bin", "rb") as f:
    client.upload_file(
        "large.bin",
        f,
        bucket=bucket,
        resumable=True,
        chunk_size=2 * 1024 * 1024,
        on_progress=lambda sent, total: print(f"{sent}/{total}"),
    )
```

## Range Downloads

```python
# First 1024 bytes
head = client.download_file(bucket, "video.mp4", range=(0, 1023))

# Bytes 1024–2047
mid = client.download_file(bucket, "video.mp4", range=(1024, 2047))

# From 1024 to the end
tail = client.download_file(bucket, "video.mp4", range=(1024, None))
```

## Signed URLs

Generate upload or download links without transferring data yourself:

```python
upload_url = client.sign_upload_url(
    "incoming/report.pdf",
    bucket=bucket,
    content_type="application/pdf",
    target_filesize=1024,
)

download_url = client.sign_download_url(bucket, "report.pdf", expires=600)
```

## Permissions

```python
client.grant_permission(
    bucket,
    path="report.pdf",
    grantee="OTHER_CLIENT_PID",
    grantee_type="client",
    permission="read",
)

perms = client.list_permissions(bucket, path="report.pdf")

client.revoke_permission(
    bucket,
    path="report.pdf",
    grantee="OTHER_CLIENT_PID",
    grantee_type="client",
)
```

## Error Handling

All API errors raise subclasses of `PPDriveError`:

```python
from ppdrive import (
    PPDriveClient,
    AuthorizationError,
    NotFoundError,
    PayloadTooLargeError,
    PPDriveError,
)

try:
    client.download_file(bucket, "missing.pdf", expires=300)
except NotFoundError:
    print("No such file")
except AuthorizationError:
    print("Access denied")
except PayloadTooLargeError:
    print("File too large — use resumable upload")
except PPDriveError as e:
    print(f"HTTP {e.status}: {e.message}")
```

| Status | Exception |
|---|---|
| 400 | ValidationError |
| 401 | AuthenticationError |
| 403 | AuthorizationError |
| 404 | NotFoundError |
| 409 | ConflictError |
| 413 | PayloadTooLargeError |
| 416 | RangeError |
| 429 | RateLimitError |
| 500 | ServerError |

## API Reference

| Method | Description |
|---|---|
| `upload_file(path, data, **opts)` | Upload a file (single or chunked) |
| `upload_folder(path, **opts)` | Create a folder |
| `sign_upload_url(path, **opts)` | Return a signed upload URL |
| `download_file(bucket, path, **opts)` | Download a private file |
| `download_public_file(url)` | Download from a public bucket |
| `sign_download_url(bucket, path, expires=...)` | Return a signed download URL |
| `create_bucket(label=..., **opts)` | Create a bucket, returns its PID |
| `grant_permission(bucket, **opts)` | Grant a file-level permission |
| `revoke_permission(bucket, **opts)` | Revoke a file-level permission |
| `list_permissions(bucket, path=None)` | List permissions |
| `login(**credentials)` | Authenticate against `/auth/login` |

## Development

```bash
python -m venv .venv
source .venv/bin/activate   # or .\.venv\Scripts\Activate.ps1 on Windows
pip install -e ".[dev]"
pytest -q
```

## License

Licensed under the PolyForm Noncommercial License.
Commercial use requires permission.
