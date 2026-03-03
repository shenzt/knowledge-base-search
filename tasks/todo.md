# Plan: Fix so-001 timeout + RAGAS default + CI DeepSeek v3.2

## Context

Three improvements to the eval system:
1. **so-001 timeout** — the pipelining comparison case takes ~300s and times out with only 95 chars of answer
2. **RAGAS default** — make faithfulness scoring run by default, not opt-in via `--ragas`
3. **CI model** — use DeepSeek v3.2 (not Claude) for agent model in CI eval to save costs

---

## Task 1: Fix so-001 timeout

### Root Cause

From `eval/skill-eval-results.json`:
- so-001: **300.2s** timeout, answer_length: **95 chars**, status: FAIL
- Agent found correct docs (pipelining.md + transactions.md) BUT also read 8+ noise docs
- Retrieved: transpipe.md (nodejs, dotnet, jedis, hiredis), timeseries _index.md, benchmarks
- Passing cases (single-topic): so-003=188s, so-008=191s, so-015=167s

**Why slow:** Multi-doc comparison question → agent searches for BOTH topics → hybrid_search returns client-specific transpipe.md variants alongside core docs → agent reads these one by one → 10 turns exhausted on search+read loops → no turns left for synthesis → timeout.

### 1a. Align timeout defaults

`eval_skill.py` line 233: `run_eval()` defaults to `timeout_sec=300` but CLI `--timeout` defaults to `600`. Inconsistent.

**Change:** `scripts/eval_skill.py:233` — `timeout_sec: int = 300` → `timeout_sec: int = 600`

### 1b. Improve SKILL.md for comparison queries

**File:** `.claude/skills/search/SKILL.md` — add to Step 2 (chunk sufficiency):

- For comparison questions (A vs B), focus on core concept docs not client-specific variants
- Prefer `using-commands/`, `data-types/`, `management/` over `clients/*/` for concepts
- Once BOTH core concept docs are Read, stop searching and synthesize

### 1c. Add MODEL_NAME env var support

`run_single_case()` doesn't pass `model` to `ClaudeAgentOptions`. Add support for `MODEL_NAME` env var (needed for Task 3).

**File:** `scripts/eval_skill.py:100-112` — add model param to options dict

---

## Task 2: Make RAGAS scoring default

### 2a. Default --ragas to True

**File:** `scripts/eval_skill.py:341`
- `--ragas` → `default=True`
- Add `--no-ragas` opt-out flag

### 2b. Score partial answers on timeout

Line 211 skips RAGAS if `result["error"]` is truthy. Timeout cases with partial answers (so-001 has 95 chars) should still get scored.

**Change:** `if use_ragas and result["answer"] and not result["error"]:` → `if use_ragas and result["answer"]:`

---

## Task 3: CI with DeepSeek v3.2

### 3a. Update kb-eval.yml skill eval

Replace `ANTHROPIC_API_KEY` (Claude) with `claude-code-router` + DeepSeek:

1. Add `Install Claude Code` step
2. Add `Install claude-code-router` step
3. Add `Start claude-code-router (DeepSeek)` step — configure DeepSeek provider
4. Update skill eval env: `ANTHROPIC_BASE_URL=http://127.0.0.1:3456`, `ANTHROPIC_AUTH_TOKEN=router-placeholder`
5. Remove `ANTHROPIC_API_KEY` from skill eval step

### 3b. ci.yml retrieval eval — no changes needed

Already uses DeepSeek for RAGAS judge. E2E already uses Qwen via router.

---

## Implementation Order

- [x] Task 1b: SKILL.md comparison query optimization
- [x] Task 1a: Align timeout defaults (300→600 in run_single_case + run_eval)
- [x] Task 1c: Add MODEL_NAME env var support
- [x] Task 2a+2b: RAGAS defaults (--ragas=True, --no-ragas opt-out, score partial answers)
- [x] Task 3a: CI workflow changes (DeepSeek via claude-code-router, no ANTHROPIC_API_KEY)

## Verification

- Run `python scripts/eval_skill.py` (golden subset, includes so-001) to verify timeout fix
- Verify RAGAS scores appear in default output
- CI changes verified by workflow dispatch after merge
