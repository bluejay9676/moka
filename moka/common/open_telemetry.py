import os

import environ
from grpc import ssl_channel_credentials
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.django import DjangoInstrumentor
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


def otel_init():
    env = environ.Env(
        HONEYCOMB_API_KEY=(str),
    )
    HONEYCOMB_API_KEY = env("HONEYCOMB_API_KEY")
    SYSTEM_ENV = env("SYSTEM_ENV", default="dev")
    HONEYCOMB_DATASET = f"moka-{SYSTEM_ENV}"

    print(f"otel initialization in process pid {os.getpid()}.")

    # resource describes app-level information that will be added to all spans
    resource = Resource(attributes={"service.name": f"moka-{SYSTEM_ENV}"})

    # create new trace provider with our resource
    trace_provider = TracerProvider(resource=resource)

    # create exporter to send spans to Honycomb
    otlp_exporter = OTLPSpanExporter(
        endpoint="api.honeycomb.io:443",
        insecure=False,
        credentials=ssl_channel_credentials(),
        headers=(
            ("x-honeycomb-team", HONEYCOMB_API_KEY),
            ("x-honeycomb-dataset", HONEYCOMB_DATASET),
        ),
    )

    # register exporter with provider
    trace_provider.add_span_processor(
        BatchSpanProcessor(otlp_exporter)
        #        BatchSpanProcessor(ConsoleSpanExporter())
    )

    # register trace provider
    trace.set_tracer_provider(trace_provider)

    DjangoInstrumentor().instrument()
    Psycopg2Instrumentor().instrument()
    RequestsInstrumentor().instrument()
