# Istio Ingress 502 Bad Gateway Troubleshooting

A 502 Bad Gateway error through the Istio Ingress Gateway occurs when Envoy cannot complete a TCP connection or mutual TLS handshake with the upstream Kubernetes pod.

## Root Cause 1: mTLS Strict Mode Mismatch

When a namespace enforces `PeerAuthentication` with mode `STRICT`, every calling workload or gateway must present a valid SPIFFE mTLS certificate via a matching `DestinationRule` configured with `ISTIO_MUTUAL` TLS mode.

```bash
kubectl get peerauthentication -n <namespace> -o yaml
kubectl get destinationrule -n <namespace> -o yaml
```

## Root Cause 2: Readiness Probe and Connection Refused

If Envoy reports `delayed connect error: 111` (Connection Refused), verify that the pod container is passing readiness probes and listening on the exact Service `targetPort`.

```bash
kubectl logs -n <namespace> -l app=<service-name> -c istio-proxy --tail=100
kubectl get endpoints -n <namespace> <service-name>
```
