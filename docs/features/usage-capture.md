# Usage capture

While a Claude Code session works in the repository, a hook records what each model call spent, and the agent's own commits carry those records to the pull request. Nothing is sent anywhere: the records stay on the machine until a commit takes them.

**Status:** designed, not built yet.

**Requirements:** R2, R3, R5, R7, R8, R9, R10, R11, R13

## Expected behaviour

- **What is recorded.** For each model call, once: its UTC day, its model, a hash of its message id, whether the main agent or a subagent made it, and its input, output, cache-write and cache-read tokens. Where the transcript gives them, it also records the attributes that change the price: service tier, speed, inference region and server-side tool requests.
- **Where from.** Only calls made while Claude's working directory is in this repository or one of its worktrees. Calls made from anywhere else, including another repository that the same session works in, are not recorded here.
- **When.** The hook runs when Claude finishes responding, when a subagent finishes, when a turn ends in an API error, when the session ends, and before and after each Bash command that runs git.
- **How it reaches the pull request.** Just before the agent's `git commit`, the hook writes the waiting calls into one new ledger file and stages it, so that the commit takes it. It does this only for a commit whose branch and contents it can tell from the command. Otherwise the calls wait for a later commit.
- **When no commit takes the file.** If the commit fails, is refused, is cancelled or never runs, the hook takes the file back, and its calls wait for a later commit.
- **Counts are checked.** A count that is not a whole number within the documented ceiling is refused, and the ledger says how many calls were refused.
- **Two runs at once.** Runs at the same time, such as a session's and a subagent's, never split each other's records or record one call twice.
- **It never gets in the way.** A failure in the hook never stops the session. The hook prints nothing that Claude reads, writes no transcript text anywhere, and stops at a time budget, leaving the rest for its next run.

## Not covered

- Commits the hook cannot follow: `git merge`, `git cherry-pick`, `git rebase --continue`, a script, an API, a commit in the background, in a pipeline, a subshell or a group, joined by `||` or behind a wrapper, and commits made through Claude Code's PowerShell tool. Their calls wait, and may reach no pull request. The design's risks list every such case.
- Agents other than Claude Code.

## See also

- `usage-capture` in `openspec/` for the full requirements and their scenarios.
- Design decision 1 of `add-pr-cost-calculator`, and its risks.
