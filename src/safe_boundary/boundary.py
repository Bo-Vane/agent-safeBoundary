"""
ComputeSafeBoundary：CapabilityBound ∩ ScopeBound ∩ ¬ConstraintBound

这里实现你 method_details 里的核心算法骨架。
"""
from __future__ import annotations
from typing import Dict, List
from .models import RequirementNode, SafeBoundary, OrgPolicy
from .templates import t_max
from .policy import build_constraint_bound
from .scope_expand import expand_scope

def compute_safe_boundary(r: RequirementNode, org: OrgPolicy) -> SafeBoundary:
    cap_bound = t_max(r.goal)
    scope_bound = expand_scope(r.anchors, org=org)
    constraint_bound = build_constraint_bound(r.constraints, org=org)

    allowed: Dict[str, List[str]] = {}

    for c in cap_bound:
        # 能力禁区：直接跳过
        if c in constraint_bound.forbidden_capabilities:
            continue

        # 允许作用域：scope_bound - forbidden_paths
        # demo 用“从 scope_bound 中剔除与 forbidden_paths 同类的 pattern”
        allowed_scope = []
        for sp in scope_bound:
            # 简化：如果 pattern 包含 forbidden 的关键词就过滤
            blocked = False
            for fp in constraint_bound.forbidden_paths:
                key = fp.split("/")[0].replace("**", "").replace("*", "")
                if key and key in sp:
                    blocked = True
                    break
            if not blocked:
                allowed_scope.append(sp)

        # 组合禁区（demo 没细化）
        if allowed_scope:
            allowed[c] = allowed_scope

    return SafeBoundary(allowed=allowed)
