"""Tests for the brain-vault tool."""

import shutil
from pathlib import Path

import pytest

from mcp_server.config import Settings
import mcp_server.tools.vault as vault_module
from mcp_server.schemas.vault import (
    VaultSearchInput,
    VaultReadInput,
    VaultListInput,
)
from mcp_server.tools.vault import (
    VaultTool,
    VaultPathError,
    VaultUnavailableError,
)


# Skip the whole module if ripgrep isn't installed locally (CI image without rg).
pytestmark = pytest.mark.skipif(
    shutil.which("rg") is None,
    reason="ripgrep not installed; install with `brew install ripgrep` or apt-get",
)


@pytest.fixture
def fake_vault(tmp_path: Path) -> Path:
    """Build a small markdown vault with a known structure for tests."""
    (tmp_path / "Projects").mkdir()
    (tmp_path / "Projects" / "aura.md").write_text(
        "# Aura\n\n## Overview\n\nWeekend orchestrator shipped on 2026-05-10.\n"
        "Login redesign followed on 2026-05-17.\n"
    )
    (tmp_path / "Projects" / "secret-side-quest.md").write_text(
        "# Secret\n\nThis should be excluded by .auraignore.\n"
    )
    (tmp_path / "Career").mkdir()
    (tmp_path / "Career" / "index.md").write_text(
        "# Career\n\n## Goals\n\nApply to Anthropic in October 2026.\n"
    )
    (tmp_path / ".obsidian").mkdir()
    (tmp_path / ".obsidian" / "workspace.json").write_text("{}\n")
    (tmp_path / ".auraignore").write_text("Projects/secret-side-quest.md\n")
    return tmp_path


@pytest.fixture
def vault_tool(fake_vault: Path, monkeypatch: pytest.MonkeyPatch) -> VaultTool:
    """Patch settings to point at the fake vault and return a tool instance."""
    test_settings = Settings(vault_root=str(fake_vault))
    monkeypatch.setattr(vault_module, "get_settings", lambda: test_settings)
    return VaultTool()


class TestVaultSearch:
    @pytest.mark.asyncio
    async def test_finds_keyword_match(self, vault_tool):
        result = await vault_tool.search(
            VaultSearchInput(query="Weekend orchestrator")
        )
        assert result.total >= 1
        paths = [hit.path for hit in result.hits]
        assert "Projects/aura.md" in paths

    @pytest.mark.asyncio
    async def test_attaches_preceding_heading(self, vault_tool):
        result = await vault_tool.search(VaultSearchInput(query="orchestrator"))
        hit = next(h for h in result.hits if h.path == "Projects/aura.md")
        assert hit.preceding_heading == "Overview"

    @pytest.mark.asyncio
    async def test_folder_filter_scopes_results(self, vault_tool):
        result = await vault_tool.search(
            VaultSearchInput(query="Anthropic", folder="Career")
        )
        assert result.total == 1
        assert result.hits[0].path == "Career/index.md"

    @pytest.mark.asyncio
    async def test_respects_auraignore(self, vault_tool):
        # "Secret" appears only in the ignored file; should not be returned.
        result = await vault_tool.search(VaultSearchInput(query="Secret"))
        paths = [hit.path for hit in result.hits]
        assert "Projects/secret-side-quest.md" not in paths

    @pytest.mark.asyncio
    async def test_truncated_when_over_limit(self, vault_tool, fake_vault):
        # Add enough matches to exceed limit=2.
        for i in range(5):
            (fake_vault / f"note-{i}.md").write_text(f"# Note {i}\nunique-token here\n")
        result = await vault_tool.search(
            VaultSearchInput(query="unique-token", limit=2)
        )
        assert result.total == 2
        assert result.truncated is True


class TestVaultRead:
    @pytest.mark.asyncio
    async def test_returns_file_content(self, vault_tool):
        result = await vault_tool.read(VaultReadInput(path="Projects/aura.md"))
        assert "Weekend orchestrator shipped" in result.content
        assert result.size_bytes > 0

    @pytest.mark.asyncio
    async def test_rejects_path_traversal(self, vault_tool):
        with pytest.raises(VaultPathError):
            await vault_tool.read(VaultReadInput(path="../etc/passwd"))

    @pytest.mark.asyncio
    async def test_rejects_absolute_path(self, vault_tool):
        with pytest.raises(VaultPathError):
            await vault_tool.read(VaultReadInput(path="/etc/passwd"))

    @pytest.mark.asyncio
    async def test_missing_file_raises(self, vault_tool):
        with pytest.raises(FileNotFoundError):
            await vault_tool.read(VaultReadInput(path="Projects/does-not-exist.md"))


class TestVaultList:
    @pytest.mark.asyncio
    async def test_lists_root_with_folders_first(self, vault_tool):
        result = await vault_tool.list(VaultListInput())
        names = [e.path for e in result.entries]
        # Folders come before files; both are present.
        assert "Projects" in names
        assert "Career" in names

    @pytest.mark.asyncio
    async def test_skips_dotfiles(self, vault_tool):
        result = await vault_tool.list(VaultListInput())
        names = [e.path for e in result.entries]
        assert ".obsidian" not in names
        assert ".auraignore" not in names

    @pytest.mark.asyncio
    async def test_lists_folder_contents(self, vault_tool):
        result = await vault_tool.list(VaultListInput(folder="Projects"))
        names = [e.path for e in result.entries]
        assert "Projects/aura.md" in names

    @pytest.mark.asyncio
    async def test_rejects_traversal(self, vault_tool):
        with pytest.raises(VaultPathError):
            await vault_tool.list(VaultListInput(folder="../etc"))


class TestVaultUnavailable:
    @pytest.mark.asyncio
    async def test_search_errors_when_root_unset(self, monkeypatch):
        monkeypatch.setattr(
            vault_module, "get_settings", lambda: Settings(vault_root=None)
        )
        tool = VaultTool()
        with pytest.raises(VaultUnavailableError):
            await tool.search(VaultSearchInput(query="anything"))

    @pytest.mark.asyncio
    async def test_read_errors_when_root_missing(self, monkeypatch, tmp_path):
        bogus = tmp_path / "does-not-exist"
        monkeypatch.setattr(
            vault_module, "get_settings", lambda: Settings(vault_root=str(bogus))
        )
        tool = VaultTool()
        with pytest.raises(VaultUnavailableError):
            await tool.read(VaultReadInput(path="anything.md"))
