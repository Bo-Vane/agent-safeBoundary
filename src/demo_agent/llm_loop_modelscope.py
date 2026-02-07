from __future__ import annotations
import json
from src.demo_agent.llm_modelscope import chat_once
from src.safe_boundary.models import Request, RequirementNode, OrgPolicy
from src.safe_boundary.authorize import authorize
from src.safe_boundary.graph import RequirementGraph
from src.demo_agent import tools as local_tools

def toolcall_to_request(name, args):
    if name == "run_tests":
        return Request("exec:test", "repo_sim/tests/**")
    if name == "apply_patch":
        return Request("write:src", f"repo_sim/{args['path']}")
    if name == "network_install":
        return Request("network:egress", f"pip install {args['package']}")
    return Request("unknown", name)

def execute_tool(name, args):
    if name == "run_tests":
        return local_tools.run_tests()
    if name == "apply_patch":
        return local_tools.apply_patch(args["path"], args["content"])
    if name == "network_install":
        return local_tools.network_install(args["package"])
    raise ValueError(name)

def run_llm_agent(user_instruction: str, r: RequirementNode, org: OrgPolicy, graph: RequirementGraph, max_steps=20):
    messages = [
        {"role": "system", "content": "You are a coding agent. Use tools and respect denials."},
        {"role": "user", "content": user_instruction},
        {"role": "user", "content": f"Requirement: goal={r.goal}, anchors={r.anchors}, constraints={list(r.constraints)}"},
    ]
    for _ in range(max_steps):
        resp = chat_once(messages)
        msg = resp.choices[0].message
        if not msg.tool_calls:
            return msg.content or ""

        for tc in msg.tool_calls:
            args = json.loads(tc.function.arguments or "{}")
            req = toolcall_to_request(tc.function.name, args)
            decision = authorize(req, r, org, ttl_seconds=300)

            if not decision.ok:
                out = f"DENIED: {decision.reason}\nSUGGEST: {decision.suggestion}"
            else:
                tr = execute_tool(tc.function.name, args)
                if tc.function.name == "run_tests":
                    graph.on_run_tests(r.rid, ok=tr.ok, stdout=tr.stdout)
                elif tc.function.name == "apply_patch":
                    graph.on_code_patch(r.rid, path=args.get("path",""), diff_summary="llm patch")
                out = f"OK={tr.ok}\nSTDOUT={tr.stdout}"

            messages.append({"role": "tool", "tool_call_id": tc.id, "content": out})

        messages.append({"role": "user", "content": f"Updated anchors={r.anchors}, state={r.state}, evidences={[e.kind for e in r.evidences]}"})
        if r.state == "completed":
            return "Completed"

    return "Stopped"
