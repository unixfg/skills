#!/usr/bin/env python3
"""Look up read-only online music metadata."""

from __future__ import annotations

import argparse
import sys

from music_lookup import DEFAULT_LIMIT, add_common_args, lookup_music, run_main


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", required=True)
    parser.add_argument(
        "--type",
        choices=["all", "artist", "release", "release-group", "recording"],
        default="all",
    )
    parser.add_argument("--source", choices=["all", "wikipedia", "musicbrainz"], default="all")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    add_common_args(parser)
    args = parser.parse_args()
    return run_main(lambda: lookup_music(args.query, args.type, args.source, args.limit, args.timeout))


if __name__ == "__main__":
    sys.exit(main())
