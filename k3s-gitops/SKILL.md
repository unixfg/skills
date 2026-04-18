---
name: k3s-gitops
description: Manage Ryan's 3-node k3s cluster via GitOps. Use for cluster maintenance, Longhorn storage issues, ArgoCD sync problems, node operations, and PRs to the gitops repo. Covers pre-flight checks, drain procedures, and troubleshooting faulted volumes.
---

# k3s GitOps Cluster Management

## References

- `references/repo-structure.md` - GitOps repo layout, app structure, PR workflow
- `references/kubectl-contexts.md` - Default vs admin kubeconfig
- `references/storage-backups.md` - Longhorn B2 backups, restore procedures, B2 CLI

## Cluster Overview

- **Nodes**: node1 (192.168.30.31), node2 (192.168.30.32), node3 (192.168.30.33)
- **All nodes**: control-plane, etcd, master (HA setup)
- **OS**: AlmaLinux 10
- **Storage**: Longhorn on NVMe at `/var/lib/longhorn`
- **GitOps repo**: `github.com:unixfg/gitops` (local: `~/workspace/gitops`)
- **CD**: ArgoCD with auto-sync and self-heal

## Pre-Maintenance Checklist

Before draining or restarting any node:

```bash
# 1. Check all Longhorn nodes are healthy and schedulable
kubectl get nodes.longhorn.io -n longhorn-system -o json | \
  jq -r '.items[] | "\(.metadata.name): ready=\(.status.diskStatus[].conditions[] | select(.type=="Ready") | .status) schedulable=\(.status.diskStatus[].conditions[] | select(.type=="Schedulable") | .status)"'

# 2. Check for degraded/faulted volumes
kubectl get volumes.longhorn.io -n longhorn-system -o json | \
  jq -r '.items[] | select(.status.robustness != "healthy") | "\(.metadata.name): \(.status.state) \(.status.robustness)"'

# 3. Check ArgoCD app health
kubectl get applications -n argocd -o json | \
  jq -r '.items[] | select(.status.health.status != "Healthy" or .status.sync.status != "Synced") | "\(.metadata.name): sync=\(.status.sync.status) health=\(.status.health.status)"'
```

**Do not proceed if:**
- Any Longhorn node shows `schedulable=False`
- Any volume is degraded or faulted
- Critical apps are unhealthy

## Node Drain Procedure

```bash
# Drain with pod eviction
kubectl drain <node> --ignore-daemonsets --delete-emptydir-data

# After maintenance, uncordon
kubectl uncordon <node>
```

## Longhorn Configuration

Key settings in `apps/longhorn/helm/bees/application.yaml`:

- `defaultReplicaCount: 2` (not 3 - safer for 3-node cluster)
- `nodeDrainPolicy: block-for-eviction-if-contains-last-replica`
- `autoSalvage: true`
- `storageOverProvisioningPercentage: 200`

## Troubleshooting Faulted Volumes

### Symptoms
- Pod stuck in `ContainerCreating`
- Volume shows `state: detached, robustness: faulted`
- Logs show `input/output error`

### Recovery Options

**Option 1: Salvage (preserves data)**
```bash
# Check replica status
kubectl get replicas.longhorn.io -n longhorn-system -l longhornvolume=<volume-name> -o json | \
  jq -r '.items[] | "\(.metadata.name) | \(.status.currentState) | age=\(.metadata.creationTimestamp)"'

# Salvage via API (pick oldest/healthiest replica)
kubectl -n longhorn-system exec deploy/longhorn-driver-deployer -- \
  curl -s -X POST "http://longhorn-backend:9500/v1/volumes/<volume-name>?action=salvage" \
  -H "Content-Type: application/json" \
  -d '{"names":["<replica-name>"]}'
```

**Option 2: Delete and recreate (loses data)**
```bash
# Delete stuck pod
kubectl delete pod -n <namespace> <pod> --force

# Delete PVC (may need finalizer patch)
kubectl delete pvc -n <namespace> <pvc-name> --force
kubectl patch pvc <pvc-name> -n <namespace> -p '{"metadata":{"finalizers":null}}' --type=merge

# Delete faulted volume
kubectl delete volume.longhorn.io -n longhorn-system <volume-name> --force
kubectl patch volume.longhorn.io <volume-name> -n longhorn-system -p '{"metadata":{"finalizers":null}}' --type=merge
```

### Cleaning Up Orphaned Replicas

If a volume has hundreds of stopped/error replicas:
```bash
# Keep only specific replicas, delete rest
kubectl get replicas.longhorn.io -n longhorn-system -l longhornvolume=<volume-name> -o name | \
  grep -v -E '<replica-to-keep-1>|<replica-to-keep-2>' | \
  xargs kubectl delete -n longhorn-system
```

## ArgoCD Patterns

### Ignoring Expected Diffs

For resources with runtime mutations (e.g., Kyverno ClusterPolicy annotations):
```yaml
spec:
  ignoreDifferences:
    - group: kyverno.io
      kind: ClusterPolicy
      jqPathExpressions:
        - .metadata.annotations
```

### Forcing Sync
```bash
kubectl -n argocd patch application <app-name> -p '{"operation":{"initiatedBy":{"username":"jobe"},"sync":{"force":true}}}' --type=merge
```

## k3s Service Management

Config location: `/etc/rancher/k3s/config.yaml`

```bash
# Restart k3s (on node via SSH)
sudo systemctl restart k3s

# Check status
sudo systemctl status k3s
sudo journalctl -u k3s -f
```

## Common Issues

### OpenClaw on this cluster: source of truth vs runtime state
For the bees OpenClaw deployment, distinguish Git-tracked source of truth from the files materialized inside the container:

- `apps/openclaw/base/config/openclaw.json` is the durable source for gateway config.
- `apps/openclaw/base/runtime/skills/skills-sources.json` controls which skill sources are synced.
- `/home/node/.openclaw/openclaw.json` is a runtime copy on the PVC, populated by init containers.
- `/home/node/.openclaw/skills` is a runtime sync target for first-party skills from `https://github.com/unixfg/skills.git`.

Operational rule:
- Do not treat `/home/node/.openclaw/skills` or `/home/node/.openclaw/openclaw.json` as the canonical edit target for durable changes.
- Runtime edits can appear to work immediately, but they are cache/materialized state and may be overwritten by restart, init, or the 5 minute first-party skill sync loop.

### OpenClaw web auth behind oauth2-proxy/nginx
For this deployment, keep external OAuth enabled at the nginx/oauth2-proxy edge and use OpenClaw gateway `auth.mode = "token"` for the backend hop.

Why this is the preferred pattern here:
- `trusted-proxy` is brittle in Kubernetes when the immediate source IP seen by OpenClaw is a pod-internal or loopback hop.
- The web UI path needs websocket support and long-lived upgraded connections through the sidecar proxy.
- A shared secret between nginx and OpenClaw is a cleaner boundary when OAuth is already enforced in front.

Practical guidance:
- Keep oauth2-proxy enforcing login for the public entrypoint.
- Preserve websocket upgrade headers and generous proxy timeouts in nginx.
- Store the gateway token in Kubernetes secrets and expose it under the env var expected by `openclaw.json`.
- If the control UI suddenly stops authenticating after an app upgrade or proxy change, check for accidental drift back to `trusted-proxy` assumptions.

### OpenClaw workspace permissions on PVC/NFS-backed storage
When bootstrapping OpenClaw workspaces from init containers on shared volumes, ownership and mode fixes that look reasonable on paper can still fail in practice.

Observed cluster lesson:
- Precreating workspace paths with `chown 1000:1000` and `0775` was not reliable enough after migration.
- Switching the precreated Discord workspace roots to `0777` was the pragmatic fix that restored writeability for non-root runtime processes.

Operational takeaway:
- If Discord or secondary workspaces break after migration, inspect directory mode/ownership before debugging the agent itself.
- Expect init containers running as root to create paths later used by non-root OpenClaw processes.
- Treat PVC/NFS permission behavior as a deployment concern, not an application bug, until proven otherwise.

### Kyverno Webhook Deadlock
If apiserver can't start due to missing Kyverno endpoints:
```bash
kubectl delete validatingwebhookconfiguration kyverno-resource-validating-webhook-cfg
kubectl delete mutatingwebhookconfiguration kyverno-resource-mutating-webhook-cfg
```
Kyverno will re-register them with `failurePolicy: Ignore`.

### Kyverno Admission Controller Stuck
If stuck in `Init:0/1` waiting for leader election:
```bash
kubectl delete lease -n kyverno kyvernopre
```

### DNS Resolution (ndots)
Kyverno policy `inject-ndots-1` mutates pods to use `ndots:1` instead of default `ndots:5`. Existing pods need restart to pick up the mutation.
