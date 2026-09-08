# Runbook: orders-api

## Service overview
- **What it does:** Serves order and user data via REST API (dummy e-commerce backend).
- **Where it runs:** GKE Autopilot cluster `devops-sre-cluster`, namespace `default`.
- **Owner:** [your name]
- **SLO:** 99.5% of requests return non-5xx within 500ms, measured over a rolling 30-day window.

## Health checks
| Check | Command |
|---|---|
| Pods running | `kubectl get pods -l app=orders-api` |
| Recent logs | `kubectl logs -l app=orders-api --tail=100` |
| Service reachable | `curl http://<EXTERNAL_IP>/health` |
| Current chaos mode | `curl http://<EXTERNAL_IP>/chaos` |
| Metrics snapshot | `curl http://<EXTERNAL_IP>/metrics` |

## Common alerts and responses

### Alert: High error rate (5xx > 5% over 5 min)
1. Check current chaos mode isn't accidentally left on: `curl .../chaos`. If not `none`, reset it: `curl ".../chaos?mode=none"`.
2. Check pod status and recent restarts: `kubectl get pods -l app=orders-api -o wide`.
3. Check logs for stack traces: `kubectl logs -l app=orders-api --tail=200`.
4. If a bad deploy is suspected, roll back: `kubectl rollout undo deployment/orders-api`.
5. If unresolved in 15 minutes, escalate.

### Alert: High latency (p95 > 1s over 5 min)
1. Check HPA status — are we under-scaled? `kubectl get hpa orders-api-hpa`.
2. Check node/pod resource usage: `kubectl top pods -l app=orders-api`.
3. If CPU-bound, consider manually bumping `maxReplicas` in the HPA as a stopgap.
4. Check for a stuck chaos-mode latency injection (see error-rate steps above).

### Alert: Pod crash-looping
1. `kubectl describe pod <pod-name>` to see the reason (OOMKilled, failed probe, etc.).
2. `kubectl logs <pod-name> --previous` to see logs from before the crash.
3. If OOMKilled, check if resource limits in `k8s/deployment.yaml` need raising.

## Rollback procedure
```
kubectl rollout history deployment/orders-api
kubectl rollout undo deployment/orders-api            # to previous revision
kubectl rollout undo deployment/orders-api --to-revision=<N>  # to specific revision
```

## Escalation
- [Define your own escalation path here — e.g., Slack channel, PagerDuty, email]

## Useful links
- Cloud Monitoring dashboard: [link]
- Cloud Logging query for this service: `resource.type="k8s_container" AND resource.labels.container_name="orders-api"`
- Source repo: [link]
