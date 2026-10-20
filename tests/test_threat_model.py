"""The threat model's answers point at things that exist.

`docs/threat-model.md` lists each threat with what holds its answer: a scenario
in a spec, a task or a decision of a change, or a file in this repository. A
citation that names nothing reads as a control while holding none, so every
citation must resolve, and every threat must cite something or say why it is
accepted.

Every threat is also rated for impact and likelihood, from 1 to 3 each, and its
risk is their product. The risk matrix places each threat in the cell its two
ratings name, so a reader sees at a glance where the risk sits, and a rating
changed in one place and not the other is reported.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
THREAT_MODEL = ROOT / "docs" / "threat-model.md"

FIELDS = ("Kind", "Impact", "Likelihood", "Risk", "What could happen", "Answer", "Held by")
KINDS = {
    "spoofing",
    "tampering",
    "repudiation",
    "information disclosure",
    "denial of service",
    "elevation of privilege",
    "reliability",
}
IMPACTS = {1: "low", 2: "medium", 3: "high"}
LIKELIHOODS = {1: "unlikely", 2: "possible", 3: "likely"}

HEADING = re.compile(r"^### (T(\d+))\. .+$", re.M)
ANY_HEADING = re.compile(r"^#{1,3} ", re.M)
FIELD = re.compile(r"^- \*\*([^*]+):\*\* ?(.*)$", re.M)
SCENARIO = re.compile(r"^#### Scenario: (.+?)\s*$", re.M)
SCENARIO_REF = re.compile(r'`([a-z0-9-]+)`: "([^"]+)"')
TASK_REF = re.compile(r"`([a-z0-9-]+)` task (\d+\.\d+)")
DECISION_REF = re.compile(r"`([a-z0-9-]+)` decision (\d+)")
PATH_REF = re.compile(r"`([^`\s]+)`")
ARCHIVE_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}-")
RATING = re.compile(r"([1-3]) \(([a-z]+)\)")
MATRIX_HEADING = re.compile(r"^## Risk matrix$", re.M)
MATRIX_ROW = re.compile(r"^\| ([1-3]) [a-z]+ \|(.*)\|\s*$", re.M)
THREAT_ID = re.compile(r"T\d+")


@dataclass(frozen=True)
class Threat:
    ident: str
    number: int
    fields: dict[str, list[str]]


@dataclass(frozen=True)
class Index:
    scenarios: dict[str, set[str]]
    changes: dict[str, Path]


def threats_in(text: str) -> list[Threat]:
    marks = list(HEADING.finditer(text))
    found = []
    for mark in marks:
        body = text[mark.end() :]
        following = ANY_HEADING.search(body)
        if following:
            body = body[: following.start()]
        fields: dict[str, list[str]] = {}
        for field in FIELD.finditer(body):
            fields.setdefault(field.group(1), []).append(field.group(2).strip())
        found.append(Threat(mark.group(1), int(mark.group(2)), fields))
    return found


def index(root: Path) -> Index:
    scenarios: dict[str, set[str]] = {}
    for spec in sorted((root / "openspec").rglob("spec.md")):
        scenarios.setdefault(spec.parent.name, set()).update(SCENARIO.findall(spec.read_text()))
    changes: dict[str, Path] = {}
    base = root / "openspec" / "changes"
    for folder in sorted(base.glob("*")) + sorted((base / "archive").glob("*")):
        if folder.is_dir() and folder.name != "archive":
            changes[ARCHIVE_DATE.sub("", folder.name)] = folder
    return Index(scenarios, changes)


def citation_problems(ident: str, held: str, found: Index, root: Path) -> tuple[list[str], int]:
    problems: list[str] = []
    cited = 0
    for capability, name in SCENARIO_REF.findall(held):
        cited += 1
        if name not in found.scenarios.get(capability, set()):
            problems.append(f'{ident} cites `{capability}`: "{name}", which no spec holds')
    rest = SCENARIO_REF.sub("", held)
    for change, number in TASK_REF.findall(rest):
        cited += 1
        tasks = found.changes[change] / "tasks.md" if change in found.changes else None
        line = re.compile(rf"^- \[[ x]\] {re.escape(number)} ", re.M)
        if tasks is None or not tasks.is_file() or not line.search(tasks.read_text()):
            problems.append(f"{ident} cites `{change}` task {number}, which does not exist")
    rest = TASK_REF.sub("", rest)
    for change, number in DECISION_REF.findall(rest):
        cited += 1
        design = found.changes[change] / "design.md" if change in found.changes else None
        heading = re.compile(rf"^### {re.escape(number)}\. ", re.M)
        if design is None or not design.is_file() or not heading.search(design.read_text()):
            problems.append(f"{ident} cites `{change}` decision {number}, which does not exist")
    rest = DECISION_REF.sub("", rest)
    for path in PATH_REF.findall(rest):
        cited += 1
        target = (root / path).resolve()
        if root.resolve() not in target.parents or not target.exists():
            problems.append(f"{ident} cites `{path}`, which is not a file in this repository")
    return problems, cited


def problems_in(text: str, root: Path) -> tuple[list[str], int]:
    threats = threats_in(text)
    if not threats:
        return ["no threat found"], 0
    problems: list[str] = []
    numbers = [threat.number for threat in threats]
    if numbers != list(range(1, len(threats) + 1)):
        problems.append(f"threats are not numbered T1 to T{len(threats)} in order: {numbers}")
    found = index(root)
    cited = 0
    for threat in threats:
        missing = [name for name in FIELDS if not threat.fields.get(name)]
        doubled = [name for name, values in threat.fields.items() if len(values) > 1]
        if missing or doubled:
            problems.append(f"{threat.ident} lacks {missing} or repeats {doubled}")
            continue
        kinds = [kind.strip() for kind in threat.fields["Kind"][0].split(",")]
        unknown = [kind for kind in kinds if kind not in KINDS]
        if unknown:
            problems.append(f"{threat.ident} has a kind outside the list: {unknown}")
        problems += rating_problems(threat)
        held = threat.fields["Held by"][0]
        if held.lower().startswith("accepted"):
            if not re.match(r"accepted: \S", held):
                problems.append(f"{threat.ident} is accepted without a reason")
            continue
        found_problems, count = citation_problems(threat.ident, held, found, root)
        problems += found_problems
        cited += count
        if count == 0:
            problems.append(f"{threat.ident} cites nothing and is not accepted")
    problems += matrix_problems(text, threats)
    return problems, cited


def rating(value: str, levels: dict[int, str]) -> int | None:
    match = RATING.fullmatch(value)
    if not match or levels.get(int(match.group(1))) != match.group(2):
        return None
    return int(match.group(1))


def rating_problems(threat: Threat) -> list[str]:
    impact = rating(threat.fields["Impact"][0], IMPACTS)
    likelihood = rating(threat.fields["Likelihood"][0], LIKELIHOODS)
    problems = []
    if impact is None:
        problems.append(f"{threat.ident} has an impact outside the list")
    if likelihood is None:
        problems.append(f"{threat.ident} has a likelihood outside the list")
    if impact and likelihood and threat.fields["Risk"][0] != str(impact * likelihood):
        problems.append(f"{threat.ident} has a risk that is not impact times likelihood")
    return problems


def matrix_problems(text: str, threats: list[Threat]) -> list[str]:
    heading = MATRIX_HEADING.search(text)
    if not heading:
        return ["no risk matrix found"]
    body = text[heading.end() :]
    following = ANY_HEADING.search(body)
    if following:
        body = body[: following.start()]
    placed: dict[str, list[tuple[int, int]]] = {}
    rows = MATRIX_ROW.findall(body)
    for impact, cells in rows:
        columns = [cell.strip() for cell in cells.split("|")]
        if len(columns) != len(LIKELIHOODS):
            return [f"the risk matrix row for impact {impact} does not have three columns"]
        for likelihood, cell in enumerate(columns, start=1):
            for ident in THREAT_ID.findall(cell):
                placed.setdefault(ident, []).append((int(impact), likelihood))
    if sorted(int(impact) for impact, _ in rows) != sorted(IMPACTS):
        return ["the risk matrix does not have one row for each impact"]
    problems = []
    for threat in threats:
        expected = [
            (
                rating(threat.fields.get("Impact", [""])[0], IMPACTS) or 0,
                rating(threat.fields.get("Likelihood", [""])[0], LIKELIHOODS) or 0,
            )
        ]
        if placed.pop(threat.ident, []) != expected:
            problems.append(f"{threat.ident} is not in the one risk matrix cell its ratings name")
    problems += [f"the risk matrix names {ident}, which is not a threat" for ident in placed]
    return problems


def test_every_threat_cites_what_holds_its_answer() -> None:
    problems, cited = problems_in(THREAT_MODEL.read_text(), ROOT)
    assert not problems, "\n".join(problems)
    assert cited, "no citation was checked, so this test covered nothing"


def synthetic_repository(root: Path) -> None:
    change = root / "openspec" / "changes" / "demo"
    (change / "specs" / "thing").mkdir(parents=True)
    (change / "specs" / "thing" / "spec.md").write_text("#### Scenario: It works\n")
    (change / "tasks.md").write_text("- [ ] 1.1 Do it\n- [x] 1.2 Did it\n")
    (change / "design.md").write_text("### 1. A choice\n")
    old = root / "openspec" / "changes" / "archive" / "2026-01-01-old"
    old.mkdir(parents=True)
    (old / "tasks.md").write_text("- [x] 3.1 Done long ago\n")
    (root / "docs").mkdir()
    (root / "docs" / "note.md").write_text("A file.\n")


MATRIX = (
    "## Risk matrix\n\n"
    "| Impact \\ Likelihood | 1 unlikely | 2 possible | 3 likely |\n"
    "|---|---|---|---|\n"
    "| 3 high | | | |\n"
    "| 2 medium | | | |\n"
    "| 1 low | {low} | | |\n"
)


def matrix(low: str = "T1") -> str:
    return MATRIX.format(low=low)


def threat(
    held: str,
    number: int = 1,
    kind: str = "tampering",
    impact: str = "1 (low)",
    likelihood: str = "1 (unlikely)",
    risk: str = "1",
) -> str:
    return (
        f"### T{number}. Something goes wrong\n\n"
        f"- **Kind:** {kind}\n"
        f"- **Impact:** {impact}\n"
        f"- **Likelihood:** {likelihood}\n"
        f"- **Risk:** {risk}\n"
        "- **What could happen:** a thing.\n"
        "- **Answer:** another thing.\n"
        f"- **Held by:** {held}\n"
    )


def test_citations_that_exist_resolve(tmp_path: Path) -> None:
    synthetic_repository(tmp_path)
    held = (
        '`thing`: "It works"; `demo` task 1.1; `demo` task 1.2; `old` task 3.1; '
        "`demo` decision 1; `docs/note.md`"
    )
    assert problems_in(threat(held) + matrix(), tmp_path) == ([], 6)


def test_an_accepted_risk_with_its_reason_cites_nothing(tmp_path: Path) -> None:
    synthetic_repository(tmp_path)
    text = threat("accepted: the report is an estimate.") + matrix()
    assert problems_in(text, tmp_path) == ([], 0)


@pytest.mark.parametrize(
    ("held", "expected"),
    [
        ('`thing`: "It fails"', 'cites `thing`: "It fails", which no spec holds'),
        ('`other`: "It works"', 'cites `other`: "It works", which no spec holds'),
        ("`demo` task 9.9", "cites `demo` task 9.9, which does not exist"),
        ("`missing` task 1.1", "cites `missing` task 1.1, which does not exist"),
        ("`demo` decision 2", "cites `demo` decision 2, which does not exist"),
        ("`docs/absent.md`", "cites `docs/absent.md`, which is not a file in this repository"),
        ("`../outside.md`", "cites `../outside.md`, which is not a file in this repository"),
        ("the hook, somehow", "cites nothing and is not accepted"),
        ("accepted", "is accepted without a reason"),
    ],
)
def test_a_citation_that_names_nothing_is_reported(
    tmp_path: Path, held: str, expected: str
) -> None:
    synthetic_repository(tmp_path)
    (tmp_path.parent / "outside.md").write_text("Outside the repository.\n")
    problems, _ = problems_in(threat(held) + matrix(), tmp_path)
    assert [problem for problem in problems if expected in problem], problems


def test_a_threat_without_its_fields_is_reported(tmp_path: Path) -> None:
    synthetic_repository(tmp_path)
    text = threat("`docs/note.md`").replace("- **Answer:** another thing.\n", "") + matrix()
    problems, _ = problems_in(text, tmp_path)
    assert problems == ["T1 lacks ['Answer'] or repeats []"]


def test_a_repeated_field_is_reported(tmp_path: Path) -> None:
    synthetic_repository(tmp_path)
    text = threat("`docs/note.md`") + "- **Held by:** `docs/note.md`\n" + matrix()
    problems, _ = problems_in(text, tmp_path)
    assert problems == ["T1 lacks [] or repeats ['Held by']"]


def test_kinds_and_impacts_come_from_their_lists(tmp_path: Path) -> None:
    synthetic_repository(tmp_path)
    text = threat("`docs/note.md`", kind="tampering, mischief", impact="huge") + matrix()
    problems, _ = problems_in(text, tmp_path)
    assert problems == [
        "T1 has a kind outside the list: ['mischief']",
        "T1 has an impact outside the list",
        "T1 is not in the one risk matrix cell its ratings name",
    ]


@pytest.mark.parametrize(
    ("impact", "likelihood", "risk", "expected"),
    [
        ("3 (high)", "2 (possible)", "6", []),
        ("2 (medium)", "3 (likely)", "6", []),
        ("3 (medium)", "1 (unlikely)", "3", ["T1 has an impact outside the list"]),
        ("high", "1 (unlikely)", "3", ["T1 has an impact outside the list"]),
        ("1 (low)", "4 (certain)", "4", ["T1 has a likelihood outside the list"]),
        ("1 (low)", "2 (likely)", "2", ["T1 has a likelihood outside the list"]),
        ("2 (medium)", "2 (possible)", "2", ["T1 has a risk that is not impact times likelihood"]),
        (
            "3 (high)",
            "3 (likely)",
            "9 (high)",
            ["T1 has a risk that is not impact times likelihood"],
        ),
    ],
)
def test_a_rating_is_a_level_from_its_list_and_risk_is_their_product(
    tmp_path: Path, impact: str, likelihood: str, risk: str, expected: list[str]
) -> None:
    synthetic_repository(tmp_path)
    held = "`docs/note.md`"
    text = threat(held, impact=impact, likelihood=likelihood, risk=risk)
    problems, _ = problems_in(text + matrix(""), tmp_path)
    assert [p for p in problems if "risk matrix" not in p] == expected


def test_each_threat_sits_in_the_matrix_cell_its_ratings_name(tmp_path: Path) -> None:
    synthetic_repository(tmp_path)
    text = threat("`docs/note.md`", impact="3 (high)", likelihood="2 (possible)", risk="6")
    placed = MATRIX.format(low="").replace("| 3 high | | | |", "| 3 high | | T1 | |")
    assert problems_in(text + placed, tmp_path) == ([], 1)


@pytest.mark.parametrize(
    ("low", "expected"),
    [
        ("", ["T1 is not in the one risk matrix cell its ratings name"]),
        ("T1, T1", ["T1 is not in the one risk matrix cell its ratings name"]),
        ("T1, T2", ["the risk matrix names T2, which is not a threat"]),
    ],
)
def test_a_threat_missing_doubled_or_unknown_in_the_matrix_is_reported(
    tmp_path: Path, low: str, expected: list[str]
) -> None:
    synthetic_repository(tmp_path)
    problems, _ = problems_in(threat("`docs/note.md`") + matrix(low), tmp_path)
    assert problems == expected


def test_a_threat_in_the_wrong_cell_is_reported(tmp_path: Path) -> None:
    synthetic_repository(tmp_path)
    moved = MATRIX.format(low="").replace("| 2 medium | | | |", "| 2 medium | T1 | | |")
    problems, _ = problems_in(threat("`docs/note.md`") + moved, tmp_path)
    assert problems == ["T1 is not in the one risk matrix cell its ratings name"]


def test_a_matrix_that_is_missing_or_malformed_is_reported(tmp_path: Path) -> None:
    synthetic_repository(tmp_path)
    text = threat("`docs/note.md`")
    assert problems_in(text, tmp_path)[0] == ["no risk matrix found"]
    short = matrix().replace("| 2 medium | | | |\n", "")
    assert problems_in(text + short, tmp_path)[0] == [
        "the risk matrix does not have one row for each impact"
    ]
    narrow = matrix().replace("| 1 low | T1 | | |", "| 1 low | T1 | |")
    assert problems_in(text + narrow, tmp_path)[0] == [
        "the risk matrix row for impact 1 does not have three columns"
    ]


def test_threats_are_numbered_in_order(tmp_path: Path) -> None:
    synthetic_repository(tmp_path)
    text = threat("`docs/note.md`", number=1) + "\n" + threat("`docs/note.md`", number=3)
    problems, _ = problems_in(text + matrix("T1, T3"), tmp_path)
    assert problems == ["threats are not numbered T1 to T2 in order: [1, 3]"]


def test_a_document_without_threats_is_reported(tmp_path: Path) -> None:
    synthetic_repository(tmp_path)
    assert problems_in("# Threat model\n\nNothing here.\n", tmp_path) == (["no threat found"], 0)
