"""Requirement Graph（需求图）——论文级 demo 版本

把你文档 3.3 的“事件驱动更新”落到代码里：
- 用户指令：创建节点（goal/constraints/anchors）
- 运行测试：失败->更新 anchors；写入 test_fail 证据；通过->完成任务
- 代码修改：写入 diff 证据（可扩展：校验是否在 scope 内）
- 任务完成：state=completed（后续可以回收 lease）

demo 当前只维护 1 个节点，但结构上是 Graph，便于你扩展多节点 DAG。
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import time

from .models import RequirementNode, Evidence

@dataclass
class GraphEvent:
    ts: float
    etype: str
    rid: str
    payload: Dict[str, Any] = field(default_factory=dict)

@dataclass
class RequirementGraph:
    nodes: Dict[str, RequirementNode] = field(default_factory=dict)
    active_rid: Optional[str] = None
    events: List[GraphEvent] = field(default_factory=list)

    def add_node(self, node: RequirementNode) -> None:
        self.nodes[node.rid] = node
        self.active_rid = node.rid

    def active_node(self) -> RequirementNode:
        if not self.active_rid or self.active_rid not in self.nodes:
            raise RuntimeError("No active requirement node")
        return self.nodes[self.active_rid]

    def log(self, etype: str, rid: str, payload: Dict[str, Any] | None = None) -> None:
        self.events.append(GraphEvent(ts=time.time(), etype=etype, rid=rid, payload=payload or {}))

    # ---- 事件驱动更新 ----

    def on_user_instruction(self, rid: str, goal: str, constraints: set[str], anchors: dict[str, str]) -> RequirementNode:
        node = RequirementNode(rid=rid, goal=goal, anchors=dict(anchors), constraints=set(constraints), state="active")
        self.add_node(node)
        self.log("USER_INSTRUCTION", rid, {"goal": goal, "constraints": sorted(list(constraints)), "anchors": anchors})
        return node

    def on_run_tests(self, rid: str, ok: bool, stdout: str) -> None:
        node = self.nodes[rid]
        node.evidences.append(Evidence(kind=("test_pass" if ok else "test_fail"), payload={"raw": stdout}))
        payload: Dict[str, Any] = {"ok": ok, "stdout": stdout}

        if not ok:
            import re
            m = re.search(r"FAILED\s+(\S+\.py)::([A-Za-z_]\w*)", stdout)
            if m:
                test_file = m.group(1)
                test_name = m.group(2)
                node.anchors["test"] = f"{test_file}::{test_name}"
                node.anchors["path"] = test_file
                payload["anchors_update"] = dict(node.anchors)

        self.log("RUN_TESTS", rid, payload)

        if ok and node.goal == "fix_failing_test":
            node.state = "completed"
            self.log("TASK_COMPLETE", rid, {"reason": "tests passed"})

    def on_code_patch(self, rid: str, path: str, diff_summary: str) -> None:
        node = self.nodes[rid]
        node.evidences.append(Evidence(kind="diff", payload={"file": path, "summary": diff_summary}))
        self.log("CODE_PATCH", rid, {"path": path, "diff": diff_summary})

    # ---- 图快照 ----
    def snapshot(self) -> Dict[str, Any]:
        def node_view(n: RequirementNode) -> Dict[str, Any]:
            return {
                "rid": n.rid,
                "goal": n.goal,
                "state": n.state,
                "anchors": dict(n.anchors),
                "constraints": sorted(list(n.constraints)),
                "evidences": [e.kind for e in n.evidences],
            }
        return {
            "active_rid": self.active_rid,
            "nodes": {rid: node_view(n) for rid, n in self.nodes.items()},
            "events": [{"etype": e.etype, "rid": e.rid, "payload": e.payload} for e in self.events],
        }
