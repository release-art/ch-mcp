"""Permanent binary cache for Companies House document payloads.

Documents are immutable once filed — they never change for a given
``(document_id, content_type)``. This cache stores the raw bytes in Azure
Blob Storage so that expensive upstream fetches only happen once across
the server's lifetime. Intentionally not a key-value wrapper: we want to
round-trip raw ``bytes`` without the JSON/base64 layer that the
``key_value_aio`` stores impose.
"""

from __future__ import annotations

import logging
import urllib.parse

from azure.core.exceptions import ResourceNotFoundError
from azure.storage.blob import ContentSettings
from azure.storage.blob.aio import BlobServiceClient, ContainerClient

logger = logging.getLogger(__name__)


def _blob_key(document_id: str, content_type: str) -> str:
    """Form a safe blob name from a document id + MIME type.

    Blob names can contain '/' (they're displayed as pseudo-directories), so
    we namespace by ``document_id`` and slugify the content-type to avoid
    trouble with slashes inside MIME strings.
    """
    safe_content_type = urllib.parse.quote(content_type, safe="")
    return f"{document_id}/{safe_content_type}"


class DocumentBlobCache:
    """Read-through / write-through cache for binary document payloads."""

    _container_client: ContainerClient

    def __init__(self, container_client: ContainerClient) -> None:
        self._container_client = container_client

    @classmethod
    async def open(
        cls,
        blob_service_client: BlobServiceClient,
        container_name: str,
    ) -> "DocumentBlobCache":
        """Return an instance with the container created if necessary."""
        try:
            await blob_service_client.create_container(name=container_name, public_access=None)
        except Exception as exc:  # noqa: BLE001 — differentiate on attribute, not class
            if getattr(exc, "error_code", None) != "ContainerAlreadyExists":
                raise
        return cls(container_client=blob_service_client.get_container_client(container_name))

    async def get(self, document_id: str, content_type: str) -> bytes | None:
        """Return the cached bytes or ``None`` on miss."""
        blob = self._container_client.get_blob_client(_blob_key(document_id, content_type))
        try:
            downloader = await blob.download_blob()
        except ResourceNotFoundError:
            return None
        return await downloader.readall()

    async def put(self, document_id: str, content_type: str, data: bytes) -> None:
        """Write bytes under ``(document_id, content_type)``. Overwrites on conflict."""
        blob = self._container_client.get_blob_client(_blob_key(document_id, content_type))
        await blob.upload_blob(
            data,
            overwrite=True,
            content_settings=ContentSettings(content_type=content_type),
        )
