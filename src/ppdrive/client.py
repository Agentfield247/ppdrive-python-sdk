from __future__ import annotations

from typing import Any, BinaryIO, Callable

import httpx

from ._http import HTTPCore, compact


class PPDriveClient:
    """Synchronous Python client for the PPDRIVE REST API."""

    def __init__(
        self,
        base_url: str,
        client_token: str,
        *,
        client_header_key: str = "x-ppdrive-client",
        timeout: float = 30.0,
    ) -> None:
        self._core = HTTPCore(
            base_url,
            client_token,
            client_header_key=client_header_key,
            timeout=timeout,
        )

    @classmethod
    def from_token(
        cls,
        base_url: str,
        client_token: str,
        **kwargs: Any,
    ) -> "PPDriveClient":
        return cls(base_url, client_token, **kwargs)

    def close(self) -> None:
        self._core.close()

    def __enter__(self) -> "PPDriveClient":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Upload
    # ------------------------------------------------------------------

    def sign_upload_url(
        self,
        path: str,
        *,
        bucket: str | None = None,
        content_type: str | None = None,
        target_filesize: int | None = None,
        overwrite: bool | None = None,
        create_parents: bool | None = None,
        expires: int | None = None,
        accepts: str | None = None,
        public: bool | None = None,
        asset_type: str = "File",
    ) -> str:
        """Create an upload session and return the signed upload URL."""
        body = compact(
            asset_type=asset_type,
            path=path,
            bucket=bucket,
            content_type=content_type,
            target_filesize=target_filesize,
            overwrite=overwrite,
            create_parents=create_parents,
            expires=expires,
            accepts=accepts,
            public=public,
        )
        token = self._core.request("POST", "/upload/session", json=body)
        return f"{self._core.base_url}/upload/session/play/{token}"

    def upload_file(
        self,
        path: str,
        data: bytes | BinaryIO,
        *,
        bucket: str | None = None,
        content_type: str | None = None,
        overwrite: bool | None = None,
        create_parents: bool | None = None,
        resumable: bool | None = None,
        chunk_size: int = 1 << 20,
        expires: int | None = None,
        accepts: str | None = None,
        public: bool | None = None,
        on_progress: Callable[[int, int], None] | None = None,
    ) -> None:
        """Upload a file in one or more chunks.

        For files >= 2 MB the server requires ``resumable=True``.
        """
        payload = data if isinstance(data, (bytes, bytearray)) else data.read()
        size = len(payload)

        upload_url = self.sign_upload_url(
            path,
            bucket=bucket,
            content_type=content_type,
            target_filesize=size,
            overwrite=overwrite,
            create_parents=create_parents,
            expires=expires,
            accepts=accepts,
            public=public,
        )

        if not resumable:
            self._core.request("POST", upload_url, content=payload)
            if on_progress:
                on_progress(size, size)
            return

        sent = 0
        token = upload_url.rsplit("/", 1)[-1]
        for offset in range(0, size, chunk_size):
            chunk = payload[offset : offset + chunk_size]
            response = self._core.request(
                "POST",
                f"/upload/session/play/{token}",
                content=chunk,
            )
            sent += len(chunk)
            if on_progress:
                on_progress(sent, size)
            if response:
                token = (
                    response
                    if isinstance(response, str)
                    else response.get("token", token)
                )

    def upload_folder(
        self,
        path: str,
        *,
        bucket: str | None = None,
        overwrite: bool | None = None,
        create_parents: bool | None = None,
        expires: int | None = None,
    ) -> None:
        """Create a folder on the server."""
        upload_url = self.sign_upload_url(
            path,
            bucket=bucket,
            overwrite=overwrite,
            create_parents=create_parents,
            expires=expires,
            asset_type="Folder",
        )
        self._core.request("POST", upload_url)

    # ------------------------------------------------------------------
    # Download
    # ------------------------------------------------------------------

    def sign_download_url(
        self,
        bucket: str,
        path: str,
        *,
        expires: int,
    ) -> str:
        """Sign a private-bucket download and return the full URL.

        ``expires`` is required (30–3600 seconds).
        """
        body = compact(path=path, bucket=bucket, expires=expires)
        token = self._core.request("POST", "/download/sign", json=body)
        return f"{self._core.base_url}/download/{token}"

    def download_file(
        self,
        bucket: str,
        path: str,
        *,
        expires: int = 300,
        range: tuple[int, int | None] | None = None,
    ) -> bytes:
        """Download a private-bucket file (optionally a byte range)."""
        url = self.sign_download_url(bucket, path, expires=expires)
        headers: dict[str, str] = {}
        if range is not None:
            start, end = range
            headers["Range"] = f"bytes={start}-{end if end is not None else ''}"
        response = self._core.raw("GET", url, headers=headers)
        return response.content

    def download_public_file(self, url: str) -> bytes:
        """Download from a public bucket or static directory (no auth)."""
        response = httpx.get(url)
        response.raise_for_status()
        return response.content

    # ------------------------------------------------------------------
    # Buckets
    # ------------------------------------------------------------------

    def create_bucket(
        self,
        *,
        label: str,
        root_path: str | None = None,
        public: bool | None = None,
        size: float | None = None,
        accepts: str | None = None,
    ) -> str:
        """Create a bucket and return its PID.

        ``accepts`` is a single comma-separated string, e.g.
        ``"custom:application/zip,audio/3gpp"``.
        """
        body = compact(
            label=label,
            root_path=root_path,
            public=public,
            size=size,
            accepts=accepts,
        )
        return self._core.request("POST", "/buckets", json=body)

    # ------------------------------------------------------------------
    # Permissions
    # ------------------------------------------------------------------

    def grant_permission(
        self,
        bucket_pid: str,
        *,
        path: str,
        grantee: str,
        grantee_type: str,
        permission: str,
    ) -> bool:
        """Grant a file-level permission."""
        body = compact(
            path=path,
            grantee=grantee,
            grantee_type=grantee_type,
            permission=permission,
        )
        result = self._core.request(
            "POST", f"/buckets/{bucket_pid}/permissions", json=body
        )
        return bool(result.get("granted")) if isinstance(result, dict) else bool(result)

    def revoke_permission(
        self,
        bucket_pid: str,
        *,
        path: str,
        grantee: str,
        grantee_type: str,
    ) -> bool:
        """Revoke a file-level permission."""
        body = compact(path=path, grantee=grantee, grantee_type=grantee_type)
        result = self._core.request(
            "DELETE", f"/buckets/{bucket_pid}/permissions", json=body
        )
        return bool(result.get("granted")) if isinstance(result, dict) else bool(result)

    def list_permissions(
        self,
        bucket_pid: str,
        path: str | None = None,
    ) -> list[dict[str, Any]]:
        """List permissions, optionally filtered by file path."""
        params = compact(path=path)
        return self._core.request(
            "GET", f"/buckets/{bucket_pid}/permissions", params=params
        )

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------

    def login(self, **credentials: Any) -> Any:
        """Authenticate against ``POST /auth/login``."""
        return self._core.request("POST", "/auth/login", json=credentials)
