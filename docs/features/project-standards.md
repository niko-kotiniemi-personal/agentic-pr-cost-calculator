# Product-wide standards

What holds for the whole product rather than for one feature: documentation that names everything the tool does, connections only where that documentation says, rated threats, pull request text without private references, action pins that their repositories tagged, and a record of each decision.

**Status:** the documentation, the threat ratings, the workflow checks and the decision records are in place; the network guard, the check of pull request text and the check of pins are designed, not built yet.

**Spec:** `project-standards`

**Requirements:** R29, R100, R101, R30, R31, R33, R34, R73, R74, R124, R125, R126, R127, R128, R129, R130, R131, R132, R133, R134

## Expected behaviour

- **Documentation.** A register of every requirement, one page per feature, and [`../how-it-works.md`](../how-it-works.md), which names every credential, permission, connection and flow. Tests fail when the register and the specs disagree, when a workflow grants a permission or runs an action that the page does not name, and when a flow has no diagram.
- **Validation, written down.** Each feature is one spec, with a page that names all its requirements and says how the feature is validated, and each change's proposal says how each of its capabilities is validated. Tests fail when a page and its spec disagree, when a page is missing from the index, and when a proposal leaves a capability out.
- **Connections.** The hook opens no network connection. The report connects only to GitHub's REST API, at the address the workflow gives, over HTTPS, with the workflow's own token. Prices are read from the price table in the repository and never fetched.
- **Threats.** Every threat in [`../threat-model.md`](../threat-model.md) is rated for impact and likelihood from 1 to 3, with a risk that is their product, and placed in the one cell of the risk matrix that its ratings name. The threat model is reviewed independently before a design is approved, and again against what was built before its pull request merges.
- **Pull request text.** A pull request's title and body are checked against the same private patterns as the repository's files, each time the pull request is opened, edited, reopened or updated. A match fails the check, which names the pattern and quotes none of the text.
- **Pinned actions.** Every action and container image that a workflow uses is pinned to a full commit or a digest that a tag of its source names, so a commit that only a fork holds is refused.
- **Decision records.** Each decision has a record of its own in [`../decisions/`](../decisions/README.md), holding one choice: its type, its status, who decided it, the requirements and threats it shapes, why it was made, what else was considered, what follows from it and what reversing it would change. An index lists every record. Once the default branch holds a record, it is never edited or removed, only closed by the record that replaces it, after which lines of its text may become `[removed]`, so each decision can be reversed on its own and its history stays readable. Tests fail when a record is out of form, holds anything but plain ASCII text, names something that does not exist, or changes other than by being closed, when the records' folder holds anything but the records and their index, when an attribute hides a record's diff, when the index and the records disagree, when a threat leaves out a record that lists it, when a document gives a record a title that is not its own, and when a document outside the history follows a closed record. Threat IDs, like requirement IDs, are retired rather than reused, so a record never comes to cite another threat.

## Not covered

- Whether a threat's answer still says what holds it. The tests check that each citation resolves; the reviews at design and before merge check what it says.
- Whether a decision record holds one choice, describes rather than instructs, and says what its sources say, and whether the owner made a decision that a record attributes to the owner. The reviews check the first three, and the owner checks the last before merging.

## How it is validated

This feature is validated first by its spec's scenarios: each whose code is still to be written gets an acceptance test before that code, seen to fail for the expected reason, and each that a check already in place holds is named in that check's test (task 1.4). Then come the checks that DR-084 to DR-093 and DR-109 apply to all the tool's code. Beyond those, this feature has its own:

- Already in place: the documentation tests (tasks 1.12 and 1.17), the threat model's tests (task 1.10), the workflow checks (task 1.16) and the decision records' tests (task 1.18).
- To be built: the network guard's two rules (task 1.13), the check of pull request text (task 1.14), the check that every pin is a tagged commit (task 1.15), and a check that every network call and environment variable the tool's code reads is named in the documentation (task 5.3).
- By review rather than by a test: that the threat model is revisited before a design is approved and again against what was built (tasks 1.10 and 5.2).

## See also

- `project-standards` in `openspec/`, design decisions 8, 9, 12 and 13 of `add-pr-cost-calculator`, and the decision records' [index](../decisions/README.md).
