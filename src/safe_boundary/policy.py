"""
组织策略 + 约束解析

- 用户约束：比如 no-network
- 组织策略：比如禁止访问 secrets/**
"""
from __future__ import annotations
from typing import Set
from .models import ConstraintBound, OrgPolicy

def build_constraint_bound(user_constraints: Set[str], org: OrgPolicy) -> ConstraintBound:
    cb = ConstraintBound()
    # 组织策略：敏感路径
    cb.forbidden_paths.extend(org.forbidden_paths)

    # 用户约束：能力禁区（demo 只示范 no-network）
    if "no-network" in user_constraints:
        cb.forbidden_capabilities.add("network:egress")

    # 任务隐含约束（demo 做一个例子：不允许 deploy）
    cb.forbidden_capabilities.add("exec:deploy")

    return cb
