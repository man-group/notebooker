import socket
import time

from flask import Blueprint, make_response, request
from prometheus_client import CONTENT_TYPE_LATEST, REGISTRY, Counter, Histogram, generate_latest

from notebooker.utils.caching import get_cache

REQUEST_LATENCY = Histogram(
    "notebooker_request_latency_seconds",
    "Flask request latency",
    registry=REGISTRY,
    labelnames=["env", "path", "hostname"],
)
REQUEST_COUNT = Counter(
    "notebooker_request_count",
    "Flask request count",
    registry=REGISTRY,
    labelnames=["env", "method", "path", "http_status", "hostname"],
)
N_SUCCESSFUL_REPORTS = Counter(
    "notebooker_n_successful_reports",
    "Number of successful runs in the current session for the report",
    registry=REGISTRY,
    labelnames=["report_name", "report_title"],
)
N_FAILED_REPORTS = Counter(
    "notebooker_n_failed_reports",
    "Number of failed runs in the current session for the report",
    registry=REGISTRY,
    labelnames=["report_name", "report_title"],
)

prometheus_bp = Blueprint("prometheus", __name__)


def start_timer():
    request.start_time = time.time()


def stop_timer(response):
    resp_time = time.time() - request.start_time
    env = get_cache("env")
    REQUEST_LATENCY.labels(env, request.path, socket.gethostname()).observe(resp_time)
    return response


def record_request_data(response):
    env = get_cache("env")
    REQUEST_COUNT.labels(env, request.method, request.path, response.status_code, socket.gethostname()).inc()
    return response


def record_successful_report(report_name, report_title):
    N_SUCCESSFUL_REPORTS.labels(report_name, report_title).inc()
    # Increment by zero because this will make using increase() in Prometheus possible.
    N_FAILED_REPORTS.labels(report_name, report_title).inc(0)


def record_failed_report(report_name, report_title):
    N_FAILED_REPORTS.labels(report_name, report_title).inc()
    # Increment by zero because this will make using increase() in Prometheus possible.
    # This means that we can easily detect reports that have failed,
    # as long as they have either succeeded once or failed more than once.
    # https://github.com/prometheus/prometheus/issues/1673
    N_SUCCESSFUL_REPORTS.labels(report_name, report_title).inc(0)


def setup_metrics(app):
    app.before_request(start_timer)
    # The order here matters since we want stop_timer
    # to be executed first
    app.after_request(record_request_data)
    app.after_request(stop_timer)


@prometheus_bp.route("/metrics")
def metrics():
    """Default URL for prometheus metrics, as required by the prometheus collector."""
    response = make_response(generate_latest(REGISTRY), 200)
    response.headers[str("Content-type")] = CONTENT_TYPE_LATEST
    return response
