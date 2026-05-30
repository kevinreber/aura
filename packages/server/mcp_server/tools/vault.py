"""Brain-vault tool: ripgrep-backed search + read + list over a local markdown vault.

Exposes the user's personal knowledge base (Obsidian-style markdown notes) to
the agent so chat can answer questions about projects, career, meetings,
and past decisions directly from primary sources.

Backed by `rg --json` for speed. Vault location is `settings.vault_root`
(env: `VAULT_ROOT`). All input paths are vault-relative and validated
against directory traversal. A `.auraignore` file at the vault root
(gitignore syntax) controls which files are visible.
"""

import asyncio
import json
import re
from pathlib import Path
from typing import List, Optional

from ..schemas.vault import (
    VaultSearchInput,
    VaultSearchOutput,
    VaultSearchHit,
    VaultReadInput,
    VaultReadOutput,
    VaultListInput,
    VaultListOutput,
    VaultEntry,
)
from ..config import get_settings
from ..utils.logging import get_logger, log_tool_call

logger = get_logger("vault_tool")

# How many lines of surrounding context to include in each hit snippet.
_CONTEXT_LINES = 2

# Hard cap on file size for vault.read to avoid loading huge files into memory.
_MAX_READ_BYTES = 1_000_000  # 1 MB

# Wall-clock timeout for a single ripgrep invocation.
_RIPGREP_TIMEOUT_SECS = 15.0

# Heading detection regex (markdown ATX headings).
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")


class VaultUnavailableError(RuntimeError):
    """Raised when the vault root is not configured or does not exist on disk."""


class VaultPathError(ValueError):
    """Raised when a user-supplied path tries to escape the vault root."""


class VaultTool:
    """Search, read, and list a local markdown vault via ripgrep + pathlib."""

    def __init__(self) -> None:
        self.settings = get_settings()

    # ---------------------------------------------------------------- vault root

    def _vault_root(self) -> Path:
        """Resolve the vault root on disk, or raise if it isn't available.

        We resolve symlinks so subsequent path-traversal checks compare
        canonical paths.
        """
        root = self.settings.vault_root
        if not root:
            raise VaultUnavailableError(
                "Vault is not configured. Set VAULT_ROOT to enable vault tools."
            )

        root_path = Path(root).expanduser().resolve()
        if not root_path.is_dir():
            raise VaultUnavailableError(
                f"Vault root '{root_path}' does not exist or is not a directory."
            )
        return root_path

    def _resolve_within_vault(self, user_path: str, root: Path) -> Path:
        """Resolve a user-supplied vault-relative path, rejecting traversal.

        Accepts only forward-slash relative paths. Absolute paths and any path
        that escapes the vault root after resolution are rejected.
        """
        if not user_path:
            raise VaultPathError("Path must be non-empty.")

        # Disallow absolute paths and Windows drive letters defensively.
        if user_path.startswith(("/", "\\")) or (len(user_path) > 1 and user_path[1] == ":"):
            raise VaultPathError(f"Absolute paths are not allowed: {user_path!r}")

        candidate = (root / user_path).resolve()
        # Ensure the resolved candidate stays inside the vault root.
        try:
            candidate.relative_to(root)
        except ValueError as exc:
            raise VaultPathError(
                f"Path {user_path!r} escapes the vault root."
            ) from exc
        return candidate

    def _ignore_file(self, root: Path) -> Optional[Path]:
        """Return path to .auraignore if it exists, else None."""
        candidate = root / ".auraignore"
        return candidate if candidate.is_file() else None

    # ---------------------------------------------------------------- search

    async def search(self, input_data: VaultSearchInput) -> VaultSearchOutput:
        """Search the vault using ripgrep and return ranked hits with context."""
        start = asyncio.get_event_loop().time()
        try:
            root = self._vault_root()

            # We pass a *relative* search path and run rg with cwd=root so
            # gitignore-style anchored patterns in .auraignore
            # (e.g. `Projects/foo.md`) behave the way users expect. With
            # absolute search paths, ripgrep silently treats anchored
            # patterns as non-matching.
            if input_data.folder:
                # Validate that the folder is inside the vault before we hand
                # it to rg as a relative path.
                self._resolve_within_vault(input_data.folder, root)
                relative_search = input_data.folder
                if not (root / input_data.folder).is_dir():
                    raise VaultPathError(
                        f"Folder {input_data.folder!r} is not a directory."
                    )
            else:
                relative_search = "."

            cmd = [
                "rg",
                "--json",
                "--context",
                str(_CONTEXT_LINES),
                "--type",
                "md",
            ]
            # We intentionally don't pass --max-count: it's per-file, which
            # makes the truncation flag wrong when a single file has more
            # matches than `limit`. Global trimming below is correct.
            if not input_data.regex:
                cmd.append("--fixed-strings")

            ignore = self._ignore_file(root)
            if ignore is not None:
                # Pass the ignore-file as a basename so rg anchors patterns
                # to the vault root (rg's cwd).
                cmd.extend(["--ignore-file", ignore.name])

            # `--` separates flags from positional args so a query/folder
            # starting with "-" (e.g. user searches for "-rf") doesn't
            # get parsed as a flag.
            cmd.extend(["--", input_data.query, relative_search])

            hits, truncated = await self._run_ripgrep(cmd, root, input_data.limit)

            result = VaultSearchOutput(
                query=input_data.query,
                folder=input_data.folder,
                hits=hits,
                total=len(hits),
                truncated=truncated,
            )
            duration_ms = (asyncio.get_event_loop().time() - start) * 1000
            log_tool_call("vault.search", input_data.model_dump(), duration_ms)
            return result
        except Exception as exc:
            duration_ms = (asyncio.get_event_loop().time() - start) * 1000
            log_tool_call("vault.search", input_data.model_dump(), duration_ms)
            logger.error(f"vault.search failed: {exc}")
            raise

    async def _run_ripgrep(
        self, cmd: List[str], root: Path, limit: int
    ) -> tuple[List[VaultSearchHit], bool]:
        """Execute ripgrep (in cwd=root) and parse its --json output."""
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(root),
            )
        except FileNotFoundError as exc:
            raise RuntimeError(
                "ripgrep (`rg`) is not installed in this environment. "
                "Install it (e.g. `apt-get install ripgrep` or `brew install ripgrep`) "
                "to use vault.search."
            ) from exc

        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=_RIPGREP_TIMEOUT_SECS
            )
        except asyncio.TimeoutError as exc:
            proc.kill()
            await proc.wait()
            raise RuntimeError(
                f"vault.search timed out after {_RIPGREP_TIMEOUT_SECS}s"
            ) from exc

        # rg exit codes: 0 = matches found, 1 = no matches, 2 = error.
        if proc.returncode not in (0, 1):
            err = stderr.decode("utf-8", errors="replace").strip()
            raise RuntimeError(f"ripgrep failed (exit {proc.returncode}): {err}")

        # Parse `match` events, capped at a small multiple of `limit` so a
        # pathological query (e.g. regex 'a' across the whole vault) can't
        # balloon memory. We still parse `limit + 1` to detect truncation.
        max_parsed = limit * 10 + 1
        match_events: List[dict] = []
        for raw_line in stdout.splitlines():
            try:
                event = json.loads(raw_line)
            except json.JSONDecodeError:
                continue
            if event.get("type") == "match":
                match_events.append(event)
                if len(match_events) >= max_parsed:
                    break

        hits: List[VaultSearchHit] = []
        for event in match_events[:limit]:
            data = event.get("data", {})
            file_path_str = data.get("path", {}).get("text")
            if not file_path_str:
                continue

            # rg was run with cwd=root, so its path strings are relative
            # (possibly with a leading "./"). Normalize to a vault-relative
            # path and re-derive an absolute path for context extraction.
            rel_path = Path(file_path_str)
            if rel_path.is_absolute():
                try:
                    rel_path = rel_path.relative_to(root)
                except ValueError:
                    continue
            else:
                # Strip a leading "./" if present.
                parts = [p for p in rel_path.parts if p != "."]
                rel_path = Path(*parts) if parts else Path(".")

            abs_path = (root / rel_path).resolve()

            line_no = data.get("line_number")
            line_text = data.get("lines", {}).get("text", "").rstrip("\n")
            if line_no is None or not line_text:
                continue

            snippet = self._build_snippet(abs_path, line_no)
            heading = self._preceding_heading(abs_path, line_no)

            hits.append(
                VaultSearchHit(
                    path=str(rel_path),
                    line_no=line_no,
                    snippet=snippet,
                    preceding_heading=heading,
                )
            )

        truncated = len(match_events) > limit
        return hits, truncated

    def _build_snippet(self, file_path: Path, line_no: int) -> str:
        """Read N lines of context around `line_no` from a file."""
        try:
            with file_path.open("r", encoding="utf-8", errors="replace") as fh:
                lines = fh.readlines()
        except OSError:
            return ""
        start = max(0, line_no - 1 - _CONTEXT_LINES)
        end = min(len(lines), line_no + _CONTEXT_LINES)
        return "".join(lines[start:end]).rstrip("\n")

    def _preceding_heading(self, file_path: Path, line_no: int) -> Optional[str]:
        """Find the nearest markdown heading at or before `line_no`."""
        try:
            with file_path.open("r", encoding="utf-8", errors="replace") as fh:
                lines = fh.readlines()
        except OSError:
            return None
        # Walk upward from the match.
        for i in range(min(line_no, len(lines)) - 1, -1, -1):
            match = _HEADING_RE.match(lines[i].rstrip("\n"))
            if match:
                return match.group(2).strip()
        return None

    # ---------------------------------------------------------------- read

    async def read(self, input_data: VaultReadInput) -> VaultReadOutput:
        """Read a single vault file (size-capped) and return its raw contents."""
        start = asyncio.get_event_loop().time()
        try:
            root = self._vault_root()
            target = self._resolve_within_vault(input_data.path, root)

            if not target.is_file():
                raise FileNotFoundError(f"Vault file not found: {input_data.path}")

            size = target.stat().st_size
            if size > _MAX_READ_BYTES:
                raise ValueError(
                    f"File {input_data.path} is {size} bytes; exceeds {_MAX_READ_BYTES} cap."
                )

            content = target.read_text(encoding="utf-8", errors="replace")
            result = VaultReadOutput(
                path=input_data.path,
                content=content,
                size_bytes=size,
            )
            duration_ms = (asyncio.get_event_loop().time() - start) * 1000
            log_tool_call("vault.read", input_data.model_dump(), duration_ms)
            return result
        except Exception as exc:
            duration_ms = (asyncio.get_event_loop().time() - start) * 1000
            log_tool_call("vault.read", input_data.model_dump(), duration_ms)
            logger.error(f"vault.read failed: {exc}")
            raise

    # ---------------------------------------------------------------- list

    async def list(self, input_data: VaultListInput) -> VaultListOutput:
        """List immediate children of a vault folder (one level deep)."""
        start = asyncio.get_event_loop().time()
        try:
            root = self._vault_root()
            target = root if not input_data.folder else self._resolve_within_vault(
                input_data.folder, root
            )

            if not target.is_dir():
                raise NotADirectoryError(
                    f"Vault folder not found: {input_data.folder or '.'}"
                )

            entries: List[VaultEntry] = []
            for child in sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
                # Skip dotfiles by default — vault config (.obsidian, .git) shouldn't
                # surface through the agent's view of "the vault."
                if child.name.startswith("."):
                    continue
                rel = child.relative_to(root)
                if child.is_dir():
                    entries.append(VaultEntry(path=str(rel), type="folder"))
                else:
                    entries.append(
                        VaultEntry(
                            path=str(rel),
                            type="file",
                            size_bytes=child.stat().st_size,
                        )
                    )

            result = VaultListOutput(
                folder=input_data.folder or ".",
                entries=entries,
                total=len(entries),
            )
            duration_ms = (asyncio.get_event_loop().time() - start) * 1000
            log_tool_call("vault.list", input_data.model_dump(), duration_ms)
            return result
        except Exception as exc:
            duration_ms = (asyncio.get_event_loop().time() - start) * 1000
            log_tool_call("vault.list", input_data.model_dump(), duration_ms)
            logger.error(f"vault.list failed: {exc}")
            raise
