"""Brain-vault git sync.

Keeps the vault directory at `settings.vault_root` fresh against a remote
git repository. Runs as part of the FastAPI lifespan: clones (or pulls) on
boot, then refreshes every `SYNC_INTERVAL_SECS` in the background.

Auth model: HTTPS + GitHub fine-grained PAT. The PAT is injected into the
clone URL at call time so it never persists in git config. SSH/deploy-key
auth is intentionally not supported here — fine-grained PATs are equally
scoped (single repo, read-only Contents) but avoid container SSH ceremony.

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
# the loop indefinitely.
GIT_TIMEOUT_SECS = 60.0


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
        """Shallow-clone the remote into vault_root.

        We always shallow-clone (--depth 1) because the vault is a working
        knowledge base, not source history. Saves time, bandwidth, and disk.
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
        rc, err = await self._run_git("clone", "--depth", "1", self._authed_url(), str(vault_root))
        if rc != 0:
            logger.error(f"vault_sync: clone failed (exit {rc}): {err}")
        else:
            logger.info("vault_sync: initial clone complete")

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
