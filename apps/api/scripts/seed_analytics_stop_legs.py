#!/usr/bin/env python3
"""Deprecated — analytics_stop_legs table removed in one-SoT cleanup."""

from __future__ import annotations

import sys


def main() -> int:
    print("seed_analytics_stop_legs: skipped — analytics tables dropped (q9r0s1t2u3v4)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
