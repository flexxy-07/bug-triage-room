#!/usr/bin/env python3
"""Reproduction script for Bug 01: Subcommand argument order in memcli.

Bug: Passing -u / --user AFTER a subcommand (e.g., `memcli list -u repro-bot`)
fails with `unrecognized arguments: -u repro-bot` because the option was only
registered on the root parser before subparsers were instantiated.
"""
import subprocess
import sys


def run_repro():
    print("[repro_01] Testing command: memcli list -u repro-bot")
    cmd = [sys.executable, "-m", "memcli.cli", "list", "-u", "repro-bot"]
    proc = subprocess.run(cmd, capture_output=True, text=True)

    print(f"[repro_01] Return code: {proc.returncode}")
    if proc.returncode != 0:
        print("[repro_01] Observed Error Output:")
        print(proc.stderr.strip() or proc.stdout.strip())
        print("\n[repro_01] RESULT: Bug successfully reproduced.")
        return 1
    else:
        print("[repro_01] Command succeeded unexpectedly.")
        return 0


if __name__ == "__main__":
    sys.exit(run_repro())
