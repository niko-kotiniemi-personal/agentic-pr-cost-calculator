# Requirements

Every requirement the tool must meet, in one list. The specs under `openspec/` hold each requirement's full text and the scenarios that test it; this register is their index, so that what the product must do can be read in one place. `tests/test_documentation.py` checks that the register and the specs hold the same requirements, each once.

Each requirement has one kind:

- **functional:** what the tool does.
- **behavioural:** how it responds to conditions, failures and inputs it must refuse.
- **non-functional:** a quality it must keep, such as privacy, security, compatibility, or how it is released and documented.

The capability names the spec that holds the requirement. Each functional and behavioural requirement belongs to a page in [`features/`](features/README.md).

| ID | Kind | Capability | Requirement |
|---|---|---|---|
| R1 | behavioural | `usage-capture` | Capture runs only where the tool is on and the person has opted in |
| R2 | functional | `usage-capture` | Usage is recorded per model call |
| R3 | functional | `usage-capture` | Only calls made from this repository are recorded |
| R4 | non-functional | `usage-capture` | The ledger holds counts, never content |
| R5 | behavioural | `usage-capture` | Counts are whole numbers |
| R6 | functional | `usage-capture` | Each entry carries an activity type |
| R7 | functional | `usage-capture` | Usage reaches the pull request with the agent's commits |
| R8 | behavioural | `usage-capture` | A ledger file is staged only for a commit whose branch and contents the step can tell |
| R9 | behavioural | `usage-capture` | A ledger file that no commit takes is taken back |
| R10 | behavioural | `usage-capture` | A ledger file is written once |
| R11 | behavioural | `usage-capture` | Runs at the same time keep every record whole |
| R12 | non-functional | `usage-capture` | The capture step is one self-contained file |
| R13 | behavioural | `usage-capture` | Capture never breaks or steers the session |
| R14 | functional | `cost-pricing` | Prices are dated |
| R15 | functional | `cost-pricing` | Every token type is priced at its own rate |
| R16 | functional | `cost-pricing` | Price modifiers are applied or named |
| R17 | behavioural | `cost-pricing` | An unknown model is reported, not guessed |
| R18 | functional | `cost-pricing` | CI minutes are billed per job, rounded up |
| R19 | functional | `cost-reporting` | One file turns the tool on or off, and a pull request cannot turn off its own report |
| R20 | functional | `cost-reporting` | A merged pull request gets one report comment |
| R21 | behavioural | `cost-reporting` | The comment shows only what the report computed |
| R22 | functional | `cost-reporting` | The ledger is the record |
| R23 | behavioural | `cost-reporting` | The report reads the ledger from git, within bounds |
| R24 | non-functional | `cost-reporting` | The report runs only trusted code, with the least it needs |
| R25 | non-functional | `project-standards` | The tool runs on the oldest supported Python and on every later release |
| R26 | non-functional | `project-standards` | The oldest supported Python and major updates change only on the owner's decision |
| R27 | non-functional | `project-standards` | Releases follow semantic versioning and are made from a tag |
| R28 | non-functional | `project-standards` | Every release carries a software bill of materials |
| R29 | non-functional | `project-standards` | The documentation names everything the tool does |
| R30 | non-functional | `project-standards` | The tool connects only where its documentation says |
| R31 | non-functional | `project-standards` | Every threat is rated for impact and likelihood |
| R32 | behavioural | `project-standards` | The capture step does nothing below its floors |
| R33 | non-functional | `project-standards` | Pull request text carries no private reference |
| R34 | non-functional | `project-standards` | Every pinned action is a commit its repository tagged |
| R35 | behavioural | `cost-reporting` | Each ledger line is held to the ledger format |

IDs are stable: a requirement keeps its ID while it exists, and a new one takes the next free number, so the rows follow the order in which requirements were added rather than the order of the specs. A requirement that a later change removes leaves the table, and its ID is listed below with the change that removed it, never to be used again.

## Retired IDs

None yet. An entry names the ID and the change that removed it, as in "R7, removed by `change-name`".
