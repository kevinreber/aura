#!/bin/bash
# Detect documentation drift in the staged diff.
#
# Heuristically checks whether code surfaces that have user-facing docs
# (MCP tools, agent endpoints, UI API routes, env vars) were changed
# without the corresponding doc files. If drift is found and we're not
# already inside a Claude Code session, invokes `claude -p` headlessly
# to refresh the affected docs, then re-stages them so the commit
# captures the doc updates atomically.
#
# Always exits 0 by default — this hook never blocks a commit unless
# AURA_DOC_CHECK_MODE=block is set. To opt out entirely:
#
#   AURA_SKIP_DOC_CHECK=1 git commit ...
#
# Env vars:
#   AURA_SKIP_DOC_CHECK=1            skip entirely
#   AURA_DOC_CHECK_MODE=warn         print drift report, never call claude
#   AURA_DOC_CHECK_MODE=update       (default) call claude when outside a session
#   AURA_DOC_CHECK_MODE=block        exit 1 if drift detected (use sparingly)
#   AURA_DOC_CHECK_REENTRY=1         (set internally to prevent recursion)
#   CLAUDECODE=1                     (set by Claude Code) → skip AI call
#   AURA_DOC_CHECK_TIMEOUT=120       seconds before killing headless claude

set -u

# ─── Opt-outs ──────────────────────────────────────────────────────────

if [ "${AURA_SKIP_DOC_CHECK:-0}" = "1" ]; then
  exit 0
fi

if [ "${AURA_DOC_CHECK_REENTRY:-0}" = "1" ]; then
  # We invoked claude, which is now trying to commit. Don't re-enter.
  exit 0
fi

MODE="${AURA_DOC_CHECK_MODE:-update}"
TIMEOUT="${AURA_DOC_CHECK_TIMEOUT:-120}"

# ─── Helpers ───────────────────────────────────────────────────────────

# Get the staged file list (added/copied/modified, no deletions)
staged_files() {
  git diff --cached --name-only --diff-filter=ACM
}

# Get added files only (for "new route" / "new tool file" detection)
added_files() {
  git diff --cached --name-only --diff-filter=A
}

# Get the staged diff scoped to a path
staged_diff() {
  git diff --cached -- "$@"
}

# Was at least one of the given files staged?
any_staged() {
  for f in "$@"; do
    if staged_files | grep -qFx "$f"; then
      return 0
    fi
  done
  return 1
}

# ─── Skip docs-only commits ────────────────────────────────────────────

# If every staged file is markdown / CHANGELOG / under docs/, there's
# nothing to drift away from.
non_doc_count=$(staged_files | grep -vE '(\.md$|^docs/|CHANGELOG\.md$|LICENSE$)' | wc -l | tr -d ' ')
if [ "$non_doc_count" -eq 0 ]; then
  exit 0
fi

# ─── Detect drift triggers ─────────────────────────────────────────────

declare -a drift_reasons
declare -a docs_to_review

# Trigger 1: New / changed MCP tool ───────────────────────────────────
new_tool_files=$(added_files | grep -E '^packages/server/mcp_server/tools/[a-z_]+\.py$' || true)
new_tool_registrations=$(staged_diff packages/server/mcp_server/server.py 2>/dev/null \
  | grep -E '^\+\s+"[a-z_]+_[a-z_]+":\s*\{' || true)

if [ -n "$new_tool_files" ] || [ -n "$new_tool_registrations" ]; then
  drift_reasons+=("MCP server tool added or registered")
  docs_to_review+=(
    "packages/server/README.md"
    "packages/server/CLAUDE.md"
    "README.md"
    "packages/agent/src/daily_ai_agent/agent/tools.py"
    "packages/agent/README.md"
    "packages/agent/CLAUDE.md"
  )
fi

# Trigger 2: New agent endpoint ───────────────────────────────────────
agent_api="packages/agent/src/daily_ai_agent/api.py"
new_routes=$(staged_diff "$agent_api" 2>/dev/null | grep -E '^\+\s+@app\.route\(' || true)
if [ -n "$new_routes" ]; then
  drift_reasons+=("Agent REST endpoint added/changed")
  docs_to_review+=(
    "packages/agent/README.md"
    "packages/agent/CLAUDE.md"
  )
fi

# Trigger 3: New UI API route ─────────────────────────────────────────
new_ui_routes=$(added_files | grep -E '^packages/ui/app/routes/api\.v1\.[a-z0-9.-]+\.ts$' || true)
if [ -n "$new_ui_routes" ]; then
  drift_reasons+=("New UI API proxy route")
  docs_to_review+=(
    "packages/ui/README.md"
    "packages/ui/CLAUDE.md"
  )
fi

# Trigger 4: New env var ──────────────────────────────────────────────
env_example_changed=$(staged_files | grep -E '(^|/)(\.)?env\.example$' || true)

# New Pydantic config field — heuristic: added line under a config class
# with a type annotation
new_config_field=""
for cfg in packages/server/mcp_server/config.py \
           packages/agent/src/daily_ai_agent/models/config.py; do
  if [ -f "$cfg" ]; then
    field=$(staged_diff "$cfg" 2>/dev/null \
      | grep -E '^\+\s+[a-z_]+:\s+(str|int|bool|Optional|List)' || true)
    if [ -n "$field" ]; then
      new_config_field="$cfg"
      break
    fi
  fi
done

if [ -n "$env_example_changed" ] || [ -n "$new_config_field" ]; then
  drift_reasons+=("Environment variable / config field added")
  docs_to_review+=(
    "README.md"
    "CLAUDE.md"
    "packages/server/README.md"
    "packages/server/CLAUDE.md"
    "packages/agent/README.md"
    "packages/agent/CLAUDE.md"
    "packages/ui/README.md"
    "packages/ui/CLAUDE.md"
  )
fi

# ─── Bail if no drift ──────────────────────────────────────────────────

if [ ${#drift_reasons[@]} -eq 0 ]; then
  exit 0
fi

# Deduplicate the docs list (portable: macOS bash 3.2 lacks `mapfile`)
deduped=()
while IFS= read -r line; do
  deduped+=("$line")
done < <(printf '%s\n' "${docs_to_review[@]}" | awk '!seen[$0]++')
docs_to_review=("${deduped[@]}")
unset deduped

# ─── Filter: skip docs that were already touched in this commit ───────

declare -a unfreshed_docs
for d in "${docs_to_review[@]}"; do
  if any_staged "$d"; then
    continue
  fi
  if [ -f "$d" ]; then
    unfreshed_docs+=("$d")
  fi
done

if [ ${#unfreshed_docs[@]} -eq 0 ]; then
  # All flagged docs were edited alongside the code. Looks healthy.
  exit 0
fi

# ─── Print the drift report ────────────────────────────────────────────

printf '\n📚 \033[1;33mDoc-drift detected\033[0m — staged code suggests these docs may be stale:\n\n'
for r in "${drift_reasons[@]}"; do
  printf '  • %s\n' "$r"
done
printf '\nCandidates to review:\n'
for d in "${unfreshed_docs[@]}"; do
  printf '  - %s\n' "$d"
done
printf '\n'

# ─── Decide what to do about it ────────────────────────────────────────

if [ "$MODE" = "warn" ]; then
  printf '\033[0;36m(mode=warn — proceeding without updates. Set AURA_DOC_CHECK_MODE=update to invoke Claude.)\033[0m\n\n'
  exit 0
fi

if [ "$MODE" = "block" ]; then
  printf '\033[0;31mAURA_DOC_CHECK_MODE=block — commit refused.\033[0m\n'
  printf 'Either update the docs above, run this commit with AURA_SKIP_DOC_CHECK=1, or use `git commit --no-verify`.\n\n'
  exit 1
fi

# MODE=update from here on

if [ "${CLAUDECODE:-0}" = "1" ]; then
  printf '\033[0;36m(inside Claude Code session — parent agent will handle. Skipping headless invocation.)\033[0m\n'
  printf 'If you want Claude to update these now, run: /update-docs-code\n\n'
  exit 0
fi

if ! command -v claude >/dev/null 2>&1; then
  printf '\033[0;36m(`claude` CLI not found — falling back to warn-only.)\033[0m\n\n'
  exit 0
fi

# ─── Headless Claude invocation ────────────────────────────────────────

printf '\033[0;34m🤖 Invoking Claude to refresh affected docs (timeout: %ss)...\033[0m\n\n' "$TIMEOUT"

# Build a focused prompt
diff_summary=$(git diff --cached --stat | head -50)
doc_list=$(printf '  - %s\n' "${unfreshed_docs[@]}")
reasons_list=$(printf '  - %s\n' "${drift_reasons[@]}")

prompt=$(cat <<EOF
You are running headlessly inside the Aura monorepo's pre-commit hook to
refresh docs that may have gone stale alongside the staged changes.

What changed in this commit:
${diff_summary}

Why docs may be stale:
${reasons_list}

Docs to inspect and update if needed:
${doc_list}

Rules:
1. ONLY edit the files listed above. Do not create new files. Do not
   touch source code.
2. Read each candidate doc and the staged diff before editing. If a
   doc is already accurate for the change, leave it alone.
3. Match each README/CLAUDE.md's existing structure and tone — tables
   stay tables, bullets stay bullets.
4. Keep edits minimal and surgical. Update tool counts, route tables,
   env-var tables, tool name references, and version mentions as
   needed. Do not rewrite unrelated sections.
5. Do NOT commit or run \`git add\` — the hook will re-stage your
   edits.
6. When done, print a one-line summary of which files you changed and
   why.

Get the staged diff with: \`git diff --cached\`
EOF
)

# Re-entry guard: if Claude makes a commit, the next pre-commit run
# sees AURA_DOC_CHECK_REENTRY=1 and skips this check.
export AURA_DOC_CHECK_REENTRY=1

# Run claude headlessly. --dangerously-skip-permissions is intentional
# here: we're trusting the hook's scoped prompt, and the alternative
# (interactive permission prompts) is incompatible with a git hook.
# The headless call is sandboxed by the prompt to only edit listed docs.
set +e
timeout "$TIMEOUT" claude -p "$prompt" \
  --allowed-tools "Read,Edit,Bash(git diff:*)" \
  2>&1 | sed 's/^/  /'
claude_exit=$?
set -e

unset AURA_DOC_CHECK_REENTRY

if [ "$claude_exit" -eq 124 ]; then
  printf '\n\033[0;33m⚠️  Claude timed out after %ss. Proceeding without doc updates.\033[0m\n' "$TIMEOUT"
  printf 'Run `claude /update-docs-code` after the commit to refresh manually.\n\n'
  exit 0
elif [ "$claude_exit" -ne 0 ]; then
  printf '\n\033[0;33m⚠️  Claude exited %d. Proceeding without doc updates.\033[0m\n' "$claude_exit"
  exit 0
fi

# ─── Re-stage any doc files Claude edited ──────────────────────────────

restaged=0
for d in "${unfreshed_docs[@]}"; do
  if ! git diff --quiet -- "$d" 2>/dev/null; then
    git add "$d"
    printf '  📎 re-staged %s\n' "$d"
    restaged=$((restaged + 1))
  fi
done

if [ "$restaged" -gt 0 ]; then
  printf '\n\033[0;32m✅ Refreshed %d doc file(s) and re-staged them.\033[0m\n\n' "$restaged"
else
  printf '\n\033[0;36m(no doc edits made — Claude judged the docs already accurate.)\033[0m\n\n'
fi

exit 0
