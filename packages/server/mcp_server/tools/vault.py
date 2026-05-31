"""Brain-vault tool: ripgrep-backed search + read + list over a local markdown vault.

Exposes the user's personal knowledge base (Obsidian-style markdown notes) to
the agent so chat can answer questions about projects, career, meetings,
and past decisions directly from primary sources.

Search is a two-stage pipeline:

1. **Candidate selection (ripgrep)** — `rg --json` scans every markdown file
   in the vault for literal/regex matches of the query. Cheap and fast even
   on a vault with thousands of files.
2. **Re-ranking (BM25)** — once we have the set of files that contain a
   match, we re-rank them by Okapi BM25 against the query so the file with
   the densest, most-meaningful matches surfaces first. Ripgrep alone
   returns hits in filesystem-walk order (basically alphabetical), which
   leads the agent to read whichever note happened to sort earliest rather
   than whichever is most relevant.

Vault location is `settings.vault_root` (env: `VAULT_ROOT`). All input paths
are vault-relative and validated against directory traversal. A `.auraignore`
file at the vault root (gitignore syntax) controls which files are visible.
"""

import asyncio
import json
import re
from collections import OrderedDict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import bm25s

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

# Hard cap on file size for vault_read to avoid loading huge files into memory.
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
                folder_abs = self._resolve_within_vault(input_data.folder, root)
                if not folder_abs.is_dir():
                    raise VaultPathError(
                        f"Folder {input_data.folder!r} is not a directory."
                    )
                relative_search = input_data.folder
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

            hits, truncated = await self._run_ripgrep(
                cmd, root, input_data.limit, input_data.query
            )

            result = VaultSearchOutput(
                query=input_data.query,
                folder=input_data.folder,
                hits=hits,
                total=len(hits),
                truncated=truncated,
            )
            duration_ms = (asyncio.get_event_loop().time() - start) * 1000
            log_tool_call("vault_search", input_data.model_dump(), duration_ms)
            return result
        except Exception as exc:
            duration_ms = (asyncio.get_event_loop().time() - start) * 1000
            log_tool_call("vault_search", input_data.model_dump(), duration_ms)
            logger.error(f"vault_search failed: {exc}")
            raise

    async def _run_ripgrep(
        self, cmd: List[str], root: Path, limit: int, query: str
    ) -> tuple[List[VaultSearchHit], bool]:
        """Execute ripgrep (in cwd=root), parse output, and BM25-rank hits."""
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
                "to use vault_search."
            ) from exc

        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=_RIPGREP_TIMEOUT_SECS
            )
        except asyncio.TimeoutError as exc:
            proc.kill()
            await proc.wait()
            raise RuntimeError(
                f"vault_search timed out after {_RIPGREP_TIMEOUT_SECS}s"
            ) from exc

        # rg exit codes: 0 = matches found, 1 = no matches, 2 = error.
        if proc.returncode not in (0, 1):
            err = stderr.decode("utf-8", errors="replace").strip()
            raise RuntimeError(f"ripgrep failed (exit {proc.returncode}): {err}")

        # Parse `match` events, capped at a small multiple of `limit` so a
        # pathological query (e.g. regex 'a' across the whole vault) can't
        # balloon memory. We still parse enough to compute a meaningful BM25
        # ranking — a tight cap (limit + 1) would defeat the rerank.
        max_parsed = limit * 20 + 1
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

        # Group matches by vault-relative file path, preserving rg's natural
        # within-file ordering. OrderedDict keys give us deterministic file
        # iteration order for BM25 corpus construction.
        file_matches: "OrderedDict[str, List[dict]]" = OrderedDict()
        for event in match_events:
            rel_path = self._normalize_match_path(event, root)
            if rel_path is None:
                continue
            file_matches.setdefault(str(rel_path), []).append(event)

        if not file_matches:
            return [], False

        # Re-rank the matched files by BM25 against the query. We score on
        # full file content (not just snippets) so notes that repeat the
        # query terms in headings + body — which is usually the right note —
        # bubble to the top.
        ranked_paths = self._bm25_rank(list(file_matches.keys()), query, root)

        hits: List[VaultSearchHit] = []
        for rel_path_str in ranked_paths:
            for event in file_matches[rel_path_str]:
                if len(hits) >= limit:
                    break
                hit = self._event_to_hit(event, rel_path_str, root)
                if hit is not None:
                    hits.append(hit)
            if len(hits) >= limit:
                break

        # Truncation: we have more hits available than `limit` allowed, OR
        # we cut off parsing at max_parsed (so there may have been more rg
        # matches beyond what we even saw).
        total_available = sum(len(v) for v in file_matches.values())
        truncated = total_available > len(hits) or len(match_events) >= max_parsed
        return hits, truncated

    def _normalize_match_path(self, event: dict, root: Path) -> Optional[Path]:
        """Pull the file path out of an rg match event, vault-relative."""
        file_path_str = event.get("data", {}).get("path", {}).get("text")
        if not file_path_str:
            return None
        rel_path = Path(file_path_str)
        if rel_path.is_absolute():
            try:
                return rel_path.relative_to(root)
            except ValueError:
                return None
        # Strip a leading "./" if present.
        parts = [p for p in rel_path.parts if p != "."]
        return Path(*parts) if parts else Path(".")

    def _event_to_hit(
        self, event: dict, rel_path_str: str, root: Path
    ) -> Optional[VaultSearchHit]:
        """Build a VaultSearchHit from a single rg match event."""
        data = event.get("data", {})
        line_no = data.get("line_number")
        line_text = data.get("lines", {}).get("text", "").rstrip("\n")
        if line_no is None or not line_text:
            return None
        abs_path = (root / rel_path_str).resolve()
        snippet, heading = self._extract_context(abs_path, line_no)
        return VaultSearchHit(
            path=rel_path_str,
            line_no=line_no,
            snippet=snippet,
            preceding_heading=heading,
        )

    def _bm25_rank(
        self, rel_paths: List[str], query: str, root: Path
    ) -> List[str]:
        """Return `rel_paths` sorted by BM25 score against `query`, descending.

        We score against full file content rather than snippets so that a
        note that mentions the query in its frontmatter, headings, AND body
        outranks one that has a single inline reference.

        For trivial corpora (0-1 documents) we skip BM25 — it's pointless
        and bm25s warns on empty corpora.
        """
        if len(rel_paths) <= 1:
            return rel_paths

        corpus: List[str] = []
        for rel_path in rel_paths:
            abs_path = (root / rel_path).resolve()
            try:
                content = abs_path.read_text(encoding="utf-8", errors="replace")
            except OSError as exc:
                logger.warning(f"bm25_rank: failed to read {abs_path}: {exc}")
                content = ""  # zero-score document
            corpus.append(content)

        try:
            retriever = bm25s.BM25()
            corpus_tokens = bm25s.tokenize(corpus, show_progress=False)
            retriever.index(corpus_tokens, show_progress=False)
            query_tokens = bm25s.tokenize([query], show_progress=False)
            # k=len(corpus) so we get back every candidate, sorted.
            results, _scores = retriever.retrieve(
                query_tokens, k=len(corpus), show_progress=False
            )
        except Exception as exc:
            # BM25 should never fail on well-formed input, but if it does we
            # want vault_search to keep working — just return rg's order.
            logger.warning(f"bm25_rank: scoring failed, falling back to rg order: {exc}")
            return rel_paths

        # results is a 2D array shaped (n_queries=1, k); the row is the
        # ranking of indices into our corpus, best first.
        return [rel_paths[idx] for idx in results[0]]

    def _extract_context(self, file_path: Path, line_no: int) -> tuple[str, Optional[str]]:
        """Read the file once and return (snippet, preceding_heading) for `line_no`.

        Consolidates the two pieces of per-hit metadata so we only hit the
        disk once per match, even when many hits share a file.
        """
        try:
            with file_path.open("r", encoding="utf-8", errors="replace") as fh:
                lines = fh.readlines()
        except OSError as exc:
            logger.warning(f"vault: could not read {file_path} for context: {exc}")
            return "", None

        start = max(0, line_no - 1 - _CONTEXT_LINES)
        end = min(len(lines), line_no + _CONTEXT_LINES)
        snippet = "".join(lines[start:end]).rstrip("\n")

        heading: Optional[str] = None
        for i in range(min(line_no, len(lines)) - 1, -1, -1):
            match = _HEADING_RE.match(lines[i].rstrip("\n"))
            if match:
                heading = match.group(2).strip()
                break

        return snippet, heading

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
            log_tool_call("vault_read", input_data.model_dump(), duration_ms)
            return result
        except Exception as exc:
            duration_ms = (asyncio.get_event_loop().time() - start) * 1000
            log_tool_call("vault_read", input_data.model_dump(), duration_ms)
            logger.error(f"vault_read failed: {exc}")
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
            log_tool_call("vault_list", input_data.model_dump(), duration_ms)
            return result
        except Exception as exc:
            duration_ms = (asyncio.get_event_loop().time() - start) * 1000
            log_tool_call("vault_list", input_data.model_dump(), duration_ms)
            logger.error(f"vault_list failed: {exc}")
            raise
