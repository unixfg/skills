#!/usr/bin/env python3
"""List read-only Plex movie and TV metadata from library sections."""

from __future__ import annotations

import argparse
import sys

from plex_media import DEFAULT_LIMIT, add_common_args, list_media, run_main


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--type", choices=["movie", "tv", "show", "season", "episode"], required=True)
    parser.add_argument("--sort", default=None)
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    parser.add_argument("--latest-episodes", action="store_true")
    add_common_args(parser)
    args = parser.parse_args()
    return run_main(
        lambda: list_media(
            args.type,
            args.sort,
            args.limit,
            args.latest_episodes,
            args.timeout,
        )
    )


if __name__ == "__main__":
    sys.exit(main())
