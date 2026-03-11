# kubectl Contexts

Two kubeconfig files are available with different permission levels.

## Default Context (jobe)

**Config**: `~/.kube/config`
**Usage**: Default - no flags needed

```bash
kubectl get pods -n media
```

**Permissions**: Limited RBAC via `cluster-rbac` app
- Can list/get most resources
- Cannot patch/delete many resources
- Cannot access some namespaces

## Admin Context

**Config**: `~/.kube/admin`
**Usage**: Set KUBECONFIG or use --kubeconfig

```bash
# Option 1: Environment variable
KUBECONFIG=~/.kube/admin kubectl delete pod -n monitoring loki-0 --force

# Option 2: Flag
kubectl --kubeconfig ~/.kube/admin patch pvc ...
```

**Permissions**: Full cluster admin
- Use for destructive operations (delete, patch finalizers)
- Use when default context returns "Forbidden"

## When to Use Admin

- Force-deleting stuck pods/PVCs
- Patching finalizers on stuck resources
- Deleting Longhorn volumes
- Any operation that returns "Forbidden" with default context
