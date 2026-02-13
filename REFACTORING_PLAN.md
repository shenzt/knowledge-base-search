# Knowledge Base Search - Refactoring Plan

**Date**: 2025-02-13
**Goal**: Reorganize project structure following Claude Code best practices, BMAD-METHOD, and spec-kit principles

## Current Issues

1. **Root directory clutter**: 20+ markdown files, test files mixed with source
2. **Inconsistent naming**: `kb_skills/` vs `meta_skills/` vs `.claude/skills/`
3. **Test organization**: Test files scattered in root, no clear structure
4. **Documentation sprawl**: Multiple summary/status/report files with overlapping content
5. **Missing verification**: No systematic way to verify changes work
6. **Configuration scattered**: API config, environment setup not centralized

## Refactoring Principles (from Claude Code Best Practices)

1. **Give Claude a way to verify its work** - Add tests and validation
2. **Explore first, then plan, then code** - Use Plan Mode for complex changes
3. **Provide specific context** - Clear CLAUDE.md with project conventions
4. **Configure environment properly** - Skills, hooks, permissions
5. **Manage context aggressively** - Clean up unnecessary files

## Target Structure

```
knowledge-base-search/
├── .claude/
│   ├── skills/              # All skills consolidated here
│   │   ├── search/
│   │   ├── ingest/
│   │   ├── index-docs/
│   │   ├── review/
│   │   └── run-rag-task/
│   ├── rules/               # Path-based rules
│   │   ├── retrieval-strategy.md
│   │   ├── doc-frontmatter.md
│   │   └── python-style.md
│   └── agents/              # Custom subagents (if needed)
│
├── docs/
│   ├── design.md            # Architecture & design
│   ├── api/                 # API documentation
│   ├── runbook/             # Operational runbooks
│   └── guides/              # User guides
│       ├── setup.md
│       ├── configuration.md
│       └── workflows.md
│
├── specs/                   # Specifications (spec-kit style)
│   ├── 001-hybrid-search/
│   │   ├── spec.md
│   │   ├── plan.md
│   │   └── validation.md
│   └── 002-rag-worker/
│       ├── spec.md
│       └── plan.md
│
├── scripts/
│   ├── mcp_server.py        # MCP Server
│   ├── index.py             # Indexing tool
│   ├── requirements.txt
│   └── utils/               # Utility modules
│
├── tests/
│   ├── unit/                # Unit tests
│   ├── integration/         # Integration tests
│   │   ├── test_mcp_server.py
│   │   └── test_hybrid_search.py
│   ├── e2e/                 # End-to-end tests
│   │   ├── test_simple_e2e.py
│   │   ├── test_rag_worker.py
│   │   └── fixtures/
│   └── conftest.py          # Pytest configuration
│
├── eval/                    # Evaluation results
│   └── results/
│
├── raw/                     # Raw documents (not indexed)
│
├── .env.example             # Environment template
├── .env                     # Local environment (gitignored)
├── .gitignore
├── .mcp.json
├── CLAUDE.md                # Improved with best practices
├── README.md                # Clean, focused README
├── Makefile
├── docker-compose.yml
└── pyproject.toml           # Python project metadata
```

## Phase 1: Documentation Consolidation

### Actions:
1. **Create specs/ directory** following spec-kit methodology
   - Move hybrid search validation to `specs/001-hybrid-search/`
   - Move RAG worker design to `specs/002-rag-worker/`
   - Create spec templates

2. **Consolidate documentation**
   - Keep: README.md, CLAUDE.md, docs/design.md
   - Archive to docs/archive/:
     - All *_SUMMARY.md files
     - All *_REPORT.md files
     - STATUS.md, DEMO.md, TEST_REPORT.md
   - Create docs/guides/ for user-facing guides

3. **Update README.md**
   - Focus on quick start
   - Link to detailed docs
   - Remove redundant information

### Files to Archive:
- AGENTIC_RAG_IMPROVEMENT.md → specs/003-agentic-improvements/
- COMPLETE_SUMMARY.md → docs/archive/
- CURRENT_STATUS.md → docs/archive/
- DEMO.md → docs/guides/demo.md
- DUAL_LAYER_SUMMARY.md → docs/archive/
- E2E_*.md (7 files) → specs/001-hybrid-search/validation/
- FINAL_*.md → docs/archive/
- HYBRID_SEARCH_*.md → specs/001-hybrid-search/
- NEXT_STEPS.md → docs/archive/
- PERFORMANCE_RESULTS.md → specs/001-hybrid-search/
- PROJECT_STATUS.md → docs/archive/
- SIMPLE_E2E_ANALYSIS.md → specs/001-hybrid-search/
- STATUS.md → docs/archive/
- SUMMARY.md → docs/archive/
- TEST_REPORT.md → docs/archive/

## Phase 2: Test Organization

### Actions:
1. **Create tests/ directory structure**
   ```
   tests/
   ├── unit/
   ├── integration/
   ├── e2e/
   └── conftest.py
   ```

2. **Move and organize test files**
   - test_simple_e2e.py → tests/e2e/
   - test_rag_worker.py → tests/e2e/
   - test_direct_mcp.py → tests/integration/
   - test_hybrid_search.py → tests/integration/
   - test_mcp_hybrid.py → tests/integration/
   - test_quick_*.py → tests/integration/
   - test_search*.py → tests/integration/
   - simple_rag_worker.py → scripts/workers/
   - rag_worker.py → scripts/workers/

3. **Create test utilities**
   - tests/conftest.py - pytest configuration
   - tests/fixtures/ - test data
   - tests/utils.py - test helpers

4. **Add verification to CLAUDE.md**
   ```markdown
   # Testing & Verification
   - Run tests after changes: `make test`
   - E2E tests validate full workflow
   - Integration tests check MCP server
   ```

## Phase 3: Skills Consolidation

### Actions:
1. **Consolidate all skills to .claude/skills/**
   - Move kb_skills/* → .claude/skills/
   - Move meta_skills/* → .claude/skills/
   - Remove empty kb_skills/ and meta_skills/ directories

2. **Review and optimize skills**
   - Ensure each skill has clear description
   - Add verification steps to skills
   - Update skill documentation

3. **Create skill index**
   - .claude/skills/README.md listing all skills

## Phase 4: Configuration & Environment

### Actions:
1. **Create pyproject.toml** for Python project metadata
   ```toml
   [project]
   name = "knowledge-base-search"
   version = "0.1.0"
   description = "Agentic RAG knowledge base with hybrid search"
   requires-python = ">=3.10"
   ```

2. **Improve .env management**
   - Keep .env.example comprehensive
   - Update API_CONFIG.md → docs/guides/configuration.md

3. **Update .gitignore** based on best practices
   - Add common Python patterns
   - Add test artifacts
   - Add eval results

## Phase 5: CLAUDE.md Enhancement

### Actions:
1. **Rewrite CLAUDE.md** following best practices:
   - Keep it concise (current is good)
   - Add testing commands
   - Add verification workflows
   - Reference skills properly
   - Add common gotchas

2. **Example improvements**:
   ```markdown
   # Testing & Verification
   - After code changes: `make test`
   - After indexing: `.venv/bin/python scripts/index.py --status`
   - E2E validation: `pytest tests/e2e/ -v`

   # Common Commands
   - Start services: `make start`
   - Run tests: `make test`
   - Index docs: `make index`

   # Gotchas
   - Always activate venv before running Python scripts
   - Qdrant must be running for MCP server
   - First run downloads BGE-M3 model (~2-3 min)
   ```

## Phase 6: Makefile Enhancement

### Actions:
1. **Add comprehensive targets**:
   ```makefile
   .PHONY: help setup start stop test test-unit test-integration test-e2e clean

   help:  ## Show this help
   setup: ## Setup environment
   start: ## Start services
   stop:  ## Stop services
   test:  ## Run all tests
   test-unit: ## Run unit tests
   test-integration: ## Run integration tests
   test-e2e: ## Run E2E tests
   clean: ## Clean artifacts
   ```

## Implementation Order

1. **Phase 1** (Documentation) - Low risk, high clarity gain
2. **Phase 2** (Tests) - Medium risk, enables verification
3. **Phase 3** (Skills) - Low risk, better organization
4. **Phase 4** (Config) - Low risk, better structure
5. **Phase 5** (CLAUDE.md) - Low risk, better guidance
6. **Phase 6** (Makefile) - Low risk, better DX

## Verification Strategy

After each phase:
1. Run existing tests to ensure nothing broke
2. Verify skills still work: `/search`, `/index-docs`
3. Check MCP server still starts
4. Validate documentation links

## Success Criteria

- [ ] Root directory has <10 files
- [ ] All tests in tests/ directory
- [ ] All skills in .claude/skills/
- [ ] Documentation organized and navigable
- [ ] CLAUDE.md follows best practices
- [ ] All tests pass
- [ ] Skills work correctly
- [ ] Clear verification workflow exists

## Notes

- Keep git history clean with semantic commits
- Test after each phase
- Update documentation as we go
- Don't break existing functionality
