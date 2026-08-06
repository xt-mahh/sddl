# Spec-Driven Development Loop（SDDL）最终方案

> **版本**：1.0（最终版）| 2026-08-06
> **性质**：自包含独立文档，不依赖任何外部方案文件
> **演进**：历经 3 轮评审循环（35 个问题）+ 2 轮文献验证后定稿

---

## 1. 背景与目标

### 1.1 问题定义

AI 编程时代的三个核心痛点：

| 痛点 | 本质 | 后果 |
|------|------|------|
| 上下文漂移 | 对话越长，AI 越易遗忘早期约定 | 第 N 轮推翻第 3 轮的接口约定 |
| 多 artifact 不同步 | 代码改了，测试/文档没跟上 | "文档谎言"在 AI 时代被放大 |
| 验收主观化 | "感觉对了"代替"符合规格" | 无法审计、无法复现、无法交接 |

### 1.2 目标

构建一个以**结构化 Spec 为单一事实来源**、通过 **Loop** 驱动测试/代码/文档三件套同步、以**分层一致性检查**控制收敛的闭环系统。

### 1.3 与 TDD/BDD 的关系

| 方法 | 先写什么 | 驱动什么 |
|------|---------|---------|
| TDD | 测试用例 | 实现代码 |
| BDD | 行为场景 | 测试 + 代码 |
| **SDDL** | 完整规格（接口+模型+行为+边界+质量） | 测试 + 代码 + 文档 |

BDD 是 SDDL 的子集（行为层），TDD 是 SDDL 的验证手段之一（测试执行）。

### 1.4 核心原则

1. **Spec 是神谕，但可被质疑**：spec→artifacts 单向派生不够，实现中发现的 spec 缺陷必须能回写修订（双向通道）。
2. **确定性优先**：能用静态分析/schema 验证/测试执行解决的，绝不用 LLM。LLM 只填语义缺口。
3. **收敛是工程系统，不是布尔命题**：硬条件门禁 + 软条件计票 + 预算约束 + 人工兜底。
4. **检查者必须被检查**：checker 的错误是 silent 的，必须 meta-testing + golden set 校准。
5. **不惩罚诚实**：发现 spec 缺陷是质量贡献，不是 loop 的失败，激励设计不得扭曲这一行为。

---

## 2. 核心架构总览

```
┌────────────────────────────────────────────────────────────────────┐
│                    Spec Store（单一事实来源）                        │
│  ┌──────────────────────────────┐  ┌─────────────────────────────┐ │
│  │ specs/（当前真相，已批准）      │◄─│ changes/（增量提案，未批准）  │ │
│  │  每个领域一个 spec.md          │  │  每个变更一个目录             │ │
│  │  含 requirements + scenarios  │  │  proposal + specs 增量      │ │
│  └──────────────┬───────────────┘  └──────────────┬──────────────┘ │
│                 │ archive（归档合并）               │                │
└─────────────────┼──────────────────────────────────┼────────────────┘
                  │                                  │
         ┌────────▼──────────┐            ┌─────────▼─────────┐
         │  派生通道 (下行)    │            │  回写通道 (上行)    │
         │  spec → artifacts  │            │  impl → spec 修订  │
         └────────┬──────────┘            └─────────▲─────────┘
                  │                                 │
      ┌───────────┼───────────────┐                 │
      ▼           ▼               ▼                 │
┌─────────┐ ┌─────────┐    ┌─────────┐              │
│  Tests  │ │  Code   │    │  Docs   │              │
└────┬────┘ └────┬────┘    └────┬────┘              │
     │           │              │                   │
     ▼           ▼              ▼                   │
┌──────────────────────────────────────────────┐    │
│      分层一致性检查器（Layered Checker）        │    │
│  硬条件: C1-def C2-def C3 C4b-def             │    │
│  软条件: C1-sem C2-sem C4a C4b-sem（Checklist）│    │
└──────────────────┬───────────────────────────┘    │
                   │                                 │
                   ▼                                 │
        ┌──────────────────────┐                     │
        │  收敛判定（门禁+共识率）│─────────────────────┘
        └────┬─────────────┬───┘
             │             │
        Converged      NotConverged
             │         (violations → 路由 → 派生/回写)
             ▼
        Convergence Report（可审计证据链）
```

---

## 3. Spec Store 与变更管理

### 3.1 双区制

```
specs/                          # 当前真相（已批准）
├── auth/spec.md
├── payments/spec.md
└── ui/spec.md

changes/                        # 增量提案（未批准，可并行）
├── add-dark-mode/
│   ├── proposal.md             # 意图 + 范围 + 理由
│   ├── specs/auth/spec.md      # 增量 delta（ADDED/MODIFIED/REMOVED）
│   ├── design.md               # 技术方案（大变更才有）
│   └── tasks.md                # 实施清单
└── fix-rate-limit/
    └── ...
```

**变更生命周期**：`propose → review → apply → verify → archive`。归档时增量 delta 合并入 specs/，变更目录移入归档区。

### 3.2 修订分级

| 级别 | 定义 | 触发重派生 | 需人工审批 |
|------|------|-----------|-----------|
| L1 澄清性 | 不改契约，只补语义（措辞、边界细化） | 否（只更新 docs/注释） | 否 |
| L2 增量 | 改契约但兼容（加可选参数、加错误类型、加行为） | 是（受影响 artifacts 局部重派） | 是（提案制） |
| L3 破坏性 | 改契约且不兼容（删接口、改签名、改数据模型） | 是（全量重派） | **必须** |

### 3.3 STALE 失效管理

L2/L3 修订归档时自动执行：
1. 影响面分析（见 §7.2）确定受影响 artifacts
2. 标记受影响 artifacts 为 `STALE`（过期，禁止交付）
3. 触发重新派生（局部或全量）
4. 新 artifacts 验证通过后才解除 STALE

### 3.4 ping-pong 检测

同一领域连续 N=3 轮内发生 ≥3 次往返修订（spec→impl→spec）→ 冻结该领域，标记 `needs_human_review`，不再自动往返。

### 3.5 审计追踪

每次修订生成 `CHANGELOG.md`：改了什么（diff）、为什么改（触发 violation 原文）、谁改的、影响面。**回写通道永不静默**——任何 spec 修订都是可见的变更提案。

---

## 4. Spec Schema

### 4.1 分层定义

| 层 | 内容 | 机器可消费性 | 检查方法 |
|----|------|------------|---------|
| L1 接口契约 | 函数签名、参数、返回、错误类型 | 完全 | 静态类型检查 / AST 对比 |
| L2 数据模型 | JSON Schema / 类型定义 | 完全 | Schema 验证器 |
| L3 行为描述 | GWT 场景 + 优先级 | 半（结构可解析） | 测试生成 + Checklist 语义检查 |
| L4 边界条件 | 显式枚举的极端情况 + 优先级 | 半 | 专项测试 + Checklist |
| L5 质量约束 | 性能/安全/可观测性 | 弱 | 翻译为可执行规则；性能类标注 env |

### 4.2 字段结构

```yaml
meta:
  id: "auth-service"
  version: "0.1.0"
  domain: "auth"
  status: "draft | reviewing | locked | evolved"
  dependencies: ["user-model@>=1.0"]

non_goals:            # 非目标：防 scope creep，checker 可检测越界
  - "本服务不负责用户注册"

interfaces:           # L1
  - name: "authenticate"
    signature: { params: [...], returns: {...} }
    errors: ["InvalidCredentialsError", ...]

data_models:          # L2
  - name: "Credentials"
    schema: { type: "object", properties: {...}, required: [...] }

behaviors:            # L3
  - id: "B001"
    interface: "authenticate"
    priority: "must"          # must | should | could | wont
    scenario: "valid credentials"
    given: "..."
    when: "..."
    then: ["...", "..."]
    acceptance: true

boundaries:           # L4
  - condition: "数据库连接断开"
    expectation: "抛出 ServiceUnavailableError"
    priority: "must"

quality_constraints:  # L5
  performance:
    - metric: "P99 latency", threshold: "500ms",
      scope: "authenticate", verification: "env", priority: "should"
```

### 4.3 优先级与收敛的关系

- `must`：硬性，未覆盖阻塞收敛
- `should`：软性，未覆盖不阻塞，进风险清单
- `could`：不阻塞，仅记录
- `wont`：显式排除（等价 non_goals）

---

## 5. 分层一致性检查器

### 5.1 检查矩阵

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
| C1-def | 硬 | 验收覆盖映射 + 结构反推 |
| C1-sem | 软 | 测试实际断言 ↔ 行为语义（Checklist） |
| C2-def | 硬 | 接口/签名/模型/错误类型静态对比 |
| C2-sem | 软 | 代码行为 ↔ 行为语义（Checklist） |
| C3 | 硬 | 测试执行 + 覆盖率 + 无跳过 |
| C4a | 软 | spec ↔ docs（Checklist） |
| C4b-def | 硬 | code ↔ docs 符号表对比（docs 声明的 API 在 code 中存在） |
| C4b-sem | 软 | docs 描述的行为在 code 中可实现（Checklist） |

### 5.2 硬条件检查

**C1-def 三层（打破自证循环）**——不信任生成方贴的标签：
```
L1 标签索引：B001 → test_auth.py        （仅作索引；失败不判 violation）
L2 结构反推：解析测试 AST，提取实际断言
    - 构造了什么输入 / assert 了什么 / 覆盖了 GIVEN/WHEN/THEN 的哪部分
    - L1 失败 → 强制 L2；L2 无法确认 → violation
L3 变异验证（must 级验收 + C3 通过后执行）：
    对实现做变异（改比较符、删 guard、反转布尔、改返回值、改循环边界）
    变异被杀 = 测试真的在测该行为；变异存活 = 测试是假的/弱的 → violation
```

**C2-def**：所有 interfaces 在代码中存在、签名匹配、data_models 一致、错误类型一致、无超出 spec 的公开 API（AST/符号表对比）。

**C3**：测试全绿 + 覆盖率达标 + 无跳过/禁用测试。注意：C3 通过 ≠ 满足 spec，是必要非充分条件。

**C4b-def**：docs 的 `current` 分区中声明的 API 必须存在于 code（符号表对比）。docs 需分区标注：`status: current | planned`，planned 分区（roadmap）不参与检查。

### 5.3 软条件：Checklist 语义检查

#### 判定项生成（双重校验）

从 behavior 自动派生判定项，每项是二分问题：

```
对每个 behavior B：
  [B-GIVEN]  测试/代码是否构造了 B 的 GIVEN 前置条件？
  [B-WHEN]   测试/代码是否调用了 B 声明的接口？
  [B-THEN-1] 测试/代码是否断言/实现了 THEN 子句 1？
  [B-THEN-N] ...
  [B-ERR]    测试/代码是否覆盖了 B 关联的错误类型？
  [B-SIDE]   测试/代码是否验证了 B 的副作用约束？
```

质量约束：
- **双重校验**：生成器 A 产出 → 校验器 B（不同模型）检查覆盖度（是否覆盖所有 THEN/ERR/SIDE、是否有不可验证项）
- **可验证性约束**：每个判定项必须引用 behavior 的具体子句（如 B001-THEN-1），无引用无效
- **判定项集版本化**：每轮 loop 开始冻结判定项集（含版本号），轮内不增删——共识率分母固定，不可操纵

#### 分层投票漏斗（成本控制）

```
L0 快筛（1 模型，全量判定项）→ 判"是"的项默认接受
  ↓ 判"否"或证据缺失的项
L1 投票（3 模型）→ 一致项采纳
  ↓ 分裂项
L2 复核（异模型确认）→ 确认/否决
  ↓ 复核仍无法确认
人工
```

成本对比（20 行为 spec，120 判定项，假设 20% 问题项、5% 分裂项）：
- 全量 3 模型投票：360 次调用/轮
- 分层漏斗：120×1 + 24×3 + 6×1 = **198 次/轮**

**增量缓存**：上轮已共识判定项带版本哈希缓存，本轮变更未触及的不重投。

#### 投票模型独立性（防系统性偏置）

- **独立性矩阵**：在 golden set 上计算模型两两错误相关度；相关度 > 0.6 → 不安排同组投票。投票组必须异质（不同供应商/生态）。
- **golden 锚定**：每个判定项附带同类型 golden 样本（few-shot），模型先校准再投票。
- **偏置降权**：模型在 golden set 上某类判定项错误率超阈值 → 该类票权减半。
- **确定性锚点**：语义判"否"但确定性检查支持实现存在 → 以确定性为准（semantic_only 不阻塞收敛）。

#### 不确定滥用防护

- 投票选项强制为：`是 | 否 | 证据缺失`（无"不确定"）
- "证据缺失" ≠ "不确定"：表示无法从材料判定；进 LLM 复核队列（不直接推给人工）
- 复核仍证据缺失 → 标记 non-verifiable，移出判定集（不阻塞）
- 单轮证据缺失率 > 20% → 模型降权；连续 2 轮 > 20% → 移出投票组，换替补

---

## 6. 收敛判定

```python
def judge(spec, tests, code, docs) -> Verdict:
    hard = {
        "c1_def": check_c1_def(spec, tests),
        "c2_def": check_c2_def(spec, code),
        "c3":     check_c3(tests, code),
        "c4b_def": check_c4b_def(code, docs),
    }
    if not all(h.passed for h in hard.values()):
        return NotConverged(...)          # 门禁：硬条件全过才谈收敛

    consensus = {                          # 软条件：客观计票（非 LLM 评分）
        "c1_sem":  run_checklist(spec, tests, "c1_sem").rate,
        "c2_sem":  run_checklist(spec, code, "c2_sem").rate,
        "c4a":     run_checklist(spec, docs, "c4a").rate,
        "c4b_sem": run_checklist(code, docs, "c4b_sem").rate,
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
    return Verdict(converged, ConvergenceReport(...))
```

**阈值与校准**：0.95/0.90、独立性相关度 0.6、证据缺失率 20%、ping-pong N=3 均为**初值**。Phase 2 用 golden set（已知正确/错误样本 ≥10 对）校准：记录各阈值下的假阳性/假阴性率，调至无假阳性（宁可漏报不可误报），校准记录写入 checker 配置。

**Convergence Report（收敛证明文件）**，分两节：
- `deterministic_evidence`：可重跑（含命令 + 输入哈希）
- `semantic_evidence`：可审计不可复现（记录模型/温度/seed/判定项集版本/投票原始记录）

---

## 7. 路由与回写

### 7.1 三层混合判定路由

```
第一层：确定性预筛（规则）
  - 测试失败但 spec 明确规定该行为 → implementation_error
  - 代码缺少 spec 声明的接口 → implementation_error
  - 行为描述内部矛盾 → spec_error
  - 无法规则确定 → 第二层
第二层：语义裁决（LLM，附证据要求）
  - 输出分类必须附证据（spec 行号 + code 行号 + 原文）
  - spec_error/spec_gap 必须过复核队列（异模型确认）
第三层：人工升级
  - spec_error（改验收标准 = 改游戏规则，必须人工）
  - 连续 2 轮同一 violation 未解决
  - 语义裁决置信度 < 0.7
```

### 7.2 路由矩阵

| 分类 | 触发条件 | 动作 | 需人工 |
|------|---------|------|--------|
| spec_error | spec 内部矛盾/不可实现 | 回写（L2/L3 修订） | 是（必须） |
| spec_gap | 实现暴露未定义情况 | 回写（L2 补充） | 是（提案制） |
| implementation_error | 代码偏离 spec | 重派 code | 否 |
| test_error | 测试缺失/错误 | 重派 tests | 否 |
| doc_error | 文档不同步 | 重派 docs | 否 |

**关键原则**：改 spec 永远比改代码重（提案 + 人工审批 + 归档）。防止 loop 自我放松标准。

### 7.3 影响面分析

变更类型驱动的静态引用分析：

| 变更元素 | 受影响集合 |
|---------|-----------|
| interface | 所有调用方代码 + 该接口测试 + 文档引用 |
| model | 所有读写该模型的代码 + 测试 fixture + 文档 |
| behavior | 该行为的测试（标签追踪辅助）+ 文档引用 |
| boundary | 该边界的测试 |

规则：接口/模型变更走引用图精确局部重派；引用图分析不到的保守标记 STALE（宁多勿漏）；L3 全量重派不依赖影响面分析。

---

## 8. 成本模型

### 8.1 双预算制

```
budget:
  implementation:              # 实现预算（正常迭代）
    total_token: 15M
    max_sessions: 4
  revision:                    # 修订预算（spec 质量成本，单列）
    total_token: 5M
    L2_revision_cost: 0.10     # 每次 L2 修订消耗修订预算 10%
    L3_revision_cost: 0.25     # 每次 L3 修订消耗修订预算 25%
    first_L3_free: true        # 首次 L3 修订免费
```

**激励设计**：修订预算单列 + 首次免费 → loop 诚实报告 spec_error 无成本代价，消除"误分类 spec_error 为 implementation_error 以逃避扣预算"的激励扭曲。修订不是惩罚，是质量成本。

### 8.2 止损与降级（量化）

```
预算/轮数耗尽时的降级路径（按顺序）：
  D1: 语义检查降级（快筛 1 模型，投票只在 must 级跑）      [省 ~60% 语义成本]
  D2: 缩小收敛目标（must 不变，should/could 移入风险清单） [省 ~30% 派生成本]
  D3: 缩小变异测试范围（只跑 P0 验收）                     [省 ~70% 变异成本]
  D4: 拆分 spec（按领域拆，每领域独立 loop）               [线性化成本]
  D5: 交付"最优可行解 + 已知 violation 清单"（最佳努力态）
```

**must 覆盖优先于一切**：预算耗尽 + must 未全覆盖 → 不自动降级，转人工（人工决定：加预算 / 降 must / 接受风险）。D2 只对 should/could 生效。

每次降级生成 Degradation Report（原因、达成度、未达成项）。

---

## 9. Checker 可信度保障

checker 的错误是 silent 的（不会表现为测试失败），因此：

1. **meta-testing**：`tests/checker/` 含已知 spec/test/code 对，检查器必须判对（good/bad fixtures 各 ≥10 个）；checker 改动后 golden set 通过率 100% 才可发布。
2. **独立性矩阵**：见 §5.3（在 golden set 上计算模型错误相关度）。
3. **置信度标注**：确定性检查置信度 = 1.0；语义检查输出投票记录 + 共识率。
4. **已知限制清单**：每个 checker 模块声明能力边界（如"结构反推只支持 Python/Go 常见断言模式"）。

---

## 10. 机器可读 Violation 格式

```json
{
  "schema_version": "1.0",
  "loop_round": 3,
  "spec_version": "0.1.2",
  "violations": [{
    "id": "V-3-001",
    "layer": "c1_def",
    "severity": "blocker",
    "category": "test_error",
    "evidence": {
      "spec_ref": {"file": "specs/auth/spec.md", "line": 42, "text": "THEN 返回 AuthResult"},
      "test_ref": {"file": "tests/test_auth.py", "line": 15, "text": "assert response.status_code == 200"},
      "description": "测试断言 HTTP 状态码而非 AuthResult 对象"
    },
    "route": "regenerate_tests",
    "confidence": 0.95,
    "confidence_type": "deterministic"
  }],
  "convergence_score": 0.72,
  "budget_remaining": "62%"
}
```

CI 集成：blocker 级 violation → 非零 exit code，loop 可挂 CI gate。

---

## 11. 组件分解与跨组件检查

- 组件内部 loop 只查本组件 spec ↔ artifacts
- 组件间通过**接口契约**检查（签名 + 跨组件行为场景）
- 跨组件验收标准带 `cross_component: true`，生成集成测试（`tests/integration/`），顶层 loop 验证
- 跨组件测试失败责任定位：先 C2-def 查接口签名，再 C2-sem 查行为语义
- 集成测试分层：L1 接口级契约测试（确定性）→ L2 行为级场景测试（执行验证）→ L3 环境级（性能/并发，不进 loop）

---

## 12. 人工审查回流

人工反馈结构化模板（机器可消费，不依赖 LLM 解析）：

```
verdict: approve | reject | modify_spec
if reject:
  reason_category: implementation_error | test_error | doc_error | spec_error | other
  reason_text: <自由文本>
  evidence_ref: <可选>
  required_fix: <期望修复方向>
if modify_spec:
  diff: <结构化修改>
  change_level: L1 | L2 | L3
```

回流：approve → 归档解除 STALE；reject → 生成 violation 反馈进路由；modify_spec → 触发修订流程。人工确认的假阳性 → checker 校准库（few-shot 范例持续校准）。

---

## 13. 适用门槛与降级模式

| 模式 | Spec | Loop | 检查 | 成本 |
|------|------|------|------|------|
| 完整 SDDL | specs/+changes/ 双区 | 自动 | 硬+软+变异 | 高 |
| 标准 SDDL | 单 spec + changes/ | 自动 | 硬+软（无变异） | 中 |
| 轻量 SDD | 单 spec（L1-L2） | 手动 | 只硬条件 | 低 |
| 纯 TDD | 无 | 无 | 只 C3 | 最低 |

**门槛判定**：
```
完整 SDDL：接口 ≥ 8 且 must 验收 ≥ 10 且多 artifact 同步 且 项目 > 4 周 且 spec 相对稳定
标准 SDDL：接口 5-8 或 must 验收 5-10
轻量 SDD：接口 < 5 但多 artifact
否则：纯 TDD 或直接写
```

**不适用**：一次性脚本、原型/POC、探索性研究代码。

---

## 14. 实施路线

```
Phase 0: Spec Store 搭建
  ├── specs/ + changes/ 目录制 + 变更生命周期
  ├── 修订分级 + STALE + CHANGELOG 审计
Phase 1: 确定性检查器
  ├── C2-def / C3 / C4b-def / C1-def L1+L2
  ├── checker meta-testing（golden set）
Phase 2: 语义检查器 + 基础 Loop
  ├── Checklist 判定项生成器 + 双重校验
  ├── 分层投票（快筛→投票→复核）+ 独立性矩阵
  ├── 收敛判定（门禁 + 共识率）+ golden set 校准阈值
  ├── 基础 loop（派生→验证→判定，不含回写）
  └── Convergence Report
Phase 3: 回写通道 + 路由 + 成本控制
  ├── 三层混合判定路由 + 影响面分析
  ├── 双预算 + 修订衰减 + 降级路径
  ├── 人工审查回流（结构化模板）
  └── 多变更并行冲突测试
Phase 4: 变异测试 + 集成
  ├── C1-def L3 变异验证（守卫条件）
  ├── 跨组件契约测试
  ├── Ouroboros 集成（Seed → spec 适配，evaluate 注入 C1/C4）
  └── CI 集成（violation JSON 消费）
```

---

## 15. 开放问题与验证项

| # | 问题 | 状态 | 验证方式 |
|---|------|------|---------|
| O1 | 语义检查稳定性 | 机制已定（分层投票+独立性+双重校验） | golden set 校准实验 |
| O2 | 回写冲突解决 | 双区制 + 修订分级 + 人工审批 | 多变更并行测试 |
| O3 | 跨组件行为形式化 | 契约测试 + 分层 | 实践验证 |
| O4 | L5 质量约束自动翻译 | 移出 loop + env 标记 | 约束→测试模式库 |
| O5 | Ouroboros 适配层 | 概念映射已定义 | Phase 4 实现 |
| O6 | 成本基线 | 双预算 + 分层投票模型 | 收集真实数据 |
| O7 | spec gap 自动检测 | 路由层已定义 | runtime 监控实验 |
| O8 | 变异测试实际开销 | must_only + 守卫 | Phase 4 评估 |
| O9 | 多变更并行冲突 | changes/ 支持 | Phase 3 测试 |
| O10 | 判定项模板判别力 | 双重校验 + golden set | 验证 |

---

## 附录 A：证据来源

| 来源 | 支撑点 |
|------|--------|
| Self-Refine: Iterative Refinement with Self-Feedback (arXiv 2303.17651, 2023) | self-refine loop 范式源头 |
| CYCLE: Learning to Self-Refine the Code Generation (arXiv 2024-03) | 代码生成自我精炼 loop |
| Pride and Prejudice: LLM Amplifies Self-Bias in Self-Refinement (arXiv 2402.11436, 2024) | 自反馈放大自偏置 → 异模型检查 |
| Feedback Over Form (arXiv 2026-04) | 执行反馈 > 管线拓扑 → 确定性执行反馈优先 |
| LLMorpheus: Mutation Testing using LLMs (arXiv 2404.09954, 2024) | LLM 变异测试可行 → C1 反推验证 |
| Intent-Based Mutation Testing (arXiv 2026-07) | 意图变异 → 行为导向变异算子 |
| TICKing All the Boxes (arXiv 2410.07061, 2024) | checklist 生成改善 LLM 评估 → 判定项 |
| Fairness or Fluency: Language Bias of Pairwise LLM-as-a-Judge (arXiv 2026-01) | pairwise judge 语言偏置 → 异模型投票 |
| BiasScope (arXiv 2026-02) | LLM-as-a-Judge 偏置系统性、可检测 |
| Bias and Uncertainty in LLM-as-a-Judge (arXiv 2026-05) | judge 估计偏置 → 不用绝对分数 |
| SLMEval: Entropy-Based Calibration (arXiv 2505.xxxx, 2025) | 熵基校准 → golden set 校准参考 |
| Calibration Collapse Under Sycophancy (arXiv 2026-04) | 谄媚微调致校准崩溃 → 绝对分数不可信 |
| Ensemble Learning for Heterogeneous LLMs (arXiv 2404.xxxx, 2024) | 异构 LLM 集成 → 异模型投票 |
| Efficient Dynamic Ensembling (arXiv 2412.xxxx, 2024) | 动态集成 → 分层投票 |
| Ranked Voting Self-Consistency (arXiv 2505.xxxx, 2025) | 排序投票自一致性 → 投票变体 |
| LLM Peer-Review Ensemble (arXiv 2512.xxxx, 2025) | peer-review 集成 → 复核机制 |
| OpenSpec (Fission-AI, GitHub) | specs/+changes/+archive 变更管理；verify 工作流 |

## 附录 B：完整 Spec 示例（auth 服务）

```yaml
meta:
  id: "auth-service"
  version: "0.1.0"
  domain: "auth"
  status: "locked"
  dependencies: ["user-model@>=1.0"]

non_goals:
  - "本服务不负责用户注册"
  - "不支持多租户"
  - "不做密码找回（由 user-service 提供）"

interfaces:
  - name: "authenticate"
    signature:
      params:
        - { name: "credentials", type: "Credentials", required: true }
      returns: { type: "AuthResult" }
    errors: ["InvalidCredentialsError", "AccountLockedError", "RateLimitError"]
  - name: "refreshToken"
    signature:
      params:
        - { name: "token", type: "string", required: true }
      returns: { type: "AuthResult" }
    errors: ["InvalidTokenError", "TokenExpiredError"]

data_models:
  - name: "Credentials"
    schema:
      type: "object"
      properties:
        email: { type: "string", format: "email" }
        password: { type: "string", minLength: 8 }
      required: ["email", "password"]
  - name: "AuthResult"
    schema:
      type: "object"
      properties:
        access_token: { type: "string" }
        refresh_token: { type: "string" }
        expires_in: { type: "integer", minimum: 300 }
        user_id: { type: "string" }
      required: ["access_token", "refresh_token", "expires_in", "user_id"]

behaviors:
  - id: "B001"
    interface: "authenticate"
    priority: "must"
    scenario: "valid credentials"
    given: "用户存在且密码匹配"
    when: "调用 authenticate(valid credentials)"
    then:
      - "返回 AuthResult，包含有效的 access_token"
      - "expires_in >= 300"
      - "access_token 可通过 refreshToken 续期"
    acceptance: true

  - id: "B002"
    interface: "authenticate"
    priority: "must"
    scenario: "invalid password"
    given: "用户存在但密码不匹配"
    when: "调用 authenticate(credentials with wrong password)"
    then:
      - "抛出 InvalidCredentialsError"
      - "不修改任何持久状态"
    acceptance: true

  - id: "B003"
    interface: "authenticate"
    priority: "should"
    scenario: "rate limit"
    given: "同一 IP 在 60 秒内连续失败 5 次"
    when: "第 6 次调用 authenticate"
    then:
      - "抛出 RateLimitError"
      - "锁定该 IP 300 秒"
    acceptance: true

boundaries:
  - condition: "数据库连接断开"
    expectation: "抛出 ServiceUnavailableError，不产生部分写入"
    priority: "must"

quality_constraints:
  performance:
    - metric: "P99 latency"
      threshold: "500ms"
      scope: "authenticate"
      verification: "env"
      priority: "should"
  security:
    - "密码不以明文存储或记录到日志"
    - "access_token 使用 RS256 签名"
  observability:
    - "每次 authenticate 调用记录 audit log（不含密码）"
```

---

> **最终方案一句话**：以 Spec Store（双区制）为单一事实来源，硬条件（确定性）门禁 + 软条件（Checklist 共识计票）收敛，通过分层投票、双预算、修订激励设计和 checker 可信度保障，让 spec↔tests↔code↔docs 四件套在受控成本内同步收敛。
