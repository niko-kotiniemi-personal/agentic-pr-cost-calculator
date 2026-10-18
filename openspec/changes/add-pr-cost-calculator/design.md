# Design

## Context

See `proposal.md` for why. These facts shape the approach:

- Claude Code writes each session's transcript as JSON lines on the machine running the session. Each assistant message carries its model and a `usage` block with input, output, cache-write (split into five-minute and one-hour lifetimes) and cache-read tokens. Current versions also give the service tier, the speed, the inference region and the server-side tool requests, all of which can change the price. One message can be written over several transcript lines. In the main transcripts examined, every line of a message gave its stop reason and the same usage. Subagent transcripts were seen in two shapes. In some, a message's earlier lines gave partial usage and no stop reason, and only its last line gave the final usage and the stop reason. In others, almost no message had a line that gave a stop reason, the lines of a message almost always gave the same usage, and a few messages' only usage was plainly partial: a handful of output tokens for a message that thought and called tools.
- Each transcript line names the session's working directory at the time of the call. A call that works on files elsewhere through absolute paths, or that changes directory inside its own command, still names the directory it started from. The branch a line names was seen reading `HEAD` while a branch was checked out, so it is not used.
- Claude Code runs hooks at set points of a session. `Stop` runs when the main agent finishes responding, and not when the user interrupts it. `StopFailure` runs instead when a turn ends in an API error. `SubagentStop` runs when a subagent finishes, including the agents Claude Code runs for its own features, and names the subagent's own transcript as `agent_transcript_path`. `PreToolUse` runs before a tool call, with a Bash command's text in its input, and `PostToolUse` or `PostToolUseFailure` runs after it, as it succeeded or failed. A hook on a tool event can carry an `if` condition in permission-rule syntax, such as `Bash(git *)`, which matches any of the commands that a Bash input is made of. Every hook receives the transcript's path and the working directory. Claude Code documents that the transcript is written asynchronously and can lag behind the conversation, and that all matching hooks run in parallel. It creates its worktrees under `.claude/worktrees/` in the repository's folder.
- What a hook's exit code and output do, as Claude Code documents them: Claude never sees the standard error of a hook that exits 0. A `PreToolUse` hook that exits 2 blocks the tool call. A `Stop` or `SubagentStop` hook that exits 2 sends Claude back to work with the hook's standard error as the reason, unless its standard output is empty and its standard error says that a file is missing, which Claude Code treats as a non-blocking error. JSON printed on standard output can block or approve whatever the exit code, except that an exit of 2 blocks whatever the JSON says. Python exits 2 when it cannot open its script, and says that the file is missing or that permission is denied. A command hook's default timeout is 600 seconds, and a timed-out `PreToolUse` hook does not block the tool call.
- A repository's `.claude/settings.json` can set environment variables for everyone who works in it, and they reach every process Claude Code starts, its hooks included. Claude Code ignores some variables from project settings, among them `HOME` and the `XDG_*` variables. Git reads its global configuration from the file that `GIT_CONFIG_GLOBAL` names when it is set, and `GIT_CONFIG_COUNT` with its companion variables adds settings.
- A cloud session's machine is disposable, and the transcript is gone after it ends, so usage has to be captured during the session. Reading transcripts after the fact also turned out to be slow at the scale of a long pull request.
- GitHub's jobs API gives each job's start and end times with the default `GITHUB_TOKEN` and `actions: read`. It lists only the latest attempt of each job unless asked for all of them, and a job that has not finished has no end time. Its per-run "billable" timing figure was seen returning zero, so minutes are computed from job times.
- A squash merge puts one new commit on the default branch, and GitHub's rebase merge always makes new commits, so neither brings to the default branch the commits that CI ran on. A pull request's head stays readable from git as `refs/pull/<number>/head`.
- A reusable workflow receives its caller's `github` context, including the event that triggered the caller. The `job` context names the reusable workflow's own repository and commit. Events caused by `GITHUB_TOKEN`, such as a merge a workflow makes, start no new workflow run.
- Anthropic's pricing has modifiers beyond the four token rates: higher rates for long prompts on some models, a multiplier for US-only inference, premium rates for fast mode, and a charge per web search. Web fetches cost nothing beyond their tokens.

## Goals / Non-Goals

**Goals:**

- Capture with no service outside GitHub and the repository itself.
- Keep everything a public repository can publish: counts, prices and totals, never content.
- Publish a person's usage only with that person's consent, and only the calls their sessions make from the repository that publishes it.
- Make every number in a report reproducible from the ledger, the price table and the jobs API.
- Treat everything that crosses into the tool as untrusted: transcripts, ledgers, API data, and the pull request being reported. `docs/threat-model.md` lists the threats and what answers each.

**Non-Goals:**

- Billing reconciliation. The figure is an API-equivalent estimate, and plans, discounts and included minutes are not modelled.
- Agents other than Claude Code in this change. The ledger format is documented so they can be added later.
- The cost of AI code review on the pull request, such as the tokens a review app or a review job in CI spends. The owner decided on 2026-10-18 to leave it to a later change, which can add it once it is known where that usage can be read.
- Live cost while a pull request is open. The report runs at merge.
- GitHub Enterprise Server, which lacks the `job` context values that decision 7 relies on.

## Decisions

### 1. Capture with Claude Code hooks, into the git directory, then into the agent's own commits

One script is registered for six hook events: `Stop`, `SubagentStop` and `StopFailure`, and `PreToolUse`, `PostToolUse` and `PostToolUseFailure` for Bash commands, with the condition `Bash(git *)`, so that it starts only for commands that run git.

When a turn, a subagent or a failed turn ends, the script reads the session's transcript on from where it last stopped, and the subagents' own transcripts, which Claude Code keeps in a `subagents/` folder nested under the session's. It keeps each call whose line gives a working directory in this repository: one whose git common directory is this repository's, so that the repository's worktrees count and a separate repository nested in its folder does not. It records each such call in a store inside the repository's common git directory (`git rev-parse --git-common-dir`), outside the working tree and shared by every worktree, together with the worktree that the call's line names and the branch checked out there at that moment, or the fact that none was. It changes nothing in the working tree or the index, so it never blocks switching branches or rebasing.

A call's usage is read from its lines that give a stop reason. Where none does, as in one shape of subagent transcript, the call is read from its last line once it is over: once a later call follows it in the same transcript, or once its agent has stopped, which `Stop`, `StopFailure` and `SubagentStop` say. The ledger counts the calls read that way, because a few were seen with plainly partial usage, and the comment gives that count. A call that is not over yet waits for a later run.

Before a Bash command that runs `git commit` in this repository, the script first reads the transcripts as above. A command runs `git commit` when one of the commands it is made of, split as the shell splits it, is `git`, then any of git's own options, then `commit`, without `--dry-run`. The script then writes the calls recorded for this worktree and the branch now checked out there, which no ledger file holds yet, into one new file, `.pr-cost/ledger/<YYYY-MM>/<random>.jsonl`, created only if no file of that name exists, and stages that file alone, with `--force` so that an ignore rule cannot drop it. It writes nothing when the commit would commit nothing without the file, so a commit that would fail still fails, or when the command names the paths to commit, which leaves the rest of the index out. After the command, its `PostToolUse` or `PostToolUseFailure` run checks whether the new commit holds the file. If not, that run takes the file back, from the index and the working tree, and its calls wait for a later commit. No other run touches the index.

A call is recorded once, by a SHA-256 hash of its message id. The store and the ids in the ledger files that the branch holds together say which calls are already recorded, so a session resumed in a fresh clone records nothing again that its branch already holds. An entry records the UTC day of the call and not its time, because pricing needs only the day, and a time on every call would show when a contributor works. An entry records whether the main agent or a subagent made the call, and no session value.

The registered command is `python3 -I <script> || true`, with a timeout below Claude Code's default, and the script stops at a time budget inside that timeout, leaving what it has not read for its next run. Both values are set from measured run times when the hook is built. `|| true` matters because Python exits 2 when it cannot open its script, which a `PreToolUse` hook turns into a blocked commit, and a `Stop` hook into "keep working" when the script is unreadable rather than missing. The script prints nothing on standard output, and its standard error carries only its own words. Calls it refuses are counted in the ledger, because no one sees the standard error of a hook that succeeds.

The script is one file that imports only Python's standard library, because under `python3 -I` a script cannot import a module beside it, and adding its folder to the import path would undo what isolated mode is for. An adopter copies that file into their repository from a release tag and checks it against the SHA-256 checksum that the README gives for that tag. From then on it is reviewed and versioned with the rest of their repository, and an update is a pull request that replaces it. The file carries the model names and price attribute values of the price table it was released with, and records any other value as `unknown`, so that a gateway's private alias is not published.

A line's working directory is the session's, not where a call worked (see Context). So a session started in this repository that also works on another one, such as a private one, records those calls here. No rule over a transcript's working directories can tell them apart, and telling them apart by reading what each call did would mean reading commands, which can do anything. This is a residual (the threat model's T2), and the README tells a person who opts in to keep work on other repositories out of sessions started in a repository that has the tool on.

*Alternatives:* staging entries at the end of every turn, the first version of this design, which left the index changed between commits, so that in a test repository `git checkout` and `git rebase` refused to run; taking a ledger file that no commit took back at the next turn's end, the second version, which left it staged until then, where in a test repository it made `git rebase` refuse and followed `git checkout` to another branch, and where a run holding the index lock makes a commit fail; a `pre-commit` git hook, which would sit beside the repository's own git hooks and run for every commit, not just the agent's; delivering the script as a Claude Code plugin, which a repository's own session hook can install for everyone, as this repository's hook installs Superpowers, so it would give no stronger consent than the opt-in; reading transcripts after the session through an API, which is slow and depends on access a CI job does not have; a separate service the hook posts to, which the repository would have to run and trust; pushing a separate ref from the hook, which makes every turn a network write that can fail.

### 2. Python, standard library only

The hook runs on whatever machine the session uses, and the workflow runs on a stock runner. With no dependencies, both run with nothing to install, and nothing in the supply chain has to be pinned for users. Development tools (pytest, ruff, mypy, and the testing tools in decision 8) are pinned in `requirements-dev.txt`, and task 1.8 locks their own dependencies too, with hashes.

### 3. The ledger is the record, and the report writes nothing to the repository

*Decided by the owner, 2026-10-18.* Using the tool means the pull request is tracked; not tracking it means not turning the tool on. Supporting both inside the tool adds complexity for no gain.

The ledger reaches the default branch with the merge and stays there. It is the pull request's record, and the cost can be recomputed from it with the price table. The report only posts its comment, so it needs no `contents: write` and no exception in a ruleset that protects the default branch.

Because a ledger file is written once, under a random name, a pull request's usage is the ledger files its merge adds. Files the default branch already held, such as those that a reused branch name still carries from an earlier pull request, are not added again, so they are not counted again. An added entry whose call the default branch already held before the merge is not counted, and a change to an earlier ledger file is flagged, not counted. A removed ledger file is not lost: git history keeps it.

*Not chosen:* a record file that could be turned off, with a workflow commit removing the ledger at merge, which needs write access and adds a commit to every pull request; keeping the ledger on a side branch that is never merged, which needs a push from the hook on every turn.

### 4. A dated price table as data in the repository

`prices/models.json` and `prices/github-actions.json` list each price with its effective date and the source page it came from, including the modifiers in the last fact under Context, and web fetches at no charge. A change to a price is a pull request that adds a row dated after the rows already there, so history is never rewritten. Anthropic publishes no price API that could replace this.

### 5. Activity type from tool names

The type comes from the first tool call in a message: edits and writes are code generation, reads and searches are file reading, shell commands are tooling, `mcp__` tools are MCP, starting a subagent is subagent, a tool the classification does not know is other, and no tool call is conversation. The rule is simple enough to test fully and to explain in one line of the report. A review cannot be told apart from other work by tool names alone, so review is not a type in this change.

### 6. The repository turns the tool on, and each person turns on their own capture

*Decided by the owner, 2026-10-18.* In a public repository, publishing someone's usage needs their own consent.

`.pr-cost.json` at the repository root holds `enabled`. Capture reads it in the working tree. The report reads it from the default branch before and after the merge (decision 7), so the pull request being reported cannot turn its own report off. A file is visible in review and versioned with the code.

Capture also needs the consent of the person whose session it records: `pr-cost.capture` set to `true` in their global git configuration. The repository decides whether the tool is used there. Only the person decides whether their session's usage is published, so an outside contributor's usage is not committed merely because the repository's owner turned the tool on.

The script reads that setting from the global configuration files in the home directory, `~/.gitconfig` and git's file in the XDG configuration folder, and ignores the variables that point git at other files or add settings, because a repository's settings can set those for everyone who works in it, though not `HOME` or the `XDG_*` variables. One opt-in covers every repository that uses the tool, so `pr-cost.capture` set to `false` in a repository's own git configuration turns capture off there. Set to `true` there, it opts no one in.

*Not chosen:* the repository's setting alone, which would publish the usage of everyone who works in the repository, including people who never agreed to it.

### 7. The report runs on the push that a merge makes to the default branch

The tool provides a reusable workflow. A repository calls it from a workflow of its own, triggered by `push` to its default branch, which grants `contents: read`, `actions: read` and `pull-requests: write` and passes no secrets. The README gives that caller, pinned to a full commit of this tool.

A reusable workflow receives its caller's event, so the report checks the event itself and refuses anything but a push to the default branch. It checks out its own code by `job.workflow_repository` at `job.workflow_sha`, which name the reusable workflow's commit and not the caller's, and runs it with `python3 -I`, reading the caller's repository only as data.

The report finds the merged pull request with GitHub's "List pull requests associated with a commit", which for a commit on the default branch returns the merged pull request that introduced it. It looks up each commit that the push adds to the default branch's first-parent history, and when they do not all belong to one pull request, as when a merge queue merges several in one push, it posts no comment and says why in its job summary. It reads the ledger from git, comparing the push's commit before with the one after: the ledger files the merge adds, and the earlier ledger files it removes or changes. It reads `.pr-cost.json` at both commits, and runs when either turns the tool on, so the pull request that turns the tool on gets its report too.

The CI cost comes from the pull request's own commits, which the report reads from git as those that `refs/pull/<number>/head` holds and the default branch did not hold before the merge, because a squash or rebase merge brings new commits that no CI ran on. It counts the runs on those commits only, so the runs that the merge's push starts, its own included, are not counted, and a run on those commits that has not finished makes the CI cost incomplete. Commits that a force-push removed from the pull request's head are no longer in that ref, so runs on them are not counted, and the comment says that the CI minutes are those of the pull request's own commits.

The report flags a change to `.pr-cost.json` or to any workflow file, because any workflow in the repository can run with the identity that posts the comment, and so could change it later. Because the push belongs to the base repository, a pull request from a fork gets its report too.

A pull request can still change the calling workflow itself. It can remove it, so that its own merge goes unreported, or pin a different version of the tool. Either is in its diff for review, and a pull request that changes the workflow and still gets a report has that change flagged. A merge that a workflow makes with `GITHUB_TOKEN` starts no workflow run, so it gets no report.

*Alternatives:* the `pull_request` event when a pull request closes, whose token GitHub makes read-only for pull requests from forks, so those would get no report; `pull_request_target`, which gives a write token in the base repository's context while the pull request is still untrusted, and which GitHub's documentation says to avoid when a workflow builds or runs the pull request's code; reading the configuration after the merge only, which would let a pull request turn off its own report; taking the CI commits from the push's range, the second version of this design, which after a squash or rebase merge holds none of the commits that CI ran on; GitHub's lists of a pull request's files and commits, which return at most 3000 files and 250 commits.

### 8. Everything that can be tested is tested, and every check is shown to fail

A test that passes once shows that the code can pass. It does not show that the tests would notice the code breaking. So, for every behaviour:

- **Acceptance tests come first,** at least one per scenario, each seen failing for its expected reason before its code exists. They are kept as expected failures that may not pass early (`pytest.mark.xfail` with `strict=True` and the expected error), so CI stays green and meaningful while the code is built.
- **Traceability is a test.** Every scenario has a test that names it, every test that names a scenario names one that exists, and every threat in `docs/threat-model.md` cites a scenario, task, decision or file that exists.
- **Unit tests are positive and negative,** at every boundary: zero, one, the ceiling and one above it, and the values that Python accepts where it should not, such as `true` read as a number and not-a-number read from JSON.
- **Property-based tests** (Hypothesis) hold the invariants: no planted string reaches the ledger or the comment, a second capture changes nothing, the cost adds up across any split of the ledger, and no cost is negative. CI runs them derandomised, so a run can be repeated exactly.
- **Branch coverage is 100%** of the tool's code (coverage.py). Any exclusion carries its reason.
- **Mutation testing** (mutmut) changes the tool's code one small fault at a time and expects a test to fail each time. A surviving mutant fails CI, unless it is marked as making no difference, with the reason.
- **Every check is shown to fail.** Each CI gate has a test that plants the defect it exists for, and asserts that the gate fails for that reason. Each check also reports what it examined, and fails when that is nothing.
- **No test uses the network.** A test that opens a connection fails, and recorded responses stand in for GitHub's API.
- **A defect found becomes a test** that reproduces it, before the fix.
- **End to end:** the hook runs against fixture transcripts in a temporary git repository, the report runs against a temporary repository and recorded API responses, and this change's own merge is reported (task 6.1).
- **The change is reviewed in a context separate from the one that built it,** by `/simplify`, `/security-review`, `/code-review` and `/verify`, and every finding is fixed or answered before the owner merges.

The testing tools are added to `requirements-dev.txt` with the first code, at versions that have been out for at least the 14 days Renovate waits.

*Alternatives:* one failing example per task, then green, which shows the code can pass and little more; line coverage alone, which counts the lines that ran, not the faults the tests would catch.

## Risks / Trade-offs

- [Claude Code changes its transcript format] → The parser keeps to the fields it needs, refuses unknown shapes with a count instead of guessing, and its fixtures carry every shape seen in each kind of transcript, so a change shows up as a failing test. Two final lines of one call that disagree, or a usage block whose cache-write split disagrees with its total, are refused.
- [A call read without a stop reason can be partial] → The ledger counts such calls, and the comment gives the count and says that their usage may be low.
- [Calls made after the agent's last commit on a branch, such as pushing and opening the pull request, reach no commit] → They are not in the pull request's ledger unless a later commit carries them. The same holds for commits made other ways than `git commit`, such as `git merge`, `git cherry-pick`, a script, or a commit made through an API, whose calls wait for the agent's next `git commit`. The comment counts the usage that the pull request's commits carry, and the README says so.
- [A session works from a folder that contains the repository] → Its calls are not recorded, so its figure is too low. The README says to start a session in the repository.
- [A session started in the repository also works on another one] → Those calls are recorded here, because a call's working directory is the session's (decision 1). The README tells a person who opts in to keep other repositories' work, and above all private repositories', out of such sessions.
- [A session resumed in another clone, on another branch, records calls that an earlier branch's ledger files already hold] → The report never counts a call the default branch already held, so such a call is counted once across pull requests, for whichever merges first.
- [A force-push removes commits that CI ran on] → Their runs are not counted, and the comment says that the CI minutes are those of the pull request's own commits.
- [Capture fails without anyone seeing it, since a hook that succeeds shows nothing] → Refused calls are counted in the ledger, a failed run leaves its records for the next run, and a pull request whose capture never ran says that no agent usage was recorded.
- [A ledger edited by hand changes the reported cost] → The ledger is in the pull request's diff like any other file, and the report is an estimate, not a bill.
- [Cache writes recorded without their lifetime] → Decision 1 records the lifetime the transcript gives. Where it is absent, the report gives a range (see `cost-pricing`).
- [Prices go stale, or a new model appears] → Every report names the price table's date, and an unpriced model or attribute is named rather than guessed. A model the hook's copy of the price table does not list is recorded as `unknown` until the adopter updates the hook.
- [The report reads the call ids of every ledger file on the default branch, which grow with every pull request] → How long that takes is measured in the end-to-end test, and what to do about it is decided from that measurement.
- [Mutation testing takes time in CI] → Its duration is measured when it is added, and what to do about it is decided then, from that measurement.

## Open Questions

- Whether to show a reasoning-token count separately. It is part of output tokens and priced the same, so this changes only the report's layout.
