"""The documentation says what the repository holds, and keeps saying it.

Three documents describe the tool, and each is checked against what it
describes, so that one cannot quietly fall behind:

- `docs/requirements.md` registers every requirement in the specs, once, with
  its kind. A requirement added to a spec and not to the register is reported,
  and so is a row for a requirement that no spec holds.
- `docs/features/` has one page per feature, and each feature is one spec. A
  page is named for its spec, names every requirement that the spec holds and
  no other, and says how the feature is validated; every spec has a page, and
  the index links every page.
- `docs/how-it-works.md` explains the tool as a whole. It names every
  permission that a workflow grants and every action that a workflow runs, and
  draws each flow it lists.

Each change's proposal is checked too: it lists every spec that the change
holds as a capability, and gives each a row of its own, with a statement, in
its section on how the outcome is validated.
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
PAGE_SPEC = re.compile(r"^\*\*Spec:\*\* `([a-z0-9-]+)`\s*$", re.M)
CAPABILITY_LINE = re.compile(r"^- `([a-z0-9-]+)`: ", re.M)
VALIDATION_ROW = re.compile(r"^\| `([a-z0-9-]+)` \|([^|\n]*)\|", re.M)
CHANGES = ROOT / "openspec" / "changes"
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
    capabilities = {row.capability for row in rows.values()}
    paged: set[str] = set()
    for page in pages:
        text = page.read_text(encoding="utf-8")
        if page.resolve() not in linked:
            problems.append(f"{page.name} is not linked from the index")
        specs = PAGE_SPEC.findall(text)
        named = PAGE_REQUIREMENTS.findall(text)
        if len(specs) != 1 or len(named) != 1:
            problems.append(
                f"{page.name} does not have one line naming its spec and one its requirements"
            )
            continue
        spec = specs[0]
        if page.stem != spec:
            problems.append(f"{page.name} is not named for its spec `{spec}`")
        if spec not in capabilities:
            problems.append(
                f"{page.name} names the spec `{spec}`, which the register does not hold"
            )
        paged.add(spec)
        idents = REQUIREMENT_ID.findall(named[0])
        for ident in idents:
            if ident not in rows:
                problems.append(f"{page.name} names {ident}, which the register does not hold")
            elif rows[ident].capability != spec:
                problems.append(
                    f"{page.name} names {ident}, which `{rows[ident].capability}` holds"
                )
        problems += [
            f"{ident} is not on the page for `{spec}`"
            for ident, row in rows.items()
            if row.capability == spec and ident not in idents
        ]
        if not section(text, "How it is validated").strip():
            problems.append(f"{page.name} does not say how it is validated")
    for link in sorted(linked):
        if not link.is_file():
            problems.append(f"the index links {link.name}, which does not exist")
    for capability in sorted(capabilities - paged):
        held = ", ".join(ident for ident, row in rows.items() if row.capability == capability)
        problems.append(f"`{capability}` has no feature page for {held}")
    return problems


def proposal_problems(proposal: str, specs: set[str]) -> list[str]:
    listed = CAPABILITY_LINE.findall(section(proposal, "Capabilities"))
    problems = [
        f"`{name}` is a spec the proposal does not list" for name in sorted(specs - set(listed))
    ]
    problems += [
        f"the proposal lists `{name}`, which has no spec" for name in sorted(set(listed) - specs)
    ]
    validated = {
        name: cell.strip()
        for name, cell in VALIDATION_ROW.findall(section(proposal, "How the outcome is validated"))
    }
    problems += [
        f"the proposal does not say how `{name}` is validated"
        for name in sorted(specs)
        if not validated.get(name)
    ]
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


PAGE = (
    "**Spec:** `thing`\n\n**Requirements:** R1, R2\n\n## How it is validated\n\nBy its scenarios.\n"
)


def synthetic_features(root: Path, index: str, page: str, name: str = "thing.md") -> Path:
    features = root / "features"
    features.mkdir(parents=True)
    (features / "README.md").write_text(index)
    (features / name).write_text(page)
    return features


def test_a_complete_feature_folder_has_no_problem(tmp_path: Path) -> None:
    features = synthetic_features(tmp_path, "- [Thing](thing.md)\n", PAGE)
    assert feature_problems(REGISTER, features) == []


@pytest.mark.parametrize(
    ("index", "page", "expected"),
    [
        ("Nothing linked.\n", PAGE, ["thing.md is not linked from the index"]),
        (
            "- [Thing](thing.md)\n",
            PAGE.replace("R1, R2", "R1, R2, R9"),
            ["thing.md names R9, which the register does not hold"],
        ),
        (
            "- [Thing](thing.md)\n",
            PAGE.replace("**Requirements:** R1, R2\n", "No requirements named.\n"),
            [
                "thing.md does not have one line naming its spec and one its requirements",
                "`thing` has no feature page for R1, R2",
            ],
        ),
        (
            "- [Thing](thing.md)\n",
            PAGE.replace("**Spec:** `thing`\n", ""),
            [
                "thing.md does not have one line naming its spec and one its requirements",
                "`thing` has no feature page for R1, R2",
            ],
        ),
        (
            "- [Thing](thing.md)\n- [Gone](gone.md)\n",
            PAGE,
            ["the index links gone.md, which does not exist"],
        ),
        (
            "- [Thing](thing.md)\n",
            PAGE.replace("R1, R2", "R2"),
            ["R1 is not on the page for `thing`"],
        ),
        (
            "- [Thing](thing.md)\n",
            PAGE.replace("R1, R2", "R1"),
            ["R2 is not on the page for `thing`"],
        ),
        (
            "- [Thing](thing.md)\n",
            PAGE.replace("## How it is validated\n\nBy its scenarios.\n", ""),
            ["thing.md does not say how it is validated"],
        ),
        (
            "- [Thing](thing.md)\n",
            PAGE.replace("By its scenarios.\n", ""),
            ["thing.md does not say how it is validated"],
        ),
    ],
)
def test_a_feature_folder_out_of_step_with_the_register_is_reported(
    tmp_path: Path, index: str, page: str, expected: list[str]
) -> None:
    features = synthetic_features(tmp_path, index, page)
    assert feature_problems(REGISTER, features) == expected


def test_a_page_is_named_for_its_spec_and_holds_only_its_spec_requirements(
    tmp_path: Path,
) -> None:
    features = synthetic_features(tmp_path, "- [Other](other.md)\n", PAGE, name="other.md")
    assert feature_problems(REGISTER, features) == ["other.md is not named for its spec `thing`"]
    register = REGISTER + "| R3 | functional | `else` | It flies |\n"
    features = synthetic_features(
        tmp_path / "b", "- [Thing](thing.md)\n", PAGE.replace("R1, R2", "R1, R2, R3")
    )
    assert feature_problems(register, features) == [
        "thing.md names R3, which `else` holds",
        "`else` has no feature page for R3",
    ]


def test_a_page_for_a_spec_the_register_does_not_hold_is_reported(tmp_path: Path) -> None:
    ghost = "**Spec:** `ghost`\n\n**Requirements:** none\n\n## How it is validated\n\nBy review.\n"
    features = synthetic_features(tmp_path, "- [Ghost](ghost.md)\n", ghost, name="ghost.md")
    assert feature_problems(REGISTER, features) == [
        "ghost.md names the spec `ghost`, which the register does not hold",
        "`thing` has no feature page for R1, R2",
    ]


def test_a_features_folder_without_an_index_or_pages_is_reported(tmp_path: Path) -> None:
    (tmp_path / "features").mkdir()
    assert feature_problems(REGISTER, tmp_path / "features") == ["the features folder has no index"]
    (tmp_path / "features" / "README.md").write_text("Index.\n")
    assert feature_problems(REGISTER, tmp_path / "features") == ["the features folder has no page"]


def change_problems(changes: Path) -> list[str]:
    problems = []
    for proposal in sorted(changes.rglob("proposal.md")):
        specs = {spec.parent.name for spec in (proposal.parent / "specs").glob("*/spec.md")}
        text = proposal.read_text(encoding="utf-8")
        problems += [f"{proposal.parent.name}: {p}" for p in proposal_problems(text, specs)]
    return problems


def test_each_proposal_lists_its_specs_and_says_how_each_is_validated() -> None:
    assert list(CHANGES.rglob("proposal.md")), "no proposal was found, so this test covered nothing"
    problems = change_problems(CHANGES)
    assert not problems, "\n".join(problems)


PROPOSAL = (
    "## Capabilities\n\n### New Capabilities\n\n- `thing`: does it.\n\n"
    "## How the outcome is validated\n\n| `thing` | by its scenarios |\n"
)


def test_a_proposal_out_of_step_with_its_specs_is_reported() -> None:
    assert proposal_problems(PROPOSAL, {"thing"}) == []
    assert proposal_problems(PROPOSAL, {"thing", "else"}) == [
        "`else` is a spec the proposal does not list",
        "the proposal does not say how `else` is validated",
    ]
    assert proposal_problems(PROPOSAL, set()) == ["the proposal lists `thing`, which has no spec"]


@pytest.mark.parametrize(
    "row",
    ["", "| `thing` |  |", "`thing` is not validated yet."],
    ids=["no row", "an empty row", "a mention that is not a row"],
)
def test_a_capability_without_a_validation_row_is_reported(row: str) -> None:
    unvalidated = PROPOSAL.replace("| `thing` | by its scenarios |", row)
    assert proposal_problems(unvalidated, {"thing"}) == [
        "the proposal does not say how `thing` is validated"
    ]


def test_a_capability_listed_outside_its_section_is_not_counted() -> None:
    elsewhere = PROPOSAL.replace("- `thing`: does it.\n\n", "") + (
        "\n## Impact\n\n- `thing`: does it.\n"
    )
    assert proposal_problems(elsewhere, {"thing"}) == [
        "`thing` is a spec the proposal does not list"
    ]


def test_a_validation_row_outside_its_section_is_not_counted() -> None:
    elsewhere = PROPOSAL.replace("| `thing` | by its scenarios |\n", "") + (
        "\n## Impact\n\n| `thing` | by its scenarios |\n"
    )
    assert proposal_problems(elsewhere, {"thing"}) == [
        "the proposal does not say how `thing` is validated"
    ]


def test_every_change_is_checked_against_its_own_specs(tmp_path: Path) -> None:
    for name in ("one", "archive/2026-01-01-two"):
        spec = tmp_path / name / "specs" / "thing" / "spec.md"
        spec.parent.mkdir(parents=True)
        spec.write_text("### Requirement: It works\n")
        (tmp_path / name / "proposal.md").write_text(PROPOSAL)
    assert change_problems(tmp_path) == []
    for name in ("one", "archive/2026-01-01-two"):
        (tmp_path / name / "specs" / "else").mkdir()
        (tmp_path / name / "specs" / "else" / "spec.md").write_text("### Requirement: It flies\n")
    assert change_problems(tmp_path) == [
        "2026-01-01-two: `else` is a spec the proposal does not list",
        "2026-01-01-two: the proposal does not say how `else` is validated",
        "one: `else` is a spec the proposal does not list",
        "one: the proposal does not say how `else` is validated",
    ]


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
