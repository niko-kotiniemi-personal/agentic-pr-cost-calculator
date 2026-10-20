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
import tomllib
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
    "CONTRIBUTING.md",
    "CODE_OF_CONDUCT.md",
    "CHANGELOG.md",
    ".editorconfig",
    ".github/CODEOWNERS",
    ".github/pull_request_template.md",
    ".github/ISSUE_TEMPLATE/bug_report.yml",
    ".github/ISSUE_TEMPLATE/feature_request.md",
    ".github/ISSUE_TEMPLATE/config.yml",
    "docs/requirements.md",
    "docs/how-it-works.md",
    "docs/features/README.md",
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
    folder = ROOT / ".github" / "workflows"
    return sorted([*folder.glob("*.yml"), *folder.glob("*.yaml")])


def test_every_workflow_declares_a_read_only_token() -> None:
    assert workflows(), "no workflow was found, so this test covered nothing"
    for path in workflows():
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert doc.get("permissions") == {"contents": "read"}, path.name


# The workflows that may grant a job a write permission, and which ones. The
# report's and the release's workflows add their entries when they are built.
WRITES_ALLOWED: dict[str, set[str]] = {}

# Triggers that run a workflow with this repository's token on someone else's code.
FORBIDDEN_TRIGGERS = {"pull_request_target", "workflow_run"}


def triggers(doc: dict[Any, Any]) -> set[str]:
    # YAML 1.1 reads a bare `on:` key as the boolean true.
    on = doc.get("on", doc.get(True))
    if isinstance(on, str):
        return {on}
    return set(on or [])


def writes(permissions: Any) -> set[str]:
    if permissions == "write-all":
        return {"write-all"}
    if isinstance(permissions, dict):
        return {f"{scope}: write" for scope, level in permissions.items() if level == "write"}
    return set()


def workflow_problems(name: str, text: str) -> list[str]:
    doc = yaml.safe_load(text)
    problems = [
        f"{name} triggers on {trigger}" for trigger in sorted(triggers(doc) & FORBIDDEN_TRIGGERS)
    ]
    blocks = [("the workflow", doc.get("permissions"))] + [
        (f"job `{job}`", body.get("permissions")) for job, body in (doc.get("jobs") or {}).items()
    ]
    allowed = WRITES_ALLOWED.get(name, set())
    for where, permissions in blocks:
        problems.extend(
            f"{name} {where} grants `{grant}`" for grant in sorted(writes(permissions) - allowed)
        )
    if re.search(r"\bsecrets\b", text):
        problems.append(f"{name} reads a secret")
    return problems


def test_no_workflow_writes_runs_on_foreign_triggers_or_reads_a_secret() -> None:
    problems = [
        problem
        for path in workflows()
        for problem in workflow_problems(path.name, path.read_text(encoding="utf-8"))
    ]
    assert not problems, problems


PLANTED_WORKFLOW = """\
on:
  pull_request_target:
  workflow_run:
    workflows: [ci]
  push:
permissions: write-all
jobs:
  a:
    permissions:
      contents: read
      issues: write
    steps:
      - run: echo ${{ secrets.TOKEN }}
"""


def test_the_workflow_checks_name_each_planted_violation() -> None:
    assert workflow_problems("x.yaml", PLANTED_WORKFLOW) == [
        "x.yaml triggers on pull_request_target",
        "x.yaml triggers on workflow_run",
        "x.yaml the workflow grants `write-all`",
        "x.yaml job `a` grants `issues: write`",
        "x.yaml reads a secret",
    ]


def test_a_write_the_workflow_is_allowed_is_not_reported(monkeypatch: Any) -> None:
    text = "on: push\njobs:\n  a:\n    permissions:\n      pull-requests: write\n"
    assert workflow_problems("r.yml", text) == ["r.yml job `a` grants `pull-requests: write`"]
    monkeypatch.setitem(WRITES_ALLOWED, "r.yml", {"pull-requests: write"})
    assert workflow_problems("r.yml", text) == []
    assert triggers({"on": ["push", "pull_request"]}) == {"push", "pull_request"}


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


# The oldest Python the tool supports. It rises only when this version nears
# its end of life, so that adopters on older systems can keep using the tool.
def pyproject() -> dict[str, Any]:
    config: dict[str, Any] = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return config


def oldest_python() -> str:
    """The one source of the oldest supported Python: `requires-python`."""
    match = re.fullmatch(r">=(3\.\d+)", pyproject()["project"]["requires-python"])
    assert match, "requires-python is not of the form >=3.N"
    return match.group(1)


STATED_PYTHON = re.compile(r"\bPython (3\.\d+)\b")


def python_floor_problems(oldest: str, copies: dict[str, Any], prose: dict[str, str]) -> list[str]:
    """Name each copy of the oldest supported Python that disagrees with `oldest`.

    `copies` maps a setting to its value; `prose` maps a document to its text, where every
    "Python 3.N" it states must be the oldest version.
    """
    expected = {
        "ruff target-version": "py" + oldest.replace(".", ""),
        "mypy python_version": oldest,
        ".python-version": oldest,
    }
    problems = [
        f"{name} says {copies.get(name)!r}, not {value!r}"
        for name, value in expected.items()
        if copies.get(name) != value
    ]
    matrix = copies.get("CI matrix") or []
    if oldest not in matrix:
        problems.append(f"the CI matrix lacks the oldest supported Python {oldest}")
    if "3.x" not in matrix:
        problems.append("the CI matrix lacks the newest release, 3.x")
    for document, text in sorted(prose.items()):
        problems.extend(
            f"{document} names Python {version}, not {oldest}"
            for version in STATED_PYTHON.findall(text)
            if version != oldest
        )
    return problems


PYTHON_PROSE = [
    "README.md",
    "SECURITY.md",
    "CONTRIBUTING.md",
    "CLAUDE.md",
    "docs/features/releases-and-compatibility.md",
    "openspec/changes/add-pr-cost-calculator/specs/project-standards/spec.md",
]


def test_every_copy_of_the_oldest_supported_python_matches_requires_python() -> None:
    config = pyproject()
    ci = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8"))
    copies = {
        "ruff target-version": config["tool"]["ruff"]["target-version"],
        "mypy python_version": config["tool"]["mypy"]["python_version"],
        ".python-version": (ROOT / ".python-version").read_text(encoding="utf-8").strip(),
        "CI matrix": ci["jobs"]["python"]["strategy"]["matrix"]["python-version"],
    }
    prose = {name: (ROOT / name).read_text(encoding="utf-8") for name in PYTHON_PROSE}
    assert all(STATED_PYTHON.search(text) for text in prose.values()), "a document states none"
    assert python_floor_problems(oldest_python(), copies, prose) == []


def test_a_copy_of_the_oldest_python_that_disagrees_is_named() -> None:
    copies = {
        "ruff target-version": "py311",
        "mypy python_version": "3.12",
        ".python-version": "3.11",
        "CI matrix": ["3.12"],
    }
    prose = {"README.md": "Runs on Python 3.10 and later.", "SECURITY.md": "Python 3.11."}
    assert python_floor_problems("3.11", copies, prose) == [
        "mypy python_version says '3.12', not '3.11'",
        "the CI matrix lacks the oldest supported Python 3.11",
        "the CI matrix lacks the newest release, 3.x",
        "README.md names Python 3.10, not 3.11",
    ]


def test_matching_copies_of_the_oldest_python_raise_nothing() -> None:
    copies = {
        "ruff target-version": "py312",
        "mypy python_version": "3.12",
        ".python-version": "3.12",
        "CI matrix": ["3.12", "3.x"],
    }
    assert python_floor_problems("3.12", copies, {"README.md": "Python 3.12 and later."}) == []


def test_the_project_version_is_semantic_and_the_changelog_has_an_unreleased_section() -> None:
    assert re.fullmatch(r"\d+\.\d+\.\d+", pyproject()["project"]["version"])
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert re.search(r"^## \[Unreleased\]$", changelog, re.MULTILINE)


def major_updates_need_approval(config: dict[str, Any]) -> bool:
    return any(
        rule.get("matchUpdateTypes") == ["major"] and rule.get("dependencyDashboardApproval")
        for rule in config.get("packageRules", [])
    )


def test_renovate_holds_major_updates_for_the_owner_and_lets_minor_and_patch_through() -> None:
    config = renovate()
    assert major_updates_need_approval(config)
    assert not config.get("dependencyDashboardApproval"), "every update would wait for approval"
    assert config.get("dependencyDashboard") is not False


def test_the_major_update_check_names_a_rule_that_is_missing() -> None:
    assert not major_updates_need_approval({"packageRules": []})
    assert not major_updates_need_approval(
        {
            "packageRules": [
                {"matchUpdateTypes": ["major", "minor"], "dependencyDashboardApproval": True}
            ]
        }
    )


def required_privacy_checkbox(form: dict[str, Any]) -> bool:
    return any(
        field.get("type") == "checkboxes"
        and field.get("id") == "privacy"
        and all(option.get("required") for option in field["attributes"]["options"])
        for field in form.get("body", [])
    )


def test_the_bug_report_form_requires_the_privacy_checkbox() -> None:
    form = yaml.safe_load(
        (ROOT / ".github/ISSUE_TEMPLATE/bug_report.yml").read_text(encoding="utf-8")
    )
    assert required_privacy_checkbox(form)


def test_a_bug_report_form_whose_privacy_checkbox_is_optional_is_refused() -> None:
    option = {"label": "No private text.", "required": False}
    field = {"type": "checkboxes", "id": "privacy", "attributes": {"options": [option]}}
    assert not required_privacy_checkbox({"body": [field]})
    assert not required_privacy_checkbox({"body": []})
    option["required"] = True
    assert required_privacy_checkbox({"body": [field]})
