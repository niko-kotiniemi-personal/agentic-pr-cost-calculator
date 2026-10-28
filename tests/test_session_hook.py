"""The cloud session hook installs the tools inside the project, or not at all.

The hook runs each install step even when an earlier one failed, so it cannot
use `set -e`, and a failed `cd` would otherwise leave every step running in
whatever folder the hook started in. These tests run the real hook with stand-in
commands that record where they ran.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / ".claude" / "hooks" / "session-start.sh"

STAND_IN = """#!/bin/sh
printf '%s %s\\n' "$(basename "$0") $*" "$PWD" >> "$STAND_IN_LOG"
if [ "$(basename "$0")" = python3 ] && [ "$*" = "-m venv .venv" ]; then
  mkdir -p .venv/bin
  cp "$0" .venv/bin/pip
fi
"""


def run_hook(tmp_path: Path, project: Path) -> tuple[subprocess.CompletedProcess[str], list[str]]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name in ("claude", "npm", "python3"):
        (bin_dir / name).write_text(STAND_IN)
        (bin_dir / name).chmod(0o755)
    log = tmp_path / "ran.log"
    started_in = tmp_path / "elsewhere"
    started_in.mkdir()
    env = {
        "PATH": f"{bin_dir}:/usr/bin:/bin",
        "CLAUDE_CODE_REMOTE": "true",
        "CLAUDE_PROJECT_DIR": str(project),
        "STAND_IN_LOG": str(log),
        "HOME": os.environ.get("HOME", str(tmp_path)),
    }
    done = subprocess.run(
        ["bash", str(HOOK)], cwd=started_in, env=env, capture_output=True, text=True
    )
    ran = log.read_text().splitlines() if log.exists() else []
    return done, ran


def test_the_hook_runs_every_step_inside_the_project(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    done, ran = run_hook(tmp_path, project)
    assert done.returncode == 0, done.stderr
    assert [line.split()[0] for line in ran] == ["claude", "claude", "npm", "python3", "pip"]
    assert all(line.endswith(f" {project}") for line in ran), ran


def test_the_hook_runs_nothing_when_it_cannot_enter_the_project(tmp_path: Path) -> None:
    done, ran = run_hook(tmp_path, tmp_path / "missing")
    assert done.returncode != 0
    assert ran == []
