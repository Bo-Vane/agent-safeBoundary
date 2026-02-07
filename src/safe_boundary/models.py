from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
import time
import fnmatch

Capability = str  # e.g. "exec:test", "read:repo", "write:src", "network:egress"
PathPattern = str # e.g. "src/auth/**", "tests/**"

@dataclass
class Evidence:
    """
    证据：来自工具输出（测试日志、构建日志、diff 等）。
    demo 里我们只放最小字段，实际可扩展：hash、原始日志、CI 链接等。
    """
    kind: str                    # "test_fail", "test_pass", "diff", ...
    payload: Dict[str, str]      # 结构化内容

@dataclass
class RequirementNode:
    """
    需求节点：把 goal / anchors / constraints / state 汇聚起来，作为“语境容器”。
    """
    rid: str
    goal: str
    anchors: Dict[str, str] = field(default_factory=dict)       # e.g. {"test": "test_login", "path": "src/auth/"}
    constraints: Set[str] = field(default_factory=set)          # e.g. {"no-network"}
    state: str = "active"                                       # active / completed / stale
    evidences: List[Evidence] = field(default_factory=list)     # 绑定到该需求的证据集合

@dataclass
class Request:
    """
    Agent 的权限请求：能力 + 作用域（文件/命令/资源）。
    scope 在 demo 里用路径或简写命令字符串表示。
    """
    capability: Capability
    scope: str

@dataclass
class Lease:
    """
    Capability Lease：临时授权（scope + TTL + evidence 绑定），到期自动失效。
    """
    capability: Capability
    scope_patterns: List[PathPattern]
    expires_at: float
    bound_rid: str
    evidence_snapshot: List[Evidence] = field(default_factory=list)

    def is_expired(self) -> bool:
        return time.time() >= self.expires_at

@dataclass
class OrgPolicy:
    """
    组织策略：全局硬约束。
    demo 里只示范：敏感路径禁止访问。
    """
    forbidden_paths: List[PathPattern] = field(default_factory=lambda: [".env", "secrets/**", "**/*.pem"])

@dataclass
class ConstraintBound:
    """
    约束边界：能力禁区 + 路径禁区 + 组合禁区。
    demo 里做了最小实现。
    """
    forbidden_capabilities: Set[Capability] = field(default_factory=set)
    forbidden_paths: List[PathPattern] = field(default_factory=list)
    forbidden_combinations: List[Tuple[Capability, PathPattern]] = field(default_factory=list)

@dataclass
class SafeBoundary:
    """
    安全边界：允许的 (capability -> [path patterns])。
    """
    allowed: Dict[Capability, List[PathPattern]] = field(default_factory=dict)

    def allows(self, req: Request) -> bool:
        if req.capability not in self.allowed:
            return False
        # scope 可能是路径，也可能是命令；demo 按“路径匹配”处理
        patterns = self.allowed[req.capability]
        return any(match_path(req.scope, p) for p in patterns)

def match_path(path: str, pattern: str) -> bool:
    """
    支持简化版 glob：
      - "**" 表示任意层级
      - "*" 表示一层
    我们用 fnmatch 做近似：把 ** 转成 * 的多层近似匹配。
    """
    # 统一斜杠
    path = path.replace("\\", "/")
    pattern = pattern.replace("\\", "/")
    # 粗略处理 **：转成 *，以便 fnmatch 工作（demo 够用）
    pattern = pattern.replace("**", "*")
    return fnmatch.fnmatch(path, pattern)
