"""DemoAgent

- 仍然是“手写策略” Agent（便于复现）
- 但每一步都会通过 RequirementGraph 记录事件并更新节点（对齐文档 3.3）
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List
from rich.console import Console

from src.safe_boundary.models import OrgPolicy, Request, RequirementNode, Lease
from src.safe_boundary.authorize import authorize
from src.safe_boundary.audit import log_event
from src.safe_boundary.graph import RequirementGraph
from . import tools

console = Console()

@dataclass
class DemoAgent:
    org: OrgPolicy
    graph: RequirementGraph
    leases: List[Lease] = field(default_factory=list)

    def _prune_leases(self) -> None:
        self.leases = [l for l in self.leases if not l.is_expired()]

    def step_request(self, req: Request, r: RequirementNode, ttl: int = 300) -> bool:
        self._prune_leases()
        decision = authorize(req, r, self.org, ttl_seconds=ttl)

        if decision.ok:
            lease = decision.lease
            assert lease is not None
            self.leases.append(lease)
            console.print(f"[green]GRANT[/green] {req.capability} scope={req.scope}")
            log_event({"type": "GRANT", "rid": r.rid, "capability": req.capability, "scope": req.scope})
            return True

        console.print(f"[red]DENY[/red] {req.capability} scope={req.scope}")
        console.print(f"  reason: {decision.reason}")
        if decision.suggestion:
            for s in decision.suggestion:
                console.print(f"  suggestion: {s}")
        log_event({"type": "DENY", "rid": r.rid, "capability": req.capability, "scope": req.scope,
                   "reason": decision.reason, "suggestion": decision.suggestion})
        return False

    def run_fix_failing_test(self, r: RequirementNode) -> None:
        console.rule("[bold]Scenario: fix failing test (graph updates)[/bold]")

        # t1: 运行测试（证据产生 + anchors 更新）
        if self.step_request(Request("exec:test", "repo_sim/tests/**"), r, ttl=120):
            tr = tools.run_tests()
            console.print(f"[cyan]tool[/cyan] run_tests -> ok={tr.ok}")
            self.graph.on_run_tests(r.rid, ok=tr.ok, stdout=tr.stdout)

        if r.state == "completed":
            return

        # t2: 代码修改（写入 diff 证据）
        patch_path = "src/auth/login.py"
        if self.step_request(Request("write:src", f"repo_sim/{patch_path}"), r, ttl=300):
            new_content = """def login(user: str, password: str) -> bool:
    # 修复：返回 True 以通过测试（demo 简化）
    return True
"""
            wr = tools.apply_patch(patch_path, new_content)
            console.print(f"[cyan]tool[/cyan] apply_patch -> ok={wr.ok}")
            self.graph.on_code_patch(r.rid, path=patch_path, diff_summary="return False -> True")

        # t3: 故意请求联网（应被 no-network 拒绝）
        self.step_request(Request("network:egress", "pip install somepkg"), r, ttl=60)

        # t4: 重跑测试（通过 -> TASK_COMPLETE）
        if self.step_request(Request("exec:test", "repo_sim/tests/**"), r, ttl=120):
            tr2 = tools.run_tests()
            console.print(f"[cyan]tool[/cyan] run_tests -> ok={tr2.ok}")
            self.graph.on_run_tests(r.rid, ok=tr2.ok, stdout=tr2.stdout)

        if r.state == "completed":
            console.print("[green]Requirement completed (state=completed).[/green]")
