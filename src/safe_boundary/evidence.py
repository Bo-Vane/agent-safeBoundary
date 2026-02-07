"""
EvidenceSupported：证据支持判断

你的方案强调“外部证据优先”（tests/build/logs/diff）。
demo 里给一个可运行的最小规则：

- exec:test：允许（本身就是为了拿证据）
- read:repo：允许
- write:src：需要存在 test_fail 证据，并且写入路径在 anchors 扩展出的范围内
- network:egress：即使模板允许，也可能被 no-network 约束禁止（在边界计算时就会剔除）
"""
from __future__ import annotations
from typing import List
from .models import Evidence, Request, RequirementNode

def evidence_supported(req: Request, r: RequirementNode, evidences: List[Evidence]) -> bool:
    if req.capability in ("exec:test", "read:repo", "exec:lint", "exec:format", "exec:build"):
        return True

    if req.capability == "write:src":
        # 需要至少一个失败测试证据即可（作用域相关性由 SafeBoundary 负责保证）
        has_fail = any(e.kind == "test_fail" for e in evidences)
        return has_fail

    # 其他能力默认需要更多证据（保守）
    return False
