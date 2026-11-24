# Runbook: 502 Bad Gateway via Ingress & Istio Service Mesh

## Description
Occurs when an ingress gateway or upstream service cannot establish a TCP connection or mutual TLS handshake with a backend microservice pod.

## Common Root Causes:
1. **mTLS Strict Mode Mismatch:**
   - The namespace has `PeerAuthentication` set to `STRICT`, but the calling client does not have a `DestinationRule` with `ISTIO_MUTUAL` mode enabled.
2. **Readiness Probe Failure:**
   - Pod is crashing or taking too long to start, returning `delayed connect error: 111` (Connection Refused).
3. **Port Number Mismatch:**
   - Service `targetPort` does not match the port exposed by the application container.

## Standard Diagnostic Commands:
```bash
# Check pod logs
kubectl logs -n <namespace> -l app=<service-name> -c <service-name> --tail=100

# Inspect DestinationRule
kubectl get destinationrule -n <namespace> -o yaml

# Inspect PeerAuthentication policy
kubectl get peerauthentication -n <namespace>
```

## Remediation:
- If a `DestinationRule` is missing or in `DISABLE` mode, apply the standard mTLS rule:
```yaml
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: <service-name>-mtls
spec:
  host: <service-name>.<namespace>.svc.cluster.local
  trafficPolicy:
    tls:
      mode: ISTIO_MUTUAL
```
- No administrative platform request needed if the developer owns the repository helm chart.
