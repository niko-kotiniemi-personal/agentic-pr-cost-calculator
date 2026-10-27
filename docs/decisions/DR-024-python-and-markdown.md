# DR-024: The tool, its release and its documentation are Python and Markdown

- **Type:** technical
- **Status:** accepted
- **Decided by:** the change `add-pr-cost-calculator`, as the owner asked on 2026-10-20
- **Requirements:** none
- **Threats:** none
- **Replaces:** none
- **Closed by:** none

## Context

The repository holds the tool, which adopters run as a copied hook file and a reusable workflow, both on Python's standard library alone (DR-023), and the tooling that develops it. Part of that tooling is OpenSpec, which holds the specs and is installed from npm at a pinned version (DR-042), so the repository carries a Node manifest and its lock file beside its Python.

## Decision

The tool, its release and its documentation are Python and Markdown, plus the YAML and JSON that GitHub and the data need. The shell scripts and the configuration that develop and check the tool, such as `scripts/verify-openspec.sh`, and `pyproject.toml`, which also holds the version that a release's tag must match (DR-149), are outside this rule. OpenSpec is a Node program, so `package.json` and `package-lock.json` stay for development only, and nothing from them ships to adopters or runs in a release.

## Alternatives

None were recorded when this was decided.

## Consequences

- The release workflow does its work in Python scripts, and its YAML only starts them (the design's decision 11).
- Node is needed only for the OpenSpec CLI, as `CONTRIBUTING.md` says: CI's `openspec` job sets Node up to run `npm ci` and `scripts/verify-openspec.sh`, and `.claude/hooks/session-start.sh` runs the same `npm ci`. `package.json` is marked private and calls itself pinned tooling, not a package.
- A release tool in Node or Go, such as one that writes the changelog from commit messages, falls outside what a release may be written in (DR-098).

## Scope

This covers what the tool, its release and its documentation are written in, and that nothing from OpenSpec's Node files ships to adopters or runs in a release. That the hook and the report use nothing beyond Python's standard library is DR-023 (The hook and the report use Python's standard library only), and how OpenSpec is pinned and checked is DR-042 (OpenSpec is pinned and its skills are regenerated in CI).

## What reversing it would change

No requirement states this, so the specs would not change. The design's decision 11 would change, and so would the line of `CLAUDE.md`'s section on compatibility and releases that keeps the tool, its release and its documentation to Python and Markdown, and `CONTRIBUTING.md`'s note on Node. DR-098, whose alternative needed a Node or Go program, would be revisited. Nothing in the public surface would change, so the change would not be a breaking one for adopters.
