# Spec-Driven Development Loop (SDDL) 方案 v0.3

> 版本 0.3 | 2026-08-06 | 基于 Round 2 评审（N1-N10）+ 发散 + 搜索验证修订
>
> **变更摘要（vs v0.2）**：
> - **语义评估重构：绝对分数 → Checklist 二分判定 + 3 模型多数投票**（修 N1，最关键）
> - 影响面分析：引用图 + 变更类型驱动（修 N2）
> - C4 拆为 C4a（spec↔docs）+ C4b（code↔docs）（修 N3）
> - 预算：会话/项目双预算 + 修订预算衰减（修 N4）
> - Convergence Report 分 deterministic/semantic 两节（修 N5）
> - C1-def L1 失败只触发 L2，不直接判 violation（修 N6）
> - 变异测试守卫条件（修 N7）
> - boundaries 增加 priority（修 N8）
> - 人工反馈结构化模板（修 N9）
> - 阈值参数来源与校准计划（修 N10）
>
> **新增搜索证据**：
> - TICKing All the Boxes (arXiv 2410.07061)：checklist 生成改善 LLM 评估
> - Fairness or Fluency (arXiv 2026-01)：pairwise LLM-judge 存在语言偏置
> - BiasScope (arXiv 2026-02)：LLM-as-a-Judge 偏置自动检测
> - Bias and Uncertainty in LLM-as-a-Judge (arXiv 2026-05)：judge 估计的偏置与不确定性
> - SLMEval (arXiv 2505.xxxx)：熵基校准
> - Calibration Collapse Under Sycophancy (arXiv 2026-04)：谄媚微调致校准崩溃
> - OpenSpec verify 工作流：执行反馈 + 人工确认路径

---

## 1. 核心架构（v0.3）

与 v0.2 一致（Spec Store 双区制 + 双向通道 + 分层检查器），关键变化在检查器内部（第 4 节）与收敛判定（第 4.4 节）。

```
┌──────────────────────────────────────────────────────────────┐
│                    Spec Store（单一事实来源）                   │
│  ┌────────────────────────┐    ┌──────────────────────────┐  │
│  │ specs/（当前真相）       │◄───│ changes/（增量提案）       │  │
│  └───────────┬────────────┘    └───────────┬──────────────┘  │
│              │ archive                      │                 │
└──────────────┼──────────────────────────────┼─────────────────┘
               ▼                              ▼
      ┌─────────────────────────────────────────────┐
      │          双向通道（派生↓ / 回写↑）             │
      └───────────────┬─────────────────────────────┘
                      ▼
      ┌─────────────────────────────────────────────┐
      │          分层一致性检查器（v0.3）              │
      │  硬条件: C1-def C2-def C3 C4b-def            │
      │  软条件: C1-sem C2-sem C4a（Checklist 判定）  │
      │  → 多数投票 → 证据要求 → 复核队列              │
      └───────────────┬─────────────────────────────┘
                      ▼
      ┌─────────────────────────────────────────────┐
      │  收敛判定：硬条件门禁 + 软条件 Checklist 共识  │
      │  + 变异测试 + 预算约束                        │
      └───────────────┬─────────────────────────────┘
                      ▼
            Convergence Report
      （deterministic 可重跑 + semantic 可审计）
```

---

## 2. Spec Store 与变更管理（v0.2 保留，微调）

同 v0.2（双区制、修订分级 L1/L2/L3、STALE 标记、ping-pong、CHANGELOG 审计）。

**v0.3 补充**：人工反馈结构化模板（修 N9）：

```
人工反馈模板（machine-consumable）：
  verdict: approve | reject | modify_spec
  if reject:
    reason_category: implementation_error | test_error | doc_error | spec_error | other
    reason_text: <自由文本>
    evidence_ref: <可选，文件+行号>
    required_fix: <期望的修复方向>
  if modify_spec:
    diff: <修改内容，结构化>
    change_level: L1 | L2 | L3
```

人工的 `reject_with_reason` 被结构化为 `reason_category`，可直接进路由矩阵，不依赖 LLM 解析自由文本。

---

## 3. Spec Schema（v0.2 保留 + 边界优先级，修 N8）

```yaml
boundaries:
  - condition: "数据库连接断开"
    expectation: "抛出 ServiceUnavailableError，不产生部分写入"
    priority: "must"          # ← v0.3 新增：边界也有优先级

quality_constraints:
  performance:
    - metric: "P99 latency"
      threshold: "500ms"
      scope: "authenticate"
      verification: "env"     # 环境验证，不进 loop
      priority: "should"      # ← v0.3 新增
```

---

## 4. 分层一致性检查器（v0.3）

### 4.1 检查矩阵（v0.3 更新，修 N3）

```
          Tests        Code        Docs
         ┌──────┐    ┌──────┐    ┌──────┐
 Spec    │ C1   │    │ C2   │    │ C4a  │
         ├──────┤    ├──────┤    ├──────┤
 Tests   │      │    │ C3   │    │  —   │
         ├──────┤    ├──────┤    ├──────┤
 Code    │      │    │      │    │ C4b  │
         └──────┘    └──────┘    └──────┘
```

| 检查 | 性质 | 内容 |
|------|------|------|
| C1-def | 硬 | 验收覆盖映射 + 结构反推（L1/L2） |
| C1-sem | 软 | 测试实际断言 ↔ 行为语义（Checklist） |
| C2-def | 硬 | 接口/签名/模型/错误类型静态对比 |
| C2-sem | 软 | 代码行为 ↔ 行为语义（Checklist） |
| C3 | 硬 | 测试执行 + 覆盖率 + 无跳过 |
| C4a | 软 | spec ↔ docs（Checklist） |
| C4b-def | 硬 | **code ↔ docs**（符号表对比：docs 声明的 API 在 code 中存在） |
| C4b-sem | 软 | docs 描述的行为在 code 中可实现（Checklist） |

### 4.2 C1-def（v0.3，修 N6）

```
L1 标签索引：B001 → test_auth.py          （仅作索引，失败不判 violation）
L2 结构反推：解析测试 AST 提取实际断言      （L1 失败 → 强制 L2；L2 无法确认 → violation）
L3 变异验证：must 级验收 + C3 通过后       （守卫条件，修 N7）
```

**L3 守卫条件**：变异测试只在 `C3 通过`（测试全绿）后运行。实现半成品（编译不过/测试红）时跳过 L3，变异失败不误报为"测试是假的"。

### 4.3 语义检查（v0.3 重构，修 N1）

**不再使用绝对分数。** 语义层采用 **Checklist 二分判定 + 3 模型多数投票**：

```
┌──────────────────────────────────────────────────────────────┐
│  Semantic Check (C1-sem / C2-sem / C4a / C4b-sem)            │
│                                                              │
│  Step 1: 生成 CheckList（结构化判定项）                        │
│    从 spec 行为自动派生判定项，每项是二分问题：                 │
│    - "测试 X 是否断言了 B001 的 THEN 子句 1？"（是/否/不确定）  │
│    - "代码 authenticate 是否处理 InvalidCredentialsError？"    │
│    - "docs 是否描述了 refreshToken 的行为？"                  │
│                                                              │
│  Step 2: 3 个不同模型独立对每个判定项投票（是/否/不确定）       │
│    - 3 模型：生成模型 + 2 个不同供应商的检查模型                │
│    - 每个判定项附证据要求（引用文件+行号+原文）                 │
│                                                              │
│  Step 3: 多数投票                                           │
│    一致（3:0 或 2:1）→ 采纳该判定                             │
│    分裂（1:1:1 或有"不确定"）→ 该项进复核队列                  │
│                                                              │
│  Step 4: 复核队列（第二层确认）                               │
│    复核模型（与 3 个投票模型都不同）逐项确认                    │
│    复核仍无法确认 → 标记 needs_human_review                  │
│                                                              │
│  Step 5: 判定项汇总 → 共识率                                  │
│    consensus_rate = 采纳的判定项 / 总判定项                   │
│    （这是"比例"，不是"分数"——是客观计票结果，非 LLM 自评）      │
└──────────────────────────────────────────────────────────────┘
```

**为什么这样设计（证据支撑）**：
- TICKing All the Boxes：checklist 结构化判定项 → 评估更可靠
- BiasScope / Fairness or Fluency：LLM-as-a-Judge 有偏置，但**偏置是系统性的，多数投票 + 异模型可大幅稀释**
- Calibration Collapse：绝对置信度不可靠，但**二分共识是客观计票**，不依赖模型自我校准
- Pride and Prejudice：异模型外部评估 > 自评

**判定项模板（从 behavior 派生）**：

```
对每个 behavior B：
  [B-GIVEN]  测试/代码是否构造了 B 的 GIVEN 前置条件？
  [B-WHEN]   测试/代码是否调用了 B 声明的接口？
  [B-THEN-1] 测试/代码是否断言/实现了 THEN 子句 1？
  [B-THEN-2] ...
  [B-ERR]    测试/代码是否覆盖了 B 关联的错误类型？
  [B-SIDE]   测试/代码是否验证了 B 的副作用约束？（如"不修改持久状态"）
```

### 4.4 收敛判定（v0.3）

```python
def judge(spec, tests, code, docs) -> Verdict:
    hard = {
        "c1_def": check_c1_def(spec, tests),        # 覆盖映射 + 结构反推
        "c2_def": check_c2_def(spec, code),          # 接口/签名/模型/错误
        "c3":     check_c3(tests, code),             # 测试执行 + 覆盖 + 无跳过
        "c4b_def": check_c4b_def(code, docs),        # docs 声明的 API 在 code 中存在
    }

    if not all(h.passed for h in hard.values()):
        return NotConverged(...)

    # 软条件：Checklist 共识率
    c1_sem = run_checklist(spec, tests, mode="c1_sem")    # → consensus_rate
    c2_sem = run_checklist(spec, code, mode="c2_sem")
    c4a    = run_checklist(spec, docs, mode="c4a")
    c4b_sem = run_checklist(code, docs, mode="c4b_sem")

    consensus = {
        "c1_sem": c1_sem.rate,     # 0-1 客观计票
        "c2_sem": c2_sem.rate,
        "c4a":    c4a.rate,
        "c4b_sem": c4b_sem.rate,
    }
    must_covered = coverage_of(spec.behaviors, priority="must")

    converged = (
        consensus["c1_sem"] >= 0.95 and
        consensus["c2_sem"] >= 0.95 and
        consensus["c4a"]    >= 0.90 and
        consensus["c4b_sem"] >= 0.90 and
        must_covered == 1.0 and
        no_blocker_violations()
    )

    return Verdict(
        converged=converged,
        report=ConvergenceReport(
            hard_evidence=hard,                    # 可重跑
            consensus_rates=consensus,             # 客观计票
            voting_records=voting_records,         # 3 模型投票原始记录
            risk_list=...,                          # 观察项
            env_verification=...,                   # L5 未验证项
        )
    )
```

**阈值来源（修 N10）**：
- 0.95/0.90 是**初值**，非终值。Phase 2 用 golden set（已知正确/错误样本 ≥10 对）校准：
  - 记录每个阈值下的假阳性率/假阴性率（checker 对 golden set 的判定）
  - 调阈值使 golden set 上无假阳性（宁可漏报不可误报）
  - 校准结果写入 checker 配置，每个阈值带校准记录
- ping-pong N=3、max_rounds=8 同理：初值 + 运行数据回填校准

### 4.5 对抗式检查（v0.2 保留）

同 v0.2（对抗式 A + 确认式复核 B + 证据要求 + 确定性锚点 + 假阳性反馈回路）。

---

## 5. 路由与回写（v0.2 保留 + 影响面分析，修 N2）

### 5.1 路由（v0.2 保留）

三层混合判定 + spec 修订需人工审批。

### 5.2 影响面分析（v0.3 新增，修 N2）

**变更类型驱动的静态引用分析**：

```python
def impact_analysis(spec_diff) -> ImpactSet:
    impacted = set()
    for element in spec_diff.changed_elements:
        kind = element.kind   # interface | model | behavior | boundary
        if kind == "interface":
            # 接口签名变更 → 所有调用方 + 该接口的测试 + 文档引用
            impacted |= refs_in_code(element.name)      # 符号表/引用图
            impacted |= refs_in_tests(element.name)     # 测试引用
            impacted |= refs_in_docs(element.name)      # 文档引用
        elif kind == "model":
            # 数据模型变更 → 所有读写该模型的代码 + 测试 fixture + 文档
            impacted |= readers_writers(element.name)   # 静态数据流
            impacted |= fixtures_using(element.name)    # 测试 fixture
            impacted |= refs_in_docs(element.name)
        elif kind == "behavior":
            # 行为描述变更 → 只波及该行为的测试
            impacted |= tests_tagged(element.id)        # 标签追踪（辅助）
            impacted |= refs_in_docs(element.id)
        elif kind == "boundary":
            impacted |= tests_tagged(element.id)
    return impacted
```

**规则**：
- 接口/模型变更 → 引用图驱动的**精确局部重派**
- 行为变更 → 标签追踪（该行为的测试）
- 引用图分析不到的地方 → 保守标记 STALE（宁多勿漏）
- L3 破坏性修订 → 全量重派（不依赖影响面分析）

---

## 6. 成本模型（v0.3，修 N4）

### 6.1 双预算制

```
budget:
  # 会话预算：单次 loop 会话
  session:
    max_token_per_round: 500K
    max_rounds: 8
  # 项目预算：整个项目的累计
  project:
    total_token: 20M
    max_sessions: 5            # 含修订触发的会话
    revision_penalty:          # 修订预算衰减（修 N4）
      L2: 0.20                 # 每次 L2 修订消耗项目预算 20%
      L3: 0.50                 # 每次 L3 修订消耗项目预算 50%
```

**核算规则**：
- 每个 loop 会话有独立 session 预算
- L2/L3 修订触发**新会话**（新 session 预算），但**项目预算按衰减比例扣减**
- 项目预算或 session 数耗尽 → 停止自动修订，转人工驱动
- L1 澄清性修订不触发新会话，不扣项目预算

**例**：项目预算 20M，一次 L3 修订扣 50% → 剩余 10M。若再来一次 L3 → 剩余 0 → 自动修订停止，转人工。

### 6.2 止损与降级（v0.2 保留）

D1-D5 降级路径 + Degradation Report。

---

## 7. Checker 可信度保障（v0.2 保留 + 校准，修 N10）

v0.2 的 meta-testing + golden set + 置信度标注保留。

**v0.3 补充**：语义检查器也用 golden set 校准（见 4.4 阈值来源）。每个判定项模板在 golden set 上验证其判别力，判别力低于阈值的判定项模板重新设计。

---

## 8. 机器可读 Violation（v0.2 保留）

格式同 v0.2，补充 `evidence` 必填字段（无证据自动降级为观察项）。

---

## 9. 组件分解（v0.2 保留）

同 v0.2（跨组件契约测试 + 集成测试分层）。

---

## 10. 人工审查回流（v0.2 保留 + 结构化，修 N9）

v0.2 回流机制保留。人工反馈采用结构化模板（第 2 节），`reason_category` 直接进路由矩阵。

---

## 11. 完整 Spec 示例（v0.2 保留 + 边界优先级）

同 v0.2 附录 B，boundaries/quality_constraints 增加 priority 字段。

---

## 12. 适用门槛（v0.2 保留）

同 v0.2。

---

## 13. 实施路线（v0.3 更新）

```
Phase 0: Spec Store 搭建（同 v0.2）
Phase 1: 确定性检查器（同 v0.2 + C4b-def 符号表对比）
Phase 2: 语义检查器 + 基础 Loop
  ├── Checklist 判定项生成器（从 behavior 派生）
  ├── 3 模型多数投票器
  ├── 复核队列
  ├── golden set 校准（阈值来源）
  ├── 基础 loop（派生→验证→判定，不含回写）
  └── Convergence Report（deterministic/semantic 两节）
Phase 3: 回写通道 + 路由 + 成本控制
  ├── 影响面分析（引用图 + 变更类型驱动）
  ├── 双预算制 + 修订衰减
  └── 人工审查回流（结构化模板）
Phase 4: 变异测试 + 集成（同 v0.2 + L3 守卫条件）
```

---

## 14. 待解决问题（v0.3 更新）

| # | 问题 | v0.3 状态 | 下一步 |
|---|------|----------|--------|
| O1 | 语义检查稳定性 | Checklist 二分 + 多数投票 + 复核 | golden set 校准实验 |
| O2 | 回写冲突 | 双区制 + 修订分级 + 人工审批 | 多变更并行测试 |
| O3 | 跨组件行为形式化 | 契约测试 + 分层 | 待实践验证 |
| O4 | L5 质量约束 | 移出 loop + env 标记 | 约束→测试模式库 |
| O5 | Ouroboros 适配 | 概念映射已定义 | Phase 4 |
| O6 | 成本基线 | 双预算制已定义 | 收集真实数据 |
| O7 | spec gap 检测 | 路由层已定义 | runtime 监控实验 |
| O8 | 变异测试成本 | must_only + 守卫条件 | 评估实际开销 |
| O9 | 多变更并行冲突 | changes/ 支持 | 需测试 |
| O10 | Checklist 判定项模板判别力 | 初版已定义 | golden set 验证 |

---

## 附录 A：搜索证据（v0.3 增补）

| 来源 | 支撑点 |
|------|--------|
| TICKing All the Boxes (arXiv 2410.07061, 2024) | checklist 生成改善 LLM 评估与生成 → Checklist 判定项 |
| Fairness or Fluency (arXiv 2026-01) | pairwise LLM-judge 语言偏置 → 异模型投票必要性 |
| BiasScope (arXiv 2026-02) | LLM-as-a-Judge 偏置检测 → 偏置是系统性、可检测 |
| Bias and Uncertainty in LLM-as-a-Judge (arXiv 2026-05) | judge 估计偏置与不确定性 → 不用绝对分数 |
| SLMEval (arXiv 2505.xxxx, 2025) | 熵基校准 → golden set 校准方法参考 |
| Calibration Collapse Under Sycophancy (arXiv 2026-04) | 谄媚微调致校准崩溃 → 绝对分数不可信 |
| OpenSpec verify workflow | 执行反馈 + 人工确认 → 硬条件优先 |

其余同 v0.2 附录 A。

---

> v0.3 核心改进一句话：**语义层从"LLM 自评分数"换成"客观计票"**——
> Checklist 二分判定 + 3 模型多数投票 + 复核队列，共识率是计票结果而非模型评分。
> 同时补齐影响面分析、双预算、C4b 双向检查、变异守卫等定义缺口。
