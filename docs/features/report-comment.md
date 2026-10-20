# The report comment

When a pull request merges with the tool on, a workflow posts one short comment on it with what it cost.

**Status:** designed, not built yet.

**Requirements:** R20, R21, R23, R35

## Expected behaviour

- **What it shows.** The total cost; the cost by model, by token type and by activity type; the CI minutes and their cost; the price table's date; the tool's version; how many ledger entries were counted, and how many were not, for each reason; how many calls capture refused; how many it read without a stop reason, and how many carried a usage field that capture does not know, with a note that the token cost is then a lower bound. It also says when the hook file at the merged commit differs from the one at the report's own commit.
- **What it says about itself.** That the figure is an API-equivalent estimate, not a bill, and that it counts the usage that the pull request's commits carry and the CI runs on those commits. Calls that Claude Code's own tools make to a model, such as a web fetch's summary, are counted only where the transcript records them.
- **Only its own words.** The comment, the job summary and the log hold numbers, the report's fixed text, and names that the price table lists. It never quotes ledger lines, file names, branch names, job names or any other text from the pull request.
- **One comment.** A second run updates the report's own comment and no one else's.
- **Within bounds.** The report reads ledger files from git as data, refuses anything in the ledger folder that is not a regular file, and refuses a ledger change above the documented size bound while still reporting the CI cost. Each ledger line is held to the ledger format: a count that is not a whole number within the ceiling, a field given twice or unknown, a line nested too deeply or a day that is not a date is refused and counted, and the report completes.
- **When there is no comment.** A push that merges no pull request, or more than one, or that has more commits than the report's call budget allows, gets no comment, and the report says why in its job summary. A pull request with more commits than the budget allows is marked incomplete.

## See also

- `cost-reporting` in `openspec/`, and design decision 7 of `add-pr-cost-calculator`.
