#!/usr/bin/env python3
"""Validate environment configuration for prom_query.py."""

from __future__ import annotations

import sys

from prom_query import print_json
from prom_query import ScriptError, build_validation_report, load_settings


def main() -> int:
    try:
        settings = load_settings()
        report = build_validation_report(settings)
    except ScriptError as exc:
        print_json({"error": str(exc), "error_code": exc.error_code})
        return 1

    print_json(report)
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    sys.exit(main())
