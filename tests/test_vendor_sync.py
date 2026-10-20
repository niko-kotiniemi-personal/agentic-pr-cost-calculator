"""The vendor sync takes only the commit that its lock's tag names.

Upstream serves commits that no release contains, such as those of its open
pull requests, and a fetch by commit id takes any of them. A lock pointing at
one would pass a check that compares the vendored tree with that commit, so the
sync also requires the lock's tag to name the lock's commit.

These tests run the real script against a local upstream, never the network.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "sync-superpowers.sh"
VENDORED = [".claude-plugin/plugin.json", "skills/a/SKILL.md", "hooks/run-hook.cmd"]
VENDORED += ["hooks/session-start", "LICENSE"]
IDENTITY = {
    "GIT_AUTHOR_NAME": "Test",
    "GIT_AUTHOR_EMAIL": "test@example.invalid",
    "GIT_COMMITTER_NAME": "Test",
    "GIT_COMMITTER_EMAIL": "test@example.invalid",
}


@dataclass(frozen=True)
class World:
    repo: Path
    remotes: Path
    tagged: str
    untagged: str


def git(*args: str, cwd: Path) -> str:
    done = subprocess.run(
        ["git", *args],
        cwd=cwd,
        env={**os.environ, **IDENTITY},
        check=True,
        capture_output=True,
        text=True,
    )
    return done.stdout.strip()


@pytest.fixture
def world(tmp_path: Path) -> World:
    work = tmp_path / "upstream"
    work.mkdir()
    git("init", "-q", "-b", "main", cwd=work)
    for path in VENDORED:
        (work / path).parent.mkdir(parents=True, exist_ok=True)
        (work / path).write_text(f"{path}, as released\n")
    git("add", "-A", cwd=work)
    git("commit", "-q", "-m", "release", cwd=work)
    tagged = git("rev-parse", "HEAD", cwd=work)
    git("tag", "-a", "v1.0.0", "-m", "v1.0.0", cwd=work)
    git("tag", "v1.0.0-light", cwd=work)
    (work / "skills/a/SKILL.md").write_text("changed in a commit no release contains\n")
    git("commit", "-q", "-a", "-m", "not released", cwd=work)
    untagged = git("rev-parse", "HEAD", cwd=work)

    remotes = tmp_path / "remotes"
    bare = remotes / "owner" / "superpowers.git"
    bare.parent.mkdir(parents=True)
    git("clone", "-q", "--bare", str(work), str(bare), cwd=tmp_path)
    git("config", "uploadpack.allowFilter", "true", cwd=bare)
    git("config", "uploadpack.allowAnySHA1InWant", "true", cwd=bare)

    repo = tmp_path / "repo"
    (repo / "scripts").mkdir(parents=True)
    shutil.copy(SCRIPT, repo / "scripts" / SCRIPT.name)
    (repo / "vendor" / "superpowers").mkdir(parents=True)
    return World(repo, remotes, tagged, untagged)


def sync(world: World, sha: str, tag: str, *args: str) -> subprocess.CompletedProcess[str]:
    lock = world.repo / "vendor" / "superpowers" / "UPSTREAM.lock"
    lock.write_text(f"repo=owner/superpowers\nsha={sha}\ntag={tag}\n")
    return subprocess.run(
        ["bash", str(world.repo / "scripts" / SCRIPT.name), *args],
        env={**os.environ, "SYNC_REMOTE_BASE": world.remotes.as_uri()},
        capture_output=True,
        text=True,
    )


def test_the_commit_the_tag_names_syncs_and_checks(world: World) -> None:
    synced = sync(world, world.tagged, "v1.0.0")
    assert synced.returncode == 0, synced.stderr
    checked = sync(world, world.tagged, "v1.0.0", "--check")
    assert checked.returncode == 0, checked.stderr
    vendored = world.repo / "vendor" / "superpowers" / "skills/a/SKILL.md"
    assert vendored.read_text() == "skills/a/SKILL.md, as released\n"


def test_syncing_a_commit_the_tag_does_not_name_is_refused(world: World) -> None:
    done = sync(world, world.untagged, "v1.0.0")
    assert done.returncode == 1
    assert f"tag v1.0.0 of owner/superpowers names {world.tagged}, not {world.untagged}" in (
        done.stderr
    )
    assert not (world.repo / "vendor" / "superpowers" / "skills").exists()


def test_a_tree_vendored_from_a_commit_the_tag_does_not_name_fails_the_check(
    world: World,
) -> None:
    # The tree matches its commit exactly, so only the tag rule can catch it.
    bare = world.remotes / "owner" / "superpowers.git"
    archive = subprocess.run(
        ["git", "archive", world.untagged], cwd=bare, check=True, capture_output=True
    ).stdout
    dest = world.repo / "vendor" / "superpowers"
    subprocess.run(["tar", "-x", "-C", str(dest)], input=archive, check=True)
    done = sync(world, world.untagged, "v1.0.0", "--check")
    assert done.returncode == 1
    assert f"tag v1.0.0 of owner/superpowers names {world.tagged}, not {world.untagged}" in (
        done.stderr
    )


def test_a_lightweight_tag_names_its_commit_directly(world: World) -> None:
    assert sync(world, world.tagged, "v1.0.0-light").returncode == 0
    refused = sync(world, world.untagged, "v1.0.0-light", "--check")
    assert refused.returncode == 1
    assert f"names {world.tagged}, not {world.untagged}" in refused.stderr


def test_a_tag_upstream_does_not_have_is_refused(world: World) -> None:
    done = sync(world, world.tagged, "v9.9.9", "--check")
    assert done.returncode == 1
    assert "tag v9.9.9 of owner/superpowers names nothing" in done.stderr


def test_an_edited_vendored_file_fails_the_check(world: World) -> None:
    assert sync(world, world.tagged, "v1.0.0").returncode == 0
    (world.repo / "vendor" / "superpowers" / "LICENSE").write_text("edited by hand\n")
    done = sync(world, world.tagged, "v1.0.0", "--check")
    assert done.returncode == 1
    assert "DIFFERS" in done.stderr
