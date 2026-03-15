#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

: "${PROM_QUERY_PROMETHEUS_URL:?PROM_QUERY_PROMETHEUS_URL is required}"
: "${PROM_QUERY_TOKEN_URL:?PROM_QUERY_TOKEN_URL is required}"
: "${PROM_QUERY_CLIENT_ID:?PROM_QUERY_CLIENT_ID is required}"
: "${PROM_QUERY_CLIENT_SECRET:?PROM_QUERY_CLIENT_SECRET is required}"

cd "$ROOT_DIR"

python3 -m unittest -v tests/test_prom_query.py
python3 scripts/check_config.py
python3 scripts/prom_query.py config
python3 scripts/prom_query.py token --refresh
python3 scripts/prom_query.py token
python3 scripts/prom_query.py query --expr 'up'
python3 scripts/prom_query.py alerts --state firing
python3 scripts/prom_query.py alerts --state pending
python3 scripts/prom_query.py alerts --state inactive
