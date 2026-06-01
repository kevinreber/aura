"""Tests for the brain-vault git sync."""

import asyncio
import shutil
import subprocess
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from mcp_server.config import Settings
import mcp_server.vault_sync as vault_sync_module
from mcp_server.vault_sync import SPARSE_PATTERNS, VaultSync


def _make_filtering_origin(origin: Path) -> None:
    """Init a bare repo that accepts both `--filter=...` and pushes from a clone.

    GitHub sets these knobs by default; local bare repos don't. Without
    `uploadpack.allowFilter` the clone falls back to a full fetch (so the
    test would silently bypass the optimization we're trying to verify),
    and without disabling `receive.denyCurrentBranch` we can't push from
    the helper work tree into the bare repo's checked-out branch.
    """
    subprocess.run(["git", "init", "--bare", str(origin)], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(origin), "config", "uploadpack.allowFilter", "true"],
        check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(origin), "config", "uploadpack.allowAnySHA1InWant", "true"],
        check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(origin), "config", "receive.denyCurrentBranch", "ignore"],
        check=True, capture_output=True,
    )


def _commit_and_push(work: Path) -> None:
    """Stage + commit + push from a helper work tree, with deterministic identity."""
    subprocess.run(["git", "-C", str(work), "add", "."], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(work), "-c", "user.email=t@t", "-c", "user.name=t",
         "commit", "-m", "test"],
        check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(work), "push", "origin", "HEAD"],
        check=True, capture_output=True,
    )


# Tests that actually shell out to git need git on PATH; skip cleanly if missing.
HAS_GIT = shutil.which("git") is not None


def _settings(**overrides) -> Settings:
    """Build a Settings instance with vault_* overrides and nothing else opinionated."""
    return Settings(**overrides)


def _make_settings_fixture(monkeypatch, **overrides):
    s = _settings(**overrides)
    monkeypatch.setattr(vault_sync_module, "get_settings", lambda: s)
    return s


class TestEnabled:
    """The boolean that decides whether anything happens at all."""

    def test_disabled_when_url_unset(self, monkeypatch, tmp_path):
        _make_settings_fixture(monkeypatch, vault_root=str(tmp_path))
        assert VaultSync().enabled is False

    def test_disabled_when_root_unset(self, monkeypatch):
        _make_settings_fixture(monkeypatch, vault_git_url="https://example.com/x.git")
        assert VaultSync().enabled is False

    def test_enabled_when_both_set(self, monkeypatch, tmp_path):
        _make_settings_fixture(
            monkeypatch,
            vault_root=str(tmp_path),
            vault_git_url="https://example.com/x.git",
        )
        assert VaultSync().enabled is True


class TestAuthedURL:
    """PAT injection into the clone URL."""

    def test_injects_token_into_https_url(self, monkeypatch, tmp_path):
        _make_settings_fixture(
            monkeypatch,
            vault_root=str(tmp_path),
            vault_git_url="https://github.com/me/brain-vault.git",
            vault_git_token="ghp_SECRET",
        )
        url = VaultSync()._authed_url()
        assert url == "https://x-access-token:ghp_SECRET@github.com/me/brain-vault.git"

    def test_passthrough_without_token(self, monkeypatch, tmp_path):
        _make_settings_fixture(
            monkeypatch,
            vault_root=str(tmp_path),
            vault_git_url="https://github.com/me/public-vault.git",
        )
        assert VaultSync()._authed_url() == "https://github.com/me/public-vault.git"

    def test_passthrough_for_non_https_url(self, monkeypatch, tmp_path):
        _make_settings_fixture(
            monkeypatch,
            vault_root=str(tmp_path),
            vault_git_url="git@github.com:me/vault.git",
            vault_git_token="ghp_SECRET",
        )
        # We don't touch SSH-style URLs; the token is ignored.
        assert VaultSync()._authed_url() == "git@github.com:me/vault.git"


class TestInitialSync:
    @pytest.mark.asyncio
    async def test_skip_when_disabled(self, monkeypatch, tmp_path):
        _make_settings_fixture(monkeypatch, vault_root=str(tmp_path))
        sync = VaultSync()
        sync._clone = AsyncMock()
        sync._pull = AsyncMock()
        await sync.initial_sync()
        sync._clone.assert_not_called()
        sync._pull.assert_not_called()

    @pytest.mark.asyncio
    async def test_skip_when_bind_mount(self, monkeypatch, tmp_path):
        # Populated directory with no .git → looks like a bind-mount.
        (tmp_path / "Projects").mkdir()
        (tmp_path / "Projects" / "note.md").write_text("hello")
        _make_settings_fixture(
            monkeypatch,
            vault_root=str(tmp_path),
            vault_git_url="https://example.com/x.git",
        )
        sync = VaultSync()
        sync._clone = AsyncMock()
        sync._pull = AsyncMock()
        await sync.initial_sync()
        sync._clone.assert_not_called()
        sync._pull.assert_not_called()

    @pytest.mark.asyncio
    async def test_pull_when_clone_exists(self, monkeypatch, tmp_path):
        (tmp_path / ".git").mkdir()
        _make_settings_fixture(
            monkeypatch,
            vault_root=str(tmp_path),
            vault_git_url="https://example.com/x.git",
        )
        sync = VaultSync()
        sync._pull = AsyncMock()
        sync._clone = AsyncMock()
        await sync.initial_sync()
        sync._pull.assert_awaited_once()
        sync._clone.assert_not_called()

    @pytest.mark.asyncio
    async def test_clone_when_missing(self, monkeypatch, tmp_path):
        target = tmp_path / "vault"
        _make_settings_fixture(
            monkeypatch,
            vault_root=str(target),
            vault_git_url="https://example.com/x.git",
        )
        sync = VaultSync()
        sync._clone = AsyncMock()
        sync._pull = AsyncMock()
        await sync.initial_sync()
        sync._clone.assert_awaited_once()
        sync._pull.assert_not_called()


class TestRunGit:
    @pytest.mark.asyncio
    async def test_missing_git_binary_returns_127(self, monkeypatch, tmp_path):
        _make_settings_fixture(monkeypatch, vault_root=str(tmp_path))
        sync = VaultSync()
        with patch("asyncio.create_subprocess_exec", side_effect=FileNotFoundError):
            rc, err = await sync._run_git("status")
        assert rc == 127
        assert "git binary not found" in err


@pytest.mark.skipif(not HAS_GIT, reason="git not installed")
class TestRealClone:
    """End-to-end test against a real (tiny, local) git repo — no network."""

    @pytest.mark.asyncio
    async def test_clone_then_pull_against_local_origin(
        self, monkeypatch, tmp_path
    ):
        # Build a real bare repo as the "remote", populate it, then verify
        # clone + pull cycles. No network needed.
        origin = tmp_path / "origin.git"
        work = tmp_path / "work"
        target = tmp_path / "vault"

        _make_filtering_origin(origin)
        subprocess.run(["git", "clone", str(origin), str(work)], check=True, capture_output=True)
        (work / "README.md").write_text("hello\n")
        _commit_and_push(work)

        _make_settings_fixture(
            monkeypatch,
            vault_root=str(target),
            vault_git_url=str(origin),
        )

        sync = VaultSync()
        await sync.initial_sync()
        assert (target / "README.md").read_text() == "hello\n"

        # Add a commit to origin, then run initial_sync again — should pull.
        (work / "README.md").write_text("hello\nupdated\n")
        _commit_and_push(work)

        await sync.initial_sync()
        assert (target / "README.md").read_text() == "hello\nupdated\n"

    @pytest.mark.asyncio
    async def test_clone_excludes_sparse_patterns(self, monkeypatch, tmp_path):
        """Files inside SPARSE_PATTERNS exclude paths must not be checked out.

        Populates the origin with files in every category we care about —
        a top-level note, a kept subfolder note, and a file inside each
        excluded directory — then verifies that after `initial_sync()`
        only the kept files are materialized in the working tree.
        """
        origin = tmp_path / "origin.git"
        work = tmp_path / "work"
        target = tmp_path / "vault"

        _make_filtering_origin(origin)
        subprocess.run(["git", "clone", str(origin), str(work)], check=True, capture_output=True)

        # Two "kept" files (top-level note, and an under-Docs note that
        # doesn't live in the excluded raw/ subdir) plus one file inside
        # each excluded directory.
        (work / "README.md").write_text("hello\n")
        (work / "Docs").mkdir()
        (work / "Docs" / "notes.md").write_text("notes\n")
        (work / "Docs" / "raw").mkdir()
        (work / "Docs" / "raw" / "big.txt").write_text("noise\n")
        (work / "Dashboards").mkdir()
        (work / "Dashboards" / "dash.md").write_text("dash\n")
        (work / "Dashboards" / "screenshots").mkdir()
        (work / "Dashboards" / "screenshots" / "img.png").write_text("pretend-png\n")
        _commit_and_push(work)

        _make_settings_fixture(
            monkeypatch,
            vault_root=str(target),
            vault_git_url=str(origin),
        )

        sync = VaultSync()
        await sync.initial_sync()

        # Sanity check: sparse-checkout patterns were the ones we expect.
        assert "!Docs/raw" in SPARSE_PATTERNS
        assert "!Dashboards/screenshots" in SPARSE_PATTERNS

        # Kept files materialized.
        assert (target / "README.md").is_file()
        assert (target / "Docs" / "notes.md").is_file()
        assert (target / "Dashboards" / "dash.md").is_file()

        # Excluded files absent from the working tree. (They still exist
        # in the repo's object DB; sparse-checkout governs the working tree.)
        assert not (target / "Docs" / "raw" / "big.txt").exists()
        assert not (target / "Dashboards" / "screenshots" / "img.png").exists()
