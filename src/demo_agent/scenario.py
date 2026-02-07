from __future__ import annotations
from rich.console import Console

from src.safe_boundary.models import OrgPolicy
from src.safe_boundary.extract import extract_requirement
from src.safe_boundary.graph import RequirementGraph
from src.demo_agent.agent import DemoAgent
from src.demo_agent.llm_loop_modelscope import run_llm_agent
from src.demo_agent.llm_modelscope import make_client

console = Console()

def _print_graph(graph: RequirementGraph, title: str) -> None:
    snap = graph.snapshot()
    console.rule(f"[bold]{title}[/bold]")
    console.print(f"active_rid={snap['active_rid']}")
    for rid, n in snap["nodes"].items():
        console.print(f"- rid={rid} state={n['state']} goal={n['goal']}")
        console.print(f"  anchors={n['anchors']}")
        console.print(f"  constraints={n['constraints']}")
        console.print(f"  evidences={n['evidences']}")
    if snap["events"]:
        last = snap["events"][-1]
        console.print(f"last_event={last['etype']} payload={last['payload']}")

def run_fix_failing_test_scenario():
    # t0: 用户指令
    user_instruction = "修复失败测试，禁止联网"
    goal, anchors, constraints = extract_requirement(user_instruction)

    graph = RequirementGraph()
    r = graph.on_user_instruction(rid="r0", goal=goal, constraints=constraints, anchors=anchors)
    _print_graph(graph, "t0 USER_INSTRUCTION -> create node")

    org = OrgPolicy()

    client, _ = make_client()
    if client is None:
        console.print("[yellow]LLM not configured, use DemoAgent (deterministic)[/yellow]")
        DemoAgent(org=org, graph=graph).run_fix_failing_test(r)
    else:
        console.print("[green]Running LLM-in-the-loop agent (ModelScope)[/green]")
        final = run_llm_agent(user_instruction, r, org, graph=graph)
        console.print(final)

    _print_graph(graph, "Final Requirement Graph")
