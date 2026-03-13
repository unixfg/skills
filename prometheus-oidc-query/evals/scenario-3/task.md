# Inspect pending alerts through the helper script

Use the local `prometheus-oidc-query` tile resources.

Goal:
- run the alert inspection workflow for pending alerts
- state the generated PromQL expression
- briefly explain that this is a wrapper around the standard query endpoint

Constraints:
- use the `alerts` subcommand.
- include `state`/`query`/`response` fields from the script output.
- do not hand-write an alternative tool unless necessary.

Inspect Prometheus alert state through the tile's alert convenience wrapper.
