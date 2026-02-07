"""
审计日志：把每次授权/拒绝记录下来，便于复查/重放。

demo 写到 .audit/ 目录下的 jsonl 文件。
"""
from __future__ import annotations
import os, json, time
from typing import Any, Dict

AUDIT_DIR = ".audit"

def log_event(event: Dict[str, Any]) -> None:
    os.makedirs(AUDIT_DIR, exist_ok=True)
    path = os.path.join(AUDIT_DIR, "audit.jsonl")
    event = dict(event)
    event["ts"] = time.time()
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")
