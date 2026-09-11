#!/usr/bin/env python3
"""One-command entrypoint: triage the synthetic inbox and write a pack."""

from invoice_triage.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
