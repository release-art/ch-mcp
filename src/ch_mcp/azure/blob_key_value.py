"""Azure Blob Storage key-value store backend for py-key-value-aio."""

from __future__ import annotations

from typing import Any

from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError
from azure.storage.blob.aio import BlobServiceClient, ContainerClient
from key_value.aio._utils.managed_entry import ManagedEntry
from key_value.aio._utils.sanitization import SanitizationStrategy
from key_value.aio._utils.sanitize import hash_excess_length
from key_value.aio.stores.base import (
    BaseContextManagerStore,
    BaseEnumerateKeysStore,
    BaseStore,
)
from typing_extensions import override

# Azure Blob name max is 1024 chars. Reserve space for the '/' separator.
MAX_COLLECTION_LENGTH = 500
MAX_KEY_LENGTH = 500


class BlobKeySanitizationStrategy(SanitizationStrategy):
    """Sanitization strategy for Azure Blob key names.

    Azure Blob Storage has a maximum blob name length of 1024 characters.
    This strategy hashes keys that exceed the specified limit.
    """

    def __init__(self, max_length: int = MAX_KEY_LENGTH) -> None:
        self.max_length = max_length

    def sanitize(self, value: str) -> str:
        return hash_excess_length(value, self.max_length, length_is_bytes=False)

    def validate(self, value: str) -> None:
        pass


class BlobCollectionSanitizationStrategy(BlobKeySanitizationStrategy):
    """Sanitization strategy for Azure Blob collection names (blob path prefixes)."""

    def __init__(self, max_length: int = MAX_COLLECTION_LENGTH) -> None:
        super().__init__(max_length=max_length)


class AzureBlobStore(BaseContextManagerStore, BaseEnumerateKeysStore, BaseStore):
    """Azure Blob Storage key-value store.

    Stores key-value pairs as individual blobs in an Azure Storage container.
    Each entry is stored at the path ``{collection}/{key}`` with the ManagedEntry
    serialized to JSON as the blob body. TTL metadata is stored in blob metadata
    and checked client-side during retrieval.

    Example:
        With a connection string (client created and managed by the store)::

            async with AzureBlobStore(
                connection_string="DefaultEndpointsProtocol=https;...",
                container_name="my-kv-store",
            ) as store:
                await store.put(key="user:123", value={"name": "Alice"}, ttl=3600)
                user = await store.get(key="user:123")

        With an existing ContainerClient (caller manages client lifecycle)::

            async with ContainerClient.from_connection_string(conn_str, "my-container") as cc:
                async with AzureBlobStore(client=cc, container_name="my-container") as store:
                    await store.put(key="config", value={"setting": "value"})
    """

    _container_name: str
    _client: ContainerClient | None
    _blob_service_client: BlobServiceClient

    def __init__(
        self,
        *,
        client: BlobServiceClient,
        container_name: str,
        default_collection: str | None = None,
        collection_sanitization_strategy: SanitizationStrategy | None = None,
        key_sanitization_strategy: SanitizationStrategy | None = None,
    ) -> None:
        self._container_name = container_name
        assert isinstance(client, BlobServiceClient), (
            f"client must be an instance of BlobServiceClient, got {type(client)}"
        )
        self._blob_service_client = client
        self._client = self._blob_service_client.get_container_client(container_name)

        super().__init__(
            default_collection=default_collection,
            collection_sanitization_strategy=collection_sanitization_strategy,
            key_sanitization_strategy=key_sanitization_strategy,
            client_provided_by_user=True,
        )

    @property
    def _connected_client(self) -> ContainerClient:
        if not self._client:
            msg = "Client not connected. Use the store as an async context manager."
            raise ValueError(msg)
        return self._client

    @override
    async def _setup(self) -> None:
        if not self._client_provided_by_user:
            raise NotImplementedError(
                "Automatic client management is not implemented. Please provide a connected ContainerClient."
            )

        try:
            await self._blob_service_client.create_container(name=self._container_name, public_access=None)
        except ResourceExistsError:
            pass

    def _blob_path(self, *, collection: str, key: str) -> str:
        sanitized_collection, sanitized_key = self._sanitize_collection_and_key(collection=collection, key=key)
        return f"{sanitized_collection}/{sanitized_key}"

    @override
    async def _get_managed_entry(self, *, key: str, collection: str) -> ManagedEntry | None:
        blob_name = self._blob_path(collection=collection, key=key)
        try:
            download = await self._connected_client.download_blob(blob_name)
            body_bytes: bytes = await download.readall()
        except ResourceNotFoundError:
            return None

        json_value = body_bytes.decode("utf-8")
        managed_entry = self._serialization_adapter.load_json(json_str=json_value)

        if managed_entry.is_expired:
            await self._delete_blob_quiet(blob_name)
            return None
        return managed_entry

    @override
    async def _put_managed_entry(self, *, key: str, collection: str, managed_entry: ManagedEntry) -> None:
        blob_name = self._blob_path(collection=collection, key=key)
        json_value = self._serialization_adapter.dump_json(entry=managed_entry)

        metadata: dict[str, str] = {}
        if managed_entry.expires_at:
            metadata["expires_at"] = managed_entry.expires_at.isoformat()
        if managed_entry.created_at:
            metadata["created_at"] = managed_entry.created_at.isoformat()

        await self._connected_client.upload_blob(
            name=blob_name,
            data=json_value.encode("utf-8"),
            metadata=metadata or None,
            overwrite=True,
        )

    @override
    async def _delete_managed_entry(self, *, key: str, collection: str) -> bool:
        blob_name = self._blob_path(collection=collection, key=key)
        try:
            await self._connected_client.delete_blob(blob_name)
        except ResourceNotFoundError:
            return False
        return True

    @override
    async def _get_collection_keys(self, *, collection: str, limit: int | None = None) -> list[str]:
        sanitized_collection = self._sanitize_collection(collection=collection)
        prefix = f"{sanitized_collection}/"
        keys: list[str] = []
        async for blob in self._connected_client.list_blobs(name_starts_with=prefix):
            name: Any = blob.name
            if isinstance(name, str) and name.startswith(prefix):
                keys.append(name[len(prefix) :])
                if limit is not None and len(keys) >= limit:
                    break
        return keys

    async def _delete_blob_quiet(self, blob_name: str) -> None:
        try:
            await self._connected_client.delete_blob(blob_name)
        except ResourceNotFoundError:
            pass
