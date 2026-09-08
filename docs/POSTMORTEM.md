# Postmortem Template (blameless)

Fill this out after running `scripts/simulate_incident.py`, using real timestamps
from your terminal output and real screenshots/queries from Cloud Monitoring/Logging.

## Summary
- **Date:**
- **Duration:**
- **Impact:** (e.g., X% of requests failed / elevated latency for N minutes)
- **Severity:** Sev1 / Sev2 / Sev3

## Timeline (all times UTC)
| Time | Event |
|---|---|
| | Chaos mode enabled (incident starts) |
| | First alert fired / anomaly noticed |
| | Root cause identified |
| | Mitigation applied |
| | Service fully recovered |

## Root cause
What actually happened, in plain language.

## Detection
How was this noticed? (alert, dashboard, user report?) How long did detection take
from incident start? Could it have been detected faster?

## Resolution
What action actually fixed it?

## Impact
Quantify it: requests affected, error rate, users impacted, SLO/error-budget burn.

## What went well

## What went poorly

## Action items
| Action | Owner | Priority | Status |
|---|---|---|---|
| | | | |

---

# Worked Example (using the dummy Orders API incident)

## Summary
- **Date:** 2026-08-14
- **Duration:** 8 minutes (14:02–14:10 UTC)
- **Impact:** ~40% of requests to `/orders` and `/orders/<id>` returned HTTP 500.
- **Severity:** Sev2 (partial outage, core read path affected)

## Timeline (UTC)
| Time | Event |
|---|---|
| 14:02 | `simulate_incident.py --mode error` triggered chaos mode on orders-api |
| 14:04 | Cloud Monitoring alert fired: 5xx rate exceeded 5% threshold over 5-minute window |
| 14:05 | On-call checked `/chaos` endpoint, confirmed error mode was active |
| 14:06 | Reviewed Cloud Logging filter `severity=ERROR` and saw "Simulated failure for SRE drill" stack traces |
| 14:07 | Root cause confirmed: chaos mode left enabled from a testing script |
| 14:08 | Ran `curl ".../chaos?mode=none"` to disable chaos mode |
| 14:10 | Error rate returned to baseline (0%); incident closed |

## Root cause
A testing script (`simulate_incident.py`) enabled a fault-injection mode on the
service that randomly threw 500 errors for ~40% of `/orders` requests. This was
intentional for the drill, standing in for a real bad deploy or dependency failure.

## Detection
Detected via a Cloud Monitoring alert policy on 5xx rate, 2 minutes after
incident start. This met the target of "detect within 5 minutes" for this SLO tier.

## Resolution
Disabled the fault-injection mode via the `/chaos` endpoint. In a real incident,
this step would instead be "rolled back bad deploy" or "failed over to healthy replica."

## Impact
- Error rate peaked at ~40% for 8 minutes.
- Estimated error-budget burn: at a 99.5% monthly SLO, an 8-minute full-severity
  outage burns roughly 3-4% of the entire month's error budget in a single incident —
  which is why fast detection matters.

## What went well
- Alert fired quickly (2 min) and pointed directly at the right service.
- Runbook step for checking `/chaos` state resolved it immediately.

## What went poorly
- No automatic safeguard preventing chaos mode from being left on accidentally.
- No Slack/PagerDuty integration yet — alert was only visible in the console.

## Action items
| Action | Owner | Priority | Status |
|---|---|---|---|
| Add auto-expiry to `/chaos` mode (e.g., reset after 5 min) | you | P2 | Open |
| Wire Cloud Monitoring alert to Slack webhook | you | P1 | Open |
| Add this scenario to onboarding runbook | you | P3 | Open |
