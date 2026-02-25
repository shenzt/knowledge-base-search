# Plan: INDEX.md + Parallel Embedding + CLAUDE.md Update

## Context

The Redis docs KB repo has 3,329 markdown files with significant versioning complexity:
- `develop/` (650 files): mostly non-versioned, except `ai/redisvl/` (12 versions)
- `operate/rs/` (1,860 files): 3 versions (7.4, 7.8, 7.22) + non-versioned root
- Massive duplication: same docs repeated across versions (~1,289 duplicated files)
- No explicit `version` field in frontmatter — version is only in the URL path

This causes problems:
1. Search returns duplicate results from different versions of the same doc
2. 15,246 chunks is inflated by ~40% due to version duplication
3. Agent doesn't know which version is "latest" or how to handle version-specific queries

## Tasks

### Task 1: Create INDEX.md for KB repo (search/generation guide)

Create `kb/kb-redis-docs/INDEX.md` that serves as a guide for the Agent during search and answer generation.

Contents:
- **KB overview**: what this KB contains, source repo, last sync date
- **Directory structure**: explain `develop/` vs `operate/` split
- **Version strategy**:
  - Default behavior: answer based on latest/non-versioned docs
  - When user asks about a specific version: scope search to that version dir
  - When user asks to compare versions: search across version dirs
- **Version mapping**: which version dirs exist and which is "latest"
  - `operate/rs/` (non-versioned) = latest
  - `operate/rs/7.22/` = Redis Enterprise 7.22
  - `operate/rs/7.8/` = Redis Enterprise 7.8
  - `operate/rs/7.4/` = Redis Enterprise 7.4
  - `develop/ai/redisvl/` (non-versioned) = latest
  - `develop/ai/redisvl/0.12.1/` = RedisVL 0.12.1 (latest pinned)
- **Search hints**: which directories to search for common query types
  - Data types → `develop/data-types/`
  - Client libraries → `develop/clients/`
  - Cluster/HA/Sentinel → `operate/oss_and_stack/` or `operate/rs/`
  - Kubernetes → `operate/kubernetes/`
  - Redis Cloud → `operate/rc/`
  - AI/Vector search → `develop/ai/`
- **Answer generation rules**:
  - Always cite the file path and section
  - If answering from a versioned doc, state the version
  - Prefer non-versioned (latest) docs unless version-specific query

### Task 2: Update CLAUDE.md with current index stats

- Update "2811 chunks" → "15,246 chunks"
- Update data source descriptions to reflect the CI-built Redis docs index
- Add note about embedding provider abstraction (`EMBEDDING_PROVIDER` env var)
- Add CI workflow description (kb-update.yml: sync → preprocess → index → snapshot)

### Task 3: Parallel embedding in CI (plan only, implement later)

Add to `OpenAICompatibleProvider.encode_texts()`:
- Use `ThreadPoolExecutor` or `asyncio` to send 4-8 concurrent API batches
- Keep batch size at 64, but send multiple batches in parallel
- Add `EMBEDDING_CONCURRENCY` env var (default 4)
- Expected speedup: ~25 min → ~5-7 min for 15K chunks

This is a plan item — implementation deferred until next CI rebuild is needed.

### Task 4: Consider version-aware indexing (future)

Options to reduce duplication in the index:
- **Option A**: Only index non-versioned (latest) docs, skip version dirs entirely
  - Pro: cuts index from 15K to ~9K chunks, cleaner search
  - Con: can't answer version-specific questions
- **Option B**: Index all but add `version` metadata to chunks
  - Pro: can filter by version in search
  - Con: still 15K chunks, need to update index.py to extract version from path
- **Option C**: Index latest + keep version dirs as Read-only fallback
  - Pro: small index + version access via Read tool
  - Con: version content not searchable

Recommendation: Start with Option A (skip version dirs in `doc_filter`), add version dirs back later if needed. The `doc_filter` input in kb-update.yml already supports this.

## Execution Order

- [x] Task 2: Update CLAUDE.md (quick, no dependencies)
- [x] Task 1: Create INDEX.md (main deliverable)
- [x] Task 3: Parallel embedding (EMBEDDING_CONCURRENCY + ThreadPoolExecutor)
- [ ] Task 4: Version-aware indexing (future decision, on hold)
