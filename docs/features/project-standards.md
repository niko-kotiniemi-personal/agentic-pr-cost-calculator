# Product-wide standards

What holds for the whole product rather than for one feature: documentation that names everything the tool does, connections only where that documentation says, rated threats, pull request text without private references, and action pins that their repositories tagged.

**Status:** the documentation, the threat ratings and the workflow checks are in place; the network guard, the check of pull request text and the check of pins are designed, not built yet.

**Spec:** `project-standards`

**Requirements:** R29, R30, R31, R33, R34, R73, R74

## Expected behaviour

- **Documentation.** A register of every requirement, one page per feature, and [`../how-it-works.md`](../how-it-works.md), which names every credential, permission, connection and flow. Tests fail when the register and the specs disagree, when a workflow grants a permission or runs an action that the page does not name, and when a flow has no diagram.
- **Validation, written down.** Each feature is one spec, with a page that names all its requirements and says how the feature is validated, and each change's proposal says how each of its capabilities is validated. Tests fail when a page and its spec disagree, when a page is missing from the index, and when a proposal leaves a capability out.
- **Connections.** The hook opens no network connection. The report connects only to GitHub's REST API, at the address the workflow gives, over HTTPS, with the workflow's own token. Prices are read from the price table in the repository and never fetched.
- **Threats.** Every threat in [`../threat-model.md`](../threat-model.md) is rated for impact and likelihood from 1 to 3, with a risk that is their product, and placed in the one cell of the risk matrix that its ratings name. The threat model is reviewed independently before a design is approved, and again against what was built before its pull request merges.
- **Pull request text.** A pull request's title and body are checked against the same private patterns as the repository's files, each time the pull request is opened, edited, reopened or updated. A match fails the check, which names the pattern and quotes none of the text.
- **Pinned actions.** Every action and container image that a workflow uses is pinned to a full commit or a digest that a tag of its source names, so a commit that only a fork holds is refused.

## Not covered

- Whether a threat's answer still says what holds it. The tests check that each citation resolves; the reviews at design and before merge check what it says.

## How it is validated

This feature is validated first by its spec's scenarios: each whose code is still to be written gets an acceptance test before that code, seen to fail for the expected reason, and each that a check already in place holds is named in that check's test (task 1.4). Then come the checks that design decision 8 applies to all the tool's code. Beyond those, this feature has its own:

- Already in place: the documentation tests (tasks 1.12 and 1.17), the threat model's tests (task 1.10) and the workflow checks (task 1.16).
- To be built: the network guard's two rules (task 1.13), the check of pull request text (task 1.14), the check that every pin is a tagged commit (task 1.15), and a check that every network call and environment variable the tool's code reads is named in the documentation (task 5.3).
- By review rather than by a test: that the threat model is revisited before a design is approved and again against what was built (tasks 1.10 and 5.2).

## See also

- `project-standards` in `openspec/`, and design decisions 8, 9 and 12 of `add-pr-cost-calculator`.
