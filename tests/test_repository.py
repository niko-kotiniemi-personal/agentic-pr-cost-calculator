"""Checks on the repository itself, before any calculator code exists.

These hold the properties the first pull request promises: the files a
standalone public repository needs, pinned tooling, a read-only CI token, and
nothing private carried over from elsewhere.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import re
import subprocess
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "README.md",
    "LICENSE",
    "SECURITY.md",
    "CLAUDE.md",
    "renovate.json",
    "package.json",
    "package-lock.json",
    ".github/workflows/ci.yml",
    "openspec/config.yaml",
    "vendor/superpowers/UPSTREAM.lock",
]

# Built from parts so that this file does not match its own patterns.
PRIVATE_PATTERNS = [
    re.compile(re.escape("claude.ai/code/" + "session_")),
    re.compile("cmsg" + r"_[0-9A-Za-z]{8,}"),
    re.compile("chan" + r"_[0-9A-Za-z]{8,}"),
    re.compile(re.escape("/mnt/" + "project-files")),
    re.compile("Claude-" + "Session:"),
]


# Names that must not appear in this repository, kept as SHA-256 hashes so that
# this file does not publish them. Each tracked file is lower-cased and split
# into words; every word and every pair of adjacent words joined by a hyphen is
# hashed and looked up, so a two-word name is caught however it is separated.
PRIVATE_NAME_HASHES = frozenset(
    {
        "9e55544b519dc9d719dd78d15d7c454ac85830b977a93e5c086275dc6b8732ce",
    }
)


def private_names_in(text: str, hashes: frozenset[str] = PRIVATE_NAME_HASHES) -> bool:
    words = re.findall(r"[a-z0-9]+", text.lower())
    candidates = set(words) | {f"{a}-{b}" for a, b in itertools.pairwise(words)}
    return any(hashlib.sha256(c.encode()).hexdigest() in hashes for c in candidates)


def tracked_files() -> list[str]:
    out = subprocess.run(
        ["git", "ls-files", "-z"], cwd=ROOT, check=True, capture_output=True
    ).stdout.decode()
    return [p for p in out.split("\0") if p]


def test_every_required_file_exists() -> None:
    missing = [p for p in REQUIRED_FILES if not (ROOT / p).is_file()]
    assert not missing, f"missing: {missing}"


def test_the_licence_is_mit() -> None:
    text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    assert text.startswith("MIT License")


def test_no_tracked_file_carries_a_private_reference() -> None:
    hits = []
    for path in tracked_files():
        file = ROOT / path
        if not file.is_file():
            continue
        try:
            text = file.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for pattern in PRIVATE_PATTERNS:
            if pattern.search(text):
                hits.append(f"{path}: {pattern.pattern}")
        if private_names_in(text):
            hits.append(f"{path}: a private name")
    assert not hits, "private references found:\n" + "\n".join(hits)


def test_the_privacy_patterns_catch_what_they_are_for() -> None:
    samples = [
        "see https://claude.ai/code/" + "session_01ABCDEF",
        "thread cmsg" + "_01ABCDEFGHJKMNPQ",
        "project chan" + "_01ABCDEFGHJKMNPQ",
        "/mnt/" + "project-files/example/",
        "Claude-" + "Session: x",
    ]
    for sample in samples:
        assert any(p.search(sample) for p in PRIVATE_PATTERNS), sample
    assert not any(p.search("an ordinary sentence about pull requests") for p in PRIVATE_PATTERNS)


def test_the_private_name_check_matches_the_name_however_it_is_written() -> None:
    # A made-up name and its hash stand in for the real ones, so that this test
    # publishes nothing: an encoded copy of a name is still the name.
    hashes = frozenset({hashlib.sha256(b"example-venture").hexdigest()})
    assert private_names_in("see github.com/Example-Venture/x", hashes)
    assert private_names_in("Copyright Example Venture", hashes)
    assert private_names_in("EXAMPLE_VENTURE", hashes)
    assert not private_names_in("an example of a venture", hashes)
    assert not private_names_in("Example-Ventures", hashes)
    assert all(re.fullmatch(r"[0-9a-f]{64}", h) for h in PRIVATE_NAME_HASHES)


def renovate() -> dict[str, Any]:
    config: dict[str, Any] = json.loads((ROOT / "renovate.json").read_text(encoding="utf-8"))
    return config


def test_renovate_waits_fourteen_days_for_every_datable_update() -> None:
    rules = [
        r
        for r in renovate().get("packageRules", [])
        if set(r.get("matchUpdateTypes", [])) >= {"major", "minor", "patch", "digest"}
    ]
    assert rules and all(r.get("minimumReleaseAge") == "14 days" for r in rules)


def test_renovate_does_not_delay_vulnerability_fixes() -> None:
    config = renovate()
    assert config["vulnerabilityAlerts"]["minimumReleaseAge"] is None
    assert config.get("osvVulnerabilityAlerts") is True


def test_renovate_reads_the_vendored_lock() -> None:
    config = renovate()
    assert not any("vendor" in p for p in config.get("ignorePaths", [])), config.get("ignorePaths")
    patterns = [
        p for m in config.get("customManagers", []) for p in m.get("managerFilePatterns", [])
    ]
    assert any("UPSTREAM" in p for p in patterns)


def workflows() -> list[Path]:
    return sorted((ROOT / ".github" / "workflows").glob("*.yml"))


def test_every_workflow_declares_a_read_only_token() -> None:
    for path in workflows():
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert doc.get("permissions") == {"contents": "read"}, path.name


def test_every_action_is_pinned_to_a_full_commit() -> None:
    unpinned = []
    for path in workflows():
        for line in path.read_text(encoding="utf-8").splitlines():
            m = re.search(r"uses:\s*([^\s#]+)", line)
            if m and not re.fullmatch(r"[^@]+@[0-9a-f]{40}", m.group(1)):
                unpinned.append(f"{path.name}: {m.group(1)}")
    assert not unpinned, unpinned


def test_openspec_is_pinned_to_an_exact_version() -> None:
    deps = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))["devDependencies"]
    assert re.fullmatch(r"\d+\.\d+\.\d+", deps["@fission-ai/openspec"])


# OpenSpec honours DO_NOT_TRACK; the vendored Superpowers reads its own switch.
TELEMETRY_SWITCHES = {"DO_NOT_TRACK": "1", "SUPERPOWERS_DISABLE_TELEMETRY": "1"}


def telemetry_left_on(env: dict[str, str]) -> list[str]:
    return sorted(name for name, value in TELEMETRY_SWITCHES.items() if env.get(name) != value)


def test_sessions_here_turn_telemetry_off() -> None:
    settings = json.loads((ROOT / ".claude/settings.json").read_text(encoding="utf-8"))
    assert telemetry_left_on(settings.get("env", {})) == []


def test_the_telemetry_check_names_a_switch_left_on() -> None:
    assert telemetry_left_on({"DO_NOT_TRACK": "1"}) == ["SUPERPOWERS_DISABLE_TELEMETRY"]
    assert telemetry_left_on({"DO_NOT_TRACK": "0", "SUPERPOWERS_DISABLE_TELEMETRY": "1"}) == [
        "DO_NOT_TRACK"
    ]


def lock_field(name: str) -> str:
    text = (ROOT / "vendor/superpowers/UPSTREAM.lock").read_text(encoding="utf-8")
    m = re.search(rf"^{name}=(.*)$", text, re.MULTILINE)
    assert m, name
    return m.group(1)


def test_the_vendored_lock_names_a_full_commit_and_a_tag() -> None:
    # The upstream itself is pinned here, so a lock cannot move to another
    # repository's tags without this line changing in review.
    assert lock_field("repo") == "obra/superpowers"
    assert re.fullmatch(r"[0-9a-f]{40}", lock_field("sha"))
    assert re.fullmatch(r"v\d+\.\d+\.\d+", lock_field("tag"))


def test_the_sync_script_and_the_lock_list_the_same_paths() -> None:
    script = (ROOT / "scripts/sync-superpowers.sh").read_text(encoding="utf-8")
    m = re.search(r"^PATHS=\((.*)\)$", script, re.MULTILINE)
    assert m
    assert m.group(1).split() == lock_field("vendored_paths").split(",")
