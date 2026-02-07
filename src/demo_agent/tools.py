"""
工具模拟层（demo）

真实系统里，这里会对接：
- 文件读写
- 命令执行（pytest, build）
- diff 生成
- 网络请求
demo 为了可运行，用 repo_sim 目录做“伪仓库”。
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Tuple
import os

REPO_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "repo_sim")
REPO_ROOT = os.path.abspath(REPO_ROOT)

@dataclass
class ToolResult:
    ok: bool
    stdout: str = ""
    stderr: str = ""

def run_tests() -> ToolResult:
    """
    模拟 pytest：
      - 如果 login() 仍返回 False，则 test_login 失败
      - 否则通过
    """
    login_path = os.path.join(REPO_ROOT, "src", "auth", "login.py")
    code = open(login_path, "r", encoding="utf-8").read()
    if "return True" in code:
        return ToolResult(ok=True, stdout="PASSED tests/test_auth.py::test_login")
    return ToolResult(ok=False, stdout="FAILED tests/test_auth.py::test_login")

def apply_patch(rel_path: str, new_content: str) -> ToolResult:
    """
    写文件（模拟）
    """
    abs_path = os.path.join(REPO_ROOT, rel_path.replace("/", os.sep))
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    with open(abs_path, "w", encoding="utf-8") as f:
        f.write(new_content)
    return ToolResult(ok=True, stdout=f"wrote {rel_path}")

def network_install(pkg: str) -> ToolResult:
    """
    模拟联网安装（永远提示“将要联网”）
    """
    return ToolResult(ok=True, stdout=f"would download and install {pkg} (network)")
