"""
anchors -> ScopeBound（作用域边界）
按 ExpandAnchors(anchors, depth_limit=2) 思路实现：

Algorithm: ExpandAnchors(anchors, depth_limit=2)

1. scope = anchors (初始锚点集合，主要是“路径锚点”)
2. for i in range(depth_limit):
3.   for each path in scope:
4.       deps = GetDependencies(path)
5.       rev_deps = GetReverseDeps(path)
6.       scope = scope ∪ deps ∪ rev_deps
7.   scope = scope - SensitivePaths
8. return scope

demo 里我们对 Python 项目做一个可运行版本：
- GetDependencies: 解析该文件的 import，找 repo_sim/src 下对应模块文件
- GetReverseDeps: 反向依赖（哪些文件 import 了它）
- 对 scope 输出：以 “repo_sim/...” 的路径/模式列表表示
"""
from __future__ import annotations
from typing import Dict, List, Set, Tuple
import os
import ast

from .models import OrgPolicy, match_path

_REPO_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "repo_sim")
)

def _repo_rel(abs_path: str) -> str:
    p = os.path.abspath(abs_path).replace("\\", "/")
    root = _REPO_ROOT.replace("\\", "/").rstrip("/")
    if p.startswith(root + "/"):
        return "repo_sim/" + p[len(root) + 1:]
    return p

def _abs_from_repo_rel(repo_rel: str) -> str:
    repo_rel = repo_rel.replace("\\", "/")
    if repo_rel.startswith("repo_sim/"):
        repo_rel = repo_rel[len("repo_sim/"):]
    return os.path.join(_REPO_ROOT, repo_rel.replace("/", os.sep))

def _strip_test_selector(s: str) -> str:
    # "tests/test_auth.py::test_login" -> "tests/test_auth.py"
    return s.split("::", 1)[0]

def _is_file_path(repo_rel: str) -> bool:
    abs_p = _abs_from_repo_rel(repo_rel)
    return os.path.isfile(abs_p)

def _list_py_files() -> List[str]:
    out = []
    for dirpath, _, filenames in os.walk(_REPO_ROOT):
        for fn in filenames:
            if fn.endswith(".py"):
                out.append(_repo_rel(os.path.join(dirpath, fn)))
    return out

def _module_to_file(module: str) -> str | None:
    """
    把 import 的 module 名映射到 repo_sim/src 下的 .py 文件
      e.g. "src.auth.login" -> repo_sim/src/auth/login.py
           "src.utils.crypto" -> repo_sim/src/utils/crypto.py
    """
    module = module.replace("\\", ".").strip(".")
    if not module.startswith("src."):
        return None
    parts = module.split(".")
    rel = "/".join(parts) + ".py"         # src/auth/login.py
    cand = "repo_sim/" + rel
    if _is_file_path(cand):
        return cand
    # 也可能是包：src/auth/__init__.py
    rel2 = "/".join(parts) + "/__init__.py"
    cand2 = "repo_sim/" + rel2
    if _is_file_path(cand2):
        return cand2
    return None

def _imports_in_file(repo_rel: str) -> Set[str]:
    abs_p = _abs_from_repo_rel(repo_rel)
    try:
        src = open(abs_p, "r", encoding="utf-8").read()
    except FileNotFoundError:
        return set()
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return set()

    mods: Set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                mods.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                mods.add(node.module)
    return mods

def _build_dep_graph() -> Tuple[dict[str, Set[str]], dict[str, Set[str]]]:
    """
    返回：(deps, rev_deps)
    deps[a] = {b1,b2} 表示 a 依赖 b
    rev_deps[b] = {a1,a2} 表示 哪些文件依赖 b
    """
    deps: dict[str, Set[str]] = {}
    rev: dict[str, Set[str]] = {}

    for f in _list_py_files():
        deps.setdefault(f, set())
        for m in _imports_in_file(f):
            tgt = _module_to_file(m)
            if tgt:
                deps[f].add(tgt)
                rev.setdefault(tgt, set()).add(f)
        rev.setdefault(f, set())
    return deps, rev

# 缓存图（demo 足够；真实系统要做增量更新）
_DEPS, _REV = _build_dep_graph()

def get_dependencies(repo_rel: str) -> Set[str]:
    return set(_DEPS.get(repo_rel, set()))

def get_reverse_deps(repo_rel: str) -> Set[str]:
    return set(_REV.get(repo_rel, set()))

def _remove_sensitive(scope: Set[str], org: OrgPolicy) -> Set[str]:
    """
    从 scope 中排除敏感路径（org.forbidden_paths）
    """
    cleaned: Set[str] = set()
    for p in scope:
        blocked = any(match_path(p, pat) for pat in org.forbidden_paths)
        if not blocked:
            cleaned.add(p)
    return cleaned

def _add_dir_wildcards(scope: Set[str]) -> Set[str]:
    """
    按示例：如果包含 src/auth/login.py，则加入 src/auth/** 这种目录范围
    注意：demo 的 SafeBoundary 用 repo_sim/ 前缀
    """
    extra: Set[str] = set()
    for p in scope:
        if p.startswith("repo_sim/src/") and p.endswith(".py"):
            dirp = p.rsplit("/", 1)[0]
            extra.add(dirp + "/**")
        if p.startswith("repo_sim/tests/") and p.endswith(".py"):
            # 测试文件一般允许 tests/**（方便跑相关测试）
            extra.add("repo_sim/tests/**")
    return scope | extra

def expand_scope(anchors: Dict[str, str], org: OrgPolicy, depth_limit: int = 2) -> List[str]:
    """
    anchors: 可能包含
      - path: "tests/test_auth.py" 或 "src/auth/login.py" 等（无 repo_sim 前缀）
      - test: "tests/test_auth.py::test_login"
    返回：ScopeBound（repo_sim/ 前缀的路径/模式列表）
    """
    # 1) 初始 scope = anchors
    scope: Set[str] = set()

    # 允许 anchors 为空：此时只允许 repo 根读/跑测试（写权限仍需更具体 anchors 才会 EvidenceSupported）
    if not anchors:
        scope = {"repo_sim/**"}
        scope = _remove_sensitive(scope, org)
        return sorted(scope)

    # 优先使用 path 锚点
    if "path" in anchors:
        p = anchors["path"].replace("\\", "/")
        p = _strip_test_selector(p)
        if not p.startswith("repo_sim/"):
            p = "repo_sim/" + p.lstrip("/")
        scope.add(p)

    # 如果有 test 锚点，也加入其文件路径
    if "test" in anchors:
        t = anchors["test"].replace("\\", "/")
        tfile = _strip_test_selector(t)
        if not tfile.startswith("repo_sim/"):
            tfile = "repo_sim/" + tfile.lstrip("/")
        scope.add(tfile)

    # 去敏感
    scope = _remove_sensitive(scope, org)

    # 2) 迭代扩展
    for _depth in range(depth_limit):
        new_nodes: Set[str] = set()
        for p in list(scope):
            # 只对“具体文件”做依赖扩展；对 ** 模式不扩展
            if p.endswith("/**") or p.endswith("*"):
                continue
            if not _is_file_path(p):
                continue
            new_nodes |= get_dependencies(p)
            new_nodes |= get_reverse_deps(p)

        before = set(scope)
        scope |= new_nodes
        scope = _remove_sensitive(scope, org)
        # 若无新增则提前停止
        if scope == before:
            break

    # 3) 加入目录通配（如 src/auth/**），符合你示例的输出风格
    scope = _add_dir_wildcards(scope)

    # 4) 最终返回
    return sorted(scope)
