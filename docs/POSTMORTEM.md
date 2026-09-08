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

---

# Incident 2: Stale Chaos State After Distributed Restart (Real, Unplanned)

## Summary
- **Date:** 2026-09-08
- **Duration:** ~15 minutes of elevated error rate
- **Impact:** Error rate fluctuated between 0.5-1.5 errors/sec even after chaos mode was reset via the public endpoint
- **Severity:** Sev3 (self-discovered during dashboard validation, no customer impact)

## Timeline
| Time | Event |
|---|---|
| ~20:42 | Chaos mode reset via curl - confirmed "none" in response |
| ~20:50 | Dashboard still showed elevated error rate despite reset confirmation |
| ~20:53 | Investigated: deployment runs 2 replicas behind a LoadBalancer Service |
| ~20:55 | Hypothesis: chaos_mode stored in each pod's local Python memory, not shared state |
| ~20:58 | Ran kubectl rollout restart deployment/orders-api for guaranteed clean state |
| ~21:00 | New pods confirmed Running; chaos_mode: none verified via repeated curls |
| ~21:05 | Ran full load test - zero 500s across the entire run, confirming resolution |

## Root cause
Chaos-mode state lived in an in-process Python dict local to each pod's memory.
With 2 replicas behind one Service, a single reset request only affected
whichever pod received it via round-robin routing. The other replica kept
serving errors indefinitely.

## Detection
Dashboard showed persistently elevated error rate despite an apparently
successful reset - the mismatch was the signal something deeper was wrong.

## Resolution
kubectl rollout restart deployment/orders-api - forces all pods to restart
fresh, resetting in-memory state to the code default (mode=none) everywhere
simultaneously. Confirmed via a full 120-second load test showing 100% clean
200/404 responses with zero 500s.

## Impact
Elevated error rate for approximately 15 minutes while diagnosing, entirely
self-inflicted during a monitoring/drill exercise on a personal project.

## What went well
- Dashboard caught a real anomaly a single manual curl check would have missed
- Correctly reasoned from symptom to root cause without reading app code first
- Verified the fix properly with a full load test rather than a single spot-check

## What went poorly
- Application was designed with in-memory-only state, which breaks correctness
  across multiple replicas - a real anti-pattern

## Action items
| Action | Owner | Priority | Status |
|---|---|---|---|
| Move chaos_mode to shared store (Redis/ConfigMap) for true multi-replica correctness | you | P2 | Open |
| Add pod identity to /chaos response to make per-pod state visible | you | P3 | Open |
| Document lesson: never trust in-memory state to be consistent across replicas | you | P1 | Done |
