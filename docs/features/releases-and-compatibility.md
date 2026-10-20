# Releases and compatibility

The tool is meant to be used inside other projects, so it keeps to old enough Python versions for adopters to keep up, and it is released in versions whose numbers say what changed.

**Status:** the supported versions and the update rules are in place; releases are designed, not built yet.

**Requirements:** R25, R26, R27, R28, R32

## Expected behaviour

- **Python.** The tool runs on Python 3.11 and every later release, with the standard library only. CI tests on the oldest supported version and on the newest. `requires-python` in `pyproject.toml` is the one source of the oldest version, and a test fails when another copy of it disagrees. The oldest rises only when its version nears its end of life, on the owner's decision.
- **Floors of the capture step.** Under a Python older than 3.11, or a git older than 2.43, the capture step records nothing, stages nothing, prints nothing and exits with success, so an old machine is never blocked from committing.
- **Dependency updates.** Minor and patch updates and vulnerability fixes are proposed as usual. A major update waits for the owner's approval on Renovate's dependency dashboard.
- **Versions.** Semantic: the major number rises for a change that adopters must act on, which is any change to the public surface: the hook's registered command and path (the hook's checksum in that command is a value that changes with every hook change, not a breaking change), the opt-in key, the ledger's path and format, the store's format, `.pr-cost.json`, the reusable workflow's path, inputs and permissions, and the Python and git floors. A manifest of that surface is kept in the repository, and a release whose manifest changed needs a raised major number and a `### Breaking` section; the minor number for new behaviour; the patch number for a fix.
- **Releases.** A release is made by pushing a tag `vMAJOR.MINOR.PATCH` for a commit in the default branch's first-parent history. The release workflow checks the tag's form before any other step, refuses a tag that does not match `pyproject.toml` and `CHANGELOG.md`, and publishes a GitHub release that names the commit to pin.
- **Bill of materials.** Every release carries a CycloneDX JSON software bill of materials. It is written from the tagged tree, and names the hook file's SHA-256 and each action the reusable workflow uses. A release whose bill of materials cannot be written, or misses an action, is not published.

## See also

- `project-standards` in `openspec/`, and design decisions 10 and 11 of `add-pr-cost-calculator`.
- [`../../CHANGELOG.md`](../../CHANGELOG.md).
