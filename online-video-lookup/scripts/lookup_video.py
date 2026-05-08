#!/usr/bin/env python3
"""Look up read-only online movie and TV metadata."""

from __future__ import annotations

import argparse
import sys

from video_lookup import DEFAULT_LIMIT, add_common_args, lookup_video, run_main


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", required=True)
    parser.add_argument("--type", choices=["all", "movie", "tv"], default="all")
    parser.add_argument("--source", choices=["all", "wikipedia", "tmdb", "tvdb"], default="all")
    parser.add_argument("--year")
    parser.add_argument("--include-trailers", action="store_true")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    add_common_args(parser)
    args = parser.parse_args()
    return run_main(
        lambda: lookup_video(
            args.query,
            args.type,
            args.source,
            args.year,
            args.include_trailers,
            args.limit,
            args.timeout,
        )
    )


if __name__ == "__main__":
    sys.exit(main())
