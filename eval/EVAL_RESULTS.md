# Eval Results

> Generated: 2026-03-02 16:36 UTC | Commit: `d0a2dc9` | Branch: `master`

## Summary

| Eval | Cases | Passed | Rate | Faithfulness | Time |
|------|-------|--------|------|-------------|------|
| Retrieval | 35 | 35 | 100.0% | — | 26.4m |
| Skill (E2E) | 6 | 5 | 83.3% | — | 7.2m |

## Retrieval Eval — Detail

| ID | Topic | Status | Tools | Retrieved Paths | Answer | Time |
|----|-------|--------|-------|-----------------|--------|------|
| so-001 | pipelining | ✅ | — | transpipe.md, transpipe.md | top=2.28 | — |
| so-002 | pipelining | ✅ | — | transpipe.md, pipelining.md | top=2.64 | — |
| so-003 | sentinel | ✅ | — | sentinel.md, sentinel.md | top=2.30 | — |
| so-004 | sentinel | ✅ | — | sentinel.md, sentinel.md | top=5.03 | — |
| so-005 | data-types | ✅ | — | sorted-sets.md, sorted-sets.md | top=1.08 | — |
| so-006 | data-types | ✅ | — | lists.md, _index.md | top=2.22 | — |
| so-007 | data-types | ✅ | — | hash_vs_json.md, hash_vs_json.md | top=3.00 | — |
| so-008 | persistence | ✅ | — | persistence.md, database-persistence.md | top=6.16 | — |
| so-009 | persistence | ✅ | — | persistence.md, persistence.md | top=3.05 | — |
| so-010 | memory | ✅ | — | resource-usage.md, resource-usage.md | top=0.73 | — |
| so-011 | memory | ✅ | — | index.md, index.md | top=5.32 | — |
| so-012 | security | ✅ | — | acl.md, acl.md | top=3.07 | — |
| so-013 | security | ✅ | — | admin.md, sentinel.md | top=4.11 | — |
| so-014 | pubsub-streams | ✅ | — | _index.md, _index.md | top=4.99 | — |
| so-015 | cluster | ✅ | — | scaling.md, scaling.md | top=4.65 | — |
| so-016 | cluster | ✅ | — | sentinel-clients.md, sentinel.md | top=5.82 | — |
| so-017 | replication | ✅ | — | replication.md, replication.md | top=4.11 | — |
| so-018 | clients | ✅ | — | connect.md, _index.md | top=4.06 | — |
| so-019 | ai | ✅ | — | _index.md, _index.md | top=6.05 | — |
| so-020 | scripting | ✅ | — | _index.md, eval-intro.md | top=2.77 | — |
| so-021 | security | ✅ | — | connect.md, _index.md | top=5.01 | — |
| so-022 | cloud | ✅ | — | _index.md, rc-quickstart.md | top=5.95 | — |
| so-023 | kubernetes | ✅ | — | _index.md, _index.md | top=5.83 | — |
| so-024 | data-types | ✅ | — | use_cases.md, index.md | top=4.07 | — |
| so-025 | benchmark | ✅ | — | _index.md, memtier-benchmark.md | top=3.88 | — |
| cn-001 | pipelining | ✅ | — | transpipe.md, transpipe.md | top=3.68 | — |
| cn-002 | sentinel | ✅ | — | sentinel.md, sentinel.md | top=2.77 | — |
| cn-003 | persistence | ✅ | — | persistence.md, persistence.md | top=4.19 | — |
| cn-004 | memory | ✅ | — | index.md, _index.md | top=2.82 | — |
| cn-005 | cluster | ✅ | — | scaling.md, scaling.md | top=4.75 | — |
| cn-006 | data-types | ✅ | — | sorted-sets.md, sorted-sets.md | top=0.88 | — |
| cn-007 | pubsub-streams | ✅ | — | _index.md, _index.md | top=3.35 | — |
| cn-008 | security | ✅ | — | acl.md, acl.md | top=3.47 | — |
| cn-009 | ai | ✅ | — | schema.md, _index.md | top=4.64 | — |
| cn-010 | replication | ✅ | — | replication.md, replication.md | top=3.30 | — |

## Skill Eval (E2E Agent) — Detail

| ID | Topic | Status | Tools | Retrieved Paths | Answer | Time |
|----|-------|--------|-------|-----------------|--------|------|
| so-001 | pipelining | ❌ | Grep, Read, hybrid_search | _index.md, 8-4.md | ⚠️ timeout (300s) | 300s |
| so-003 | sentinel | ✅ | Grep, Read, hybrid_search | sentinel.md | 2964c | 189s |
| so-008 | persistence | ✅ | Grep, Read, hybrid_search | data-persistence.md, persistence.md | 3264c | 191s |
| so-015 | cluster | ✅ | Grep, Read, hybrid_search | scaling.md, cluster-spec.md | 2683c | 167s |
| so-019 | ai | ✅ | Grep, Read, hybrid_search | redisearch-2.4-release-notes.md, schema.md | 5796c | 242s |
| cn-003 | persistence | ✅ | Grep, Read, hybrid_search | data-persistence.md, persistence.md | 2050c | 132s |

### Failed Cases (1)

- **so-001**: timeout (300s)
