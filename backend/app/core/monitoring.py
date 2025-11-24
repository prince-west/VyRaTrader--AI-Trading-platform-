# backend/app/core/monitoring.py
from prometheus_client import Counter, Gauge, generate_latest, CONTENT_TYPE_LATEST
from prometheus_client import CollectorRegistry
from prometheus_client import multiprocess
from starlette.responses import Response
from starlette.applications import Starlette
from starlette.routing import Route
import sentry_sdk
from backend.app.core.config import settings

# Initialize Sentry if configured
if getattr(settings, "SENTRY_DSN", None):
    sentry_sdk.init(getattr(settings, "SENTRY_DSN"))

registry = CollectorRegistry()
trade_counter = Counter("vyra_trades_total", "Total trades executed", registry=registry)
exec_latency = Gauge("vyra_execution_latency_seconds", "Order execution latency", registry=registry)
current_equity = Gauge("vyra_current_equity", "Current equity snapshot", registry=registry)

async def _metrics(request):
    data = generate_latest(registry)
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)

metrics_app = Starlette(routes=[Route("/metrics", _metrics)])
