"""
最大安全模板的“搜索/优化”求解器（带终端日志）

优化目标（字典序）：
1) 最大化 count（选中能力数量，Max Power）
2) count 相同时最大化 utility_sum（更贴近任务）

约束：
- cap ∉ hard_ban
- sum(risk) <= budget(goal)

算法：
- 0/1 DP
- dp[b] = (count, utility_sum, chosen_caps)
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Set, Tuple


@dataclass(frozen=True)
class CapAttr:
    risk: int
    utility: int


def _better(a: Tuple[int, int, List[str]], b: Tuple[int, int, List[str]]) -> bool:
    """
    判断 a 是否比 b 更优（字典序：count 优先，其次 utility）
    """
    return (a[0] > b[0]) or (a[0] == b[0] and a[1] > b[1])


def _dp_summary(dp: List[Tuple[int, int, List[str]]]) -> str:
    """
    简短展示 dp 状态：每个 budget 下 (count, utility)
    """
    parts = []
    for b, (cnt, util, _) in enumerate(dp):
        parts.append(f"b={b}:(cnt={cnt},u={util})")
    return "  " + " | ".join(parts)


def solve_tmax_knapsack(
    goal: str,
    C: List[str],
    attrs_by_goal: Dict[str, Dict[str, CapAttr]],
    risk_budget_by_goal: Dict[str, int],
    hard_ban: Set[str],
    *,
    debug: bool = True,
    verbose_items: bool = True,
    print_dp_each_item: bool = False,
) -> List[str]:
    """
    返回：该 goal 的 T_max（能力列表）
    """
    budget = risk_budget_by_goal.get(goal, 3)
    attrs = attrs_by_goal.get(goal, {})

    # 1) 过滤 hard_ban，并为每个能力取 (risk, utility)
    items: List[Tuple[str, int, int]] = []
    for cap in C:
        if cap in hard_ban:
            if debug:
                print(f"[TMAX] HARD_BAN skip cap={cap}")
            continue
        a = attrs.get(cap, CapAttr(risk=2, utility=0))
        items.append((cap, a.risk, a.utility))

    if debug:
        print("\n" + "=" * 80)
        print(f"[TMAX] goal={goal}  budget={budget}")
        print(f"[TMAX] |C|={len(C)}  items_after_ban={len(items)}  hard_ban={sorted(list(hard_ban))}")
        print("[TMAX] items (cap, risk, utility):")
        for cap, r, u in items:
            print(f"  - {cap:15s}  risk={r}  util={u}")
        print("=" * 80 + "\n")

    # 2) 初始化 DP
    dp: List[Tuple[int, int, List[str]]] = [(0, 0, []) for _ in range(budget + 1)]
    if debug:
        print("[TMAX][DP] init:", _dp_summary(dp))

    # 3) 0/1 背包：逐个能力尝试加入
    for i, (cap, risk, util) in enumerate(items, start=1):
        if debug and verbose_items:
            print("\n" + "-" * 80)
            print(f"[TMAX][ITEM {i}/{len(items)}] cap={cap}  risk={risk}  util={util}")

        # 从后往前遍历 budget，保证 0/1（每个能力最多选一次）
        updated_any = False
        for b in range(budget, -1, -1):
            nb = b - risk
            if nb < 0:
                continue

            prev_cnt, prev_u, prev_list = dp[nb]
            cand = (prev_cnt + 1, prev_u + util, prev_list + [cap])

            cur = dp[b]

            if _better(cand, cur):
                dp[b] = cand
                updated_any = True
                if debug and verbose_items:
                    print(
                        f"[TMAX][DP UPDATE] budget={b}: "
                        f"old=(cnt={cur[0]},u={cur[1]},caps={cur[2]})  ->  "
                        f"new=(cnt={cand[0]},u={cand[1]},caps={cand[2]}) "
                        f"(from nb={nb})"
                    )

        if debug and verbose_items:
            if not updated_any:
                print("[TMAX][ITEM] no dp state improved by this cap.")

        if debug and print_dp_each_item:
            print("[TMAX][DP] after item:", _dp_summary(dp))

    # 4) 从 dp[0..budget] 里选最优
    best = max(dp, key=lambda x: (x[0], x[1]))
    chosen = best[2]
    chosen_set = set(chosen)

    # 输出顺序：按 C 原始顺序（更稳定）
    ordered = [cap for cap in C if cap in chosen_set]

    if debug:
        print("\n" + "=" * 80)
        print("[TMAX][RESULT]")
        print(f"best_count={best[0]}  best_utility={best[1]}")
        print("chosen (dp raw order):", chosen)
        print("chosen (ordered by C):", ordered)
        print("=" * 80 + "\n")

    return ordered
