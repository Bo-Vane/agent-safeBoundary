"""
从用户指令中抽取 goal / anchors / constraints 的最小可运行实现（rule-based）

真实系统里这一步可以替换为：
- LLM/小模型分类 + JSON schema 约束
- 规则 + 统计模型（关键词/意图分类）
- 或者“多候选 -> 验证 -> 选最一致”的策略

demo 版本目标：
- 让 RequirementNode 不再“写死”
- 给一个可解释、可复现的抽取过程
"""
from __future__ import annotations
from typing import Dict, Set, Tuple
import re

# --- goal 分类（demo：关键词规则） ---
_GOAL_RULES = [
    # (pattern, goal)
    (r"(修复|fix).*(失败测试|failing\s+test|test\s+fail)", "fix_failing_test"),
    (r"(运行|run).*(测试|tests?)", "run_tests"),
    (r"(格式化|format)", "format_code"),
    (r"(lint|静态检查)", "lint_code"),
]

def extract_requirement(user_instruction: str) -> Tuple[str, Dict[str, str], Set[str]]:
    """
    输入：用户指令（自然语言）
    输出：(goal, anchors, constraints)

    anchors（初始锚点）：
      - 如果用户指令里显式提到文件路径 / 测试用例，则抽取出来
      - 否则为空（让 Agent 先跑测试拿证据，之后再更新 anchors）
    constraints：
      - demo 只示范 no-network
    """
    text = user_instruction.strip()

    # 1) goal
    goal = "unknown"
    for pat, g in _GOAL_RULES:
        if re.search(pat, text, flags=re.IGNORECASE):
            goal = g
            break

    # 2) constraints
    constraints: Set[str] = set()
    if re.search(r"(禁止联网|不联网|no\s*network|without\s*network|offline)", text, flags=re.IGNORECASE):
        constraints.add("no-network")

    # 3) anchors
    anchors: Dict[str, str] = {}

    # 抽取 tests/foo.py::test_xxx 形式
    m = re.search(r"((?:tests|test)[/\\][\w\-/\\\.]+\.py)::([A-Za-z_]\w*)", text)
    if m:
        test_file = m.group(1).replace("\\", "/")
        test_name = m.group(2)
        anchors["test"] = f"{test_file}::{test_name}"
        anchors["path"] = test_file  # 作为初始锚点文件路径

    # 抽取 repo 内路径（非常简化：出现 src/... 或 tests/...）
    m2 = re.search(r"((?:src|tests)[/\\][\w\-/\\\.]+)", text)
    if m2 and "path" not in anchors:
        anchors["path"] = m2.group(1).replace("\\", "/")

    return goal, anchors, constraints
