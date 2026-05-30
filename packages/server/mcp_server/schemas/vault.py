"""Pydantic schemas for brain-vault tool validation."""

from pydantic import BaseModel, Field
from typing import List, Optional


class VaultSearchInput(BaseModel):
    """Input schema for vault.search tool."""

    query: str = Field(
        min_length=1,
        description="Search query (literal text by default, regex if regex=true)",
        examples=["aura roadmap", "weekend orchestrator"],
    )
    folder: Optional[str] = Field(
        default=None,
        description="Vault-relative folder to scope the search (e.g., 'Projects', 'Career/interview-prep')",
        examples=["Projects", "Career", "Activity"],
    )
    limit: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum number of matches to return",
    )
    regex: bool = Field(
        default=False,
        description="Treat query as a regex pattern instead of fixed-string",
    )


class VaultSearchHit(BaseModel):
    """A single search hit within the vault."""

    path: str = Field(description="Vault-relative file path")
    line_no: int = Field(description="1-indexed line number of the match")
    snippet: str = Field(description="Matched line plus surrounding context")
    preceding_heading: Optional[str] = Field(
        default=None,
        description="Nearest markdown heading above the match (for orientation)",
    )


class VaultSearchOutput(BaseModel):
    """Output schema for vault.search tool."""

    query: str = Field(description="Echoed query string")
    folder: Optional[str] = Field(default=None, description="Echoed folder scope")
    hits: List[VaultSearchHit] = Field(description="Ranked list of matches")
    total: int = Field(description="Number of hits returned (capped at limit)")
    truncated: bool = Field(
        default=False,
        description="True if more matches existed than `limit` allowed",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "query": "weekend orchestrator",
                "folder": "Projects",
                "hits": [
                    {
                        "path": "Projects/aura.md",
                        "line_no": 70,
                        "snippet": "Weekend Orchestrator Phases 1-4 + Google Calendar write-back",
                        "preceding_heading": "### 2026-05-09 (Sat)",
                    }
                ],
                "total": 1,
                "truncated": False,
            }
        }


class VaultReadInput(BaseModel):
    """Input schema for vault.read tool."""

    path: str = Field(
        min_length=1,
        description="Vault-relative path to a markdown file",
        examples=["Projects/aura.md", "Career/interview-prep/index.md"],
    )


class VaultReadOutput(BaseModel):
    """Output schema for vault.read tool."""

    path: str = Field(description="Echoed vault-relative path")
    content: str = Field(description="Raw file contents")
    size_bytes: int = Field(description="File size in bytes")


class VaultListInput(BaseModel):
    """Input schema for vault.list tool."""

    folder: Optional[str] = Field(
        default=None,
        description="Vault-relative folder to list (defaults to vault root)",
        examples=["Projects", "Career/interview-prep"],
    )


class VaultEntry(BaseModel):
    """A single file or folder entry."""

    path: str = Field(description="Vault-relative path")
    type: str = Field(description="'file' or 'folder'")
    size_bytes: Optional[int] = Field(default=None, description="File size in bytes (files only)")


class VaultListOutput(BaseModel):
    """Output schema for vault.list tool."""

    folder: str = Field(description="Echoed folder (or '.' for root)")
    entries: List[VaultEntry] = Field(description="Entries at this level (one level deep)")
    total: int = Field(description="Number of entries")
