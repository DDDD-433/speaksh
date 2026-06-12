from __future__ import annotations

import subprocess


def run_command(command: str) -> int:
    process = subprocess.run(command, shell=True, text=True)
    return int(process.returncode)
