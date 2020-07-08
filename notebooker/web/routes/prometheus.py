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


def setup_metrics(app):
    app.before_request(start_timer)
    # The order here matters since we want stop_timer
    # to be executed first
    app.after_request(record_request_data)
    app.after_request(stop_timer)


@prometheus_bp.route("/metrics")
def metrics():
    """ Default URL for prometheus metrics, as required by the prometheus collector. """
    response = make_response(generate_latest(REGISTRY), 200)
    response.headers[str("Content-type")] = CONTENT_TYPE_LATEST
    return response
