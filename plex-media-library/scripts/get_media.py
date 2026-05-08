#!/usr/bin/env python3
"""Fetch read-only Plex movie or TV metadata by rating key."""

from __future__ import annotations

import argparse
import sys

from plex_media import add_common_args, get_media, run_main


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rating-key", required=True)
    parser.add_argument("--include-children", action="store_true")
    parser.add_argument("--children-limit", type=int, default=50)
    add_common_args(parser)
    args = parser.parse_args()
    return run_main(
        lambda: get_media(
            args.rating_key,
            args.include_children,
            args.children_limit,
            args.timeout,
        )
    )


if __name__ == "__main__":
    sys.exit(main())
