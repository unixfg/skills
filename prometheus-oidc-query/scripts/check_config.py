#!/usr/bin/env python3
"""Validate environment configuration for prom_query.py."""

from __future__ import annotations

import sys

from prom_query import ConfigError, build_validation_report, load_settings, print_json


def main() -> int:
    try:
        settings = load_settings()
        report = build_validation_report(settings)
    except ConfigError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print_json(report)
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    sys.exit(main())
