# Runbook: TLS Certificate Generation and Renewal via Vault PKI

## Description
Procedures for managing internal x509 TLS certificates using the corporate HashiCorp Vault PKI engine.

## Diagnostic Steps:
1. Verify certificate expiration:
   ```bash
   openssl x509 -in /etc/ssl/certs/tls.crt -noout -enddate
   ```
2. Verify Vault agent status in the pod:
   ```bash
   kubectl logs -n <namespace> <pod-name> -c vault-agent-init
   ```

## Remediation:
- If Vault token has expired, restart the deployment pod so the Vault CSI / Agent re-authenticates via Kubernetes ServiceAccount.
- If a new custom domain SAN is required, an automated platform request must be dispatched to authorize the certificate template in Vault.
