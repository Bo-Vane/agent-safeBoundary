# SafeBoundary Demo（可运行最小原型）

## 1. 基本说明
- Requirement Graph（需求图）
- SafeBoundary 推断：CapabilityBound ∩ ScopeBound ∩ ¬ConstraintBound
- Evidence-Grounded Capability Lease（带 scope + TTL + 证据绑定的租约）
- Drift Gate（越界诊断：能力越界 / 作用域越界 / 约束冲突）


## 2. 运行

你会看到类似输出：

- t0：用户指令创建需求节点（goal=fix failing test, constraints=no-network）
- t1：Agent 请求 `exec:test` → 在边界内 → 自动授权（lease）
- t1：工具返回测试失败证据 → anchors 更新 → SafeBoundary 扩展
- t2：Agent 请求写入 `repo_sim/src/auth/login.py` → 有证据支持 → 授权
- t3：Agent 请求联网装依赖 → 触发 no-network 约束 → 拒绝 + 诊断
- t4：重跑测试通过 → 需求完成 → 回收 lease

---

## 3. src 目录结构说明

```
src/
  safe_boundary/                 # 框架核心实现（偏“系统/安全层”）
    models.py                    # 数据结构：RequirementNode, Evidence, Lease, Request, Boundary
    templates.py                 # T_max / T_min 模板（按 goal 类型）
    scope_expand.py              # anchors -> ScopeBound 的扩展规则（依赖/反依赖深度限制等）
    policy.py                    # 组织策略 OrgPolicy + constraint 规则
    boundary.py                  # ComputeSafeBoundary 核心算法
    evidence.py                  # EvidenceSupported 判定（可替换为更复杂实现）
    authorize.py                 # Authorize + DiagnoseViolation（Drift Gate 输出）
    audit.py                     # 审计日志（写到 .audit/）
  demo_agent/                    # 实验 Agent（偏“行为层/任务层”）
    agent.py                     # 模拟Agent：提出权限请求、调用工具、按诊断调整策略
    tools.py                     # 工具模拟：run_tests / apply_patch / (mock) network
    scenario.py                  # 场景脚本：修复失败测试（模拟 repo）
```

---

## 4. 扩展成真实项目

- 把 `demo_agent/tools.py` 换成真实工具调用（文件系统、CI、命令执行、Git diff）
- 把 `scope_expand.py` 的依赖分析换成真实解析（import graph / build graph）
- 把 `templates.py` 的 T_max 从静态表换成derivation 流水线
- 把 `audit.py` 对接日志/追踪系统



---

## 5. “算法闭环”说明：输入/输出/轮转/需求图更新

### 5.1 算法输入与输出

**输入（Input）**：
- `user_instruction`：用户自然语言指令
- `tool_results`：工具输出（测试 stdout、diff 摘要）作为外部证据
- `org_policy`：组织策略（敏感路径、禁用能力等）

**输出（Output）**：
- 更新后的 `RequirementGraph`（节点 state / anchors / constraints / evidences + 事件时间线）
- 每一步基于 active node 计算得到的 `SafeBoundary(r_active)`（用于授权）

### 5.2 执行轮转（Control Loop）

每一步循环都遵循同一条链路：

1) `extract_requirement(user_instruction)` 抽取 goal/anchors/constraints
2) `graph.on_user_instruction(...)` 创建需求节点（成为 active）
3) `compute_safe_boundary(r_active)` 计算边界
4) Agent 提议动作 -> `Request(capability, scope)`
5) `authorize(req, r_active, org_policy)`
   - GRANT：执行工具，得到 tool_result
   - DENY：返回 Drift Gate 诊断（原因+建议）
6) `graph.on_run_tests / on_code_patch ...` 用事件更新需求图
7) 若 `state=completed`：终止（可回收 lease）

### 5.3 需求图更新

| 事件 | 更新 |
|---|---|
| 用户指令 | 创建需求节点，提取 goal 与 constraints（anchors 可能为空） |
| 运行测试 | 失败：更新 anchors（失败测试名、涉及文件）；写入 test_fail 证据 |
| 代码修改 | 写入 diff 证据（可扩展：校验 diff 是否在 ScopeBound 内） |
| 任务完成 | state=completed（后续 SafeBoundary 自动失效 / 回收 lease） |

### 5.4 终端观察“需求图更新轨迹”

每个时间步（t0/t1/t2/...）打印：
- 当前 active node 的 goal/anchors/constraints/state
- 最近事件类型与 payload（USER_INSTRUCTION / RUN_TESTS / CODE_PATCH / TASK_COMPLETE）

