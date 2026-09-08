"""
Incident simulator - triggers the app's /chaos endpoint to create a realistic
degradation, then times how long you take to detect and resolve it.

Usage:
  python simulate_incident.py --url http://<EXTERNAL_IP> --mode error --duration 120

Suggested drill:
  1. Run this in one terminal.
  2. In another terminal, run load_test.py against the same URL.
  3. Watch Cloud Monitoring dashboards / logs to detect the issue.
  4. Manually call /chaos?mode=none to "resolve" it once you've noticed.
  5. Write up docs/POSTMORTEM.md using the real timestamps from this run.
"""
import argparse
import time
import urllib.request


def set_mode(base_url, mode):
    url = f"{base_url.rstrip('/')}/chaos?mode={mode}"
    with urllib.request.urlopen(url, timeout=10) as resp:
        print(f"[{time.strftime('%H:%M:%S')}] Set chaos mode to '{mode}' -> {resp.read().decode()}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--mode", choices=["latency", "error"], default="error")
    parser.add_argument("--duration", type=int, default=120, help="Seconds before auto-resolving")
    args = parser.parse_args()

    print(f"=== INCIDENT START: {time.strftime('%Y-%m-%d %H:%M:%S')} ===")
    set_mode(args.url, args.mode)
    print(f"Incident will auto-resolve in {args.duration}s. Go find it in your dashboards!")
    time.sleep(args.duration)
    set_mode(args.url, "none")
    print(f"=== INCIDENT RESOLVED: {time.strftime('%Y-%m-%d %H:%M:%S')} ===")
    print("Now fill out docs/POSTMORTEM.md with the real start/end times above.")


if __name__ == "__main__":
    main()
