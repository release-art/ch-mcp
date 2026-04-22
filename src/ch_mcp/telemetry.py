from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)


def configure() -> None:
    """Configure OpenTelemetry tracing and log correlation.

    No-op if OTEL_EXPORTER_OTLP_ENDPOINT is not set, so local dev works
    without any OTel infrastructure.
    """
    if not os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT"):
        logger.debug("OTEL_EXPORTER_OTLP_ENDPOINT not set — skipping OpenTelemetry setup")
        return

    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
    from opentelemetry.instrumentation.logging import LoggingInstrumentor
    from opentelemetry.instrumentation.starlette import StarletteInstrumentor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    import ch_mcp.__version__ as _v

    resource = Resource(
        attributes={
            "service.name": os.environ.get("OTEL_SERVICE_NAME", "ch-mcp"),
            "service.version": _v.__version__,
        }
    )

    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(provider)

    StarletteInstrumentor().instrument()
    HTTPXClientInstrumentor().instrument()
    LoggingInstrumentor().instrument(set_logging_format=True)

    logger.info("OpenTelemetry configured (endpoint: %s)", os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"])
