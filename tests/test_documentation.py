"""The documentation says what the repository holds, and keeps saying it.

Three documents describe the tool, and each is checked against what it
describes, so that one cannot quietly fall behind:

- `docs/requirements.md` registers every requirement in the specs, once, with
  its kind. A requirement added to a spec and not to the register is reported,
  and so is a row for a requirement that no spec holds.
- `docs/features/` has one page per feature. Every functional or behavioural
  requirement belongs to a feature page, every requirement a page names is in
  the register, and the index links every page.
- `docs/how-it-works.md` explains the tool as a whole. It names every
  permission that a workflow grants and every action that a workflow runs, and
  draws each flow it lists.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]

KINDS = ("functional", "behavioural", "non-functional")
REQUIREMENT = re.compile(r"^### Requirement: (.+?)\s*$", re.M)
REGISTER_ROW = re.compile(r"^\| (R\d+) \| ([a-z-]+) \| `([a-z0-9-]+)` \| (.+?) \|\s*$", re.M)
RETIRED_ROW = re.compile(r"^- (R\d+), removed by `([a-z0-9-]+)`", re.M)
PAGE_REQUIREMENTS = re.compile(r"^\*\*Requirements:\*\* (.+)$", re.M)
REQUIREMENT_ID = re.compile(r"R\d+")
LINK = re.compile(r"\]\(([^)#\s]+)(?:#[^)]*)?\)")
USES = re.compile(r"^\s*-?\s*uses:\s*([^\s@#]+)@", re.M)
PERMISSION_ROW = re.compile(r"^\| `([^`]+\.ya?ml)` \| `([^`]+)` \| (.+?) \|\s*$", re.M)


@dataclass(frozen=True)
class Row:
    ident: str
    kind: str
    capability: str
    name: str


def spec_requirements(root: Path) -> set[tuple[str, str]]:
    found = set()
    for spec in sorted((root / "openspec").rglob("spec.md")):
        for name in REQUIREMENT.findall(spec.read_text(encoding="utf-8")):
            found.add((spec.parent.name, name))
    return found


def register_rows(text: str) -> list[Row]:
    return [Row(*match) for match in REGISTER_ROW.findall(text)]


def register_problems(text: str, root: Path) -> list[str]:
    rows = register_rows(text)
    if not rows:
        return ["the register holds no requirement"]
    problems = []
    idents = [row.ident for row in rows]
    retired = [ident for ident, _change in RETIRED_ROW.findall(text)]
    numbers = sorted(int(ident[1:]) for ident in idents + retired)
    if numbers != list(range(1, len(numbers) + 1)):
        problems.append("the register's and the retired IDs do not run from R1 without a gap")
    if idents != sorted(idents, key=lambda ident: int(ident[1:])):
        problems.append("the register's IDs are not in order")
    problems += [f"{ident} is both registered and retired" for ident in idents if ident in retired]
    problems += [
        f"{row.ident} has a kind outside the list" for row in rows if row.kind not in KINDS
    ]
    listed = [(row.capability, row.name) for row in rows]
    specified = spec_requirements(root)
    for capability, name in sorted(specified - set(listed)):
        problems.append(f'`{capability}`: "{name}" is in a spec and not in the register')
    for row in rows:
        if (row.capability, row.name) not in specified:
            problems.append(f"{row.ident} names a requirement that no spec holds")
        if listed.count((row.capability, row.name)) > 1:
            problems.append(f"{row.ident} registers a requirement twice")
    return problems


def feature_problems(register: str, features: Path) -> list[str]:
    rows = {row.ident: row for row in register_rows(register)}
    index = features / "README.md"
    if not index.is_file():
        return ["the features folder has no index"]
    pages = sorted(p for p in features.glob("*.md") if p.name != "README.md")
    if not pages:
        return ["the features folder has no page"]
    problems = []
    linked = {(features / link).resolve() for link in LINK.findall(index.read_text())}
    covered: set[str] = set()
    for page in pages:
        if page.resolve() not in linked:
            problems.append(f"{page.name} is not linked from the index")
        named = PAGE_REQUIREMENTS.findall(page.read_text(encoding="utf-8"))
        if len(named) != 1:
            problems.append(f"{page.name} does not have one line naming its requirements")
            continue
        for ident in REQUIREMENT_ID.findall(named[0]):
            if ident not in rows:
                problems.append(f"{page.name} names {ident}, which the register does not hold")
            covered.add(ident)
    for link in sorted(linked):
        if not link.is_file():
            problems.append(f"the index links {link.name}, which does not exist")
    for ident, row in rows.items():
        if row.kind != "non-functional" and ident not in covered:
            problems.append(f"{ident} belongs to no feature page")
    return problems


def section(text: str, heading: str) -> str:
    match = re.search(rf"^## {re.escape(heading)}\s*$", text, re.M)
    if not match:
        return ""
    body = text[match.end() :]
    following = re.search(r"^## ", body, re.M)
    return body[: following.start()] if following else body


# A job that declares no permissions, in a workflow that declares none, gets
# whatever the repository's settings give the token, so the page must say so.
DEFAULT = "repository default"


def permission_set(block: Any) -> set[str]:
    if isinstance(block, dict):
        return {f"{scope}: {level}" for scope, level in block.items()}
    if isinstance(block, str):
        return {block}
    return {DEFAULT}


def granted(workflow: dict[str, Any]) -> dict[str, set[str]]:
    """Each job's effective permissions: its own block, else the workflow's."""
    top = workflow.get("permissions")
    return {
        name: permission_set(job.get("permissions", top))
        for name, job in (workflow.get("jobs") or {}).items()
    }


def images(workflow: dict[str, Any]) -> set[str]:
    found = set()
    for job in (workflow.get("jobs") or {}).values():
        container = job.get("container")
        if isinstance(container, str):
            found.add(container)
        elif isinstance(container, dict) and container.get("image"):
            found.add(container["image"])
        for service in (job.get("services") or {}).values():
            if isinstance(service, dict) and service.get("image"):
                found.add(service["image"])
    return found


def listed_permissions(section_text: str) -> dict[tuple[str, str], set[str]]:
    table = {}
    for workflow, job, cell in PERMISSION_ROW.findall(section_text):
        table[(workflow, job)] = set(re.findall(r"`([^`]+)`", cell))
    return table


def how_it_works_problems(text: str, workflow_files: list[Path]) -> list[str]:
    problems = []
    permissions = section(text, "Credentials and permissions")
    connections = section(text, "Connections to the outside world")
    flows = section(text, "Flows")
    for heading, body in [
        ("Credentials and permissions", permissions),
        ("Connections to the outside world", connections),
        ("Flows", flows),
    ]:
        if not body.strip():
            problems.append(f"how it works has no section {heading!r}")
    table = listed_permissions(permissions)
    seen = set()
    for path in workflow_files:
        source = path.read_text(encoding="utf-8")
        workflow = yaml.safe_load(source)
        for job, effective in sorted(granted(workflow).items()):
            seen.add((path.name, job))
            listed = table.get((path.name, job))
            if listed is None:
                problems.append(f"{path.name} job `{job}` is not in the permissions table")
                continue
            for permission in sorted(effective - listed):
                problems.append(f"{path.name} job `{job}` gets `{permission}`, which is not listed")
            for permission in sorted(listed - effective):
                problems.append(
                    f"{path.name} job `{job}` is listed with `{permission}`, not granted"
                )
        for action in sorted(set(USES.findall(source))):
            if f"`{action}`" not in connections:
                problems.append(f"{path.name} runs `{action}`, which is not listed")
        for image in sorted(images(workflow)):
            if f"`{image}`" not in connections:
                problems.append(f"{path.name} runs the image `{image}`, which is not listed")
    for workflow_name, job in sorted(set(table) - seen):
        problems.append(
            f"the permissions table lists {workflow_name} job `{job}`, which no workflow has"
        )
    parts = re.split(r"^### (.+?)\s*$", flows, flags=re.M)
    names = parts[1::2]
    if flows.strip() and not names:
        problems.append("how it works lists no flow")
    for name, body in zip(names, parts[2::2], strict=True):
        if "```mermaid" not in body:
            problems.append(f"the flow {name!r} has no diagram")
    return problems


def workflows(root: Path = ROOT) -> list[Path]:
    folder = root / ".github" / "workflows"
    return sorted([*folder.glob("*.yml"), *folder.glob("*.yaml")])


def test_the_register_holds_every_requirement_once() -> None:
    text = (ROOT / "docs" / "requirements.md").read_text(encoding="utf-8")
    assert not register_problems(text, ROOT), "\n".join(register_problems(text, ROOT))
    assert spec_requirements(ROOT), "no requirement was found in the specs"


def test_every_feature_page_resolves_and_every_requirement_has_a_feature() -> None:
    register = (ROOT / "docs" / "requirements.md").read_text(encoding="utf-8")
    problems = feature_problems(register, ROOT / "docs" / "features")
    assert not problems, "\n".join(problems)


def test_how_it_works_names_every_permission_and_action_and_draws_every_flow() -> None:
    text = (ROOT / "docs" / "how-it-works.md").read_text(encoding="utf-8")
    assert workflows(), "no workflow was found, so this test covered nothing"
    problems = how_it_works_problems(text, workflows())
    assert not problems, "\n".join(problems)


def synthetic_specs(root: Path) -> None:
    spec = root / "openspec" / "changes" / "demo" / "specs" / "thing" / "spec.md"
    spec.parent.mkdir(parents=True)
    spec.write_text("### Requirement: It works\n\n### Requirement: It is fast\n")


REGISTER = (
    "| ID | Kind | Capability | Requirement |\n"
    "|---|---|---|---|\n"
    "| R1 | functional | `thing` | It works |\n"
    "| R2 | non-functional | `thing` | It is fast |\n"
)


def test_a_complete_register_has_no_problem(tmp_path: Path) -> None:
    synthetic_specs(tmp_path)
    assert register_problems(REGISTER, tmp_path) == []


def test_a_retired_id_keeps_its_number_out_of_use(tmp_path: Path) -> None:
    synthetic_specs(tmp_path)
    register = REGISTER.replace("| R2 | non", "| R3 | non") + "\n- R2, removed by `old-change`\n"
    assert register_problems(register, tmp_path) == []


@pytest.mark.parametrize(
    ("register", "expected"),
    [
        ("", ["the register holds no requirement"]),
        (
            REGISTER.replace("| R2 | non-functional | `thing` | It is fast |\n", ""),
            ['`thing`: "It is fast" is in a spec and not in the register'],
        ),
        (
            REGISTER + "| R3 | functional | `thing` | It flies |\n",
            ["R3 names a requirement that no spec holds"],
        ),
        (
            REGISTER + "| R3 | functional | `thing` | It works |\n",
            ["R1 registers a requirement twice", "R3 registers a requirement twice"],
        ),
        (
            REGISTER.replace("| R2 | non", "| R5 | non"),
            ["the register's and the retired IDs do not run from R1 without a gap"],
        ),
        (
            REGISTER.replace("| R1 | fun", "| R3 | fun") + "\n- R1, removed by `old-change`\n",
            ["the register's IDs are not in order"],
        ),
        (
            REGISTER + "\n- R2, removed by `old-change`\n",
            [
                "the register's and the retired IDs do not run from R1 without a gap",
                "R2 is both registered and retired",
            ],
        ),
        (
            REGISTER.replace("non-functional", "nice-to-have"),
            ["R2 has a kind outside the list"],
        ),
    ],
)
def test_a_register_out_of_step_with_the_specs_is_reported(
    tmp_path: Path, register: str, expected: list[str]
) -> None:
    synthetic_specs(tmp_path)
    assert register_problems(register, tmp_path) == expected


def synthetic_features(root: Path, index: str, page: str) -> Path:
    features = root / "features"
    features.mkdir()
    (features / "README.md").write_text(index)
    (features / "working.md").write_text(page)
    return features


def test_a_complete_feature_folder_has_no_problem(tmp_path: Path) -> None:
    features = synthetic_features(tmp_path, "- [Working](working.md)\n", "**Requirements:** R1\n")
    assert feature_problems(REGISTER, features) == []


@pytest.mark.parametrize(
    ("index", "page", "expected"),
    [
        (
            "Nothing linked.\n",
            "**Requirements:** R1\n",
            ["working.md is not linked from the index"],
        ),
        (
            "- [Working](working.md)\n",
            "**Requirements:** R1, R9\n",
            ["working.md names R9, which the register does not hold"],
        ),
        (
            "- [Working](working.md)\n",
            "No requirements named.\n",
            [
                "working.md does not have one line naming its requirements",
                "R1 belongs to no feature page",
            ],
        ),
        (
            "- [Working](working.md)\n- [Gone](gone.md)\n",
            "**Requirements:** R1\n",
            ["the index links gone.md, which does not exist"],
        ),
        (
            "- [Working](working.md)\n",
            "**Requirements:** R2\n",
            ["R1 belongs to no feature page"],
        ),
    ],
)
def test_a_feature_folder_out_of_step_with_the_register_is_reported(
    tmp_path: Path, index: str, page: str, expected: list[str]
) -> None:
    features = synthetic_features(tmp_path, index, page)
    assert feature_problems(REGISTER, features) == expected


def test_a_features_folder_without_an_index_or_pages_is_reported(tmp_path: Path) -> None:
    (tmp_path / "features").mkdir()
    assert feature_problems(REGISTER, tmp_path / "features") == ["the features folder has no index"]
    (tmp_path / "features" / "README.md").write_text("Index.\n")
    assert feature_problems(REGISTER, tmp_path / "features") == ["the features folder has no page"]


WORKFLOW = """\
permissions:
  contents: read
jobs:
  report:
    permissions:
      contents: read
      pull-requests: write
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7
"""

HOW_IT_WORKS = """\
## Credentials and permissions

| Workflow | Job | Permissions |
|---|---|---|
| `report.yml` | `report` | `contents: read`, `pull-requests: write` |

## Connections to the outside world

- `actions/checkout`, from GitHub, over HTTPS.

## Flows

### A merge

```mermaid
flowchart LR
  A --> B
```
"""


def synthetic_workflow(root: Path, text: str = WORKFLOW) -> list[Path]:
    path = root / "report.yml"
    path.write_text(text)
    return [path]


def test_a_complete_how_it_works_page_has_no_problem(tmp_path: Path) -> None:
    assert how_it_works_problems(HOW_IT_WORKS, synthetic_workflow(tmp_path)) == []


@pytest.mark.parametrize(
    ("page", "expected"),
    [
        (
            HOW_IT_WORKS.replace(", `pull-requests: write`", ""),
            ["report.yml job `report` gets `pull-requests: write`, which is not listed"],
        ),
        (
            HOW_IT_WORKS.replace(
                "`pull-requests: write`", "`pull-requests: write`, `issues: write`"
            ),
            ["report.yml job `report` is listed with `issues: write`, not granted"],
        ),
        (
            HOW_IT_WORKS.replace("| `report.yml` | `report` |", "| `report.yml` | `other` |"),
            [
                "report.yml job `report` is not in the permissions table",
                "the permissions table lists report.yml job `other`, which no workflow has",
            ],
        ),
        (
            HOW_IT_WORKS.replace("`actions/checkout`", "a checkout"),
            ["report.yml runs `actions/checkout`, which is not listed"],
        ),
        (
            HOW_IT_WORKS.replace("```mermaid\nflowchart LR\n  A --> B\n```\n", "Words only.\n"),
            ["the flow 'A merge' has no diagram"],
        ),
        (
            HOW_IT_WORKS.replace("### A merge", "A merge"),
            ["how it works lists no flow"],
        ),
    ],
)
def test_a_how_it_works_page_missing_a_permission_action_or_diagram_is_reported(
    tmp_path: Path, page: str, expected: list[str]
) -> None:
    assert how_it_works_problems(page, synthetic_workflow(tmp_path)) == expected


def test_a_how_it_works_page_missing_a_section_is_reported(tmp_path: Path) -> None:
    page = HOW_IT_WORKS.replace("## Flows", "## Other")
    assert how_it_works_problems(page, synthetic_workflow(tmp_path)) == [
        "how it works has no section 'Flows'"
    ]


def test_each_job_gets_its_own_permissions_or_else_the_workflows() -> None:
    text = (
        "permissions: read-all\njobs:\n  a:\n    permissions:\n      actions: read\n"
        "  b:\n    runs-on: x\n"
    )
    assert granted(yaml.safe_load(text)) == {"a": {"actions: read"}, "b": {"read-all"}}
    assert granted(yaml.safe_load("jobs:\n  c:\n    runs-on: x\n")) == {"c": {DEFAULT}}


def test_a_widened_job_permission_is_reported_even_when_the_page_mentions_it(
    tmp_path: Path,
) -> None:
    widened = WORKFLOW.replace("contents: read\n      pull", "contents: write\n      pull")
    page = HOW_IT_WORKS + "\nIt needs no `contents: write`.\n"
    assert how_it_works_problems(page, synthetic_workflow(tmp_path, widened)) == [
        "report.yml job `report` gets `contents: write`, which is not listed",
        "report.yml job `report` is listed with `contents: read`, not granted",
    ]


def test_a_container_or_service_image_must_be_named(tmp_path: Path) -> None:
    text = (
        WORKFLOW
        + "    container: alpine@sha256:abc\n    services:\n      db:\n        image: postgres:16\n"
    )
    assert how_it_works_problems(HOW_IT_WORKS, synthetic_workflow(tmp_path, text)) == [
        "report.yml runs the image `alpine@sha256:abc`, which is not listed",
        "report.yml runs the image `postgres:16`, which is not listed",
    ]


def test_workflows_ending_in_yaml_are_collected(tmp_path: Path) -> None:
    folder = tmp_path / ".github" / "workflows"
    folder.mkdir(parents=True)
    (folder / "a.yml").write_text(WORKFLOW)
    (folder / "b.yaml").write_text(WORKFLOW)
    assert [p.name for p in workflows(tmp_path)] == ["a.yml", "b.yaml"]
