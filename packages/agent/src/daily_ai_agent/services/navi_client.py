"""Client for Navi — the planning-orchestrator sub-agent (an external service).

Aura calls Navi's `/plan` to turn a fuzzy intent ("plan my Saturday") into a
concrete, grounded, time-blocked plan. Navi is a separate deployment
(`navi-planner.fly.dev`); Aura is the *operator*, Navi the *composer* — see
docs/NAVI_BOUNDARY.md. Auth mirrors the MCP server: send `X-Internal-Auth` when
`NAVI_INTERNAL_AUTH_SECRET` is configured (Navi enforces it in prod).
"""

from __future__ import annotations

import time
from typing import Any, Dict, Optional

import httpx
from loguru import logger

from ..models.config import get_settings


class NaviError(Exception):
    """A call to Navi failed."""


class NaviClient:
    """Thin async client for Navi's HTTP contract (currently just `/plan`)."""

    def __init__(self) -> None:
        settings = get_settings()
        self.base_url: str = settings.navi_url.rstrip("/")
        self.timeout: int = settings.navi_timeout
        self._secret: Optional[str] = settings.navi_internal_auth_secret

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self._secret:
            headers["X-Internal-Auth"] = self._secret
        return headers

    async def plan(
        self,
        intent: str,
        on: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """POST /plan → a Navi Plan dict ({intent, summary, blocks[]})."""
        payload: Dict[str, Any] = {"intent": intent}
        if on:
            payload["on"] = on
        if context:
            payload["context"] = context

        # Timing + outcome are logged on every path so a silent failure is
        # diagnosable from `fly logs` next time (grep "navi.plan").
        start = time.monotonic()
        logger.info(f"navi.plan start url={self.base_url} timeout={self.timeout}s intent={intent!r}")
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    f"{self.base_url}/plan", json=payload, headers=self._headers()
                )
                resp.raise_for_status()
                data = resp.json()
                elapsed = time.monotonic() - start
                logger.info(
                    f"navi.plan ok in {elapsed:.1f}s blocks={len(data.get('blocks', []))}"
                )
                return data
        except httpx.TimeoutException as e:
            elapsed = time.monotonic() - start
            logger.warning(f"navi.plan TIMEOUT after {elapsed:.1f}s (limit {self.timeout}s)")
            raise NaviError(
                f"Navi didn't respond within {self.timeout}s — it may be waking up or "
                f"working on a long plan. Try again in a moment."
            ) from e
        except httpx.ConnectError as e:
            elapsed = time.monotonic() - start
            logger.warning(f"navi.plan UNREACHABLE at {self.base_url} after {elapsed:.1f}s: {e}")
            raise NaviError(f"Couldn't reach Navi at {self.base_url}.") from e
        except httpx.HTTPStatusError as e:
            elapsed = time.monotonic() - start
            code = e.response.status_code
            logger.warning(f"navi.plan HTTP {code} after {elapsed:.1f}s: {e.response.text[:200]}")
            if code == 401:
                # Config problem, not a user problem: the shared secret is wrong/unset.
                raise NaviError(
                    "Navi rejected the request (401) — NAVI_INTERNAL_AUTH_SECRET is "
                    "missing or doesn't match Navi's."
                ) from e
            raise NaviError(f"Navi returned HTTP {code}.") from e
        except httpx.HTTPError as e:
            elapsed = time.monotonic() - start
            logger.warning(f"navi.plan FAILED after {elapsed:.1f}s: {e}")
            raise NaviError(f"Navi request failed: {e}") from e
