"""
能力模板：T_min / T_max
T_max 通过“搜索/优化”动态计算得到。

核心：
  T_max(goal) = argmax_{S ⊆ C} |S|
    s.t.  sum_{c∈S} risk(c) ≤ budget(goal)
          c ∉ hard_ban
并用 utility(goal,c) 作为次级目标（同数量时更偏向“对任务有用”的能力）。
"""

from __future__ import annotations
from typing import Dict, List, Set

from .template_search import CapAttr, solve_tmax_knapsack

# 1) 全能力集合 C
# demo 里先放一组常见能力；后续可以把它扩成你系统完整 capability taxonomy。
C_ALL: List[str] = [
    "exec:test",
    "read:repo",
    "write:src",
    "exec:lint",
    "exec:format",
    "exec:build",
    "network:egress",
    "exec:deploy",
    "write:secrets",
    "exec:arbitrary",
]

# 2) 硬禁止能力（等价于你截图里的“非常高风险且通常不需要”）
# 它们不会被搜索纳入 T_max（相当于永远在 C_risky(goal) 中）
HARD_BAN: Set[str] = {
    "exec:deploy",
    "write:secrets",
    "exec:arbitrary",
}

# 3) goal 的风险预算（预算越大 => T_max 越“宽”）
# 这是一个可调超参：论文里可以说“由组织安全策略/环境可信度决定”
RISK_BUDGET_BY_GOAL: Dict[str, int] = {
    "fix_failing_test": 7,
}

# 4) 每个 goal 下每个能力的 (risk, utility) 估计
# - risk：能力本身的危险程度（越大越危险）
# - utility：对该 goal 的可能有用程度（越大越可能用得上）
# “不是从用了什么出发，而是从什么是安全的出发”可以落地的地方：
#   - risk 可来自：静态安全分级、历史事故、权限可逆性、影响面等
#   - utility 可来自：历史轨迹统计、任务类型先验、规则/模型估计
ATTRS_BY_GOAL: Dict[str, Dict[str, CapAttr]] = {
    "fix_failing_test": {
        "exec:test":      CapAttr(risk=1, utility=10),
        "read:repo":      CapAttr(risk=1, utility=8),
        "write:src":      CapAttr(risk=2, utility=8),
        "exec:lint":      CapAttr(risk=1, utility=4),
        "exec:format":    CapAttr(risk=1, utility=3),
        "exec:build":     CapAttr(risk=2, utility=5),
        "network:egress": CapAttr(risk=3, utility=2),  # 注意：允许进入 T_max，但会被 constraint (no-network) 在边界计算时剔除
        # deploy/secrets/arbitrary 在 HARD_BAN 里，不参与搜索
    }
}

# 仍然保留一个最小必要模板（如果你要对比 Min Power）
T_MIN: Dict[str, List[str]] = {
    "fix_failing_test": [
        "exec:test",
        "read:repo",
        "write:src",
    ],
}

# 结果缓存：避免每次都 DP（工程上很必要）
_TMAX_CACHE: Dict[str, List[str]] = {}


def t_max(goal: str) -> List[str]:
    """
    通过优化搜索求 T_max(goal)
    """
    if goal in _TMAX_CACHE:
        return list(_TMAX_CACHE[goal])

    tmax = solve_tmax_knapsack(
        goal=goal,
        C=C_ALL,
        attrs_by_goal=ATTRS_BY_GOAL,
        risk_budget_by_goal=RISK_BUDGET_BY_GOAL,
        hard_ban=HARD_BAN,
    )
    _TMAX_CACHE[goal] = list(tmax)
    return list(tmax)

