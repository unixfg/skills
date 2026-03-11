# Storage Management

## Longhorn Backups to Backblaze B2

Longhorn is configured to backup volumes to Backblaze B2.

### Configuration

In `apps/longhorn/helm/bees/application.yaml`:

```yaml
defaultSettings:
  backupTarget: "s3://longhorn-backup-bees@us-west-004/"
  backupTargetCredentialSecret: "longhorn-b2-credentials"
```

Secret location: `apps/secrets/overlays/bees/longhorn-b2-credentials.enc.yaml`

### Recurring Backup Jobs

Defined in Longhorn Helm values under `extraObjects`:

- **daily-snapshot**: Runs at 6:00 UTC, retains 7 snapshots
- **daily-backup**: Runs at 2:00 UTC, retains 30 backups (to B2)

### B2 CLI

The Backblaze B2 CLI can be used to manage backups directly.

**Installation** (if not installed):
```bash
pip install b2
```

**Authentication**:
```bash
b2 authorize-account <applicationKeyId> <applicationKey>
```

**Common Commands**:
```bash
# List buckets
b2 list-buckets

# List files in backup bucket
b2 ls longhorn-backup-bees

# Download a backup
b2 download-file-by-name longhorn-backup-bees <backup-path> <local-path>

# Check bucket usage
b2 get-bucket longhorn-backup-bees
```

### Restoring from B2 Backup

Via Longhorn UI or API:
1. Create new volume with "from backup" option
2. Specify backup URL: `s3://longhorn-backup-bees@us-west-004/<backup-name>`

Via kubectl (if volume exists):
```bash
kubectl -n longhorn-system exec deploy/longhorn-driver-deployer -- \
  curl -s -X POST "http://longhorn-backend:9500/v1/volumes/<volume-name>?action=restore" \
  -H "Content-Type: application/json" \
  -d '{"name":"<backup-name>"}'
```

## Volume Health Monitoring

Check all volumes:
```bash
kubectl get volumes.longhorn.io -n longhorn-system -o json | \
  jq -r '.items[] | "\(.metadata.name): \(.status.state) \(.status.robustness)"'
```

Check backup status:
```bash
kubectl get volumes.longhorn.io -n longhorn-system -o json | \
  jq -r '.items[] | "\(.metadata.name): lastBackup=\(.status.lastBackup) at=\(.status.lastBackupAt)"'
```
