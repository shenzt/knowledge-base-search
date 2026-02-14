#!/usr/bin/env python3
"""eval_module 单元测试。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from eval_module import (
    extract_contexts, _extract_doc_paths, get_tools_used,
    get_retrieved_doc_paths, gate_check,
)


class TestExtractDocPaths:
    def test_grep_result(self):
        text = "Found 2 files\ndocs/runbook/redis.md\ndocs/api/auth.md"
        paths = _extract_doc_paths(text, "Grep")
        assert "docs/runbook/redis.md" in paths
        assert "docs/api/auth.md" in paths

    def test_glob_returns_empty(self):
        """Glob 结果太多噪音，不提取。"""
        text = "/path/to/docs/a.md\n/path/to/docs/b.md"
        paths = _extract_doc_paths(text, "Glob")
        assert paths == []

    def test_read_result(self):
        text = "1→---\n2→id: test\n3→title: Test Doc"
        paths = _extract_doc_paths(text, "Read")
        assert paths == []  # Read result 没有 .md 路径

    def test_mcp_hybrid_search_result(self):
        """MCP hybrid_search 返回 JSON，提取 path 字段。"""
        text = '{"result":"[{\"score\": 3.43, \"path\": \"tests/fixtures/kb-sources/redis-docs/content/operate/oss_and_stack/management/sentinel.md\", \"title\": \"High availability\"}]"}'
        paths = _extract_doc_paths(text, "mcp__knowledge-base__hybrid_search")
        assert any("sentinel.md" in p for p in paths)


class TestExtractContexts:
    def test_tool_use_and_result(self):
        messages = [
            {"content": "[ToolUseBlock(id='abc', name='Grep', input={'-i': True, 'path': 'docs/', 'pattern': 'Redis'})]"},
            {"content": "[ToolResultBlock(tool_use_id='abc', content='Found 1 file\\ndocs/runbook/redis.md', is_error=None)]"},
        ]
        contexts = extract_contexts(messages)
        assert len(contexts) == 1
        assert contexts[0]["tool"] == "Grep"
        assert "redis.md" in str(contexts[0]["doc_paths"])

    def test_text_block_ignored(self):
        messages = [
            {"content": "[TextBlock(text='Let me search for that.')]"},
        ]
        contexts = extract_contexts(messages)
        assert len(contexts) == 0

    def test_init_and_success_ignored(self):
        messages = [
            {"subtype": "init", "data": {}},
            {"subtype": "success", "result": "answer"},
        ]
        contexts = extract_contexts(messages)
        assert len(contexts) == 0


class TestGateCheck:
    def test_local_found_passes(self):
        tc = {"expected_doc": "redis-failover.md", "source": "local"}
        contexts = [{"type": "context", "tool": "Grep", "doc_paths": ["docs/runbook/redis-failover.md"], "result": "..."}]
        answer = "根据文档... [来源: docs/runbook/redis-failover.md]"
        gate = gate_check(tc, answer, contexts)
        assert gate["passed"] is True

    def test_missing_expected_doc_fails(self):
        tc = {"expected_doc": "redis-failover.md", "source": "local"}
        contexts = [{"type": "context", "tool": "Grep", "doc_paths": ["docs/api/auth.md"], "result": "..."}]
        answer = "Some answer"
        gate = gate_check(tc, answer, contexts)
        assert gate["passed"] is False
        assert any("未检索到期望文档" in r for r in gate["reasons"])

    def test_notfound_admits_passes(self):
        tc = {"expect_no_results": True, "source": "none"}
        contexts = [{"type": "context", "tool": "Grep", "doc_paths": [], "result": "no matches"}]
        answer = "未找到相关文档。"
        gate = gate_check(tc, answer, contexts)
        assert gate["passed"] is True

    def test_notfound_with_factual_claims_fails(self):
        tc = {"expect_no_results": True, "source": "none"}
        contexts = [{"type": "context", "tool": "Grep", "doc_paths": [], "result": "no matches"}]
        answer = "x" * 600  # 长答案且不含"未找到"
        gate = gate_check(tc, answer, contexts)
        assert gate["passed"] is False

    def test_notfound_admits_with_mei_you_bao_han(self):
        """没有包含 should be recognized as admitting not found."""
        tc = {"expect_no_results": True, "source": "none"}
        contexts = [{"type": "context", "tool": "Grep", "doc_paths": [], "result": "no matches"}]
        answer = "根据检索结果，docs/ 目录中没有包含 Kafka 相关内容。" + "x" * 600
        gate = gate_check(tc, answer, contexts)
        assert gate["checks"]["admits_not_found"] is True
        assert gate["checks"]["has_factual_claims"] is False
        assert gate["passed"] is True

    def test_qdrant_without_mcp_fails(self):
        import os
        os.environ["USE_MCP"] = "0"
        tc = {"expected_doc": "pods/_index.md", "source": "qdrant"}
        contexts = [{"type": "context", "tool": "Grep", "doc_paths": ["docs/other.md"], "result": "..."}]
        answer = "Some answer about pods"
        gate = gate_check(tc, answer, contexts)
        assert gate["passed"] is False

    def test_no_contexts_fails(self):
        tc = {"expected_doc": "redis.md", "source": "local"}
        answer = "Some answer"
        gate = gate_check(tc, answer, [])
        assert gate["passed"] is False
        assert any("无检索结果" in r for r in gate["reasons"])

    def test_must_use_tool(self):
        tc = {"expected_doc": "redis.md", "source": "local", "must_use": ["hybrid_search"]}
        contexts = [{"type": "context", "tool": "Grep", "doc_paths": ["docs/redis.md"], "result": "..."}]
        answer = "Answer [来源: docs/redis.md]"
        gate = gate_check(tc, answer, contexts)
        assert gate["passed"] is False
        assert any("未调用必需工具" in r for r in gate["reasons"])
