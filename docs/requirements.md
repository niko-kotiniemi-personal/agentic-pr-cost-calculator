# Requirements

Every requirement the tool must meet, in one list. The specs under `openspec/` hold each requirement's full text and the scenarios that test it; this register is their index, so that what the product must do can be read in one place. `tests/test_documentation.py` checks that the register and the specs hold the same requirements, each once.

Each requirement has one kind:

- **functional:** what the tool does.
- **behavioural:** how it responds to conditions, failures and inputs it must refuse.
- **non-functional:** a quality it must keep, such as privacy, security, compatibility, or how it is released and documented.

The capability names the spec that holds the requirement. Each capability is one feature, and each requirement is on its capability's page in [`features/`](features/README.md).

| ID | Kind | Capability | Requirement |
|---|---|---|---|
| R1 | behavioural | `switch-and-opt-in` | Capture runs only where the tool is on and the person has opted in |
| R2 | functional | `usage-capture` | Usage is recorded per model call |
| R3 | functional | `usage-capture` | Only calls made from this repository are recorded |
| R4 | non-functional | `ledger` | The ledger holds counts, never content |
| R5 | behavioural | `usage-capture` | Counts are whole numbers |
| R6 | functional | `activity-types` | Each entry carries an activity type |
| R7 | functional | `usage-capture` | Usage reaches the pull request with the agent's commits |
| R8 | behavioural | `usage-capture` | A ledger file is staged only for a commit whose branch and contents the step can tell |
| R9 | behavioural | `usage-capture` | A ledger file that no commit takes is taken back |
| R10 | behavioural | `ledger` | A ledger file is written once |
| R11 | behavioural | `usage-capture` | Runs at the same time keep every record whole |
| R12 | non-functional | `usage-capture` | The capture step is one self-contained file |
| R13 | behavioural | `usage-capture` | Capture never breaks or steers the session |
| R14 | functional | `pricing` | Prices are dated |
| R15 | functional | `pricing` | Every token type is priced at its own rate |
| R16 | functional | `pricing` | Price modifiers are applied |
| R17 | behavioural | `pricing` | An unknown model is reported, not guessed |
| R18 | functional | `ci-minutes` | CI minutes are billed per job, rounded up |
| R19 | functional | `switch-and-opt-in` | One file turns the tool on or off, and a pull request cannot turn off its own report |
| R20 | functional | `report-comment` | A merged pull request gets one report comment |
| R21 | behavioural | `report-comment` | The comment shows only what the report computed |
| R22 | functional | `ledger` | The ledger is the record |
| R23 | behavioural | `report-comment` | The report reads the ledger from git, within bounds |
| R24 | non-functional | `report-comment` | The report runs only trusted code, with the least it needs |
| R25 | non-functional | `releases-and-compatibility` | The tool runs on the oldest supported Python and on every later release |
| R26 | non-functional | `releases-and-compatibility` | The oldest supported Python and major updates change only on the owner's decision |
| R27 | non-functional | `releases-and-compatibility` | Releases are made from a tag that matches the version and the changelog |
| R28 | non-functional | `releases-and-compatibility` | Every release carries a software bill of materials |
| R29 | non-functional | `project-standards` | The documentation names everything the tool does |
| R30 | non-functional | `project-standards` | The tool connects only where its documentation says |
| R31 | non-functional | `project-standards` | Every threat is rated for impact and likelihood |
| R32 | behavioural | `releases-and-compatibility` | The capture step does nothing below its floors |
| R33 | non-functional | `project-standards` | Pull request text carries no private reference |
| R34 | non-functional | `project-standards` | Every pinned action is a commit its repository tagged |
| R35 | behavioural | `report-comment` | Each ledger line is held to the ledger format |
| R36 | behavioural | `switch-and-opt-in` | Capture reads the configuration file only as a regular file within its bound |
| R37 | behavioural | `switch-and-opt-in` | The person's setting is read only from their global configuration files |
| R38 | behavioural | `switch-and-opt-in` | The setting is read by git's rules, and only some of git's true values opt a person in |
| R39 | behavioural | `switch-and-opt-in` | A repository's own git configuration can turn capture off |
| R40 | behavioural | `switch-and-opt-in` | Consent holds for each recorded call |
| R41 | functional | `usage-capture` | A call is identified by its message id and read from its lines that give a stop reason |
| R42 | functional | `usage-capture` | A call with no stop reason is read from its last line once it is over |
| R43 | functional | `usage-capture` | A call with an unknown usage field is recorded and counted |
| R44 | functional | `usage-capture` | Capture reads only lines that end in a line break, and no one line holds it back |
| R45 | functional | `usage-capture` | Capture reads the branch's ledger files only from git, and its git commands stay offline |
| R46 | functional | `usage-capture` | Calls recorded with no branch checked out go only to a commit made the same way |
| R47 | functional | `usage-capture` | Capture keeps what it records inside the common git directory |
| R48 | behavioural | `usage-capture` | A substitution counts as a command before the commit |
| R49 | behavioural | `usage-capture` | A ledger file is staged in the worktree where its commit runs |
| R50 | behavioural | `usage-capture` | A ledger file is added despite ignore rules and sparse checkouts, unless git refuses it |
| R51 | behavioural | `usage-capture` | A run that comes again before the same command stages nothing twice |
| R52 | behavioural | `usage-capture` | A ledger file that a commit takes stays taken |
| R53 | non-functional | `usage-capture` | The capture step's first line names its release |
| R54 | non-functional | `usage-capture` | The capture step starts only git, from an absolute path |
| R55 | behavioural | `usage-capture` | The store is versioned, and an unknown version is left alone |
| R56 | behavioural | `ledger` | The capture step stages only the ledger file it wrote |
| R57 | behavioural | `ledger` | A ledger file is noted before it is written |
| R58 | functional | `ledger` | Only the ledger files that the merge adds are counted |
| R59 | functional | `ledger` | Each call is counted at most once |
| R60 | functional | `ledger` | The job summary says how many ledger files a push without a comment removes or changes |
| R61 | functional | `pricing` | An unpriced attribute or combination is named, not guessed |
| R62 | functional | `ci-minutes` | Every job attempt of the pull request's own runs is counted |
| R63 | functional | `ci-minutes` | Minutes on a runner the price table does not list are counted, not priced |
| R64 | functional | `ci-minutes` | A CI cost missing any run or job is marked incomplete |
| R65 | functional | `report-comment` | A hook that does not come from the report's commit is named, not quoted |
| R66 | behavioural | `report-comment` | A ledger change larger than the size bound is refused |
| R67 | behavioural | `report-comment` | Ledger files that the default branch already holds are read by capture's rules |
| R68 | non-functional | `report-comment` | The report runs only for the push that a merge makes to the default branch |
| R69 | non-functional | `report-comment` | A push gets a comment only when all its commits belong to one pull request |
| R70 | non-functional | `report-comment` | The report keeps to a call budget and a time limit |
| R71 | non-functional | `releases-and-compatibility` | Versions are semantic, and their numbers say what an adopter must do |
| R72 | non-functional | `releases-and-compatibility` | A release is not published when its bill of materials is missing or fails a check |
| R73 | non-functional | `project-standards` | Each feature's page matches its spec |
| R74 | non-functional | `project-standards` | Each proposal says how its outcome is validated |

IDs are stable: a requirement keeps its ID while it exists, and a new one takes the next free number, so the rows follow the order in which requirements were added rather than the order of the specs. A requirement that a later change removes leaves the table, and its ID is listed below with the change that removed it, never to be used again.

## Retired IDs

None yet. An entry names the ID and the change that removed it, as in "R7, removed by `change-name`".
