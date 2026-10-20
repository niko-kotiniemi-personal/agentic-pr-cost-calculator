# CI minutes

The report adds what the pull request's GitHub Actions runs cost, from the times GitHub gives for each job.

**Status:** designed, not built yet.

**Requirements:** R18

## Expected behaviour

- **Which runs.** Every attempt of every job of every workflow run on the pull request's own commits, created before the pull request merged. The pull request's own commits are those its head holds that the default branch did not hold before the merge.
- **Which runs are left out.** Runs that a push to the default branch started, the merge's own runs and the report's included, and runs on commits that a force-push removed.
- **Rounding.** Each attempt's duration is rounded up to a whole minute and priced at its runner type's rate for its day.
- **Unknown runners.** A job on a runner that the price table does not list is counted in minutes and left out of the cost, and the report says how many minutes that was.

## Not covered

- A pull request based on another that was merged by squashing or rebasing counts that one's runs again unless it is rebased first.
- Included minutes and plan discounts: the figure is at GitHub's list rate.

## See also

- `cost-pricing` in `openspec/`, and design decision 7 of `add-pr-cost-calculator`.
