# Agentic PR cost calculator

An open-source tool to estimate what a GitHub pull request cost when it was built with an AI coding agent.

**Status: proposal.** No calculator code exists yet. The design is an OpenSpec change under
[`openspec/changes/`](openspec/changes/), and code starts once it is approved.

## What it will do

For each pull request, the calculator will:

- capture the tokens the agent spent while its session was working in the repository, per model and by type: input, output, cache writes and cache reads, and carry them to the pull request with the agent's own commits;
- price them from a dated price table kept in this repository, so the estimate uses the price that applied on the day the tokens were spent;
- add the GitHub Actions minutes the pull request's CI used, priced at GitHub's published rate;
- where the data allows, split the cost by activity: code generation, file reading, tooling, MCP calls, subagents and conversation, with any tool it does not know counted as other;
- post a short report comment when the pull request merges, and keep the usage ledger in the repository as the record.

A repository turns it on or off with one setting, and each person decides for themselves whether their own sessions are recorded.

Usage is recorded by the directory the session is in, not by which files it touches. A session in the repository is recorded there even for work it does on another repository from there, so work on other repositories, private ones above all, belongs in sessions of its own.

The figure is an **API-equivalent estimate**, meaning what the same tokens would cost at list prices. It is not a bill: subscription plans and included CI minutes change what you actually pay.

## Working on this repository

The rules for contributors, human or agent, are in [`CLAUDE.md`](CLAUDE.md). In short: tests come first, every figure in prose is computed rather than recalled, and scope is never narrowed silently.

Setup for a local clone:

```sh
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
npm ci --ignore-scripts
.venv/bin/pytest
.venv/bin/ruff check . && .venv/bin/ruff format --check . && .venv/bin/mypy
scripts/verify-openspec.sh
```

Cloud sessions of Claude Code run the same setup automatically through `.claude/hooks/session-start.sh`.

Two tools are pinned here:

- [OpenSpec](https://github.com/Fission-AI/OpenSpec), installed at an exact version from `package-lock.json`. It holds what the calculator must do.
- [Superpowers](https://github.com/obra/superpowers), vendored under `vendor/superpowers/` at the commit `UPSTREAM.lock` names. It guides how the code is built. CI checks that the copy matches upstream.

## Security

See [`SECURITY.md`](SECURITY.md) for reporting a vulnerability, and [`docs/threat-model.md`](docs/threat-model.md) for the threats the design answers.

## Licence

[MIT](LICENSE).
