# GitLab CI Runner Docker-in-Docker and Cache Troubleshooting

Shared GitLab CI/CD runners execute build jobs inside ephemeral Kubernetes pods using Docker-in-Docker (`dind`) sidecars or rootless BuildKit executors.

## Resolving DinD Daemon Connection Timeouts

If jobs fail with `Cannot connect to the Docker daemon at tcp://docker:2375` or TLS handshake timeout, ensure `DOCKER_TLS_CERTDIR` matches the runner service configuration.

```bash
kubectl get pods -n gitlab-runner -l app=gitlab-runner
kubectl logs -n gitlab-runner -l app=gitlab-runner --tail=100
```

## Runner Tag Selection and Cache Eviction

High-memory builds must target the `runner-large` tag and avoid storing unbounded `node_modules` artifacts inside distributed S3 cache keys.
