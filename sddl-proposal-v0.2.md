# Spec-Driven Development Loop (SDDL) 方案 v0.2

> 版本 0.2 | 2026-08-06 | 基于 Round 1 评审（P0×4/P1×6/P2×6）+ 发散思考 + 搜索验证修订
>
> **变更摘要（vs v0.1）**：
> - 收敛判定重构：硬条件/软条件分层 + 分数制（修 P0-1）
> - C1 增加变异测试反推验证，打破自证循环（修 P0-2）
> - 新增 Spec 变更管理：specs/ + changes/ 双区制 + 修订分级 + ping-pong 检测（修 P0-3）
> - 对抗式检查增加证据要求 + 复核队列 + 假阳性反馈（修 P0-4）
> - 新增成本预算模型（修 P1-1）、checker 可信度保障（修 P1-2）
> - 路由分类改为混合判定：确定性预筛 + 语义裁决 + 人工升级（修 P1-3）
> - 验收标准增加 MoSCoW 优先级（修 P1-4）、降级策略量化（修 P1-5）
> - 新增变更审计追踪（修 P1-6）、non_goals 字段、机器可读 violation、CI 集成（修 P2）
>
> **搜索证据支撑**（详见附录 A）：
> - Pride and Prejudice (arXiv 2402.11436)：LLM 自反馈放大自偏置 → 生成/检查必须异模型
> - Feedback Over Form (arXiv 2604.xxxx)：执行反馈 > 管线拓扑 → 确定性执行反馈优先
> - LLMorpheus (arXiv 2404.09954)：LLM 变异测试可行 → C1 反推验证
> - Intent-Based Mutation Testing (arXiv 2026-07)：意图变异 → 基于行为的变异算子
> - OpenSpec (Fission-AI)：specs/ + changes/ + archive 变更管理实践

---

## 1. 核心架构（v0.2）

```
┌────────────────────────────────────────────────────────────────────┐
│                    Spec Store（单一事实来源）                        │
│  ┌──────────────────────────────┐  ┌─────────────────────────────┐ │
│  │  specs/（当前真相，已批准）    │◄─│  changes/（增量提案，未批准） │ │
│  │  每个领域一个 spec.md          │ │  每个变更一个目录             │ │
│  │  含 requirements + scenarios  │ │  proposal.md + specs/ 增量   │ │
│  └──────────────┬───────────────┘  └──────────────┬──────────────┘ │
│                 │ archive（归档合并）               │                │
└─────────────────┼──────────────────────────────────┼────────────────┘
                  │                                  │
         ┌────────▼──────────┐            ┌─────────▼─────────┐
         │  派生通道 (下行)   │            │  回写通道 (上行)   │
         │  spec → artifacts │            │  impl → spec 修订  │
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
│     分层一致性检查器 (Layered Checker)        │    │
│  硬条件: C1-def C2-def C3                     │    │
│  软条件: C1-sem C2-sem C4                    │    │
└──────────────────┬───────────────────────────┘    │
                   │                                 │
                   ▼                                 │
        ┌──────────────────────┐                     │
        │  收敛判定 (Score+Gate)│─────────────────────┘
        └────┬─────────────┬───┘
             │             │
        Converged      NotConverged
             │         (violations → 路由 → 派生/回写)
             ▼
        Convergence Report（证据链）
```

**v0.2 关键变化**：Spec Store 采用 OpenSpec 式双区制（specs/ 当前真相 + changes/ 增量提案），这是 spec 演化管理的基础设施。

---

## 2. Spec Store 与变更管理（新增，修 P0-3/P1-6）

### 2.1 双区制

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

**变更生命周期**：

```
propose（提案）→ review（人工/AI 审）→ apply（实现）→ verify（验证）→ archive（归档合并）
                                                                        ↓
                                                           specs/ 更新为新真相
                                                           changes/ 目录归档
```

### 2.2 修订分级（修 P0-3）

| 级别 | 定义 | 是否触发重派生 | 是否需要人工审批 |
|------|------|---------------|-----------------|
| **L1 澄清性修订** | 不改契约，只补语义（错误消息措辞、边界条件细化） | 否（只更新 docs/注释） | 否 |
| **L2 增量修订** | 改契约但兼容（加可选参数、加错误类型、加行为场景） | 是（受影响 artifacts 局部重派） | 是（变更提案制） |
| **L3 破坏性修订** | 改契约且不兼容（删接口、改签名、改数据模型） | 是（全量重派） | 是（必须人工确认） |

**spec 修订原子事务**：L2/L3 修订必须通过 changes/ 提案 → 归档。归档时自动执行：
1. diff 影响面分析（改了哪些接口/行为 → 映射到受影响 artifacts）
2. 标记受影响 artifacts 为 `STALE`（过期），禁止交付
3. 触发重新派生（局部或全量）
4. 新 artifacts 验证通过后才解除 STALE

### 2.3 ping-pong 检测（修 P0-3）

```
同一领域 (auth/) 在连续 N=3 轮内发生 ≥3 次往返修订（spec→impl→spec）
→ 冻结该领域，标记 needs_human_review，不再自动往返
```

**审计追踪**（修 P1-6）：每次 spec 修订生成 `changes/<name>/CHANGELOG.md`，记录：
- 改了哪些 requirements/scenarios（diff）
- 为什么改（触发 violation 的原文）
- 谁改的（AI 或人工）
- 影响面（哪些 artifacts 被标记 STALE）

回写通道**永不静默**：任何 spec 修订都是可见的变更提案，不是 AI 悄悄改验收标准。

---

## 3. Spec Schema（v0.2 增量）

在 v0.1 的 L1-L5 基础上增加：

```yaml
meta:
  # ... v0.1 原有 ...

# ─── 新增：非目标（防 scope creep，checker 可检测越界）───
non_goals:
  - "本服务不负责用户注册，注册由 user-service 提供"
  - "不支持多租户隔离，仅单租户部署"

# ─── 新增：验收标准优先级（MoSCoW，修 P1-4）───
behaviors:
  - id: "B001"
    interface: "authenticate"
    priority: "must"        # must | should | could | wont
    # ... 其余同 v0.1 ...
```

**优先级与收敛的关系**：
- `must`：硬性，未覆盖阻塞收敛
- `should`：软性，未覆盖不阻塞，但进入 Convergence Report 风险清单
- `could`：不阻塞，仅记录
- `wont`：显式排除（等价 non_goals）

---

## 4. 分层一致性检查器（v0.2）

### 4.1 硬条件 / 软条件分离（修 P0-1）

| 检查 | 性质 | 收敛角色 |
|------|------|---------|
| C1-def：验收覆盖映射（标签→测试文件） | **硬** | 必须全过 |
| C2-def：接口/签名/模型/错误类型静态对比 | **硬** | 必须全过 |
| C3：测试执行 + 覆盖率 + 无跳过 | **硬** | 必须全过 |
| C1-sem：测试实际断言 ↔ 行为语义比对 | **软** | 分数制 |
| C2-sem：代码行为 ↔ 行为语义比对 | **软** | 分数制 |
| C4：文档一致性 | **软** | 分数制 |
| L5 质量约束（性能/安全） | **环境依赖** | 不在 loop 内验证，标注 `needs_env_verification`，进 Convergence Report |

**原理**：硬条件是可确定性验证的（测试执行、静态分析），永远不会因环境/措辞波动。软条件是语义判断（LLM），天然有噪声——不给它们"一票否决"权，改为分数制。

### 4.2 C1-def 反推验证（修 P0-2，打破自证循环）

**不再信任生成方贴的标签**。C1-def 由三层构成：

```
L1 标签映射：B001 → test_authenticate_valid           （快筛，仅作索引）
L2 结构反推：解析测试 AST，提取实际断言                （中间层）
    - 测试构造了什么输入
    - assert 了什么（返回值、异常、副作用）
    - 是否覆盖了 behavior 的 GIVEN/WHEN/THEN
L3 变异验证（可选，成本高，must 级验收才跑）：          （最硬证据）
    对实现做变异（改一行逻辑），跑对应验收测试
    变异被杀 = 测试真的在测这个行为
    变异存活 = 测试是假的/弱的 → violation
```

**变异算子**（参考 Intent-Based Mutation Testing）：
- 改比较符号（== → !=, > → >=）
- 删除 guard 分支
- 反转布尔条件
- 改返回值（null/错误值）
- 改循环边界（+1/-1）

**L3 的启动条件**：`must` 级验收 + 预算允许。非 must 级验收只用 L1+L2。

### 4.3 对抗式检查 + 假阳性控制（修 P0-4）

**两级检查架构**：

```
┌─────────────────────┐    ┌─────────────────────┐
│  对抗式检查器 (A)     │    │  确认式复核器 (B)    │
│  目标：找不一致证据    │───▶│  目标：复核 A 的发现  │
│  模型：checker-model  │    │  模型：另一模型       │
│  prompt：对抗性       │    │  prompt：确认性       │
└─────────────────────┘    └─────────────────────┘
         │                          │
         ▼                          ▼
   violation (A)          复核通过 → 正式 violation
                         复核否决 → 降级为观察项 (observation)
```

**证据要求**：每个正式 violation 必须附带：
- spec 引用（文件+行号+原文）
- code/test 引用（文件+行号+原文）
- 不一致的**具体描述**（不是"似乎不一致"）

无证据的发现自动降级为观察项，不阻塞收敛。

**确定性锚点**（修 P0-4 最重的一招）：
> 语义检查发现的任何问题，若确定性检查（类型/schema/测试执行）不支持，标记为 `semantic_only`，不阻塞收敛，只进风险清单。

**假阳性反馈回路**：人工确认的假阳性进入 checker 的 few-shot 范例库，持续校准。checker 的校准记录公开可查。

### 4.4 收敛判定（v0.2，分数制 + 门禁制）

```python
def judge(spec, tests, code, docs) -> Verdict:
    hard = {
        "c1_def": check_c1_def(spec, tests),      # 覆盖映射 + 结构反推
        "c2_def": check_c2_def(spec, code),        # 接口/签名/模型/错误
        "c3":     check_c3(tests, code),           # 测试执行 + 覆盖 + 无跳过
    }
    soft = {
        "c1_sem": score_c1_sem(spec, tests),       # 0-100
        "c2_sem": score_c2_sem(spec, code),        # 0-100
        "c4":     score_c4(spec, docs),            # 0-100
    }

    # 门禁：硬条件全过才谈收敛
    if not all(h.passed for h in hard.values()):
        return NotConverged([v for h in hard.values() for v in h.violations])

    # 分数制：软条件加权
    score = (soft["c1_sem"] * 0.3 + soft["c2_sem"] * 0.4 + soft["c4"] * 0.3)
    must_covered = coverage_of(spec.behaviors, priority="must")

    if score >= 0.90 and must_covered >= 1.0:
        return Converged(
            report=ConvergenceReport(
                score=score,
                hard_checks=hard,
                soft_checks=soft,
                risk_list=[v for v in all_soft_violations if v.severity == "observation"],
                env_verification=[L5 约束未验证项],
                spec_version=spec.version,
            )
        )
    return NotConverged(...)
```

**Convergence Report（收敛证明文件，新增）**：每次收敛判定输出完整证据链——每层检查的通过依据、soft 分数、风险清单、环境验证项。这份报告是可审计的：任何人可以重跑检查验证收敛声明。

---

## 5. 路由与回写（v0.2）

### 5.1 混合判定路由（修 P1-3）

**violation 分类不再由 LLM 单方面裁决**，而是三层混合：

```
┌─────────────────────────────────────────────────────────┐
│  第一层：确定性预筛（规则）                                │
│  - 测试失败但 spec 明确规定了该行为 → implementation_error │
│  - 代码缺少 spec 声明的接口 → implementation_error        │
│  - 行为描述内部矛盾（GIVEN 自相矛盾）→ spec_error          │
│  - 无法用规则确定的 → 进入第二层                           │
├─────────────────────────────────────────────────────────┤
│  第二层：语义裁决（LLM，附证据要求）                        │
│  - 输出 spec_error / spec_gap / implementation_error /   │
│    test_error / doc_error，必须附证据                       │
│  - spec_error/spec_gap 类 violation 必须过复核队列         │
│    （另一模型确认性复核），因为"改 spec"是最敏感操作          │
├─────────────────────────────────────────────────────────┤
│  第三层：人工升级                                        │
│  - spec_error 类型（改验收标准 = 改游戏规则，必须人工）       │
│  - 连续 2 轮同一 violation 未解决                          │
│  - 语义裁决置信度 < 0.7                                   │
└─────────────────────────────────────────────────────────┘
```

### 5.2 路由矩阵

| 分类 | 触发条件 | 动作 | 需人工 |
|------|---------|------|--------|
| `spec_error` | spec 内部矛盾/不可实现 | 回写 spec（L2/L3 修订） | **是**（必须） |
| `spec_gap` | 实现暴露 spec 未定义情况 | 回写 spec（L2 补充） | 是（变更提案制） |
| `implementation_error` | 代码偏离 spec | 重新派生 code | 否 |
| `test_error` | 测试缺失/错误 | 重新派生 tests | 否 |
| `doc_error` | 文档不同步 | 重新派生 docs | 否 |

**关键原则**：改 spec（spec_error/spec_gap）永远比改代码更重——需要变更提案 + 人工审批 + 归档。代码/测试/文档的重新派生是轻操作，自动执行。这是防止 loop "自我放松标准"的闸门。

---

## 6. 成本模型（新增，修 P1-1）

### 6.1 成本构成

| 环节 | 成本类型 | 估算 |
|------|---------|------|
| 派生（每轮） | token 生成 | 与 spec 规模线性 |
| C1-def L3 变异测试 | 计算（编译+跑测试×变异数） | 与变异数线性，最贵 |
| C1-sem / C2-sem | LLM 推理（每项 2 模型×2 轮） | 与行为数线性 |
| 回写 + 重派 | token 生成 | 全量重派 ≈ 重新开发 |

### 6.2 预算控制

```
budget:
  max_token_per_round: 500K           # 单轮预算上限
  max_rounds: 8                        # 最大轮数
  total_budget: 4M                     # 总预算上限（8 轮 × 500K）
  semantic_check_rounds: 2             # 语义检查每项最多 2 轮
  mutation_test: { enabled: true, scope: "must_only", max_mutants: 50 }
```

### 6.3 止损与降级（修 P1-5，量化）

```
预算/轮数耗尽时的降级路径（按顺序尝试）：
  D1: 降级语义检查（c1_sem/c2_sem 改为 1 模型 1 轮）      [省 ~50% 语义成本]
  D2: 缩小收敛目标（must 级验收不变，should 级移入风险清单）[省 ~30% 派生成本]
  D3: 缩小变异测试范围（只跑 P0 验收的变异）               [省 ~70% 变异成本]
  D4: 拆分 spec（按领域拆，每领域独立 loop）               [线性化成本]
  D5: 交付"最优可行解 + 已知 violation 清单"（最佳努力交付态）

降级不是失败：每次降级都生成 Degradation Report，记录降级原因、
当前达成度、未达成项。用户可基于报告决定继续投入或接受。
```

**收敛不是布尔，是成本曲线上的最优点**。95% 满足 + 明确风险清单，通常比 100% 满足 + 烧掉 3 倍预算更正确。

---

## 7. Checker 可信度保障（新增，修 P1-2）

checker 的错误是 silent 的——它不会表现为测试失败。因此：

### 7.1 checker 的 meta-testing

```
tests/checker/
├── test_c1_def.py          # 已知 spec/test 对 → 检查器必须判对
├── test_c2_def.py          # 已知接口错配 → 检查器必须报 violation
├── test_false_positive.py  # 已知一致对 → 检查器不得误报
└── fixtures/
    ├── good/               # 已知正确的 spec+code+test 样例
    └── bad/                # 已知有问题的样例（每类问题一个）
```

**golden set 校准**：维护已知答案的样本集（good/bad 各 ≥10 个），每次 checker 改动后跑一遍，通过率 100% 才可发布。

### 7.2 已知限制清单

每个 checker 模块声明自己的能力边界：
- C1-def L2 结构反推：只支持 Python/Go 的常见断言模式；不支持动态 mock 断言
- C1-sem：不评估性能语义；不评估并发行为
- 等

**checker 的输出带置信度标注**：确定性检查置信度 = 1.0（硬）；语义检查置信度 = 模型输出分数。

---

## 8. 机器可读 Violation 格式（新增，修 P2-2）

```json
{
  "schema_version": "1.0",
  "loop_round": 3,
  "spec_version": "0.2.1",
  "violations": [
    {
      "id": "V-3-001",
      "layer": "c1_def",
      "severity": "blocker",
      "category": "test_error",
      "evidence": {
        "spec_ref": {"file": "specs/auth/spec.md", "line": 42, "text": "THEN 返回 AuthResult"},
        "test_ref": {"file": "tests/test_auth.py", "line": 15, "text": "assert response.status_code == 200"},
        "description": "测试断言的是 HTTP 状态码，不是 AuthResult 对象"
      },
      "route": "regenerate_tests",
      "confidence": 0.95,
      "confidence_type": "deterministic"
    }
  ],
  "convergence_score": 0.72,
  "budget_remaining": "62%"
}
```

**CI 集成**（修 P2-3）：violation 输出可被 CI 消费（exit code = 非零 if 有 blocker 级 violation），loop 可挂 CI gate。

---

## 9. 组件分解与跨组件检查（v0.2 增量，修 P2-4）

v0.1 的组件分解只查接口签名，跨组件行为级集成（时序/事务/并发）缺失。v0.2 增加：

### 9.1 跨组件契约测试

```
specs/order/ 和 specs/payment/ 之间的跨组件行为：
  → 生成集成测试（放 tests/integration/），由顶层 loop 单独验证
  → 跨组件验收标准带 cross_component: true 标记
  → 跨组件契约测试失败 = 哪个组件的责任？由 C2-def 定位
    （先查接口签名，再查行为语义）
```

### 9.2 集成测试的分层

```
L1 接口级：契约测试（签名/类型/错误）     —— 确定性
L2 行为级：跨组件场景测试（GWT）          —— 半确定（执行验证）
L3 环境级：性能/并发/事务                 —— 环境验证（不进 loop）
```

---

## 10. 人工审查回流（新增，修 P2-5）

人工审查结果必须回流 loop，否则 loop 与人工脱节：

```
人工审查结论（approve / reject_with_reason / modify_spec）
  → approve：归档，specs/ 更新，解除 STALE
  → reject_with_reason：生成 violation 反馈（含人工理由），
     loop 按理由重新派生/回写
  → modify_spec：人工直接改 spec → 触发 L2/L3 修订流程
```

人工确认的假阳性 → checker 校准库（见 4.3）。

---

## 11. 完整 Spec 示例（新增，修 P2-6）

完整示例见附录 B（auth 服务，含 all 层 + non_goals + 优先级）。

---

## 12. 适用门槛与降级模式（v0.2）

| 模式 | Spec | Loop | 检查 | 成本 |
|------|------|------|------|------|
| **完整 SDDL** | specs/+changes/ 双区 | 自动 loop | 硬+软+变异 | 高 |
| **标准 SDDL** | 单 spec + changes/ | 自动 loop | 硬+软（无变异） | 中 |
| **轻量 SDD** | 单 spec（L1-L2） | 手动触发 | 只硬条件 | 低 |
| **纯 TDD** | 无 | 无 | 只 C3 | 最低 |

**门槛判定（v0.2 更新）**：
```
完整 SDDL 当且仅当：
  (接口数 ≥ 8) AND (must 级验收 ≥ 10) AND (多 artifact 需同步)
  AND (项目预期 > 4 周) AND (spec 相对稳定)
标准 SDDL：接口 5-8 或 must 验收 5-10
轻量 SDD：接口 < 5 但多 artifact
否则：纯 TDD 或直接写
```

---

## 13. 实施路线（v0.2）

```
Phase 0: Spec Store 搭建（新）
  ├── specs/ + changes/ 目录制
  ├── 变更生命周期（propose→review→apply→verify→archive）
  ├── 修订分级 + STALE 标记
  └── CHANGELOG 审计

Phase 1: 确定性检查器
  ├── C2-def（接口/签名/模型/错误静态对比）
  ├── C3（测试执行 + 覆盖率 + 无跳过）
  ├── C1-def L1+L2（标签映射 + 结构反推）
  └── checker meta-testing（golden set）

Phase 2: 语义检查器 + 基础 Loop
  ├── C1-sem / C2-sem / C4（对抗式 + 复核 + 证据要求）
  ├── 收敛判定（门禁 + 分数制）
  ├── 基础 loop（派生→验证→判定，不含回写）
  └── Convergence Report 生成

Phase 3: 回写通道 + 路由 + 成本控制
  ├── 混合判定路由（确定性预筛 + 语义裁决 + 人工升级）
  ├── 修订事务 + ping-pong 检测
  ├── 预算模型 + 降级路径
  └── 人工审查回流

Phase 4: 变异测试 + 集成
  ├── C1-def L3 变异验证（must 级验收）
  ├── 跨组件契约测试
  ├── Ouroboros 集成（Seed → spec 适配）
  └── CI 集成（violation JSON 消费）
```

---

## 14. 待解决问题（v0.2 更新）

| # | 问题 | v0.2 状态 | 下一步 |
|---|------|----------|--------|
| O1 | L3 行为语义检查稳定性 | 降为软条件 + 分数制 + 复核队列 | 需实验确定阈值 |
| O2 | 回写冲突解决 | changes/ 双区制 + 修订分级 + 人工审批 | 仍需多变更并行冲突测试 |
| O3 | 跨组件行为形式化 | 契约测试 + 分层集成测试 | 待实践验证 |
| O4 | L5 质量约束自动翻译 | 移出 loop，标注 needs_env_verification | 建约束→测试模式库 |
| O5 | Ouroboros 适配层 | 概念映射已定义 | Phase 4 实现 |
| O6 | 成本基线 | 预算模型已定义（估算） | 收集真实数据校准 |
| O7 | spec gap 自动检测 | 路由层已定义 | 需 runtime 监控实验 |
| O8 | 变异测试成本 | must_only + max_mutants 限制 | 需评估实际开销 |
| O9 | 多变更并行冲突 | changes/ 支持并行，冲突解决未验证 | 需测试 |

---

## 附录 A：搜索证据来源

| 来源 | 支撑点 |
|------|--------|
| Pride and Prejudice: LLM Amplifies Self-Bias in Self-Refinement (arXiv 2402.11436, 2024) | 自反馈放大自偏置 → 异模型检查；外部准确评估降低偏置 |
| Feedback Over Form: Why Execution Feedback Matters More Than Pipeline Topology in 1-3B Code Generation (arXiv 2026-04) | 执行反馈 > 管线拓扑 → 确定性执行反馈优先 |
| LLMorpheus: Mutation Testing using Large Language Models (arXiv 2404.09954, 2024) | LLM 变异测试可行 → C1 反推验证 |
| Intent-Based Mutation Testing: From Naturally Written Programming Intents to Mutants (arXiv 2026-07) | 意图变异 → 基于行为的变异算子 |
| OpenSpec (Fission-AI, GitHub) | specs/ + changes/ + archive 变更管理；/opsx:verify 代码-spec 对齐检查 |
| Self-Refine: Iterative Refinement with Self-Feedback (arXiv 2303.17651, 2023) | self-refine 范式源头（loop 基础） |
| CYCLE: Learning to Self-Refine the Code Generation (arXiv 2024-03) | 代码生成的自我精炼 loop |

## 附录 B：完整 Spec 示例（auth 服务）

```yaml
meta:
  id: "auth-service"
  version: "0.2.0"
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

quality_constraints:
  performance:
    - metric: "P99 latency"
      threshold: "500ms"
      scope: "authenticate"
      verification: "env"          # 环境验证，不进 loop
  security:
    - "密码不以明文存储或记录到日志"
    - "access_token 使用 RS256 签名"
  observability:
    - "每次 authenticate 调用记录 audit log（不含密码）"
```

---

> v0.2 核心改进一句话：**把"验证一致性控制 loop"从布尔命题改成了工程系统**——
> 硬条件门禁 + 软条件分数、双区制 spec 变更管理、异模型对抗式检查 + 证据要求、
> 成本预算 + 量化降级、checker meta-testing。每个 P0/P1 都有明确的机制回应。
