#!/usr/bin/env python3
"""Compatibility shim for running speaksh from the source tree."""

from __future__ import annotations

from speaksh.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
