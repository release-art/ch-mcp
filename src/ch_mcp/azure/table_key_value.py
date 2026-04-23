"""Azure Table Storage key-value store backend for py-key-value-aio."""

from __future__ import annotations

from typing import Any

from azure.core.exceptions import HttpResponseError, ResourceNotFoundError
from azure.data.tables import UpdateMode
from azure.data.tables.aio import TableClient, TableServiceClient
from key_value.aio._utils.managed_entry import ManagedEntry
from key_value.aio._utils.sanitization import AlwaysHashStrategy
from key_value.aio.stores.base import BaseContextManagerStore, BaseEnumerateKeysStore, BaseStore
from typing_extensions import override

# Azure Table Storage limits each string property to 32K UTF-16 characters
# (64KB). Entities can hold up to ~1MB across ~252 user properties, so
# splitting the serialised JSON across several ``v0``, ``v1``, … columns
# lets us cache values well above the per-property cap while staying within
# the per-entity budget.
_CHUNK_CHARS = 30000
_VALUE_CHUNK_PREFIX = "value_chunk_"
_VALUE_CHUNK_COUNT = "n_chunks"


class AzureTableStore(BaseContextManagerStore, BaseEnumerateKeysStore, BaseStore):
    """Azure Table Storage key-value store.

    Stores entries as table entities with PartitionKey=collection and RowKey=hashed_key.
    The serialised ManagedEntry JSON is split into ``_CHUNK_CHARS``-sized
    segments and written to ``value_chunk_0``, ``value_chunk_1``, … properties with the segment
    count in ``n_chunks``. TTL is enforced client-side on retrieval; Azure Table
    Storage has no native per-entity TTL.

    The TableServiceClient lifecycle is managed externally (via AzureAPI.lifespan()).
    Table creation is lazy — it happens on first use via BaseStore.setup(), not at construction.
    """

    _table_name: str
    _table_service_client: TableServiceClient
    _table_client: TableClient | None

    def __init__(
        self,
        *,
        client: TableServiceClient,
        table_name: str,
    ) -> None:
        self._table_name = table_name
        self._table_service_client = client
        self._table_client = None

        # Azure Table forbids /, \, #, ? and control chars in both PartitionKey and RowKey.
        # Hash both collection and key unconditionally — the caller (ResponseCachingMiddleware)
        # uses collection names like "tools/call" which contain forbidden slashes.
        super().__init__(
            key_sanitization_strategy=AlwaysHashStrategy(hash_length=64),
            collection_sanitization_strategy=AlwaysHashStrategy(hash_length=32),
            stable_api=True,
        )

    @property
    def _connected_client(self) -> TableClient:
        if self._table_client is None:
            raise RuntimeError("Store not initialized. Use as an async context manager or call setup() first.")
        return self._table_client

    @override
    async def _setup(self) -> None:
        self._table_client = self._table_service_client.get_table_client(self._table_name)
        try:
            await self._table_service_client.create_table(self._table_name)
        except HttpResponseError as e:
            if e.error_code != "TableAlreadyExists":  # type: ignore[attr-defined]
                raise

    async def _close(self) -> None:
        pass  # TableServiceClient lifecycle is managed externally by AzureAPI

    @staticmethod
    def _split_value(json_value: str) -> dict[str, Any]:
        """Split a JSON payload into per-property chunks plus a chunk count."""
        if not json_value:
            return {_VALUE_CHUNK_COUNT: 0}
        chunks = [json_value[i : i + _CHUNK_CHARS] for i in range(0, len(json_value), _CHUNK_CHARS)]
        payload: dict[str, Any] = {_VALUE_CHUNK_COUNT: len(chunks)}
        for i, chunk in enumerate(chunks):
            payload[f"{_VALUE_CHUNK_PREFIX}{i}"] = chunk
        return payload

    @staticmethod
    def _join_value(entity: dict[str, Any]) -> str | None:
        """Reassemble the JSON payload from an entity's chunked properties.

        Returns ``None`` when the entity has no chunked payload.
        """
        count = entity.get(_VALUE_CHUNK_COUNT)
        if not isinstance(count, int) or count <= 0:
            return None
        parts: list[str] = []
        for i in range(count):
            chunk = entity.get(f"{_VALUE_CHUNK_PREFIX}{i}")
            if not isinstance(chunk, str):
                return None
            parts.append(chunk)
        return "".join(parts)

    @override
    async def _get_managed_entry(self, *, collection: str, key: str) -> ManagedEntry | None:
        sanitized_collection, sanitized_key = self._sanitize_collection_and_key(collection=collection, key=key)
        try:
            entity = await self._connected_client.get_entity(
                partition_key=sanitized_collection,
                row_key=sanitized_key,
            )
        except ResourceNotFoundError:
            return None

        json_value = self._join_value(dict(entity))
        if not json_value:
            return None

        managed_entry = self._serialization_adapter.load_json(json_str=json_value)

        if managed_entry.is_expired:
            await self._delete_entity_quiet(sanitized_collection, sanitized_key)
            return None

        return managed_entry

    @override
    async def _put_managed_entry(self, *, collection: str, key: str, managed_entry: ManagedEntry) -> None:
        sanitized_collection, sanitized_key = self._sanitize_collection_and_key(collection=collection, key=key)
        json_value = self._serialization_adapter.dump_json(entry=managed_entry)

        entity: dict[str, Any] = {
            "PartitionKey": sanitized_collection,
            "RowKey": sanitized_key,
            **self._split_value(json_value),
        }

        await self._connected_client.upsert_entity(entity=entity, mode=UpdateMode.REPLACE)

    @override
    async def _delete_managed_entry(self, *, collection: str, key: str) -> bool:
        sanitized_collection, sanitized_key = self._sanitize_collection_and_key(collection=collection, key=key)
        try:
            await self._connected_client.delete_entity(
                partition_key=sanitized_collection,
                row_key=sanitized_key,
            )
        except ResourceNotFoundError:
            return False
        return True

    @override
    async def _get_collection_keys(self, *, collection: str, limit: int | None = None) -> list[str]:
        sanitized_collection = self._sanitize_collection(collection=collection)
        keys: list[str] = []
        async for entity in self._connected_client.query_entities(
            query_filter=f"PartitionKey eq '{sanitized_collection}'",
        ):
            keys.append(str(entity["RowKey"]))
            if limit is not None and len(keys) >= limit:
                break
        return keys

    async def _delete_entity_quiet(self, partition_key: str, row_key: str) -> None:
        try:
            await self._connected_client.delete_entity(partition_key=partition_key, row_key=row_key)
        except ResourceNotFoundError:
            pass
