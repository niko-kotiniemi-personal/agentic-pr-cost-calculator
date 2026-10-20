## Purpose

Turn recorded usage and CI job times into an API-equivalent cost, using the prices that applied on the day the usage happened.

## ADDED Requirements

### Requirement: Prices are dated

The price table SHALL give each price, and each statement of how modifiers combine, an effective date. A cost SHALL use, for each ledger entry or CI job, the latest price, and the latest statement of how modifiers combine, whose effective date is on or before the UTC day the usage happened, so that a row added later reprices nothing earlier. An entry whose day has no price yet SHALL be left out of the cost and named, and an entry dated after the day the report runs SHALL be refused.

#### Scenario: A price change applies from its date

- **WHEN** a model's output price changes on a date and a pull request has calls the day before and the day after
- **THEN** the earlier calls are priced at the old price and the later ones at the new price

#### Scenario: Usage before any known price is named, not priced

- **WHEN** an entry's day falls before the earliest effective date for its model
- **THEN** that entry is left out of the cost, and the report names its model and its day

#### Scenario: An entry from the future is refused

- **WHEN** an entry's day is after the day the report runs
- **THEN** the entry is refused, and counted as refused

#### Scenario: A changed combination reprices nothing earlier

- **WHEN** the price table adds a statement of how two modifiers combine for a model, dated after the statement before it, and a pull request has calls with both modifiers on the day before that date and on that date
- **THEN** the earlier calls are priced as the earlier statement says, and the later ones as the new one says

### Requirement: Every token type is priced at its own rate

Input, output, cache-write and cache-read tokens SHALL each be priced at their own rate. Cache writes SHALL use the rate for their cache lifetime. When the source does not give the lifetime, the cost SHALL show the range between the two lifetimes' prices.

#### Scenario: A call's cost is the sum of its token types

- **WHEN** an entry has input, output, five-minute cache-write and cache-read tokens
- **THEN** its cost is each count times its own rate, summed

#### Scenario: An unknown lifetime gives a range

- **WHEN** an entry's cache writes do not say their lifetime
- **THEN** the cost is reported as a low and a high figure

### Requirement: Price modifiers are applied or named

A call SHALL be priced with every modifier the price table lists for its model and day: higher rates for a prompt above a length, where a model has them; a multiplier for its inference region; rates for its speed and its service tier; and a per-request rate for server-side tool requests, such as web searches. A prompt's length SHALL count its input, cache-write and cache-read tokens. Modifiers SHALL combine as the price table's statement for the call's model and day says. A call with a recorded attribute whose value the price table does not price, or with a combination of attributes the table does not state, SHALL be counted in tokens, left out of the cost and named, as an unknown model is.

#### Scenario: A long prompt is priced at its higher rates

- **WHEN** a model has higher rates above a prompt length, and a call's input, cache-write and cache-read tokens together exceed that length
- **THEN** that call is priced at the higher rates

#### Scenario: A region multiplier applies to every token type

- **WHEN** a call records an inference region for which the price table gives a multiplier
- **THEN** each of that call's token costs is multiplied by it

#### Scenario: Web searches are priced per search

- **WHEN** a call records server-side web searches
- **THEN** they are priced at the table's per-search rate, in addition to the call's tokens

#### Scenario: Web fetches add nothing beyond their tokens

- **WHEN** a call records server-side web fetches, which the price table lists at no charge
- **THEN** the call is priced, and its cost is that of its tokens alone

#### Scenario: An unpriced attribute is named, not guessed

- **WHEN** a call records a speed for which the price table has no rate
- **THEN** the report shows that call's tokens, leaves it out of the cost, and names the model and that speed

#### Scenario: A fast speed is priced at its premium rates

- **WHEN** a call records a speed for which the price table gives premium rates, as it does for fast mode
- **THEN** each of that call's token types is priced at that speed's rate

#### Scenario: A service tier is priced at its own rates

- **WHEN** a call records a service tier for which the price table gives rates
- **THEN** each of that call's token types is priced at that tier's rate

#### Scenario: Modifiers combine as the price table states

- **WHEN** a call's prompt is above its model's long-prompt length, the call records an inference region that has a multiplier and a fast speed, and the price table states how those modifiers combine for its model and day
- **THEN** the call's cost is what that statement gives

#### Scenario: A combination the price table does not state is named, not guessed

- **WHEN** a call records attributes that call for two modifiers whose combination the price table does not state for its model and day
- **THEN** the report shows that call's tokens, leaves it out of the cost, and names the model and those attributes

### Requirement: An unknown model is reported, not guessed

A ledger entry whose model is `unknown`, because the capture step's price table did not list it, or whose model has no price, SHALL be counted in tokens and left out of the cost. The report SHALL name the model, or say that it is unknown, and say that its cost is missing.

#### Scenario: A new model has no price yet

- **WHEN** the ledger holds calls recorded with the model `unknown`, because the capture step's price table did not list their model
- **THEN** the report shows those calls' tokens, and says that their model is unknown and their cost is missing

### Requirement: CI minutes are billed per job, rounded up

The CI cost SHALL count every attempt of every job of every workflow run on the pull request's own commits that no push to the default branch started and that was created before the pull request merged. The pull request's own commits are those that its head holds and that the default branch did not hold before the merge, read from git, however many there are. So the runs that the merge's push starts SHALL NOT be counted, even when they run on one of the pull request's own commits, as after a fast-forward, and whatever their creation times; nor SHALL runs on any other commit, such as the new commits that a squash or rebase merge makes. The report SHALL find those runs with the fewest calls to GitHub's API that it can: a listing for each commit, or, where that takes fewer calls and GitHub returns the whole of it, the repository's runs listed page by page, filtered by their event and by when they were created. Each attempt's minutes SHALL be its duration rounded up to a whole minute, priced at the rate for its runner type on its UTC day. A job on a runner that the price table does not list SHALL be counted in minutes and left out of the cost, and the report SHALL say how many minutes ran on runners it could not price. If any run or job counted cannot be read, has not finished, or is left unread because the report's call budget ran out or because GitHub returned only part of a listing, the CI cost SHALL be marked incomplete, and SHALL NOT be presented as the total.

#### Scenario: A job's minutes are rounded up

- **WHEN** a job ran for 61 seconds on a standard Linux runner
- **THEN** it counts as two minutes at that runner's rate

#### Scenario: A re-run job counts every attempt

- **WHEN** a job ran twice, because its workflow run was re-run
- **THEN** the minutes of both attempts are counted

#### Scenario: Runs on other commits are not counted

- **WHEN** a workflow run's commit is not one of the pull request's commits
- **THEN** none of its jobs are counted

#### Scenario: Every commit is counted, beyond what the API lists

- **WHEN** a pull request has more commits than GitHub's pull request commit listing returns
- **THEN** the runs of all of its commits are counted

#### Scenario: A squash merge counts the runs on the pull request's commits

- **WHEN** a pull request whose commits ran CI is merged by squashing them into one new commit
- **THEN** the CI cost counts the runs on the pull request's own commits

#### Scenario: A rebase merge counts the runs on the pull request's commits

- **WHEN** a pull request whose commits ran CI is merged by rebasing them onto the default branch as new commits
- **THEN** the CI cost counts the runs on the pull request's own commits

#### Scenario: Runs that the merge starts are not counted

- **WHEN** the merge's push to the default branch starts workflow runs
- **THEN** none of their jobs are counted

#### Scenario: A fast-forward merge counts the pull request's runs, not the push's

- **WHEN** the default branch is moved forward to the pull request's head commit as it is, and that push starts workflow runs on the same commit, one of them with a creation time before the pull request's merge time
- **THEN** the runs created before the merge that the push did not start are counted, and none of the runs that the push started is

#### Scenario: A run that the pull request's closing starts is not counted

- **WHEN** a workflow on the pull request's `closed` event runs on its head commit, with a creation time at or after the pull request's merge time
- **THEN** none of its jobs are counted

#### Scenario: A job on a runner the price table does not list is not priced

- **WHEN** a job ran on a runner that the price table does not list
- **THEN** its minutes are counted and left out of the CI cost, and the report says how many minutes ran on runners it could not price

#### Scenario: An incomplete jobs listing is reported as incomplete

- **WHEN** the jobs of one of the pull request's runs cannot be read
- **THEN** the report marks the CI cost as incomplete

#### Scenario: A run that has not finished makes the cost incomplete

- **WHEN** a run on one of the pull request's commits has not finished when the report runs
- **THEN** none of its jobs are counted, and the report marks the CI cost as incomplete

#### Scenario: A pull request with more commits than the call budget allows is marked incomplete

- **WHEN** reading the runs and jobs of a pull request's own commits would take more calls to GitHub's API than the report's call budget leaves
- **THEN** the report reads no more than the budget allows, marks the CI cost as incomplete, and posts its comment

#### Scenario: A runs listing that GitHub cuts short is not taken as whole

- **WHEN** the repository's runs, filtered by their event and by when they were created, are more than GitHub returns for a filtered listing
- **THEN** the report reads the runs of the pull request's commits commit by commit instead, and counts every run on those commits that it would count otherwise
