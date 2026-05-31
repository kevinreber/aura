# Brain-Vault Integration

**Status:** Phases 1 + 3 + tool rename shipped (#22, #24, #25, 2026-05-30) · Phase 2 ready to deploy (#26, 2026-05-31) · Phases 4–5 pending · **Logged:** 2026-05-27 · **Effort:** ~6–10 focused hours

Expose Kevin's personal knowledge base (`~/Projects/brain-vault/`) to the Aura
agent so chat can answer questions about his projects, career, meetings, and
past decisions — directly from his second brain.

This doc captures the plan so it doesn't get lost between now and whenever it
gets prioritized. The broader strategic framing (priority vs. Anthropic spine
projects, when to promote this) lives in the brain-vault itself at
`Backlog/ideas.md#2026-05-27`.

---

## Why

Today Aura is a generic productivity bot — weather, calendar, todos, commute.
The features are useful but interchangeable with any LangChain + MCP demo.

Wiring the brain-vault changes that: Aura becomes *about Kevin*. Questions
like "what did I decide about the dashboard redesign?" or "what's the status
of project X?" or "what did so-and-so say in our last 1:1?" become answerable
from real data rather than hallucination.

This is also the strongest portfolio narrative for the Anthropic application
target — "I built an AI assistant that searches my second brain" beats
"another OpenAI chatbot."

---

## Architecture

### Data flow

```
Laptop                                       Fly.io
──────                                       ──────
~/Projects/brain-vault/  ── git push (15m) ─▶ GitHub (private repo)
                                                │
                                                │ git pull (15m cron)
                                                ▼
                                          aura-mcp-server
                                          ├─ /vault/  (cloned repo)
                                          ├─ vault_search   (ripgrep)
                                          ├─ vault_read
                                          └─ vault_list
                                                │ MCP/SSE
                                                ▼
                                          aura-agent  (LangChain wraps tools)
                                                │
                                                ▼
                                          UI chat → user
```

**Worst-case freshness:** ~30 min (15m vault→GitHub + 15m GitHub→Fly).
Acceptable for "what did I decide about X" but not for "what did I just
write." Fine for v1.

**Dev mode:** skip GitHub entirely. Bind-mount `~/Projects/brain-vault:/vault:ro`
into the server container so edits in Obsidian are visible to Aura
immediately.

### Tool surface

Three MCP tools, exposed by `aura-mcp-server`. Composable primitives, not one
mega-tool — LangChain agents reason better with small tools they can chain.

| Tool | Signature | Returns |
|---|---|---|
| `vault_search` | `(query: str, folder?: str, limit: int = 10)` | `[{path, line_no, snippet, preceding_heading}]` |
| `vault_read` | `(path: str)` | raw markdown content |
| `vault_list` | `(folder?: str)` | `[{path, type, size, modified}]` |

Backed by ripgrep — fast, no index to maintain, handles markdown well.
Snippets include `--context 3` and the nearest preceding heading so the LLM
has enough surrounding context to use them.

### Privacy boundary

`.auraignore` file at the vault root (gitignore syntax) controls what the
server can see. Default-excludes `.obsidian/`, `_attachments/`, and any
folder Kevin marks sensitive. Policy lives in the vault, not in Aura's code.

Every retrieved snippet ships to OpenAI as part of the prompt — that's the
real privacy boundary, and `.auraignore` is the lever that controls it.

---

## Implementation plan

### Phase 1 — MCP server tools (2–3 hrs) ✅ SHIPPED 2026-05-30 (PR #22)

**New file:** `packages/server/mcp_server/tools/vault.py` ✅

- ✅ Implemented `vault_search`, `vault_read`, `vault_list`
- ✅ ripgrep backend via `rg --json`; runs with `cwd=root` so anchored
  `.auraignore` patterns work as expected (this was a subtle gotcha — see
  the file for the comment)
- ✅ Path-traversal guards: `VaultPathError` on `..`, absolute paths, and
  paths that escape root after `resolve()`
- ✅ `.auraignore` parsing via `rg --ignore-file`
- ✅ Registered in `mcp_server/server.py` tools dict; routes in
  `mcp_server/app.py` under `/tools/vault.*`
- ✅ `VAULT_ROOT` read from `mcp_server/config.py` settings

**Modified:** `docker/server.Dockerfile` ✅ — installs `ripgrep`

**Modified:** `docker-compose.yml` ✅ — bind-mounts vault at `/vault:ro`;
`VAULT_HOST_PATH` env var lets you point at a non-default location

**New tests:** `packages/server/tests/test_tools/test_vault.py` ✅ — 19 tests
covering search, folder filter, `.auraignore`, truncation, path-traversal,
flag injection (`-h` query), input validation, and the vault-unavailable
error path. All passing.

**Hardening past the original plan:** PR #22 added a 15s ripgrep timeout,
a `--` flag separator (defense against `-`-prefixed queries), bounded
match-event memory for pathological queries, and a clear error if the `rg`
binary is missing.

**Done.** Vault is searchable from any MCP client (Claude Desktop, Cursor)
via `http://localhost:8000/mcp/sse`. No agent changes yet — see Phase 3.

### Phase 2 — Git sync on server (1–2 hrs) ✅ CODE READY (PR #26, 2026-05-31)

**New file:** `packages/server/mcp_server/vault_sync.py` ✅

- ✅ On boot: clones the repo if `VAULT_GIT_URL` is set and the target
  directory is missing/empty; pulls (`--ff-only`) if a `.git` already exists
- ✅ Background task: `asyncio.create_task` loop with 15-minute sleep
- ✅ Graceful degradation: every git failure is logged via `logger.warning/error`
  and the loop continues; the server never refuses to boot because sync failed
- ✅ Dev (bind-mount): detects populated-but-not-a-git-checkout directories
  and skips with a clear "treating as a bind-mount" warning

**Auth model — revised from the original plan:** Uses an **HTTPS fine-grained
PAT** (env: `VAULT_GIT_TOKEN`) instead of SSH deploy keys. Same security
posture (single-repo, read-only), simpler container setup (no SSH key file,
no `known_hosts` write, no `ssh-agent`). The PAT is injected into the clone
URL at call time and never persists in `git config`.

**Modified:** `mcp_server/app.py` lifespan ✅ — runs `initial_sync()` after
cache init and launches the periodic loop. `app.state.vault_sync` holds the
instance so the FastAPI shutdown handler can cancel cleanly.

**Modified:** `docker/server.Dockerfile` ✅ — adds `git` to the apt install
layer alongside `ripgrep`.

**Modified:** `docker-compose.yml` ✅ — passes `VAULT_GIT_URL` and
`VAULT_GIT_TOKEN` through to the server service.

**Tests:** 12 tests in `tests/test_vault_sync.py` ✅ — enabled flag, PAT URL
construction, the boot decision matrix, the missing-git-binary case, and a
real local-origin clone+pull cycle (no network).

**Done when (code):** all of the above ✅
**Done when (prod):** see Phase 5 — Fly secrets + deploy.

### Phase 3 — Agent LangChain wrapper (30–60 min)

**Modify:** `packages/agent/src/daily_ai_agent/agent/tools.py`
- Wrap the three MCP tools as LangChain `Tool` instances
- Add to the agent's tool list

**Modify:** agent system prompt
- Add a short routing section: "You have access to Kevin's personal notes
  via `vault_search` / `vault_read`. Use them when the user asks about their
  projects, career, meetings, people, or past decisions. Search first
  (narrow with `folder` when you can), then read the most relevant file."
- Mirror the routing table from `~/.claude/CLAUDE.md`'s vault section so
  the agent knows where things live (`Projects/`, `Career/`, etc.)

**Done when:** UI chat answers a vault-shaped question by actually calling
the vault tools end-to-end.

### Phase 4 — Brain-vault repo prep (15–30 min)

In the `brain-vault` GitHub repo (not this repo):
- Create `.auraignore` at the root. Day-1 content TBD — see Open Questions.
- Generate a read-only SSH deploy key for the repo
- Add the public key to the brain-vault repo's Deploy Keys (read-only)
- Save the private key for the Fly secret step

### Phase 5 — Deploy + smoke test (30–60 min)

```bash
fly secrets set \
  VAULT_GIT_URL=git@github.com:kevinreber/brain-vault.git \
  VAULT_GIT_SSH_KEY="$(cat brain-vault-deploy.key)" \
  --app aura-mcp-server

fly deploy --config packages/server/fly.toml \
  --dockerfile docker/server.Dockerfile --app aura-mcp-server

fly deploy --config packages/agent/fly.toml \
  --dockerfile docker/agent.Dockerfile --app aura-agent
```

Smoke test from the UI: "What's the status of the Aura project?" should pull
real content from `Projects/aura.md`.

---

## Tradeoffs (decided)

| Decision | Chosen | Rejected | Reason |
|---|---|---|---|
| Retrieval | ripgrep | embeddings (Chroma, sqlite-vec) | Vault is small (hundreds of files); queries are keyword-shaped. Revisit only if recall is bad. |
| Tool location | MCP server | Directly in agent | Claude Desktop / Cursor can use the same tools. Matches the CLAUDE.md "start with Server" pattern. |
| Tool granularity | Three primitives | One `vault_query(intent)` mega-tool | LangChain agents reason better with composable tools they can chain. |
| Sync | 15-min `git pull` cron | GitHub webhook → Fly endpoint | Vault already syncs every 15 min; webhook adds infra for marginal freshness gain. |
| GitHub auth | Read-only deploy key | Fine-grained PAT | Deploy key is scoped to one repo; no rotation when Kevin changes jobs. |
| Privacy | `.auraignore` opt-out | Allowlist (only certain folders) | Friendlier default; easy to escalate if a folder becomes sensitive. |
| Dev access | Bind-mount from laptop | Clone in dev container | Edits in Obsidian show up immediately; no sync lag; no double storage. |
| LLM exposure | OpenAI sees snippets | Local model (Ollama) for vault queries | Acceptable since brain-vault already lives in private GitHub. Revisit for health/financial-grade content. |
| Unavailable in prod | Graceful degradation | Hard fail | Fly cold start shouldn't 500 the agent. |

---

## Risks

1. **Agent ignores the tools.** LLMs sometimes skip tools when the prompt
   isn't explicit. Mitigation: routing examples in the system prompt,
   mirroring `~/.claude/CLAUDE.md`'s vault-routing table.
2. **Ripgrep snippets lose context.** A match with no surrounding paragraph
   is hard for the LLM to use. Mitigation: `--context 3` and nearest
   preceding heading.
3. **OpenAI sees more than intended.** Every snippet ships to GPT-4o-mini.
   Mitigation: `.auraignore` discipline; revisit boundary if vault grows
   sensitive content.
4. **Fly deploy-key SSH setup.** Sometimes a 30-min yak shave to get the
   env-mounted private key + `known_hosts` right.
5. **Vault size on Fly disk.** Probably fine (vault is small), but worth
   checking app's volume size before deploy.

---

## Open questions before kickoff

1. **`.auraignore` content for day 1.** What folders should be excluded?
   Candidates: `Career/interview-prep/` (sensitive during active job hunt),
   `Finance/` (if/when it exists), `_attachments/`. Default-exclude
   `.obsidian/` regardless.
2. **v1 scope: read-only or also write?** Read tools first. Write tools
   (`vault_append_to_daily_note`, `vault_create_note`) deferred until read
   works well.
3. **Tool-call telemetry.** Worth logging which vault queries the agent
   makes so we can tune the system prompt / discover what works? Cheap to
   add; useful for prompt iteration.

---

## Effort summary

| Phase | Hours | Risk |
|---|---|---|
| 1. MCP tools | 2–3 | Low |
| 2. Git sync | 1–2 | Medium |
| 3. Agent wrapper | 0.5–1 | Low |
| 4. Vault repo prep | 0.25–0.5 | Low |
| 5. Deploy | 0.5–1 | Medium |
| Buffer (50%) | +2–4 | — |
| **Total** | **6–10 hrs** | |

**Two evenings if it goes well, three if it doesn't.** Phase 1 alone (~2 hrs)
gives ~80% of the value — vault searchable from any MCP client (Claude
Desktop, Cursor) without touching the Aura agent. A natural stopping point
if motivation dips.

---

## Priority

**Not on the spine.** The next planned Anthropic-prep project is the
Distributed Rate Limiter in Go (Sprint #2 in `brain-vault`'s
`Career/interview-prep/anthropic-swe-prep`). This integration is
opportunistic.

**When to promote ahead of Sprint #2:** if reframing Aura (not the Go
projects) as the primary Anthropic portfolio piece. The vault integration is
the feature that makes that reframe credible.

**When to slot in as-is:** as a deep-work afternoon between Go sessions when
you need a momentum win.

---

## Related

- `brain-vault/Backlog/ideas.md#2026-05-27` — full strategic framing
- `brain-vault/Projects/aura.md` — Aura project notes (Future / parked
  section points back here)
- `brain-vault/Career/interview-prep/anthropic-swe-prep.md` — Anthropic
  spine plan
- `~/.claude/CLAUDE.md` — vault-routing table the agent system prompt
  should mirror
