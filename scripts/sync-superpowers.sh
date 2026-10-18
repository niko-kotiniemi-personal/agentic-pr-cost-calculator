#!/usr/bin/env bash
# Re-materialise vendor/superpowers from the upstream sha in UPSTREAM.lock.
#
# THE SCRIPT IS THE DEFINITION AND CI RUNS IT. `--check` re-syncs into a
# temporary tree and diffs; any difference fails, so a hand-edit to a vendored
# file is a red build rather than a silent fork. That is why no vendored file
# may be edited: the edit cannot survive the next sync and cannot hide.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="${ROOT}/vendor/superpowers"
LOCK="${DEST}/UPSTREAM.lock"

# The vendored subset, and the only paths this script touches: the plugin
# manifest, the skills, the two hook scripts (not upstream's hook registrations,
# since .claude/settings.json registers the dispatcher itself) and the licence.
# tests/test_repository.py holds this list equal to UPSTREAM.lock's
# vendored_paths.
PATHS=(.claude-plugin skills hooks/run-hook.cmd hooks/session-start LICENSE)

read_lock() { sed -n "s/^$1=//p" "$LOCK"; }

REPO="$(read_lock repo)"
SHA="$(read_lock sha)"
[ -n "$REPO" ] && [ -n "$SHA" ] || { echo "sync: UPSTREAM.lock is missing repo= or sha=" >&2; exit 2; }
TAG="$(read_lock tag)"
[ -n "$TAG" ] || { echo "sync: UPSTREAM.lock is missing tag=" >&2; exit 2; }
# Tests point this at a local fixture so that they never use the network.
URL="${SYNC_REMOTE_BASE:-https://github.com}/${REPO}.git"

# A fetch by commit id takes any commit upstream serves, including those of its
# open pull requests that no release contains. So the lock's tag must name the
# lock's commit: an annotated tag through its peeled line, a lightweight one
# directly.
tagged_commit() {
  local refs
  refs="$(git ls-remote "$URL" "refs/tags/${TAG}" "refs/tags/${TAG}^{}")"
  printf '%s\n' "$refs" | awk -v plain="refs/tags/${TAG}" -v peeled="refs/tags/${TAG}^{}" '
    $2 == plain { direct = $1 } $2 == peeled { commit = $1 }
    END { print (commit != "" ? commit : direct) }'
}
named="$(tagged_commit)"
if [ "$named" != "$SHA" ]; then
  echo "sync: tag ${TAG} of ${REPO} names ${named:-nothing}, not ${SHA}" >&2
  exit 1
fi

materialise() {
  local into="$1" work
  work="$(mktemp -d)"
  trap 'rm -rf "$work"' RETURN
  git -c advice.detachedHead=false clone -q --filter=blob:none --no-checkout \
      "$URL" "$work/src"
  git -C "$work/src" fetch -q --depth 1 origin "$SHA"
  mkdir -p "$into"
  git -C "$work/src" archive "$SHA" "${PATHS[@]}" | tar -x -C "$into"
}

if [ "${1:-}" = "--check" ]; then
  probe="$(mktemp -d)"
  trap 'rm -rf "$probe"' EXIT
  materialise "$probe"
  # Compare only the vendored subset; UPSTREAM.lock is ours and is not upstream's.
  if diff -r --exclude=UPSTREAM.lock "$probe" "$DEST" >/dev/null 2>&1; then
    echo "sync: vendor/superpowers matches ${REPO}@${SHA}"
  else
    echo "sync: vendor/superpowers DIFFERS from ${REPO}@${SHA}" >&2
    diff -r --exclude=UPSTREAM.lock "$probe" "$DEST" >&2 || true
    exit 1
  fi
else
  rm -rf "${PATHS[@]/#/${DEST}/}"
  materialise "$DEST"
  echo "sync: vendor/superpowers re-materialised from ${REPO}@${SHA}"
fi
