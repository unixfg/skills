# GitOps Repository Structure

## Location
- **Remote**: `github.com/unixfg/gitops`
- **Local**: `~/workspace/gitops` (symlinked to `~/gitops`)

## Top-Level Structure

```
gitops/
├── apps/                    # Application manifests
├── docs/                    # Documentation
├── scripts/                 # Utility scripts
├── AGENTS.md               # Agent instructions for this repo
├── CNPG-RECOVERY.md        # CloudNativePG recovery procedures
├── INGRESSROUTE_MIGRATION.md
├── README.md               # Main documentation
└── RECOVERY-PROCEDURES.md  # General recovery procedures
```

## Key Documentation Files

| File | Purpose |
|------|---------|
| `AGENTS.md` | Rules for AI agents working in this repo |
| `RECOVERY-PROCEDURES.md` | General cluster recovery |
| `CNPG-RECOVERY.md` | CloudNativePG database recovery |
| `docs/BACKUP.md` | Backup configuration and procedures |
| `apps/longhorn/README.md` | Storage configuration |

## Apps Directory Structure

Each app follows a pattern:

```
apps/<app-name>/
├── base/                   # Kustomize base (raw manifests)
│   ├── kustomization.yaml
│   └── *.yaml
├── overlays/
│   └── bees/              # Cluster-specific overlay
│       └── kustomization.yaml
└── helm/                   # For Helm-based apps
    └── bees/
        └── application.yaml  # ArgoCD Application
```

## Notable Apps

| App | Type | Notes |
|-----|------|-------|
| `longhorn` | Helm | Storage - see skill for config |
| `argocd` | Helm | GitOps CD |
| `kyverno` | Helm | Policy engine |
| `kyverno-policies` | Kustomize | Custom policies (e.g., ndots) |
| `traefik` | Helm | Ingress controller |
| `keycloak` | Helm + Kustomize | SSO/OIDC |
| `kube-prometheus-stack` | Helm | Monitoring |
| `loki` | Helm | Log aggregation |
| `cnpg-operator` | Helm | PostgreSQL operator |
| `grafana-pg`, `miniflux` | Kustomize | Apps using CNPG |

## PR Workflow

From `~/workspace/gitops` AGENTS.md:

- Always work in a named branch
- Use `gh` CLI to create PRs
- Never commit directly to main (access denied)
- Don't assume previous PR exists - it may have been closed
