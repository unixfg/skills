#!/usr/bin/env python3
"""List read-only online movie and TV metadata from TMDB."""

from __future__ import annotations

import argparse
import sys

from video_lookup import DEFAULT_LIMIT, add_common_args, list_video, run_main


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--list",
        required=True,
        choices=["trending", "popular", "now-playing", "upcoming", "top-rated"],
    )
    parser.add_argument("--type", choices=["all", "movie", "tv"], default="all")
    parser.add_argument("--time-window", choices=["day", "week"], default="day")
    parser.add_argument("--region")
    parser.add_argument("--include-trailers", action="store_true")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    add_common_args(parser)
    args = parser.parse_args()
    return run_main(
        lambda: list_video(
            args.list,
            args.type,
            args.time_window,
            args.region,
            args.include_trailers,
            args.limit,
            args.timeout,
        )
    )


if __name__ == "__main__":
    sys.exit(main())
