#!/usr/bin/env python3
"""Reproduction script for Bug 02: Windows CSV export double carriage returns.

Bug: Exporting memories to a CSV file on Windows using `-o <file>.csv` produces
double carriage returns (`\\r\\r\\n`, byte sequence 0x0D 0x0D 0x0A) because
open() is called in text mode without `newline=""`, translating CRLF twice.
"""
import os
import subprocess
import sys

OUTPUT_FILE = "repro_export_test.csv"


def run_repro():
    print(f"[repro_02] Testing command: memcli -u repro-bot export --format csv -o {OUTPUT_FILE}")
    cmd = [
        sys.executable,
        "-m",
        "memcli.cli",
        "-u",
        "repro-bot",
        "export",
        "--format",
        "csv",
        "-o",
        OUTPUT_FILE,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)

    if not os.path.exists(OUTPUT_FILE):
        print(f"[repro_02] Failed to create output file: {proc.stderr}")
        return 1

    try:
        with open(OUTPUT_FILE, "rb") as f:
            data = f.read()

        has_double_cr = b"\r\r\n" in data
        print(f"[repro_02] Output file size: {len(data)} bytes")
        print(f"[repro_02] Contains double carriage returns (\\r\\r\\n): {has_double_cr}")

        if has_double_cr:
            print("\n[repro_02] Observed raw hex pattern: 0x0D 0x0D 0x0A detected.")
            print("[repro_02] RESULT: Bug successfully reproduced.")
            return 1
        else:
            print("[repro_02] No duplicate carriage returns found.")
            return 0
    finally:
        if os.path.exists(OUTPUT_FILE):
            os.remove(OUTPUT_FILE)


if __name__ == "__main__":
    sys.exit(run_repro())

