#!/usr/bin/env python3
"""Validate Plex music library lookup configuration."""

from __future__ import annotations

import sys

from plex_music import ScriptError, build_validation_report, load_settings, print_json


def main() -> int:
    try:
        report = build_validation_report(load_settings())
    except ScriptError as exc:
        print_json({"error": str(exc), "error_code": exc.error_code})
        return exc.return_code
    print_json(report)
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    sys.exit(main())
