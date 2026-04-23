"""Factory for Azure Storage clients (blob, queue, table) driven by ``AzureSettings``."""

import contextlib
import logging

import azure.data.tables.aio as azure_tables_aio
import azure.storage.blob.aio as azure_blob_aio
import azure.storage.queue.aio as azure_queue_aio
from azure.identity.aio import DefaultAzureCredential

import ch_mcp

from .. import settings as app_settings_module

logger = logging.getLogger(__name__)


class AzureAPI:
    """Holds blob/queue/table service clients built from ``AzureSettings``.

    With ``credential="none"`` (e.g. Azurite), every client is built from
    ``storage_connection_string``. With ``credential="default"``, endpoints
    are derived from ``storage_account`` (or the explicit ``*_endpoint``
    overrides) and authenticated via ``DefaultAzureCredential``.
    """

    settings: app_settings_module.AzureSettings
    queue_service_client: azure_queue_aio.QueueServiceClient
    blob_service_client: azure_blob_aio.BlobServiceClient
    table_service_client: azure_tables_aio.TableServiceClient

    def __init__(self, settings: app_settings_module.AzureSettings) -> None:
        self.settings = settings
        # When using connection string with AccountKey (Azurite), don't pass credential
        # When using DefaultAzureCredential (production), construct from account URLs
        if self.settings.credential == ch_mcp.settings.AzureCredentialType.NONE:
            if not self.settings.storage_connection_string:
                raise ValueError("storage_connection_string is required when credential is NONE")
            self.queue_service_client = azure_queue_aio.QueueServiceClient.from_connection_string(
                conn_str=self.settings.storage_connection_string,
            )
            self.blob_service_client = azure_blob_aio.BlobServiceClient.from_connection_string(
                conn_str=self.settings.storage_connection_string,
            )
            self.table_service_client = azure_tables_aio.TableServiceClient.from_connection_string(
                conn_str=self.settings.storage_connection_string,
            )
        elif self.settings.credential == ch_mcp.settings.AzureCredentialType.DEFAULT:
            if not self.settings.storage_account:
                raise ValueError("storage_account is required when credential is DEFAULT")
            credential = DefaultAzureCredential()
            # Construct endpoint URLs from account name or use provided endpoints
            blob_url = (
                self.settings.storage_blob_endpoint or f"https://{self.settings.storage_account}.blob.core.windows.net"
            )
            queue_url = (
                self.settings.storage_queue_endpoint
                or f"https://{self.settings.storage_account}.queue.core.windows.net"
            )
            table_url = (
                self.settings.storage_table_endpoint
                or f"https://{self.settings.storage_account}.table.core.windows.net"
            )

            self.queue_service_client = azure_queue_aio.QueueServiceClient(
                account_url=queue_url,
                credential=credential,
            )
            self.blob_service_client = azure_blob_aio.BlobServiceClient(
                account_url=blob_url,
                credential=credential,
            )
            self.table_service_client = azure_tables_aio.TableServiceClient(
                endpoint=table_url,
                credential=credential,
            )
        else:
            raise ValueError(f"Unsupported Azure credential type: {self.settings.credential}")

    @contextlib.asynccontextmanager
    async def lifespan(self):
        """Lifespan context manager for Azure API."""
        logger.info("Starting Azure API lifespan...")
        try:
            async with self.queue_service_client, self.blob_service_client, self.table_service_client:
                logger.info("Connected to Azure Services.")
                yield
                logger.debug("Azure API operations completed successfully.")
        finally:
            logger.info("Azure API lifespan ended.")

    async def get_queue(self, queue_name: str) -> azure_queue_aio.QueueClient:
        """Get a QueueClient for the specified queue."""
        return self.queue_service_client.get_queue_client(queue=queue_name)

    async def get_blob_container(self, container_name: str) -> azure_blob_aio.ContainerClient:
        """Get a ContainerClient for the specified blob container."""
        return self.blob_service_client.get_container_client(container=container_name)

    def get_table(self, table_name: str) -> azure_tables_aio.TableClient:
        """Get a TableClient for the specified table."""
        return self.table_service_client.get_table_client(table_name)
