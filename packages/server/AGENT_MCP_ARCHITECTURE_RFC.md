# Architecture RFC Checklist — Agent + MCP

**Project:** Morning Routine (or <product-name>)

## 1) Scope & Goals

- [ ] **Problem statement:** one paragraph, user/job-to-be-done
- [ ] **In-scope:** features/use cases this release will cover
- [ ] **Out-of-scope:** explicitly not doing (keeps scope tight)
- [ ] **Personas:** end user, admin, support/ops

## 2) High-Level Architecture

- [ ] **Agent layer:** Coordinator agent (planner/orchestrator); any specialist agents?
- [ ] **MCP server(s):** single to start; list tool namespace (e.g., `weather.get_daily`, `mobility.get_commute`, `calendar.list_events`, `todo.list`)
- [ ] **Backends:** which APIs/SDKs each tool wraps
- [ ] **UI/API:** web/mobile app → BFF/GraphQL → agent sessions
- [ ] **State:** what we store (session memory, preferences), where (KV/DB), retention

## 3) Features (MVP)

- [ ] Read-only tools: weather, commute, calendar, todos
- [ ] Planning policy: tool-calling rules, fallback behavior
- [ ] Natural-language prompts: system prompt + rail-guard content (do/don’t)
- [ ] Result formatting: concise summary + links
- [ ] Basic error handling: retries, timeouts, user-facing errors

## 4) Security & Privacy

- [ ] **AuthN/Z:** end-user auth (OAuth/SSO), service auth for APIs
- [ ] **Secrets:** stored in vault; rotated; never exposed to agent prompts
- [ ] **RBAC/Policies:** read-only for MVP; deny destructive ops by default
- [ ] **PII/Data flow:** data classification, masking/redaction rules in MCP
- [ ] **Multi-tenant plan:** single-tenant now; outline tenant scoping for v1

## 5) SLOs & Capacity (initial targets)

- [ ] **Availability:** 99.5% MCP/Agent API (MVP) → 99.9% (v1)
- [ ] **Latency (p50/p95):** user request → response: 2s/6s (MVP); 1.5s/4s (v1)
- [ ] **Tool call budgets:** each tool ≤ 800ms p95; ≤ 2 retries w/ backoff
- [ ] **Cost guardrails:** max 3 tool calls + 1 model call per request (MVP)
- [ ] **Error budgets:** ≤ 1% failed requests / 30 days

## 6) Data Flows

**User request → response (read path):**

1. UI/BFF receives request ➜ creates agent session (corr. ID)
2. Agent plans ➜ selects `weather.get_daily` → MCP validates → calls provider
3. Agent selects next tools (`calendar.list_events`, `mobility.get_commute`)
4. MCP normalizes outputs ➜ agent summarizes ➜ BFF returns to UI

**Write-action path (future):**

1. Agent proposes write (e.g., `calendar.create_event`) ➜ MCP policy check (RBAC, idempotency key)
2. Execute ➜ audit log (who/what/when/params) ➜ return typed result

**Failure handling:**

- Tool timeout ➜ retry (jittered) ➜ degrade gracefully (“commute API unavailable”)
- Partial results OK; agent must summarize with caveats

## 7) MCP Tool Contracts (pre-filled examples)

### 1. weather.get_daily

**Input schema:**

```json
{
  "type": "object",
  "required": ["location"],
  "properties": {
    "location": { "type": "string" },
    "when": {
      "type": "string",
      "enum": ["today", "tomorrow"],
      "default": "today"
    }
  }
}
```

**Output schema:**

```json
{
  "type": "object",
  "required": ["temp_hi", "temp_lo", "summary"],
  "properties": {
    "temp_hi": { "type": "number" },
    "temp_lo": { "type": "number" },
    "precip_chance": { "type": "number" },
    "summary": { "type": "string" }
  }
}
```

### 2. mobility.get_commute

**Input schema:**

```json
{
  "type": "object",
  "required": ["origin", "destination"],
  "properties": {
    "origin": { "type": "string" },
    "destination": { "type": "string" },
    "mode": {
      "type": "string",
      "enum": ["driving", "transit", "bike"],
      "default": "driving"
    }
  }
}
```

**Output schema:**

```json
{
  "type": "object",
  "required": ["minutes", "route_hint"],
  "properties": {
    "minutes": { "type": "number" },
    "route_hint": { "type": "string" }
  }
}
```

### 3. calendar.list_events

**Input schema:**

```json
{
  "type": "object",
  "required": ["date"],
  "properties": {
    "date": { "type": "string", "format": "date" }
  }
}
```

**Output schema:**

```json
{
  "type": "object",
  "required": ["events"],
  "properties": {
    "events": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "start": { "type": "string", "format": "date-time" },
          "end": { "type": "string", "format": "date-time" },
          "title": { "type": "string" },
          "location": { "type": "string" }
        }
      }
    }
  }
}
```

### 4. todo.list

**Input schema:**

```json
{
  "type": "object",
  "properties": {
    "bucket": {
      "type": "string",
      "enum": ["errands", "work", "home"],
      "default": "work"
    }
  }
}
```

**Output schema:**

```json
{
  "type": "object",
  "required": ["items"],
  "properties": {
    "items": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "id": { "type": "string" },
          "title": { "type": "string" },
          "priority": { "type": "string", "enum": ["low", "medium", "high"] }
        }
      }
    }
  }
}
```

## 8) Observability & Ops

- [ ] **Logging:** structured logs w/ correlation IDs (UI↔BFF↔Agent↔MCP↔API)
- [ ] **Metrics:** tool latency, call counts, error rates, token/cost usage
- [ ] **Tracing:** spans per tool call; surface to dashboard (p50/p95/p99)
- [ ] **Audit:** append-only logs for any write/action tools
- [ ] **Runbooks:** common failures (auth expired, provider outage), playbooks, on-call

## 9) Testing Strategy

- [ ] **Contract tests:** JSON schema validation for each tool I/O
- [ ] **Golden tests:** fixed prompts → deterministic tool sequences
- [ ] **Chaos tests:** API timeouts, rate-limit responses, malformed payloads
- [ ] **Security tests:** authz bypass attempts, prompt-injection against tool inputs
- [ ] **Load tests:** concurrent sessions, QPS limits

## 10) Risks & Mitigations

- [ ] Provider rate limits ➜ caching, backoff, fallbacks
- [ ] Hallucinated tool usage ➜ strict tool schemas, deny-by-default policy
- [ ] Secret leakage ➜ MCP strips/redacts; never interpolate secrets into prompts
- [ ] Cost spikes ➜ tool/model call budgets, circuit breakers
- [ ] Vendor changes ➜ abstraction adapters + versioned tools

## 11) Phased Migration Plan

**Phase 0 – Prototype (week 1–2)**

- Single MCP server, **read-only** tools (weather/commute/calendar/todos)
- One coordinator agent, minimal BFF, simple UI
- Basic metrics/logs; local secrets

**Phase 1 – MVP (weeks 3–6)**

- Harden schemas, retries, caching; add tracing & dashboards
- Add **RBAC** (read-only default), secrets vault, rate-limit handling
- Ship to small beta; set initial SLOs; cost guardrails

**Phase 2 – Productize (weeks 6–10)**

- Add **first write tool** (e.g., `calendar.create_event`) with idempotency + audit
- Multi-tenant scoping in MCP; per-tenant creds; usage metering/billing hooks
- Security review, runbooks, error budgets

**Phase 3 – Scale/Refactor**

- Split MCP by domain if needed (productivity vs mobility vs home)
- Introduce specialist agents where beneficial (analytics/ops)
- Advanced policies: PII redaction, approval flows for risky tools
- Optional: replace any slow external calls with internal services/caches

## 12) Acceptance Criteria (MVP)

- [ ] 3 read tools available, validated, and versioned (`v1`)
- [ ] p95 end-to-end latency ≤ 6s on wifi; ≥ 99.5% availability over 7 days
- [ ] Zero secrets in prompts/logs; all in vault; access logged
- [ ] Dashboards show tool latency, errors, and per-request cost
- [ ] 10 golden tests pass; failure modes return graceful user messages
