## Purpose

Let a repository turn the calculator on or off, and give each merged pull request a short, readable statement of what it cost.

## ADDED Requirements

### Requirement: One file turns the tool on or off, and a pull request cannot turn off its own report

A repository SHALL turn the calculator on by adding its configuration file with the tool enabled, and off by removing the file or disabling the tool in it. Capture SHALL read the configuration in the working tree. The report SHALL read it from the default branch as it was before the merge and as it is after, and SHALL run when either turns the tool on, so that the pull request that turns the tool off still gets its report, and so does the one that turns it on. When a pull request changes the configuration file, or any workflow file, its comment SHALL say so, because any workflow in the repository can run with the identity that posts the report.

#### Scenario: Disabled means silent

- **WHEN** a pull request merges, and the configuration disables the tool both before and after the merge
- **THEN** no comment is posted

#### Scenario: A pull request cannot turn off its own report

- **WHEN** a pull request that disables the tool merges
- **THEN** its report comment is posted

#### Scenario: The pull request that turns the tool on gets its report

- **WHEN** the pull request that adds the configuration file, with the tool enabled, merges
- **THEN** its report comment is posted

#### Scenario: A changed report is flagged

- **WHEN** a pull request changes the configuration file, the workflow file that runs the report, or another workflow file
- **THEN** its comment says that the pull request changed the tool's configuration or a workflow

### Requirement: A merged pull request gets one report comment

When a pull request merges with the tool on, the report SHALL post one comment giving the total cost; the cost by model, by token type and by activity type; the CI minutes and their cost, and how many of those minutes ran on runners that the price table does not list; the price table's date; the tool's version; the number of ledger entries it counted, and the number of entries and files it did not count, for each reason this capability gives; the number of calls that capture refused; and the number of calls that capture read without a stop reason, and, when there are any, that the token cost is a lower bound. It SHALL state that the figure is an API-equivalent estimate, not a bill, and that it counts the usage that the pull request's commits carry and the CI runs on those commits. When the report runs again, it SHALL update its earlier comment, and SHALL update only a comment that its own identity wrote.

#### Scenario: The comment states the totals

- **WHEN** a pull request with a ledger and CI runs merges
- **THEN** one comment is posted with the token cost, the CI cost and their total

#### Scenario: The comment says what the figure is

- **WHEN** the report posts its comment
- **THEN** the comment says that the figure is an API-equivalent estimate and not a bill, and that it counts the usage the pull request's commits carry and the CI runs on those commits, and names the price table's date and the tool's version

#### Scenario: Calls that capture refused are counted in the comment

- **WHEN** the ledger files that a pull request adds count calls that capture refused
- **THEN** the comment gives their number

#### Scenario: Calls read without a stop reason are counted in the comment

- **WHEN** the ledger files that a pull request adds count calls that capture read without a stop reason
- **THEN** the comment gives their number, and says that the token cost is a lower bound

#### Scenario: A pull request without a ledger says so

- **WHEN** a pull request merges with no ledger on its branch
- **THEN** the comment gives the CI cost and says that no agent usage was recorded

#### Scenario: Running the report twice posts one comment

- **WHEN** the report runs again for a pull request that already has its comment
- **THEN** the existing comment is updated and no second one is posted

#### Scenario: A planted marker does not redirect the update

- **WHEN** a comment written by someone else carries the report's marker
- **THEN** that comment is left unchanged, and the report posts or updates its own

### Requirement: The comment shows only what the report computed

The comment SHALL hold only numbers, the report's own fixed text, and model, attribute and runner names that the price table lists, shown as code. It SHALL NOT quote ledger lines, file names, branch names, job names, runner labels the price table does not list, or any other text from the pull request or from the jobs API. A ledger line that names a model or an attribute value that the price table does not list, other than `unknown`, SHALL be refused.

#### Scenario: A name with markup is not shown as written

- **WHEN** a ledger line names a model with a link, an image or an @-mention in it
- **THEN** the line is refused, and the comment contains none of that text

#### Scenario: A runner label with markup is not shown

- **WHEN** a job's runner labels, as the jobs API gives them, hold a link, an image or an @-mention
- **THEN** the comment contains none of that text

#### Scenario: Refused ledger lines are counted, not shown

- **WHEN** some ledger lines that the pull request adds are not valid entries
- **THEN** the comment says how many were refused and quotes none of them

### Requirement: The ledger is the record

The pull request's usage ledger SHALL remain on the default branch after merge, as its record, and the report SHALL write nothing to the repository. The report SHALL count only the entries of ledger files that the merge adds: files in the ledger folder that the default branch holds after the merge and did not hold before it. It SHALL count each call at most once: an added entry for a call that a ledger file on the default branch held before the merge SHALL NOT be counted, added entries for one call SHALL be counted once when they are identical, and SHALL all be refused when they differ. The comment SHALL say how many ledger files that the default branch held before the merge the pull request removed or changed, and SHALL count none of their entries.

#### Scenario: The ledger stays after merge

- **WHEN** a pull request with a ledger merges
- **THEN** the default branch holds the ledger files that pull request added, and the report has made no commit

#### Scenario: A reused branch name is not double-counted

- **WHEN** a pull request's branch still holds the ledger files of an earlier pull request merged from the same branch name
- **THEN** the report counts only the ledger files this pull request adds

#### Scenario: A copied entry is counted once

- **WHEN** a pull request adds an entry for a call that a ledger file on the default branch held before the merge
- **THEN** that entry is not counted

#### Scenario: One call added twice is counted once

- **WHEN** a pull request adds two identical entries for one call, in one ledger file or in two
- **THEN** that call is counted once

#### Scenario: Entries of one call that disagree are refused

- **WHEN** a pull request adds two entries for one call that differ
- **THEN** neither entry is counted, and both are counted as refused

#### Scenario: Removed or changed ledger files are flagged

- **WHEN** a pull request removes, changes or renames a ledger file that the default branch held before the merge
- **THEN** the comment says how many such files it removed or changed, and counts none of their entries

### Requirement: The report reads the ledger from git, within bounds

The report SHALL read ledger files only as blobs from git, never through the working tree. It SHALL refuse an added path in the ledger folder that is not a regular file, such as a symbolic link or a submodule, and SHALL learn each blob's size before reading it. It SHALL refuse the ledger change when the added ledger files are larger in total than the size bound that the ledger format documents, which capture applies to each ledger file it reads, and SHALL then still report the CI cost.

#### Scenario: An oversized ledger is refused

- **WHEN** the ledger files that a pull request adds exceed the size bound
- **THEN** the comment says the ledger was too large to read, and gives the CI cost

#### Scenario: A ledger that is a link is refused

- **WHEN** a pull request adds a symbolic link in the ledger folder
- **THEN** the report reads nothing through it, and the comment counts it as a refused file

### Requirement: The report runs only trusted code, with the least it needs

The report SHALL run only for a push that a merge makes to the default branch, and SHALL refuse every other event, including when the workflow that calls it was triggered by something else. It SHALL comment only when every commit that the push adds to the default branch's first-parent history belongs to one pull request. A push that merges no pull request SHALL get no comment. A push that merges more than one pull request, as a merge queue can, or that adds commits of no pull request beside a merge, SHALL get no comment either, and the report SHALL say so in its job summary, because it cannot tell which ledger files and runs belong to which. The report SHALL run only the tool's own code, from the commit at which the calling workflow pins the tool, and SHALL read the pull request's files only as data, never running, importing or installing anything from them. It SHALL use the workflow's own token, with no permissions beyond reading the repository and its Actions data and writing pull request comments, and SHALL never write the token to its output.

#### Scenario: No secret is configured

- **WHEN** the workflow runs in a repository that has added no secret for the tool
- **THEN** the report completes

#### Scenario: A fork's pull request gets its report

- **WHEN** a pull request opened from a fork merges
- **THEN** its report comment is posted

#### Scenario: Another event is refused

- **WHEN** the report is run for a pull request event, or for a push to a branch other than the default branch
- **THEN** it posts nothing, and its job fails

#### Scenario: A push that merges no pull request gets no comment

- **WHEN** a commit is pushed straight to the default branch, without a pull request
- **THEN** no comment is posted, and the job succeeds

#### Scenario: A push that merges several pull requests gets no comment

- **WHEN** one push to the default branch merges two pull requests
- **THEN** no comment is posted, and the job summary says that the push merged more than one pull request

#### Scenario: A push that adds other commits beside a merge gets no comment

- **WHEN** one push to the default branch adds a pull request's merge and a commit that belongs to no pull request
- **THEN** no comment is posted, and the job summary says that the push holds commits of no pull request

#### Scenario: Nothing from the pull request is run

- **WHEN** a merged pull request adds a Python module, a script or a requirements file
- **THEN** the report neither runs, imports nor installs any of them

#### Scenario: The token never reaches the output

- **WHEN** the report runs, whether it succeeds or fails
- **THEN** neither its log nor its comment contains the token
