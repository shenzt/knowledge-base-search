#!/usr/bin/env python3
"""index.py 分块逻辑的单元测试。"""

import sys
from pathlib import Path

# 让 import 能找到 scripts/
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from index import split_by_headings, merge_small_sections, _same_parent, _find_code_fence_ranges, _in_code_fence


class TestSplitByHeadings:
    """测试按 Markdown 标题切分。"""

    def test_no_headings(self):
        """无标题的纯文本 → 单个 chunk，空 section_path。"""
        content = "This is plain text.\n\nAnother paragraph."
        result = split_by_headings(content)
        assert len(result) == 1
        assert result[0]["section_path"] == ""
        assert "plain text" in result[0]["text"]

    def test_single_heading(self):
        """单个标题 → 标题后的内容作为一个 section。"""
        content = "## Overview\n\nThis is the overview."
        result = split_by_headings(content)
        assert len(result) == 1
        assert result[0]["section_path"] == "Overview"
        assert "overview" in result[0]["text"].lower()

    def test_nested_headings(self):
        """嵌套标题 → section_path 保留层级。"""
        content = """## 故障恢复

恢复步骤概述。

### 手动恢复

手动恢复的详细步骤。

### 自动恢复

自动恢复的详细步骤。

## 预防措施

预防措施说明。"""
        result = split_by_headings(content)
        paths = [s["section_path"] for s in result]

        assert "故障恢复" in paths
        assert "故障恢复 > 手动恢复" in paths
        assert "故障恢复 > 自动恢复" in paths
        assert "预防措施" in paths

    def test_deep_nesting(self):
        """三级嵌套 → section_path 正确。"""
        content = """## A

text a

### B

text b

#### C

text c"""
        result = split_by_headings(content)
        paths = [s["section_path"] for s in result]
        assert "A > B > C" in paths

    def test_sibling_headings_reset(self):
        """同级标题 → 弹出栈，不累积。"""
        content = """## Section 1

content 1

## Section 2

content 2

## Section 3

content 3"""
        result = split_by_headings(content)
        paths = [s["section_path"] for s in result]
        assert paths == ["Section 1", "Section 2", "Section 3"]

    def test_text_before_first_heading(self):
        """标题前有文本 → 空 section_path。"""
        content = """Intro text before any heading.

## First Section

Section content."""
        result = split_by_headings(content)
        assert result[0]["section_path"] == ""
        assert "Intro" in result[0]["text"]
        assert result[1]["section_path"] == "First Section"

    def test_heading_in_code_block_skipped(self):
        """代码块中的 # 不应被当作标题。"""
        content = """## Real Heading

Some text.

```bash
# This is a comment, not a heading
echo hello
```

More text after code block."""
        result = split_by_headings(content)
        assert len(result) == 1
        assert result[0]["section_path"] == "Real Heading"
        assert "comment" in result[0]["text"]
        assert "More text" in result[0]["text"]

    def test_multiple_code_blocks(self):
        """多个代码块中的 # 都应跳过。"""
        content = """## Section A

```python
# python comment
def foo():
    pass
```

Text between.

```yaml
# yaml comment
key: value
```

## Section B

Content B."""
        result = split_by_headings(content)
        paths = [s["section_path"] for s in result]
        assert "Section A" in paths
        assert "Section B" in paths
        # 不应有 python comment 或 yaml comment 作为 section_path
        for s in result:
            assert "python comment" not in s["section_path"]
            assert "yaml comment" not in s["section_path"]


class TestCodeFenceRanges:
    """测试代码围栏检测。"""

    def test_single_fence(self):
        content = "before\n```\ncode\n```\nafter"
        ranges = _find_code_fence_ranges(content)
        assert len(ranges) == 1

    def test_no_fence(self):
        content = "no code blocks here"
        ranges = _find_code_fence_ranges(content)
        assert len(ranges) == 0

    def test_unclosed_fence(self):
        """未闭合的代码块 → 不形成范围。"""
        content = "before\n```\ncode without closing"
        ranges = _find_code_fence_ranges(content)
        assert len(ranges) == 0

    def test_in_code_fence(self):
        content = "before\n```\n# comment\n```\nafter"
        ranges = _find_code_fence_ranges(content)
        # "# comment" 的位置应在范围内
        pos = content.index("# comment")
        assert _in_code_fence(pos, ranges) is True
        # "after" 应在范围外
        pos_after = content.index("after")
        assert _in_code_fence(pos_after, ranges) is False


class TestMergeSmallSections:
    """测试合并过短 section。"""

    def test_merge_short_siblings(self):
        """同父级下的短 section 合并。"""
        sections = [
            {"text": "short 1", "section_path": "A > B"},
            {"text": "short 2", "section_path": "A > C"},
        ]
        result = merge_small_sections(sections, max_chars=3200)
        assert len(result) == 1  # 合并了
        assert "short 1" in result[0]["text"]
        assert "short 2" in result[0]["text"]

    def test_no_merge_different_parents(self):
        """不同父级的 section 不合并。"""
        sections = [
            {"text": "x" * 100, "section_path": "A > B"},
            {"text": "y" * 100, "section_path": "C > D"},
        ]
        result = merge_small_sections(sections, max_chars=3200)
        assert len(result) == 2

    def test_no_merge_when_too_long(self):
        """合并后超过 max_chars → 不合并。"""
        sections = [
            {"text": "x" * 2000, "section_path": "A > B"},
            {"text": "y" * 2000, "section_path": "A > C"},
        ]
        result = merge_small_sections(sections, max_chars=3200)
        assert len(result) == 2

    def test_empty_input(self):
        """空输入 → 空输出。"""
        assert merge_small_sections([]) == []

    def test_single_section(self):
        """单个 section → 原样返回。"""
        sections = [{"text": "hello", "section_path": "A"}]
        result = merge_small_sections(sections)
        assert len(result) == 1
        assert result[0]["text"] == "hello"


class TestSameParent:
    """测试 _same_parent 辅助函数。"""

    def test_same_parent(self):
        assert _same_parent("A > B", "A > C") is True

    def test_different_parent(self):
        assert _same_parent("A > B", "C > D") is False

    def test_root_level(self):
        assert _same_parent("A", "B") is True  # 都是根级

    def test_empty(self):
        assert _same_parent("", "") is True

    def test_deep_same(self):
        assert _same_parent("A > B > C", "A > B > D") is True

    def test_deep_different(self):
        assert _same_parent("A > B > C", "A > X > D") is False
