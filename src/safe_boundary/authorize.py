"""
Authorize + Drift Gate（诊断）

Grant(q, r, E) iff q ∈ SafeBoundary(r) and EvidenceSupported(q, E)
否则拒绝，并给出可操作诊断。
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional
import time

from .models import Evidence, Lease, OrgPolicy, Request, RequirementNode, SafeBoundary
from .boundary import compute_safe_boundary
from .evidence import evidence_supported

@dataclass
class Decision:
    ok: bool
    lease: Optional[Lease] = None
    reason: Optional[str] = None
    suggestion: Optional[List[str]] = None
    safe_boundary: Optional[SafeBoundary] = None

def authorize(req: Request, r: RequirementNode, org: OrgPolicy, ttl_seconds: int = 300) -> Decision:
    sb = compute_safe_boundary(r, org)

    # 1) 边界检查
    if not sb.allows(req):
        return Decision(
            ok=False,
            reason=_diagnose_violation(req, sb, r),
            suggestion=_suggest(req, sb, r),
            safe_boundary=sb,
        )

    # 2) 证据检查
    if not evidence_supported(req, r, r.evidences):
        return Decision(
            ok=False,
            reason="需要更多证据支持该请求（EvidenceSupported=false）",
            suggestion=["运行相关测试/构建以收集证据", "或补充 anchors/上下文以缩小作用域"],
            safe_boundary=sb,
        )

    # 3) 授权：发放 lease（scope + TTL + evidence snapshot）
    lease = Lease(
        capability=req.capability,
        scope_patterns=sb.allowed.get(req.capability, []),
        expires_at=time.time() + ttl_seconds,
        bound_rid=r.rid,
        evidence_snapshot=list(r.evidences),
    )
    return Decision(ok=True, lease=lease, safe_boundary=sb)

def _diagnose_violation(req: Request, sb: SafeBoundary, r: RequirementNode) -> str:
    # 能力越界
    if req.capability not in sb.allowed:
        # 可能是约束导致被剔除，也可能是模板里就没有
        if req.capability == "network:egress" and "no-network" in r.constraints:
            return "拒绝：违反约束 no-network（network:egress 被硬禁止）"
        return f"拒绝：能力越界（{req.capability} 不在当前 goal={r.goal} 的安全能力范围内）"

    # 作用域越界
    return f"拒绝：作用域越界（{req.scope} 不在 {req.capability} 的允许作用域内）"

def _suggest(req: Request, sb: SafeBoundary, r: RequirementNode) -> List[str]:
    if req.capability == "network:egress" and "no-network" in r.constraints:
        return [
            "如果确实需要联网：请用户解除 no-network 约束，或创建新需求节点显式升级权限",
            "优先尝试离线方案（使用本地缓存/锁文件/镜像）",
        ]
    if req.capability not in sb.allowed:
        return ["检查是否需要该能力完成任务", "考虑拆分任务并创建新需求节点"]
    return ["检查该路径是否与当前 anchors 相关", "扩展 anchors 以包含该路径（或创建新需求）"]
