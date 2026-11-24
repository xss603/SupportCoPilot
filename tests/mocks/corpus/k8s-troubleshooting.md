# Kubernetes Pod CrashLoopBackOff and OOMKilled Runbook

When Kubernetes pods repeatedly restart with `CrashLoopBackOff` or exit code `137` (`OOMKilled`), inspect pod events, container termination reasons, and memory resource limits.

## Diagnosing OOMKilled Exit Code 137

Exit code `137` indicates the Linux kernel cgroup OOM killer terminated the container because working-set memory exceeded `resources.limits.memory`.

```bash
kubectl describe pod -n <namespace> <pod-name>
kubectl top pods -n <namespace> --containers
kubectl get events -n <namespace> --sort-by=.lastTimestamp
```

## Readiness and Liveness Probe Tuning

Slow-starting workers often fail initial liveness probes; configure `startupProbe` or raise `initialDelaySeconds` before escalating node sizing.
