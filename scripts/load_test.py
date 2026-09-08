"""
Lightweight load generator for the Orders API - no external deps needed.
Use this to generate traffic so you have real data in Cloud Monitoring / Logging
for building dashboards and testing SLO alerts.

Usage:
  python load_test.py --url http://<EXTERNAL_IP or localhost:8080> --duration 60 --rps 5

For more serious load testing later, learn Locust or k6 - but this is enough
to populate metrics for your first dashboards.
"""
import argparse
import concurrent.futures
import random
import time
import urllib.request
import urllib.error

ENDPOINTS = [
    "/health",
    "/orders",
    "/orders?status=shipped",
    "/orders?region=PK",
    "/orders/1001",
    "/orders/9999",  # intentionally causes a 404 - useful for error-rate dashboards
    "/users",
    "/metrics",
]


def hit(base_url):
    path = random.choice(ENDPOINTS)
    url = base_url.rstrip("/") + path
    start = time.time()
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            status = resp.status
    except urllib.error.HTTPError as e:
        status = e.code
    except Exception as e:
        status = f"ERROR:{e}"
    elapsed = time.time() - start
    print(f"{time.strftime('%H:%M:%S')}  {path:<25} status={status}  latency={elapsed:.3f}s")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True, help="Base URL of the deployed service")
    parser.add_argument("--duration", type=int, default=60, help="Seconds to run")
    parser.add_argument("--rps", type=int, default=5, help="Approx requests per second")
    args = parser.parse_args()

    end_time = time.time() + args.duration
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.rps * 2) as executor:
        while time.time() < end_time:
            for _ in range(args.rps):
                executor.submit(hit, args.url)
            time.sleep(1)

    print("\nLoad test complete. Check Cloud Monitoring / Logging for the results.")


if __name__ == "__main__":
    main()
