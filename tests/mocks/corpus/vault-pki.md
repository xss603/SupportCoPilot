# HashiCorp Vault PKI TLS Certificate Lifecycle

Internal x509 TLS certificates for platform services are issued and rotated automatically through the corporate HashiCorp Vault PKI secrets engine and Kubernetes Vault Agent Injector.

## Diagnosing Expired TLS Certificates

Inspect the mounted certificate `enddate` inside the workload container and review the `vault-agent-init` sidecar logs to confirm whether the Vault Kubernetes auth token lease expired.

```bash
openssl x509 -in /etc/ssl/certs/tls.crt -noout -enddate
kubectl logs -n <namespace> <pod-name> -c vault-agent-init --tail=100
```

## Custom Domain SAN Authorization

If a service requires a new custom domain Subject Alternative Name or wildcard certificate, submit a platform escalation ticket to authorize the Vault PKI role template.
