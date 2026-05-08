#!/usr/bin/env python3
"""Search read-only Plex music metadata."""

from __future__ import annotations

import argparse
import sys

from plex_music import DEFAULT_LIMIT, add_common_args, run_main, search_music


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", required=True)
    parser.add_argument("--type", choices=["all", "artist", "album", "track"], default="all")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    add_common_args(parser)
    args = parser.parse_args()
    return run_main(lambda: search_music(args.query, args.type, args.limit, args.timeout))


if __name__ == "__main__":
    sys.exit(main())
