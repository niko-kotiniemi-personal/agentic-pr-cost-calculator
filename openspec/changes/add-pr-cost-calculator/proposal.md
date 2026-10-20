# Proposal

## Why

Teams that build pull requests with AI coding agents can see what a pull request changed, but not what it cost. The tokens a session spent and the CI minutes its pushes used are recorded in different places, in raw form, and nobody adds them up per pull request. A trial on real Claude Code sessions confirmed that the data exists: each session's transcript records per-message token usage by model, and GitHub's jobs API gives each CI job's start and end times. What's missing is a tool that collects it while the work happens and reports it when the pull request merges.

## What Changes

- A capture step for Claude Code, run by session hooks. It records each model call's token counts, model, price attributes, UTC day and activity type, and adds them to the agent's own commits as small usage ledger files. It records only calls made while the session's working directory is in the repository, and only for people who have turned it on for themselves. It records counts only, never prompts, code, tool names or transcript text.
- A dated price table in this repository, for model tokens by type and for GitHub Actions minutes by runner. A cost uses the price that applied on the day the usage happened.
- A cost step that turns the ledger and the CI jobs that ran on the pull request's own commits into a cost per model, per token type, per activity type and in total, applying the price modifiers the price table lists.
- A report at merge: one short comment on the pull request, posted by a workflow that runs on the push a merge makes to the default branch. The usage ledger stays in the repository as the pull request's record, and the report writes nothing else.
- A switch in one configuration file that turns the tool on or off for a repository. The report reads it from before the merge as well as after, so a pull request cannot turn off its own report.
- Code is Python, standard library only, supporting Python 3.11 and every later release, with synthetic test fixtures. It is delivered as a session hook script and a GitHub Actions workflow other repositories can use.
- A threat model, `docs/threat-model.md`, which every later change revisits. Each threat's answer is a scenario in these specs wherever it can be one, so an acceptance test holds it.
- Each threat rated for impact and likelihood, from 1 to 3, with a risk matrix, and the threat model revisited by an independent review at design and again at implementation (design decision 9).
- Releases by semantic version from a tag, each with a CycloneDX bill of materials, and dependency updates that keep the oldest supported Python unless it nears its end of life (design decisions 10 and 11).
- Documentation that names everything the tool does: a register of the requirements, a page per feature, and a page explaining the tool as a whole, with its flows, credentials, permissions and connections, each checked against the specs and the workflows (design decision 12).
- Verification that tests everything that can be tested: acceptance tests first, property-based tests, full branch coverage, mutation testing, every check shown to fail, and a review in a separate context before merge (design decision 8).

## Capabilities

### New Capabilities

- `usage-capture`: recording what an agent session spent, model call by model call, onto the branch it worked on.
- `cost-pricing`: the dated price table and how a cost is computed from usage and CI job times.
- `cost-reporting`: the switch, the merge-time comment, and the ledger kept as the record.
- `project-standards`: the supported Python versions, how dependencies move, releases and their bill of materials, documentation that names everything the tool does, the tool's connections, and the rating of threats.

### Modified Capabilities

None. This repository has no specs yet.

## Impact

- New: the standard files of an open-source project (a contributing guide, a code of conduct, a changelog, issue and pull request templates, code owners and an editor configuration), a release workflow, the requirements register, the feature pages and the page explaining the tool.
- New: a hook script for Claude Code, as one file that an adopter copies from the commit that their workflow pins, a reusable GitHub Actions workflow, a price table, the threat model, and their tests.
- Development tools added with the first code: coverage.py, Hypothesis, mutmut, and detect-secrets, which checks that a ledger file does not look like a secret to a common scanner, pinned like the others.
- A repository that adopts the tool gains a configuration file, the ledger files that each pull request's commits add, which stay after merge as the record, and a workflow of its own that runs on pushes to the default branch and calls the tool's reusable workflow, granting it only `pull-requests: write` to comment, `actions: read` to read job times and `contents: read` to read the ledger.
- Each person whose sessions should be recorded turns capture on in their own global git configuration. A call made while the session's working directory is in the repository is recorded there even when it works on another repository, so work on other repositories belongs in sessions of its own.
- Agents other than Claude Code are out of scope for this change. The ledger format is documented, so other agents can write it later.
- Shell commands sent through Claude Code's PowerShell tool, as on Windows, are out of scope too: the hooks are registered for Bash, so a commit or a change of branch made through that tool is not seen. The hooks that run when a turn or a session ends still run there, and the registered command is written to exit with success in PowerShell too.
- The cost of AI code review on the pull request is out of scope for this change too, as the owner decided on 2026-10-18. A later change can add it once it is known where that usage can be read.
