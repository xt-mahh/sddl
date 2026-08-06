# Spec-Driven Development Loop (SDDL) 方案草案

> 版本 0.1 | 2026-08-06 | 基于对话讨论草拟

---

## 1. 问题定义

AI 编程时代的三个核心痛点：

| 痛点 | 本质 | 现有方案不足 |
|------|------|-------------|
| **上下文漂移** | 对话越长，AI 越容易忘记早期约定 | 对话式编程无稳定锚点 |
| **多 artifact 不同步** | 代码改了，测试和文档没跟上 | 传统 SDD 只管 spec→code，单向派生 |
| **验收主观化** | "感觉对了"代替"符合规格" | TDD 只验证行为，不验证规格完整性 |

**目标**：构建一个以结构化 Spec 为单一事实来源、通过 Loop 驱动测试/代码/文档三件套同步、以分层一致性检查控制收敛的闭环系统。

---

## 2. 核心模型

```
                    ┌─────────────────────────────────────────┐
                    │           Structured Spec (SS)           │
                    │  单一事实来源 · 版本化 · 可演化          │
                    └──────────┬──────────────┬───────────────┘
                               │              │
                    ┌──────────▼──────┐ ┌─────▼──────────┐
                    │   派生通道(下行) │ │ 回写通道(上行)  │
                    │  spec → artifacts│ │ impl → spec 修订│
                    └──────────┬──────┘ └─────▲──────────┘
                               │              │
              ┌────────────────┼──────────────┼───────────┐
              ▼                ▼              ▼           │
        ┌──────────┐    ┌──────────┐   ┌──────────┐       │
        │  Tests   │    │   Code   │   │   Docs   │       │
        │ (投影)   │    │ (实现)   │   │ (描述)   │       │
        └────┬─────┘    └────┬─────┘   └────┬─────┘       │
             │               │              │              │
             ▼               ▼              ▼              │
     ┌───────────────────────────────────────────┐         │
     │        分层一致性检查器 (Layered Checker)  │─────────┘
     │  C1: Spec↔Tests  C2: Spec↔Code            │
     │  C3: Tests↔Code  C4: Spec↔Docs            │
     └──────────────────┬────────────────────────┘
                        │
                        ▼
              ┌─────────────────┐
              │  收敛判定器      │
              │  C1∧C2∧C3∧C4 ?  │
              └────┬───────┬────┘
                   │       │
              收敛 │       │ 未收敛
                   ▼       ▼
               终止      回到派生/回写通道，携带 violation 报告
```

**三个关键设计决策**：

1. **双向通道**：派生（spec→artifacts）+ 回写（impl→spec 修订）。Spec 不是神谕，实现过程会暴露 spec 的错误和欠定义。
2. **分层谓词**：一致性不是单一布尔值，是 C1∧C2∧C3∧C4 的合取。每层用不同方法检查。
3. **确定性优先**：能用静态分析/schema 验证/测试执行解决的，绝不用 LLM。LLM 只填语义缺口。

---

## 3. Structured Spec Schema 草案

Spec 的结构化程度直接决定 loop 里能走多少确定性路径。按"机器可消费性"从高到低分层：

### 3.1 Schema 定义

```yaml
# spec.yaml — 结构化规格说明
meta:
  id: "auth-service"
  version: "0.3.0"
  parent_spec: null          # 父 spec（组件分解时）
  dependencies:              # 依赖的其他 spec
    - "user-model@>=1.0"
    - "crypto-utils@>=2.1"
  language: "zh-CN"
  status: "draft | reviewing | locked | evolved"

# ─── L1: 接口契约层（完全机器可消费）───
interfaces:
  - name: "authenticate"
    signature:
      params:
        - name: "credentials"
          type: "Credentials"
          required: true
      returns:
        type: "AuthResult"
        # 引用下方 data_models 中的定义
    errors:
      - "InvalidCredentialsError"
      - "AccountLockedError"
      - "RateLimitError"

  - name: "refreshToken"
    signature:
      params:
        - name: "token"
          type: "string"
          required: true
      returns:
        type: "AuthResult"
    errors:
      - "InvalidTokenError"
      - "TokenExpiredError"

# ─── L2: 数据模型层（schema 可验证）───
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

# ─── L3: 行为描述层（半结构化，场景驱动）───
behaviors:
  - id: "B001"
    interface: "authenticate"
    scenario: "valid credentials"
    given: "用户存在且密码匹配"
    when: "调用 authenticate(valid credentials)"
    then:
      - "返回 AuthResult，包含有效的 access_token"
      - "expires_in >= 300"
      - "access_token 可通过 refreshToken 续期"
    acceptance: true           # 标记为验收标准（C1 检查对象）

  - id: "B002"
    interface: "authenticate"
    scenario: "invalid password"
    given: "用户存在但密码不匹配"
    when: "调用 authenticate(credentials with wrong password)"
    then:
      - "抛出 InvalidCredentialsError"
      - "不修改任何持久状态"
    acceptance: true

  - id: "B003"
    interface: "authenticate"
    scenario: "rate limit"
    given: "同一 IP 在 60 秒内连续失败 5 次"
    when: "第 6 次调用 authenticate"
    then:
      - "抛出 RateLimitError"
      - "锁定该 IP 300 秒"
    acceptance: true

# ─── L4: 边界与错误层（显式枚举）───
boundaries:
  - condition: "并发 1000 次 authenticate 调用"
    expectation: "响应时间 P99 < 500ms，无数据竞争"

  - condition: "数据库连接断开"
    expectation: "抛出 ServiceUnavailableError，不产生部分写入"

  - condition: "token 长度超过 10KB"
    expectation: "抛出 InvalidTokenError，不尝试解析"

# ─── L5: 质量约束层（非功能需求）───
quality_constraints:
  performance:
    - metric: "P99 latency"
      threshold: "500ms"
      scope: "authenticate"
  security:
    - "密码不以明文存储或记录到日志"
    - "access_token 使用 RS256 签名"
  observability:
    - "每次 authenticate 调用记录 audit log（不含密码）"
```

### 3.2 分层可消费性

| 层 | 内容 | 机器可消费性 | 检查方法 |
|----|------|------------|---------|
| L1 接口契约 | 函数签名、参数类型、返回类型、错误类型 | **完全** | 静态类型检查 / AST 对比 |
| L2 数据模型 | JSON Schema / 类型定义 | **完全** | Schema 验证器 |
| L3 行为描述 | Given-When-Then 场景 | **半**（结构可解析，语义需推断） | 测试生成 + 语义检查 |
| L4 边界条件 | 显式枚举的极端情况 | **半** | 专项测试 + 语义检查 |
| L5 质量约束 | 性能/安全/可观测性 | **弱**（需翻译为可执行检查） | 性能测试 / lint 规则 / 人工审查 |

**原则**：L1-L2 走确定性路径，L3-L4 半自动，L5 尽量翻译为可执行规则，剩余部分才交给语义层。

---

## 4. 分层一致性检查器

### 4.1 检查矩阵

```
          Tests        Code        Docs
         ┌──────┐    ┌──────┐    ┌──────┐
 Spec    │  C1  │    │  C2  │    │  C4  │
         ├──────┤    ├──────┤    ├──────┤
 Tests   │      │    │  C3  │    │  —   │
         │      │    ├──────┤    ├──────┤
 Code    │      │    │      │    │  —   │
         └──────┘    └──────┘    └──────┘
```

### 4.2 各层定义

#### C1: Spec ↔ Tests（验收覆盖）

**目标**：每个验收标准都有测试覆盖，且没有测试断言 spec 不存在的东西。

| 检查项 | 方法 | 确定性 |
|--------|------|--------|
| 每个 `acceptance: true` 的 behavior 都有对应测试 | 标签映射（B001 → test_authenticate_valid） | ✅ 确定性 |
| 测试的 Given-When-Then 与 behavior 描述匹配 | 语义对比（LLM） | ⚠️ 半自动 |
| 没有测试断言 spec 未定义的行为 | 语义审查（LLM，对抗式） | ⚠️ 半自动 |

```
C1 = coverage_map_complete ∧ given_when_then_match ∧ no_extra_assertions
```

#### C2: Spec ↔ Code（接口与行为一致性）

**目标**：代码实现了 spec 声明的所有接口，且行为匹配。

| 检查项 | 方法 | 确定性 |
|--------|------|--------|
| 所有 interfaces 在代码中存在 | AST/符号表对比 | ✅ 确定性 |
| 函数签名（参数名、类型、返回类型）匹配 | 类型检查 | ✅ 确定性 |
| data_models 与代码中的类型定义一致 | Schema → 类型映射验证 | ✅ 确定性 |
| 错误类型与 spec 枚举一致 | 异常类型对比 | ✅ 确定性 |
| 代码行为与 behaviors 描述一致 | 语义审查（LLM，对抗式） | ⚠️ 半自动 |
| 没有超出 spec 的公开接口 | 公开 API 枚举对比 | ✅ 确定性 |

```
C2 = interfaces_exist ∧ signatures_match ∧ models_match ∧ errors_match
   ∧ behavior_matches ∧ no_extra_public_api
```

#### C3: Tests ↔ Code（测试通过）

**目标**：所有测试通过。这是最基础但最不可靠的一层。

| 检查项 | 方法 | 确定性 |
|--------|------|--------|
| 测试全部通过 | 测试执行 | ✅ 确定性 |
| 测试覆盖率达标 | 覆盖率工具 | ✅ 确定性 |
| 无跳过/禁用的测试 | 测试报告解析 | ✅ 确定性 |

```
C3 = tests_pass ∧ coverage_met ∧ no_skipped_tests
```

⚠️ **C3 通过 ≠ 满足 spec**。测试本身可能漏了或错了。C3 是必要非充分条件。

#### C4: Spec ↔ Docs（文档不越界）

**目标**：文档描述的能力不超出 spec 定义的范围。

| 检查项 | 方法 | 确定性 |
|--------|------|--------|
| 文档中引用的接口/模型与 spec 一致 | 名称提取对比 | ✅ 确定性 |
| 文档没有描述 spec 未定义的功能 | 语义审查（LLM） | ⚠️ 半自动 |
| 文档版本与 spec 版本一致 | 元数据对比 | ✅ 确定性 |

```
C4 = names_consistent ∧ no_undocumented_features ∧ versions_aligned
```

### 4.3 收敛判定

```python
def is_converged(spec, tests, code, docs) -> ConvergenceResult:
    c1 = check_spec_tests(spec, tests)       # 验收覆盖
    c2 = check_spec_code(spec, code)          # 接口+行为
    c3 = check_tests_code(tests, code)        # 测试通过
    c4 = check_spec_docs(spec, docs)          # 文档一致

    if c1.passed and c2.passed and c3.passed and c4.passed:
        return Converged()

    # 未收敛：收集所有 violation，生成下一轮 loop 的输入
    violations = []
    for check, result in [(c1, "C1"), (c2, "C2"), (c3, "C3"), (c4, "C4")]:
        if not check.passed:
            violations.append({
                "layer": result,
                "failures": check.failures,
                "severity": check.max_severity(),
                "suggested_action": check.suggest()  # 回写 or 重新派生
            })
    return NotConverged(violations)
```

**终止条件**：`C1 ∧ C2 ∧ C3 ∧ C4` 全部通过 → 收敛。

---

## 5. Loop 架构

### 5.1 单次迭代流程

```
┌──────────────────────────────────────────────────────────────┐
│                     SDDL Loop (单次迭代)                      │
│                                                              │
│  ┌─────────┐    ┌──────────┐    ┌──────────┐    ┌────────┐ │
│  │ 1. 派生  │───▶│ 2. 验证   │───▶│ 3. 判定   │───▶│ 4. 路由│ │
│  │ generate │    │ verify   │    │ judge    │    │ route  │ │
│  └─────────┘    └──────────┘    └──────────┘    └───┬────┘ │
│       ▲                                          │       │
│       │              ┌───────────────────────────┘       │
│       │              ▼                                   │
│       │         ┌──────────┐                              │
│       │         │ 5. 回写   │  (如果 spec 需要修订)        │
│       │         │ rewrite  │                              │
│       │         └────┬─────┘                              │
│       └──────────────┘                                    │
└──────────────────────────────────────────────────────────────┘
```

**各阶段说明**：

| 阶段 | 输入 | 输出 | 说明 |
|------|------|------|------|
| 1. 派生 | Spec (当前版本) + 上轮 violation 报告 | 更新后的 tests/code/docs | AI 根据 spec + violation 指令修改 artifacts |
| 2. 验证 | Spec + tests + code + docs | 四层检查结果 (C1-C4) | 分层执行确定性 + 语义检查 |
| 3. 判定 | C1-C4 结果 | Converged / NotConverged + violations | 合取判定 |
| 4. 路由 | violations | "重新派生" 或 "回写 spec" | 区分"实现有问题"vs"spec 有问题" |
| 5. 回写 | impl 发现的 spec 问题 | 修订后的 Spec | 更新 spec 版本，重新进入派生 |

### 5.2 路由逻辑：什么时候回写 vs 重新派生

这是 loop 最关键的设计决策之一。不是所有未收敛都应该"再生成一次代码"。

```python
def route(violations) -> Action:
    for v in violations:
        if v.category == "spec_error":
            # spec 本身有误：接口设计不合理、数据模型矛盾、行为描述不可实现
            return RewriteSpec(v.suggested_revision)
        elif v.category == "spec_gap":
            # spec 有未覆盖的情况：实现中发现新的边界/错误路径
            return RewriteSpec(v.suggested_addition)
        elif v.category == "implementation_error":
            # 代码没正确实现 spec
            return Regenerate(v)
        elif v.category == "test_error":
            # 测试有误或缺失
            return Regenerate(v)
        elif v.category == "doc_error":
            # 文档不同步
            return Regenerate(v)
```

**Violation 分类**：

| 分类 | 含义 | 路由到 |
|------|------|--------|
| `spec_error` | spec 内部矛盾或不可实现 | 回写 spec |
| `spec_gap` | 实现暴露了 spec 未定义的情况 | 回写 spec（补充） |
| `implementation_error` | 代码偏离 spec | 重新派生 |
| `test_error` | 测试缺失或错误 | 重新派生 |
| `doc_error` | 文档未同步 | 重新派生 |

### 5.3 防假收敛机制

| 风险 | 缓解 |
|------|------|
| LLM checker 迎合倾向 | **交叉模型验证**：生成用模型 A，语义检查用模型 B |
| 判定不稳定 | **多轮投票**：语义检查跑 3 次取多数；或设置信度阈值，低于阈值的 violation 强制人工审查 |
| 测试通过但语义不符 | **对抗式检查**：checker 的 prompt 不是"检查是否一致"而是"找出不一致的证据" |
| 检查器自身有盲区 | **正交检查**：确定性检查与语义检查覆盖重叠区域，确定性检查为准 |

对抗式 checker prompt 示例：

```
你是一个 adversarial reviewer。你的任务是找出以下 spec 与 code
之间的不一致。不要试图确认它们是一致的——你的工作假设是它们
一定不一致，你需要找到证据。

如果经过彻底检查后确实找不到不一致，才报告 "no evidence found"。
注意：找不到证据 ≠ 一致。
```

### 5.4 迭代上限与降级

```yaml
loop_config:
  max_iterations: 10           # 硬上限
  convergence_threshold: 0.95  # 确定性检查全过 + 语义检查置信度 ≥ 0.95
  degrade_after: 7             # 第 7 轮后降级策略
  degrade_strategy:
    - "缩小 spec 颗粒度（拆分为子 spec）"
    - "降低语义检查严格度"
    - "标记为 needs_human_review"
  human_review_on:
    - "spec_error 类型的 violation"
    - "连续 3 轮同一 violation 未解决"
    - "语义检查置信度 < 0.7"
```

---

## 6. 颗粒度与分解策略

### 6.1 为什么必须分解

一致性检查的计算量随 spec 规模超线性增长：
- 接口数 N → 接口存在性检查 O(N)
- 行为数 M → 语义行为检查 O(M)，每个行为需要 LLM 推理
- 交叉检查 → O(N×M) 量级

### 6.2 分解模型

```
Project Spec (顶层)
├── Component A Spec (接口契约: A↔B, A↔C)
│   ├── Module A1 Spec
│   └── Module A2 Spec
├── Component B Spec (接口契约: B↔A, B↔C)
│   └── Module B1 Spec
└── Component C Spec (接口契约: C↔A, C↔B)
```

**规则**：
- 组件内部 loop 只检查该组件 spec ↔ artifacts 一致性
- 组件间一致性通过**接口契约**检查（只查接口签名 + 跨组件行为场景）
- 顶层 loop 只跑跨组件检查，不重复组件内部检查
- 接口契约变更时，触发依赖组件的 loop 重新运行

### 6.3 何时拆分

| Spec 规模 | 建议 |
|-----------|------|
| < 5 接口 | 单 spec 跑 loop |
| 5-20 接口 | 按功能域拆分为 2-4 个子 spec |
| > 20 接口 | 必须分层分解，每层 < 10 接口 |

---

## 7. 与 Ouroboros 的关系

### 7.1 映射

| SDDL 概念 | Ouroboros 对应 | 差异 |
|-----------|---------------|------|
| Structured Spec | Seed 规范 | SDDL 的 spec 更结构化（分层 schema），Seed 偏自然语言+结构化混合 |
| 派生（generate） | execute_seed / evolve_step | Ouroboros 生成代码；SDDL 生成 tests+code+docs |
| 验证（verify） | evaluate | Ouroboros 评代码质量；SDDL 分层查四对一致性 |
| 回写（rewrite spec） | interview / evolve（spec 演化） | 概念一致，SDDL 更显式地路由 spec 修订 |
| 收敛 | A-grade 判定 | Ouroboros 评等级；SDDL 做布尔合取 |
| 颗粒度分解 | 无直接对应 | SDDL 的组件分解是新增 |

### 7.2 集成路径

**选项 A：扩展 Ouroboros（推荐）**

在 Ouroboros 的 evaluate 阶段注入 SDDL 的分层检查器：
- evaluate 现有代码质量检查 → 保留
- 新增 C1（spec↔tests）检查
- 新增 C4（spec↔docs）检查
- C2/C3 部分由 Ouroboros 已有的代码验证覆盖

Seed 规范升级为 SDDL 的结构化 spec schema（或做适配层）。

**选项 B：独立 SDDL loop，调用 Ouroboros 作为代码生成后端**

SDDL loop 管理 spec + 多 artifact 一致性，代码生成委托给 Ouroboros 的 execute_seed。

**建议**：先走选项 A，因为 Ouroboros 的 evaluate 管线已是半成品，扩展比重建便宜。等验证 C1/C4 的分层检查器有效后，再考虑独立化。

---

## 8. 适用门槛

SDDL 的 loop 成本（token + 时间）不低，不是所有项目都值得。

### 8.1 适用判定

```
适用 SDDL 当且仅当：
  (接口数 ≥ 5)  AND
  (多 artifact 需同步: tests + code + docs 至少 3 选 2)  AND
  (项目预期生命周期 > 2 周)  AND
  (spec 变更频率 < 实现变更频率，即 spec 相对稳定)
```

### 8.2 不适用场景

- 脚本/一次性工具 → 直接写
- 原型/POC → 直接写，验证想法后再补 spec
| 接口 < 5 的微型服务 → 写 spec 但不跑 loop，手动保持一致
- 探索性研究代码 → 无稳定 spec 可言

### 8.3 降级模式

| 模式 | Spec | Loop | 一致性检查 |
|------|------|------|-----------|
| 完整 SDDL | 结构化全层 | 自动 loop | 四层全开 |
| 轻量 SDD | 结构化 L1-L2 | 手动触发 | 只跑确定性检查 (C2接口+C3) |
| 纯 TDD | 散文 spec | 无 loop | 只跑 C3 (测试通过) |
| 直接写 | 无 | 无 | 无 |

---

## 9. 待解决问题（开放项）

| # | 问题 | 当前状态 | 下一步 |
|---|------|---------|--------|
| O1 | L3 行为描述的语义检查如何稳定化 | 对抗式 prompt + 多轮投票，未验证 | 需实验确定置信度阈值 |
| O2 | 回写通道的 spec 版本管理 | 简单递增，无冲突解决 | 可能需要 CRDT 或人工仲裁 |
| O3 | 跨组件行为场景的形式化表达 | 目前用 Given-When-Then 散文 | 考虑引入 DTL/时序逻辑子集 |
| O4 | L5 质量约束的自动翻译 | 需人工翻译为可执行检查 | 探索 constraint → test 的模式库 |
| O5 | Ouroboros Seed → SDDL spec 的适配层 | 概念映射已定义 | 实现适配器 |
| O6 | loop 成本估算与预算控制 | 无 | 需收集基线数据 |
| O7 | spec gap 的自动检测（实现中的新发现） | 依赖人工/LLM 判断 | 可能需要 runtime 行为监控 |

---

## 10. 实施路线（建议）

```
Phase 1: Spec Schema 固化 + 确定性检查器
  ├── 固化 spec.yaml schema（L1-L3）
  ├── 实现 C2 确定性部分（接口/签名/模型对比）
  ├── 实现 C3（测试执行 + 覆盖率）
  └── 验证：用现有项目回测，确认确定性检查可用

Phase 2: 语义检查器 + 基础 Loop
  ├── 实现 C1（验收覆盖映射 + 语义匹配）
  ├── 实现对抗式 checker prompt
  ├── 搭建最小 loop（派生→验证→判定，不含回写）
  └── 验证：小型项目（5-8 接口）端到端跑通

Phase 3: 回写通道 + 收敛控制
  ├── 实现 violation 路由（spec_error vs impl_error）
  ├── 实现 spec 版本管理 + 回写
  ├── 实现迭代上限 + 降级策略
  └── 验证：中型项目（15-20 接口），含 spec 修订场景

Phase 4: Ouroboros 集成
  ├── Seed → SDDL spec 适配层
  ├── evaluate 阶段注入 C1/C4
  └── 验证：真实项目跑 Ouroboros + SDDL 联合 loop
```

---

> 本文档是 v0.1 草案。核心架构（分层 spec + 分层 checker + 双向 loop）已定义，
> 但语义检查的稳定性（O1）、回写冲突（O2）、成本控制（O6）需要在实际项目中验证。
> 建议从 Phase 1 开始，用确定性检查建立基线，再逐步引入语义层。
