"""Brain-vault git sync.

Keeps the vault directory at `settings.vault_root` fresh against a remote
git repository. Runs as part of the FastAPI lifespan: clones (or pulls) on
boot, then refreshes every `SYNC_INTERVAL_SECS` in the background.

Auth model: HTTPS + GitHub fine-grained PAT. The PAT is injected into the
clone URL at call time so it never persists in git config. SSH/deploy-key
auth is intentionally not supported here — fine-grained PATs are equally
scoped (single repo, read-only Contents) but avoid container SSH ceremony.

Clone shape: `--depth 1 --filter=blob:none --sparse`, plus a non-cone
sparse-checkout pattern set (see `SPARSE_PATTERNS`). The vault is a working
knowledge base, not a source repo, so we ditch history; the agent only
searches markdown, so we ditch the large attachment directories. Pulls
inherit the same sparse rules.

Behavior matrix:

| VAULT_GIT_URL | VAULT_ROOT exists | VAULT_ROOT/.git exists | Action |
|---|---|---|---|
| unset                     | —    | —    | No-op (dev mode / bind-mount path) |
| set                       | no   | no   | Clone the repo |
| set                       | yes  | yes  | `git pull --ff-only` |
| set                       | yes  | no (and populated) | Warn and skip — looks like a bind-mount |

Failures are logged and never raised; the server should keep serving stale
vault data rather than refuse to boot.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Optional

from .config import get_settings
from .utils.logging import get_logger

logger = get_logger("vault_sync")

# How often to re-pull. 15 min matches the vault's own auto-push cadence;
# combined that gives a worst-case staleness of ~30 minutes.
SYNC_INTERVAL_SECS = 15 * 60

# How long a single git invocation may run before we give up on it. Network
# hiccups happen; we'd rather time out and try again next cycle than block
# the loop indefinitely. With sparse-checkout + blob filter the cold clone
# is well under a minute even for a multi-hundred-MB vault, but we keep the
# generous ceiling for slow links and pathologically large incremental pulls.
GIT_TIMEOUT_SECS = 300.0

# Sparse-checkout patterns applied to the cloned vault. Non-cone gitignore
# syntax: a matching line *includes* the path in the working tree, a `!`
# line excludes it. `/*` matches every top-level entry (files + directories
# with their contents), and the `!` lines carve out the large attachment
# directories that aren't markdown and so add nothing to vault_search but
# everything to disk and clone time.
#
# Ripgrep already filters by `--type md` at search time — these excludes
# are a disk/network optimization, not a search-correctness one. Add new
# excludes here as the vault grows.
SPARSE_PATTERNS = (
    "/*",
    "!Docs/raw",                # ~73 MB of raw imported/clipped content
    "!Dashboards/screenshots",  # ~35 MB of PNG dashboard screenshots
)


class VaultSync:
    """Owns the vault clone-and-pull loop for the server's lifetime."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._task: Optional[asyncio.Task] = None

    # ------------------------------------------------------------------ helpers

    @property
    def enabled(self) -> bool:
        """Sync is active only when both a target path and a remote URL are set."""
        return bool(self._settings.vault_root) and bool(self._settings.vault_git_url)

    def _authed_url(self) -> str:
        """Inject the PAT into an HTTPS clone URL.

        For an `https://github.com/owner/repo.git` URL and a PAT, GitHub
        accepts `https://x-access-token:<token>@github.com/owner/repo.git`.
        Non-HTTPS URLs (e.g. `git@github.com:...`) and the no-token case
        are passed through unchanged.
        """
        url = self._settings.vault_git_url or ""
        token = self._settings.vault_git_token
        if not token or not url.startswith("https://"):
            return url
        return url.replace("https://", f"https://x-access-token:{token}@", 1)

    def _redacted_url(self) -> str:
        """The URL with the token elided, safe to log."""
        url = self._settings.vault_git_url or ""
        if self._settings.vault_git_token and url.startswith("https://"):
            return url
        return url

    def _vault_root(self) -> Path:
        return Path(self._settings.vault_root or "").expanduser()

    @staticmethod
    def _is_existing_non_git_dir(vault_root: Path) -> bool:
        """A populated dir that isn't a git checkout — almost certainly a bind-mount."""
        if not vault_root.is_dir():
            return False
        if (vault_root / ".git").exists():
            return False
        try:
            return any(vault_root.iterdir())
        except OSError:
            return False

    # ------------------------------------------------------------------ public API

    async def initial_sync(self) -> None:
        """Run once on startup. Either clones, pulls, or skips with a clear reason."""
        if not self.enabled:
            logger.info(
                "vault_sync: disabled (VAULT_GIT_URL or VAULT_ROOT unset); "
                "vault tools fall back to whatever (if anything) is at the configured path"
            )
            return

        vault_root = self._vault_root()

        if self._is_existing_non_git_dir(vault_root):
            logger.warning(
                f"vault_sync: {vault_root} exists, is populated, and has no .git directory — "
                "treating as a bind-mount and skipping sync. Unset VAULT_GIT_URL to silence this."
            )
            return

        if (vault_root / ".git").is_dir():
            await self._pull(vault_root)
        else:
            await self._clone(vault_root)

    def start_periodic_sync(self) -> None:
        """Kick off the background pull loop. Idempotent and safe to call always."""
        if not self.enabled:
            return
        if self._task and not self._task.done():
            return
        self._task = asyncio.create_task(self._periodic_loop(), name="vault-sync")
        logger.info(f"vault_sync: periodic refresh every {SYNC_INTERVAL_SECS}s started")

    async def stop_periodic_sync(self) -> None:
        """Cancel the loop and await it, used by FastAPI shutdown."""
        if not self._task or self._task.done():
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None
        logger.info("vault_sync: periodic refresh stopped")

    # ------------------------------------------------------------------ internals

    async def _clone(self, vault_root: Path) -> None:
        """Shallow + blob-filtered + sparse clone of the remote into vault_root.

        Three stacked optimizations vs. a plain `git clone`:

        1. `--depth 1` — drop commit history; the vault is a working
           knowledge base, not a source repo.
        2. `--filter=blob:none` — partial clone. Git fetches blob contents
           lazily on checkout, so excluded sparse paths never download.
        3. `--sparse` plus a non-cone pattern set — limits the working
           tree to markdown content, skipping the big attachment dirs
           listed in `SPARSE_PATTERNS`.

        Together these turn a multi-minute, ~400 MB cold clone into a
        sub-minute, mostly-markdown checkout. `git pull` later honors the
        same sparse rules, so the excluded dirs stay excluded across syncs.

        If `sparse-checkout set` fails we log a warning but leave the
        full-tree clone in place — better than no vault at all.
        """
        vault_root.parent.mkdir(parents=True, exist_ok=True)
        # If a previous attempt left an empty directory, remove it so clone
        # doesn't refuse with "destination path already exists and is not empty".
        if vault_root.exists() and not any(vault_root.iterdir()):
            try:
                vault_root.rmdir()
            except OSError:
                pass

        logger.info(f"vault_sync: cloning {self._redacted_url()} into {vault_root}")
        rc, err = await self._run_git(
            "clone",
            "--depth", "1",
            "--filter=blob:none",
            "--sparse",
            self._authed_url(),
            str(vault_root),
        )
        if rc != 0:
            logger.error(f"vault_sync: clone failed (exit {rc}): {err}")
            return

        rc, err = await self._run_git(
            "-C", str(vault_root),
            "sparse-checkout", "set", "--no-cone",
            *SPARSE_PATTERNS,
        )
        if rc != 0:
            logger.warning(
                f"vault_sync: sparse-checkout set failed (exit {rc}): {err} — "
                "vault is cloned but excluded attachment dirs are present"
            )
            return

        logger.info(
            f"vault_sync: initial clone complete (sparse patterns: {', '.join(SPARSE_PATTERNS)})"
        )

    async def _pull(self, vault_root: Path) -> None:
        """Fast-forward only pull. If history diverges, we want to know, not paper over."""
        rc, err = await self._run_git("-C", str(vault_root), "pull", "--ff-only", "--quiet")
        if rc != 0:
            # Pulls fail all the time (network, conflicts, etc.); log and move on.
            logger.warning(f"vault_sync: pull failed (exit {rc}): {err}")
        else:
            logger.debug(f"vault_sync: pulled {vault_root}")

    async def _run_git(self, *args: str) -> tuple[int, str]:
        """Invoke git non-interactively with a wall-clock timeout."""
        env = {
            **os.environ,
            # Refuse to prompt for credentials — if the PAT in the URL is
            # invalid, fail fast rather than hang waiting for stdin.
            "GIT_TERMINAL_PROMPT": "0",
            # Stable, English output for log parsing.
            "LC_ALL": "C",
        }
        try:
            proc = await asyncio.create_subprocess_exec(
                "git", *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )
        except FileNotFoundError:
            return 127, "git binary not found on PATH"

        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(), timeout=GIT_TIMEOUT_SECS
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            return 124, f"git timed out after {GIT_TIMEOUT_SECS}s"

        stderr = stderr_bytes.decode("utf-8", errors="replace").strip()
        return proc.returncode or 0, stderr

    async def _periodic_loop(self) -> None:
        """Sleep, pull, repeat. Errors are logged and swallowed."""
        while True:
            await asyncio.sleep(SYNC_INTERVAL_SECS)
            vault_root = self._vault_root()
            if not (vault_root / ".git").is_dir():
                # The bind-mount / disappeared-vault case — nothing to pull.
                continue
            try:
                await self._pull(vault_root)
            except Exception as exc:  # pragma: no cover - defensive
                logger.error(f"vault_sync: periodic pull errored: {exc}")
