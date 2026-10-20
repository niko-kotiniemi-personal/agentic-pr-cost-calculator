# The usage ledger

The ledger is a set of small files under `.pr-cost/ledger/` that the agent's commits add. It carries the counts to the pull request, and after the merge it stays on the default branch as the pull request's record, so that every reported cost can be recomputed.

**Status:** designed, not built yet.

**Requirements:** R22, R4, R10

## Expected behaviour

- **One file per commit,** named `.pr-cost/ledger/<YYYY-MM>/<random>.jsonl`, one line per call. Each file is written once and never changed.
- **Counts, never content.** A line holds no prompt, response, code, file contents, tool name, path, branch name, user name, session identifier or time of day. The model's name and the price attributes are the only text taken from a transcript, and each is recorded only when the price table lists it, or else as `unknown`.
- **The record.** The ledger stays in the repository after the merge, and the report writes nothing to the repository.
- **Counted once.** The report counts only the ledger files that the merge adds, and each call once, however many files hold it. A ledger file that the pull request removes or changes is flagged in the comment and not counted, and a ledger file that a revert brings back is counted as restored, not again.
- **Visible in review.** The ledger is in the pull request's diff like any other file. Removing a ledger file before the merge removes its calls from the cost, and the hook never records them again in that clone.

## See also

- `usage-capture` and `cost-reporting` in `openspec/`, and design decision 3 of `add-pr-cost-calculator`.
- `docs/ledger-format.md`, which task 1.2 writes, for the exact format.
