"""Client for Navi — the planning-orchestrator sub-agent (an external service).

Aura calls Navi's `/plan` to turn a fuzzy intent ("plan my Saturday") into a
concrete, grounded, time-blocked plan. Navi is a separate deployment
(`navi-planner.fly.dev`); Aura is the *operator*, Navi the *composer* — see
docs/NAVI_BOUNDARY.md. Auth mirrors the MCP server: send `X-Internal-Auth` when
`NAVI_INTERNAL_AUTH_SECRET` is configured (Navi enforces it in prod).
"""

from __future__ import annotations

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

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    f"{self.base_url}/plan", json=payload, headers=self._headers()
                )
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPStatusError as e:
            # 401 here almost always means NAVI_INTERNAL_AUTH_SECRET is unset or
            # doesn't match Navi's — a config problem, not a user problem.
            logger.warning(
                f"Navi /plan returned HTTP {e.response.status_code}: {e.response.text[:200]}"
            )
            raise NaviError(f"Navi returned HTTP {e.response.status_code}") from e
        except httpx.HTTPError as e:
            logger.warning(f"Navi /plan request failed: {e}")
            raise NaviError(f"Navi request failed: {e}") from e
