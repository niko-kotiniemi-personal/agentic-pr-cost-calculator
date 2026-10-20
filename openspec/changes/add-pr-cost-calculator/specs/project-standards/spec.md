## Purpose

Keep the tool easy to adopt and easy to trust: it runs on the Python that adopters already have, it is released in versions whose numbers say what changed, every release says what it is made of, and its documentation says everything it does, so that anything it does that the documentation leaves out is a defect.

## ADDED Requirements

### Requirement: The tool runs on the oldest supported Python and on every later release

The hook and the report SHALL run on Python 3.11, the oldest version this change supports, and on every later release, with the standard library only. CI SHALL run the tests on the oldest supported version and on the newest release, and `requires-python` in `pyproject.toml` SHALL be the one source of the oldest supported version: a test SHALL fail when any other copy of it disagrees, among them the versions that ruff and mypy check against, the CI matrix, `.python-version`, the bill of materials, the hook's own guard, and the documents that state it.

#### Scenario: The tests run on the oldest supported Python

- **WHEN** CI runs on a pull request
- **THEN** the tests run on Python 3.11 and on the newest Python release, and the `ci` check fails if either fails

#### Scenario: Code that needs a newer Python fails on the oldest

- **WHEN** a change uses a feature of the standard library or of the language that Python 3.11 lacks
- **THEN** CI fails on the oldest version's job, or ruff or mypy reports it

#### Scenario: Declared versions that disagree are reported

- **WHEN** a setting or a document names an oldest supported Python other than the one `requires-python` gives, or the CI matrix lacks either the oldest version or the newest release
- **THEN** a test fails and names the copy that differs

### Requirement: The capture step does nothing below its floors

The capture step SHALL check, before anything else, that it runs under Python 3.11 or later, and, before its first other git command, that git is 2.43 or later, the oldest git that CI tests. Below either floor it SHALL record nothing, stage nothing, print nothing and exit with success.

#### Scenario: An older Python is refused quietly

- **WHEN** the capture step starts under a Python older than 3.11
- **THEN** it records and stages nothing, prints nothing, and exits with success

#### Scenario: An older git is refused quietly

- **WHEN** the capture step finds a git older than 2.43
- **THEN** it records and stages nothing, prints nothing, and exits with success

### Requirement: The oldest supported Python and major updates change only on the owner's decision

The oldest supported Python SHALL rise only when its version nears its end of life, or when a security fix needs a newer one, and the change SHALL be recorded as a decision with its reason. Dependency updates SHALL be proposed freely for minor and patch versions and for vulnerability fixes, and a major update SHALL wait for the owner's approval on Renovate's dependency dashboard.

#### Scenario: A major update waits for the owner

- **WHEN** Renovate finds a major update of a dependency or a pinned tool
- **THEN** it lists the update on the dependency dashboard and opens no pull request until the owner approves it there

#### Scenario: A minor or patch update is proposed

- **WHEN** Renovate finds a minor or patch update that has been out for the wait the configuration sets
- **THEN** it opens a pull request without waiting for approval

#### Scenario: A vulnerability fix is not held back

- **WHEN** Renovate finds an update that fixes a known vulnerability, whatever its type
- **THEN** it opens a pull request without waiting for approval or for the release age

### Requirement: Releases follow semantic versioning and are made from a tag

A release SHALL be made only by pushing a tag `vMAJOR.MINOR.PATCH` that names a commit in the default branch's first-parent history, and the release workflow SHALL check the tag's form before any other step, and SHALL refuse a tag whose version differs from the version in `pyproject.toml` or that has no entry in `CHANGELOG.md`. The version SHALL raise its major number for a change that existing adopters must act on, which is any change to the public surface: the hook file's registered command, by its form and not the checksum it carries, and its path, the opt-in key, the ledger path and format, the store's format, the configuration file, the reusable workflow's path, inputs and permissions, and the Python and git floors. A manifest of that surface SHALL be kept in the repository, and the release workflow SHALL compare it between the previous release's commit and the tag. It SHALL raise its minor number for a change that adds behaviour without breaking any of these, and its patch number for a fix alone. A changelog entry that lists a breaking change, or a release whose surface manifest changed, SHALL come with a raised major number and a `### Breaking` section. The release's own text SHALL name the tag and the commit in the workflow's fixed words, and SHALL carry the changelog entry after them.

#### Scenario: A tag that matches the version and the changelog is released

- **WHEN** a tag `v1.2.0` is pushed for a commit on the default branch whose `pyproject.toml` says `1.2.0` and whose changelog has an entry for `1.2.0`
- **THEN** a GitHub release `v1.2.0` is published that names the commit and carries the changelog entry

#### Scenario: A tag that does not match the version is refused

- **WHEN** a tag `v1.2.0` is pushed for a commit whose `pyproject.toml` says another version, or whose changelog has no entry for `1.2.0`
- **THEN** no release is published and the workflow says which of the two disagrees

#### Scenario: A tag on a commit outside the default branch's first-parent history is refused

- **WHEN** a release tag names a commit that is not in the default branch's first-parent history, such as a commit from inside a merged pull request or one that only a fork holds
- **THEN** no release is published

#### Scenario: A tag that is not a semantic version stops the workflow first

- **WHEN** a pushed tag is not `v` followed by a semantic version, such as one holding shell characters
- **THEN** the workflow fails before any other step and publishes nothing

#### Scenario: A changed public surface needs a major version

- **WHEN** the surface manifest at the tag differs from the one at the previous release's commit, and the changelog entry has no `### Breaking` section or the major number does not rise
- **THEN** no release is published, and the workflow names what changed

#### Scenario: A breaking change raises the major version

- **WHEN** the changelog entry for a release lists a breaking change and the release does not raise the major number over the previous release
- **THEN** no release is published and the workflow says why

### Requirement: Every release carries a software bill of materials

Each release SHALL carry a software bill of materials in CycloneDX JSON, written by a standard-library Python script in this repository from the tagged tree, never from a working tree. It SHALL name the tool, its version, the commit it was built from, its licence, the oldest supported Python as `requires-python` gives it, the hook file's SHA-256, each action the reusable workflow uses at its pinned commit, and the vendored and generated parts as development-only components with their source and licence. A release SHALL NOT be published when its bill of materials cannot be written, when its reusable workflow uses an action that the bill of materials does not list, when the hook checksum in it differs from the hook file's or the README's, or when the private-reference check finds a match in it or in the release's text.

#### Scenario: The bill of materials describes the release

- **WHEN** a release is published
- **THEN** a CycloneDX JSON file is attached that names the tool, the release's version and commit, the MIT licence, the oldest supported Python, the hook file's checksum, each action the reusable workflow uses, and the development-only components

#### Scenario: An action missing from the bill of materials stops the release

- **WHEN** the reusable workflow uses an action that the bill of materials does not list, or the hook checksum in it differs from the hook file's or the README's
- **THEN** no release is published

#### Scenario: A release without a bill of materials is not published

- **WHEN** writing the bill of materials fails
- **THEN** no release is published

### Requirement: The documentation names everything the tool does

The repository SHALL keep a register of every requirement, with its kind, one page for each feature, and one page that explains the tool as a whole. That page SHALL name every credential and permission the tool uses, as a table per workflow and per job, every connection it makes to the outside world, with where to, by which protocol and why, and every flow, each drawn as a diagram. Tests SHALL fail when the register misses a requirement in the specs or names one they do not hold, when a functional or behavioural requirement belongs to no feature page, when a workflow, whether its file ends in `.yml` or `.yaml`, grants a permission in any job that the page's table does not give for that job, or the table gives one that the job is not granted, when a workflow runs an action or a container or service image that the page does not name, and when a flow has no diagram.

#### Scenario: A requirement missing from the register fails CI

- **WHEN** a spec gains a requirement that the register does not list
- **THEN** a test fails and names the requirement

#### Scenario: A requirement without a feature fails CI

- **WHEN** a functional or behavioural requirement belongs to no feature page
- **THEN** a test fails and names the requirement

#### Scenario: An undocumented permission or action fails CI

- **WHEN** a job of any workflow is granted a permission that the page's table does not give for that job, or the table gives a job a permission it is not granted, or a workflow runs an action or an image that the page does not name
- **THEN** a test fails and names the workflow, the job and the permission, or the action or image

### Requirement: Pull request text carries no private reference

CI SHALL check a pull request's title and body against the same private patterns and name hashes that the repository's tracked files are checked against, and SHALL fail when either matches, naming the pattern and quoting none of the text. The check SHALL run when a pull request is opened, edited, reopened or updated, read the text from the event, and keep its patterns in one module that the repository's tests share.

#### Scenario: A pull request body with a private reference fails CI

- **WHEN** a pull request's title or body holds a text that one of the private patterns or name hashes matches
- **THEN** the check fails, names the pattern, and quotes none of the text

#### Scenario: An edited body is checked again

- **WHEN** a pull request's body is edited to add such a text
- **THEN** the check runs again and fails

### Requirement: Every pinned action is a commit its repository tagged

Every action and container image that a workflow uses SHALL be pinned to a full commit or a digest that a tag of its source names, and CI SHALL fail when one is pinned to anything else, such as a commit that only a fork holds.

#### Scenario: An action pinned to an untagged commit fails CI

- **WHEN** a workflow pins an action to a commit that no tag of its repository names
- **THEN** CI fails and names the action and the pin

### Requirement: The tool connects only where its documentation says

The hook SHALL open no network connection. The report SHALL connect only to GitHub's REST API, at the address that the workflow's `GITHUB_API_URL` gives, over HTTPS, with the workflow's own `GITHUB_TOKEN`. Prices SHALL be read from the price table in the repository and never fetched.

#### Scenario: The hook opens no connection

- **WHEN** the hook runs, in any of its events
- **THEN** it opens no network connection

#### Scenario: The report connects only to GitHub's API

- **WHEN** the report runs
- **THEN** every connection it opens goes to the host in `GITHUB_API_URL` over HTTPS, and a connection anywhere else fails the test

#### Scenario: Prices are never fetched

- **WHEN** the report prices a pull request
- **THEN** it reads the price table from the tool's own commit and opens no connection for prices

### Requirement: Every threat is rated for impact and likelihood

Every threat in the threat model SHALL carry an impact and a likelihood, each from 1 to 3 with the level's name, and a risk that is their product, and the risk matrix SHALL place each threat in the one cell its ratings name. The threat model SHALL be revisited by a review independent of the design's author before a change's design is approved, and by a review of what was built before its pull request merges.

#### Scenario: A threat without both ratings fails CI

- **WHEN** a threat lacks an impact or a likelihood, or carries a risk that is not their product
- **THEN** a test fails and names the threat

#### Scenario: A threat outside its matrix cell fails CI

- **WHEN** the risk matrix leaves a threat out, places it twice or in another cell than its ratings name, or names a threat that does not exist
- **THEN** a test fails and names the threat
