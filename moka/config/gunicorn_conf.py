import os

import environ
from common.open_telemetry import otel_init

accesslog = "-"

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")


def post_fork(server, worker):
    env = environ.Env()
    SYSTEM_ENV = env("SYSTEM_ENV", default="dev")
    if SYSTEM_ENV == "dev":
        print("Skip initiating open_telemetry in dev")
        pass
    else:
        print("Initiating open_telemetry")
        otel_init()
