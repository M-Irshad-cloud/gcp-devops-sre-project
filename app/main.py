"""
Orders API - a small microservice for GCP DevOps/SRE practice.

Endpoints:
  GET  /health              -> liveness/readiness probe target
  GET  /orders               -> list all orders (supports ?status=, ?region=)
  GET  /orders/<id>          -> single order
  GET  /users                -> list all users
  GET  /users/<id>            -> single user
  POST /orders                -> create a new order (in-memory only)
  GET  /chaos?mode=latency|error|none  -> toggle simulated failure for SRE drills
  GET  /metrics               -> basic Prometheus-style counters (for Cloud Monitoring/GMP scraping)

Run locally:
  pip install flask --break-system-packages
  python main.py

Environment variables:
  PORT (default 8080)
"""
import json
import os
import random
import time
from flask import Flask, jsonify, request

app = Flask(__name__)

DATA_PATH = os.path.join(os.path.dirname(__file__), "dummy_data.json")
with open(DATA_PATH) as f:
    DATA = json.load(f)

# In-memory metrics counters (simple stand-in for a real metrics library)
METRICS = {
    "requests_total": 0,
    "errors_total": 0,
    "latency_seconds_sum": 0.0,
}

# Chaos mode lets you simulate incidents for SRE / postmortem practice
CHAOS_MODE = {"mode": "none"}  # none | latency | error


@app.before_request
def before():
    request.start_time = time.time()


@app.after_request
def after(response):
    METRICS["requests_total"] += 1
    METRICS["latency_seconds_sum"] += time.time() - request.start_time
    if response.status_code >= 500:
        METRICS["errors_total"] += 1
    return response


@app.route("/health")
def health():
    return jsonify({"status": "ok"}), 200


@app.route("/orders")
def list_orders():
    _maybe_inject_chaos()
    orders = DATA["orders"]
    status = request.args.get("status")
    region = request.args.get("region")
    if status:
        orders = [o for o in orders if o["status"] == status]
    if region:
        orders = [o for o in orders if o["region"] == region]
    return jsonify(orders)


@app.route("/orders/<int:order_id>")
def get_order(order_id):
    _maybe_inject_chaos()
    order = next((o for o in DATA["orders"] if o["id"] == order_id), None)
    if not order:
        return jsonify({"error": "not found"}), 404
    return jsonify(order)


@app.route("/orders", methods=["POST"])
def create_order():
    new_order = request.get_json(force=True)
    new_order["id"] = max(o["id"] for o in DATA["orders"]) + 1
    DATA["orders"].append(new_order)
    return jsonify(new_order), 201


@app.route("/users")
def list_users():
    return jsonify(DATA["users"])


@app.route("/users/<int:user_id>")
def get_user(user_id):
    user = next((u for u in DATA["users"] if u["id"] == user_id), None)
    if not user:
        return jsonify({"error": "not found"}), 404
    return jsonify(user)


@app.route("/chaos", methods=["GET", "POST"])
def chaos():
    """Toggle simulated failure modes for incident-response drills."""
    mode = request.args.get("mode")
    if mode in ("none", "latency", "error"):
        CHAOS_MODE["mode"] = mode
    return jsonify({"chaos_mode": CHAOS_MODE["mode"]})


@app.route("/metrics")
def metrics():
    avg_latency = (
        METRICS["latency_seconds_sum"] / METRICS["requests_total"]
        if METRICS["requests_total"] else 0
    )
    body = (
        f"# HELP orders_requests_total Total requests served\n"
        f"# TYPE orders_requests_total counter\n"
        f"orders_requests_total {METRICS['requests_total']}\n"
        f"# HELP orders_errors_total Total 5xx responses\n"
        f"# TYPE orders_errors_total counter\n"
        f"orders_errors_total {METRICS['errors_total']}\n"
        f"# HELP orders_latency_seconds_avg Average request latency\n"
        f"# TYPE orders_latency_seconds_avg gauge\n"
        f"orders_latency_seconds_avg {avg_latency:.4f}\n"
    )
    return body, 200, {"Content-Type": "text/plain"}


def _maybe_inject_chaos():
    mode = CHAOS_MODE["mode"]
    if mode == "latency":
        time.sleep(random.uniform(1.5, 3.5))
    elif mode == "error":
        if random.random() < 0.4:
            raise RuntimeError("Simulated failure for SRE drill")


@app.errorhandler(Exception)
def handle_error(e):
    return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
