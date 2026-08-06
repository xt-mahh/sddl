# Spec-Driven Development Loop（SDDL）最终方案 v1.1

> **版本**：1.1（最终版）| 2026-08-06
> **性质**：自包含独立文档，不依赖任何外部方案文件
> **v1.1 变更**：新增**形成 Loop**（需求→冻结 Spec）——补上 v1.0 的最大盲区：
> spec 的**形成机制**（谁生成、质量怎么验证、与用户意图的一致性怎么保证）。
> v1.0 的派生 Loop（Spec→artifacts）全部保留，本版是双 Loop 完整架构。

---

## 1. 背景与目标

### 1.1 问题定义

AI 编程时代的核心痛点：

| 痛点 | 本质 | 后果 |
|------|------|------|
| 上下文漂移 | 对话越长，AI 越易遗忘早期约定 | 第 N 轮推翻第 3 轮的接口约定 |
| 多 artifact 不同步 | 代码改了，测试/文档没跟上 | "文档谎言"被 AI 时代放大 |
| 验收主观化 | "感觉对了"代替"符合规格" | 无法审计、无法复现、无法交接 |
| **需求失真（v1.1 新增）** | **spec 形成无机制，AI 默认"自己会写对"** | **产出一致地实现错误需求的完美系统** |

第四个痛点正是本版要解决的：**C1-C4 检查器验证的是"artifacts 符合 spec"，但 spec 是否符合用户真实意图，v1.0 没有任何机制验证。** 如果 spec 写错了，派生产物会一致地实现错误需求，检查全绿、收敛通过——完美实现的错误系统。

### 1.2 目标

构建**双 Loop 闭环系统**：
1. **形成 Loop**：模糊需求 → 结构化 Spec（经过质量检查 + 意图确认，可冻结）
2. **派生 Loop**：冻结 Spec → tests/code/docs（经过分层一致性检查，可收敛）

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
6. **Spec 必须可证明地对齐用户意图（v1.1）**：形成机制包含质量检查（spec 自身可测、完整、一致）与意图确认（关键决策点由用户裁决），spec 冻结前必须完成两者。

---

## 2. 双 Loop 架构总览

```
┌─────────────────────────────────────────────────────────────────────┐
│                   形成 Loop（需求 → 冻结 Spec）                        │
│                                                                     │
│  模糊需求 ──▶ 1.需求访谈 ──▶ 2.Spec草稿生成 ──▶ 3.Spec质量检查(SQC)    │
│     ▲                        （含决策点标记）      │                 │
│     │                        │                    ▼                 │
│     │                        │            4.意图确认（决策点摘要）      │
│     │                        │                    │                 │
│     │                        │             5.冻结（SQC全过+确认签署）  │
│     └────────────────────────┴────────────────────┼─────────────────┘
│              （SQC/确认未过 → 修订 → 重检）        ▼                  │
│                                           冻结 Spec                  │
└───────────────────────────────────────────────┬─────────────────────┘
                                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Spec Store（单一事实来源）                          │
│  ┌──────────────────────────────┐  ┌─────────────────────────────┐   │
│  │ specs/（当前真相，已冻结/演进）  │◄─│ changes/（增量提案，未批准）  │   │
│  └──────────────┬───────────────┘  └──────────────┬──────────────┘   │
│                 │ archive（归档合并）               │                  │
└─────────────────┼──────────────────────────────────┼─────────────────┘
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

**两个 Loop 的职责边界**：
- **形成 Loop**：回答"做什么"（spec 是否正确、完整、可测、对齐意图）——结果：冻结 Spec
- **派生 Loop**：回答"怎么做对"（artifacts 是否符合 spec）——结果：收敛 + Convergence Report

**两个 Loop 的输入输出**：形成 Loop 的产物（冻结 Spec）是派生 Loop 的唯一输入；派生 Loop 发现的 spec 缺陷（spec_error/spec_gap）通过回写通道**解冻** spec，回到形成 Loop 的修订流程。

---

## 3. 形成 Loop（v1.1 新增，核心）

### 3.1 阶段总览

```
┌──────────────────────────────────────────────────────────────┐
│  1.需求访谈     需求澄清、场景挖掘、边界询问、优先级排序        │
│      │                                                      │
│  2.Spec 草稿    L1-L5 spec 生成 + 决策点标记                  │
│      │                                                      │
│  3.SQC 质量检查 可测试性/完整性/一致性/引用/冲突检测            │
│      │  （SQC-def 确定性 + SQC-sem 语义，复用投票机制）        │
│      ▼                                                      │
│  4.意图确认     决策点摘要 → 用户逐项确认/修改 → 确认记录       │
│      │                                                      │
│  5.冻结         SQC 无 blocker + 决策点全部确认 + 用户签署     │
│      │                                                      │
│      ▼                                                      │
│  冻结 Spec（派生 Loop 的输入）                                │
└──────────────────────────────────────────────────────────────┘
  未过 → 返回对应阶段修订（记录修订次数，超限转人工）
```

### 3.2 阶段 1：需求访谈（Interview）

**目的**：把模糊需求转化为结构化需求陈述，为 spec 草稿提供输入。

**方法**（借鉴 Ouroboros interview，分层提问防疲劳）：

| 层 | 问题类型 | 示例 | 必答 |
|----|---------|------|------|
| L0 目标 | 做什么、为谁、解决什么问题 | "这个系统给谁用？核心价值？" | 是 |
| L1 场景 | 主流程、异常、边界 | "最核心的用户操作？出错时？" | 是 |
| L2 约束 | 环境、性能、安全、兼容 | "部署环境？并发量级？" | 是 |
| L3 细节 | 按需深入（只在前面有答案后问） | "密码规则？token 有效期？" | 否（视情况） |

**产出**：结构化需求陈述（目标、角色、场景清单、约束清单、优先级初步排序）。

**防访谈疲劳**：L0-L2 必答（≤10 问），L3 只问与场景直接相关的。用户可随时说"你看着办"——未答细节标记为 `deferred`，由 AI 在草稿阶段做默认决策并标记为决策点（见 3.3），交用户在意图确认阶段裁决。

### 3.3 阶段 2：Spec 草稿生成（Draft）

**目的**：需求陈述 → L1-L5 结构化 spec 草稿。

**关键设计：决策点标记（Decision Points）**

AI 生成 spec 时，凡是在需求陈述中没有明确、需要替用户做选择的地方，**必须标记为决策点**，不静默决定：

```yaml
decision_points:        # spec 顶层的决策点登记
  - id: "DP-001"
    topic: "token 有效期"
    default: "7 天"                 # AI 的默认建议
    alternatives: ["1 天", "30 天", "7 天"]
    rationale: "平衡安全与体验；会话类应用常用 7 天"
    category: "contract"            # contract | behavior | constraint | implementation
    requires_confirmation: true
    status: "pending"               # pending | confirmed | modified | delegated
```

**决策点分类**：

| 类别 | 含义 | 确认要求 |
|------|------|---------|
| contract | 接口签名、数据模型字段、错误类型 | **必须确认**（改契约影响最大） |
| behavior | 场景的 GIVEN/WHEN/THEN、优先级 | **必须确认** |
| constraint | 非目标、边界、质量约束 | **必须确认** |
| implementation | 技术选型、性能阈值、内部结构 | 可授权 AI 决定（`delegated`） |

**规则**：
- 决策点不得内嵌在 spec 正文里静默存在——必须在 `decision_points` 登记，正文引用（如 `then: "返回 AuthResult，expires_in 按 DP-001"`）
- 需求陈述中明确的 → 直接写入，不标记
- 需求陈述中模糊/缺失的 → 默认决策 + 标记决策点
- 草稿生成后，决策点清单本身要过 SQC 的覆盖度检查（防止 AI 漏标记关键选择）

### 3.4 阶段 3：Spec 质量检查（SQC, Spec Quality Check）

**目的**：验证 spec **自身**的质量（不是 artifacts 与 spec 的一致性——那是派生 Loop 的事）。

**SQC 检查项**：

| 检查 | 性质 | 内容 |
|------|------|------|
| SQC-def-1 schema 合法 | 硬 | YAML 结构合法、必填字段齐全、类型正确 |
| SQC-def-2 引用完整 | 硬 | behaviors 引用的 interface/model/错误类型都存在；non_goals 不与 interfaces 冲突 |
| SQC-def-3 可断言性 | 硬 | THEN 子句无模糊词（见下方清单）；GIVEN 无不可构造的前置 |
| SQC-def-4 决策点登记 | 硬 | 正文中所有"需用户选择"处都有对应决策点；决策点字段完整 |
| SQC-sem-1 行为覆盖 | 软 | happy path + 主要错误路径 + 边界是否都有行为场景；优先级分配是否合理（must 不能全是 happy path） |
| SQC-sem-2 行为矛盾 | 软 | 行为间 GIVEN/THEN 是否有冲突（如 B001 说"返回 200"，B002 说"同条件下返回 400"） |
| SQC-sem-3 完整性缺口 | 软 | 是否存在需求陈述提及但 spec 未覆盖的场景 |
| SQC-sem-4 可测性判定 | 软 | THEN 是否可转化为具体断言（"响应快速"→ 不可测，需量化） |

**模糊词清单（SQC-def-3 用，正则匹配）**：
```
"成功" "正常" "正确" "尽快" "快速" "高效" "友好" "合理"
"适当" "必要时" "等" "等等" "其他" "相关" "相应" "尽可能"
"大概" "大约" "左右" "一些" "若干" "部分" "某些"
```
命中 → 警告 + 要求量化或具体化（"返回成功" → "返回 AuthResult 且 HTTP 200"）。

**SQC 与派生 Loop 检查器的关系**：
- 检查对象不同：SQC 查 spec 自身；C1-C4 查 artifacts vs spec
- 机制复用：SQC-def 走确定性规则；SQC-sem 复用 Checklist 判定 + 分层投票 + 复核（见 §6）
- **SQC 是形成 Loop 的门禁，C1-C4 是派生 Loop 的门禁，互不替代**

**SQC 输出**：violation 列表（复用 §11 机器可读格式，layer 为 `sqc_def` / `sqc_sem`）。

### 3.5 阶段 4：意图确认（Intent Confirmation）

**目的**：保证 spec 与用户真实意图一致。**这是唯一无法自动化的环节**——只能靠人工确认，但必须设计得高效、可审计。

**核心机制：决策点摘要（Decision Summary）**

不让用户读完整 spec（50 个行为场景没人读完），而是把决策点提炼成**可快速裁决的问题列表**：

```
┌─────────────────────────────────────────────────────┐
│  Spec 意图确认清单（auth-service v0.1.0）              │
│                                                     │
│  【契约类】必须确认                                   │
│  □ DP-001 token 有效期：建议 7 天（备选 1/30 天）     │
│      → 若选 7 天：用户 7 天后需重新登录                │
│  □ DP-002 错误次数上限：建议 5 次/60 秒               │
│      → 若选 3 次：更安全但误锁风险高                   │
│  【行为类】必须确认                                   │
│  □ DP-003 记住我：默认不勾选                         │
│      → 若默认勾选：安全审计可能不通过                  │
│  【约束类】必须确认                                   │
│  □ DP-004 非目标：不做密码找回（由 user-service 提供） │
│  【实现类】可授权                                    │
│  □ DP-005 JWT 签名算法：建议 RS256（已授权 AI 决定）   │
│                                                     │
│  操作：逐项选择 确认 / 修改 / 授权 AI                  │
│  全部处理后 → 签署确认记录                            │
└─────────────────────────────────────────────────────┘
```

**设计要点**：
- 每个决策点附**影响说明**（"若选 X 则 Y"），让用户有判断依据
- contract/behavior/constraint 类默认要求确认；implementation 类可授权
- 用户可整体授权（"实现类全部授权"），减少操作量
- **关键决策点（contract 类）禁止默认接受**——必须显式选择

**产出：确认记录（Confirmation Record）**——意图一致性的证据链：
```yaml
confirmation_record:
  spec_version: "0.1.0"
  confirmed_by: "用户"                  # 或用户 ID
  confirmed_at: "2026-08-06T16:00:00Z"
  decisions:
    - { id: "DP-001", result: "confirmed", value: "7 天" }
    - { id: "DP-002", result: "modified", value: "3 次", reason: "银行系统更保守" }
    - { id: "DP-005", result: "delegated", value: "AI 决定" }
  overall: "approved"
```

### 3.6 阶段 5：冻结（Freeze）

**冻结条件（全部满足）**：
1. SQC 无 blocker 级 violation（SQC-def 全过 + SQC-sem 无 blocker）
2. 决策点全部处理（confirmed / modified / delegated，无 pending）
3. 用户签署确认记录（overall: approved）
4. 确认记录与 spec 版本绑定（spec 再改 → 确认记录作废 → 重走受影响的决策点）

**冻结后**：
- spec 状态 → `frozen`，成为派生 Loop 的输入
- 变更走 changes/ 提案制（见 §4）
- 冻结即锁定：派生 Loop 期间 spec 不可静默修改

### 3.7 形成 Loop 的迭代与收敛

```
未过 SQC（spec 质量问题）→ 返回阶段 2 修订 spec 草稿 → 重跑 SQC
用户修改决策点 → 返回阶段 2 修订 → 重新生成决策点摘要（只列受影响的）
修订次数记录：每轮记入 CHANGELOG
迭代上限：形成 Loop 最多 5 轮；超限 → 转人工（人工直接改 spec 或终止）
```

**形成 Loop 收敛 = 冻结条件满足**。不满足 → 持续迭代（有上限 + 人工兜底）。

### 3.8 形成 Loop 的坑与对策

| 坑 | 对策 |
|----|------|
| 访谈疲劳（问题太多） | 分层提问（L0-L2 必答 ≤10 问），L3 按需 |
| 决策点遗漏（AI 静默决定关键选择） | 决策点覆盖度检查（SQC-def-4） |
| 确认仪式化（用户无脑点"是"） | 决策点附影响说明；contract 类禁止默认接受 |
| 过度确认（实现细节也来确认） | 决策点分类，implementation 类可授权 |
| 冻结过早（spec 质量未达标） | 冻结条件明确（SQC 全过 + 决策点处理完 + 签署） |
| 冻结过晚（形成 Loop 空转） | 迭代上限 5 轮 + 人工兜底 |

---

## 4. Spec Store 与变更管理

### 4.1 双区制

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

### 4.2 Spec 生命周期状态机（v1.1 明确）

```
draft ──▶ reviewing ──▶ frozen ──▶ evolved ──▶ frozen（重新冻结）
  ▲          │            │            ▲
  └──────────┴────────────┴────────────┘
    （形成 Loop 内迭代）   （变更提案归档后回到 frozen）
```

| 状态 | 含义 | 进入条件 |
|------|------|---------|
| draft | 形成 Loop 中（访谈/草稿） | 项目启动 |
| reviewing | SQC + 意图确认中 | 草稿生成 |
| frozen | 派生 Loop 的输入，锁定 | SQC 全过 + 决策点确认 + 签署 |
| evolved | 变更提案已归档，spec 已更新 | changes/ 归档（L2/L3 修订） |
| frozen（重新） | 新版本冻结 | 重新走 SQC + 受影响决策点确认 |

### 4.3 修订分级

| 级别 | 定义 | 触发重派生 | 需人工审批 |
|------|------|-----------|-----------|
| L1 澄清性 | 不改契约，只补语义（措辞、边界细化） | 否（只更新 docs/注释） | 否 |
| L2 增量 | 改契约但兼容（加可选参数、加错误类型、加行为） | 是（受影响 artifacts 局部重派） | 是（提案制） |
| L3 破坏性 | 改契约且不兼容（删接口、改签名、改数据模型） | 是（全量重派） | **必须** |

**v1.1 补充**：L2/L3 修订归档后，**受影响决策点必须重新确认**（确认记录作废受影响项），spec 回到 reviewing 走一遍轻量确认（只重列受影响决策点），再重新冻结。

### 4.4 STALE 失效管理

L2/L3 修订归档时自动执行：
1. 影响面分析（见 §8.3）确定受影响 artifacts
2. 标记受影响 artifacts 为 `STALE`（过期，禁止交付）
3. 触发重新派生（局部或全量）
4. 新 artifacts 验证通过后才解除 STALE

### 4.5 ping-pong 检测

同一领域连续 N=3 轮内发生 ≥3 次往返修订（spec→impl→spec）→ 冻结该领域，标记 `needs_human_review`，不再自动往返。

### 4.6 审计追踪

每次修订生成 `CHANGELOG.md`：改了什么（diff）、为什么改（触发 violation 原文）、谁改的、影响面、**是否触发决策点重确认**。**回写通道永不静默**——任何 spec 修订都是可见的变更提案。

---

## 5. Spec Schema（v1.1）

### 5.1 分层定义

| 层 | 内容 | 机器可消费性 | 检查方法 |
|----|------|------------|---------|
| L1 接口契约 | 函数签名、参数、返回、错误类型 | 完全 | 静态类型检查 / AST 对比 |
| L2 数据模型 | JSON Schema / 类型定义 | 完全 | Schema 验证器 |
| L3 行为描述 | GWT 场景 + 优先级 | 半（结构可解析） | 测试生成 + Checklist 语义检查 |
| L4 边界条件 | 显式枚举的极端情况 + 优先级 | 半 | 专项测试 + Checklist |
| L5 质量约束 | 性能/安全/可观测性 | 弱 | 翻译为可执行规则；性能类标注 env |

### 5.2 字段结构

```yaml
meta:
  id: "auth-service"
  version: "0.1.0"
  domain: "auth"
  status: "reviewing"           # draft | reviewing | frozen | evolved
  dependencies: ["user-model@>=1.0"]
  confirmation_record_ref: "changes/auth-v0.1.0/confirmation.md"

non_goals:            # 非目标：防 scope creep，checker 可检测越界
  - "本服务不负责用户注册"

decision_points:      # v1.1 新增：决策点登记（意图确认的输入）
  - id: "DP-001"
    topic: "token 有效期"
    default: "7 天"
    alternatives: ["1 天", "30 天", "7 天"]
    rationale: "平衡安全与体验"
    category: "contract"
    requires_confirmation: true
    status: "pending"           # pending | confirmed | modified | delegated

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
    then: ["...", "..."]       # 可引用决策点: "expires_in 按 DP-001"
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

### 5.3 优先级与收敛的关系

- `must`：硬性，未覆盖阻塞收敛
- `should`：软性，未覆盖不阻塞，进风险清单
- `could`：不阻塞，仅记录
- `wont`：显式排除（等价 non_goals）

---

## 6. 分层一致性检查器（派生 Loop，v1.0 完整保留）

### 6.1 检查矩阵

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

### 6.2 硬条件检查

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

### 6.3 软条件：Checklist 语义检查

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

## 7. 收敛判定

### 7.1 形成 Loop 收敛（v1.1）

**收敛条件**（§3.6 冻结条件）：
```
SQC-def 全过
SQC-sem 无 blocker
决策点全部处理（无 pending）
用户签署确认记录（overall: approved）
```

### 7.2 派生 Loop 收敛

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

**阈值与校准**：0.95/0.90、独立性相关度 0.6、证据缺失率 20%、ping-pong N=3 均为**初值**。用 golden set（已知正确/错误样本 ≥10 对）校准：记录各阈值下的假阳性/假阴性率，调至无假阳性（宁可漏报不可误报），校准记录写入 checker 配置。

**Convergence Report（收敛证明文件）**，分两节：
- `deterministic_evidence`：可重跑（含命令 + 输入哈希）
- `semantic_evidence`：可审计不可复现（记录模型/温度/seed/判定项集版本/投票原始记录）

---

## 8. 路由与回写

### 8.1 三层混合判定路由

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

### 8.2 路由矩阵

| 分类 | 触发条件 | 动作 | 需人工 |
|------|---------|------|--------|
| spec_error | spec 内部矛盾/不可实现 | 回写（L2/L3 修订）→ 解冻 → 形成 Loop 修订 | 是（必须） |
| spec_gap | 实现暴露未定义情况 | 回写（L2 补充）→ 解冻 → 受影响决策点重确认 | 是（提案制） |
| implementation_error | 代码偏离 spec | 重派 code | 否 |
| test_error | 测试缺失/错误 | 重派 tests | 否 |
| doc_error | 文档不同步 | 重派 docs | 否 |

**v1.1 关键变化**：spec_error/spec_gap 的路由不再是"直接改 spec"，而是**解冻 spec → 回到形成 Loop 的修订流程**（SQC + 受影响决策点重确认 + 重新冻结）。保证"改 spec"永远走完整质量门禁，不因回写通道绕过形成 Loop 的检查。

**关键原则**：改 spec 永远比改代码重（提案 + SQC + 决策点确认 + 审批 + 归档）。防止 loop 自我放松标准。

### 8.3 影响面分析

变更类型驱动的静态引用分析：

| 变更元素 | 受影响集合 |
|---------|-----------|
| interface | 所有调用方代码 + 该接口测试 + 文档引用 |
| model | 所有读写该模型的代码 + 测试 fixture + 文档 |
| behavior | 该行为的测试（标签追踪辅助）+ 文档引用 |
| boundary | 该边界的测试 |

规则：接口/模型变更走引用图精确局部重派；引用图分析不到的保守标记 STALE（宁多勿漏）；L3 全量重派不依赖影响面分析。

---

## 9. 成本模型

### 9.1 双预算制

```
budget:
  formation:                     # 形成 Loop 预算（v1.1 新增）
    total_token: 2M
    max_iterations: 5            # 形成 Loop 迭代上限
    decision_summary_max: 15     # 决策点摘要上限（防决策点爆炸）
  implementation:                # 实现预算（派生 Loop 正常迭代）
    total_token: 15M
    max_sessions: 4
  revision:                      # 修订预算（spec 质量成本，单列）
    total_token: 5M
    L2_revision_cost: 0.10       # 每次 L2 修订消耗修订预算 10%
    L3_revision_cost: 0.25       # 每次 L3 修订消耗修订预算 25%
    first_L3_free: true          # 首次 L3 修订免费
```

**激励设计**：修订预算单列 + 首次免费 → loop 诚实报告 spec_error 无成本代价，消除"误分类 spec_error 为 implementation_error 以逃避扣预算"的激励扭曲。修订不是惩罚，是质量成本。

### 9.2 止损与降级（量化）

```
派生 Loop 预算/轮数耗尽时的降级路径（按顺序）：
  D1: 语义检查降级（快筛 1 模型，投票只在 must 级跑）      [省 ~60% 语义成本]
  D2: 缩小收敛目标（must 不变，should/could 移入风险清单） [省 ~30% 派生成本]
  D3: 缩小变异测试范围（只跑 P0 验收）                     [省 ~70% 变异成本]
  D4: 拆分 spec（按领域拆，每领域独立 loop）               [线性化成本]
  D5: 交付"最优可行解 + 已知 violation 清单"（最佳努力态）

形成 Loop 预算耗尽：转人工驱动（人工直接改 spec 或终止），不自动降级——
  因为 spec 质量是地基，降级形成 Loop 等于在错误地基上盖楼。
```

**must 覆盖优先于一切**：预算耗尽 + must 未全覆盖 → 不自动降级，转人工（人工决定：加预算 / 降 must / 接受风险）。D2 只对 should/could 生效。

每次降级生成 Degradation Report（原因、达成度、未达成项）。

---

## 10. Checker 可信度保障

checker 的错误是 silent 的（不会表现为测试失败），因此：

1. **meta-testing**：`tests/checker/` 含已知 spec/test/code 对，检查器必须判对（good/bad fixtures 各 ≥10 个）；checker 改动后 golden set 通过率 100% 才可发布。
2. **golden set 覆盖两类**（v1.1）：派生 Loop 的 C1-C4 + **形成 Loop 的 SQC**（SQC 也需要 known-good/known-bad 的 spec 样本）。
3. **独立性矩阵**：见 §6.3（在 golden set 上计算模型错误相关度）。
4. **置信度标注**：确定性检查置信度 = 1.0；语义检查输出投票记录 + 共识率。
5. **已知限制清单**：每个 checker 模块声明能力边界（如"结构反推只支持 Python/Go 常见断言模式"）。

---

## 11. 机器可读 Violation 格式

```json
{
  "schema_version": "1.1",
  "loop": "formation | derivation",     // v1.1：标明来源 loop
  "loop_round": 3,
  "spec_version": "0.1.2",
  "violations": [{
    "id": "V-3-001",
    "layer": "c1_def | sqc_sem | ...",  // v1.1：含 sqc_def/sqc_sem
    "severity": "blocker",
    "category": "test_error | spec_error | sqc_quality | ...",
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

## 12. 组件分解与跨组件检查

- 组件内部 loop 只查本组件 spec ↔ artifacts
- 组件间通过**接口契约**检查（签名 + 跨组件行为场景）
- 跨组件验收标准带 `cross_component: true`，生成集成测试（`tests/integration/`），顶层 loop 验证
- 跨组件测试失败责任定位：先 C2-def 查接口签名，再 C2-sem 查行为语义
- 集成测试分层：L1 接口级契约测试（确定性）→ L2 行为级场景测试（执行验证）→ L3 环境级（性能/并发，不进 loop）

**v1.1 补充**：组件 spec 的接口契约变化必须**跨组件通知**——组件 A 的接口变更，组件 B 的 spec 中引用该接口的 decision point / behavior 要重新确认。影响面分析（§8.3）需覆盖跨组件引用。

---

## 13. 人工审查回流

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
  affected_decision_points: [...]     # v1.1：标记需重确认的决策点
```

回流：approve → 归档解除 STALE；reject → 生成 violation 反馈进路由；modify_spec → 触发修订流程（含决策点重确认）。人工确认的假阳性 → checker 校准库（few-shot 范例持续校准）。

---

## 14. 适用门槛与降级模式

### 14.1 模式选择

| 模式 | Spec | 形成 Loop | 派生 Loop | 成本 |
|------|------|----------|----------|------|
| 完整 SDDL | 双区制 + 决策点 | 完整（访谈+SQC+确认） | 硬+软+变异 | 高 |
| 标准 SDDL | 单 spec + 决策点 | 轻量（SQC-def + 决策点摘要） | 硬+软（无变异） | 中 |
| 轻量 SDD | 单 spec（L1-L2） | 无 SQC，只决策点摘要 | 只硬条件 | 低 |
| 纯 TDD | 无 | 无 | 只 C3 | 最低 |

### 14.2 门槛判定

```
完整 SDDL：接口 ≥ 8 且 must 验收 ≥ 10 且多 artifact 同步 且 项目 > 4 周 且 spec 相对稳定
标准 SDDL：接口 5-8 或 must 验收 5-10
轻量 SDD：接口 < 5 但多 artifact
否则：纯 TDD 或直接写
```

**v1.1 补充**：**形成 Loop 的必要性判断**——即使不跑完整 SDDL，任何 AI 编程项目都建议至少做"决策点摘要确认"（让用户确认关键选择），这是防止"完美实现错误需求"的最低成本手段。

**不适用**：一次性脚本、原型/POC、探索性研究代码。

---

## 15. 实施路线（v1.1 更新）

```
Phase 0: 形成 Loop 最小闭环（v1.1 前置，因为 spec 质量是地基）
  ├── 需求访谈模板（分层提问）
  ├── 决策点标记 + 决策点摘要生成器
  ├── SQC-def（schema 合法/引用完整/可断言性/决策点覆盖）
  └── 确认记录生成 + 冻结状态机
Phase 1: 确定性检查器（派生 Loop）
  ├── C2-def / C3 / C4b-def / C1-def L1+L2
  ├── checker meta-testing（golden set，含 SQC golden set）
Phase 2: 语义检查器 + 基础 Loop
  ├── Checklist 判定项生成器 + 双重校验（SQC-sem 与 C1-sem/C2-sem 复用）
  ├── 分层投票（快筛→投票→复核）+ 独立性矩阵
  ├── 收敛判定（形成/派生分开）+ golden set 校准阈值
  ├── 基础派生 loop（派生→验证→判定，不含回写）
  └── Convergence Report
Phase 3: 回写通道 + 路由 + 成本控制
  ├── 三层混合判定路由 + 解冻机制（spec_error → 形成 Loop 修订）
  ├── 影响面分析（含跨组件引用）
  ├── 双预算 + 修订衰减 + 降级路径
  ├── 人工审查回流（结构化模板）
  └── 多变更并行冲突测试
Phase 4: 变异测试 + 集成
  ├── C1-def L3 变异验证（守卫条件）
  ├── 跨组件契约测试
  ├── Ouroboros 集成（interview/seed → 形成 Loop，evaluate → 派生 Loop 检查）
  └── CI 集成（violation JSON 消费）
```

---

## 16. 开放问题与验证项

| # | 问题 | 状态 | 验证方式 |
|---|------|------|---------|
| O1 | 语义检查稳定性 | 机制已定（分层投票+独立性+双重校验） | golden set 校准实验 |
| O2 | 回写冲突解决 | 双区制 + 修订分级 + 解冻机制 | 多变更并行测试 |
| O3 | 跨组件行为形式化 | 契约测试 + 分层 + 跨组件重确认 | 实践验证 |
| O4 | L5 质量约束自动翻译 | 移出 loop + env 标记 | 约束→测试模式库 |
| O5 | Ouroboros 适配层 | interview/seed→形成，evaluate→派生 | Phase 4 实现 |
| O6 | 成本基线 | 三预算（形成/实现/修订） | 收集真实数据 |
| O7 | spec gap 自动检测 | 路由层已定义 | runtime 监控实验 |
| O8 | 变异测试实际开销 | must_only + 守卫 | Phase 4 评估 |
| O9 | 多变更并行冲突 | changes/ 支持 | Phase 3 测试 |
| O10 | 判定项模板判别力 | 双重校验 + golden set | 验证 |
| O11 | 决策点提炼质量 | SQC-def-4 覆盖度检查 | golden set 验证 |
| O12 | 意图确认的效率（决策点摘要 vs 全文阅读） | 机制已定义 | 用户实测反馈 |

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
| Ouroboros (Nous Research) | interview/seed（形成侧半成品）+ evaluate（派生侧） |

---

## 附录 B：完整 Spec 示例（auth 服务，含决策点）

```yaml
meta:
  id: "auth-service"
  version: "0.1.0"
  domain: "auth"
  status: "reviewing"
  dependencies: ["user-model@>=1.0"]

non_goals:
  - "本服务不负责用户注册"
  - "不支持多租户"
  - "不做密码找回（由 user-service 提供）"

decision_points:
  - id: "DP-001"
    topic: "token 有效期"
    default: "7 天"
    alternatives: ["1 天", "30 天", "7 天"]
    rationale: "平衡安全与体验；会话类应用常用 7 天"
    category: "contract"
    requires_confirmation: true
    status: "pending"
  - id: "DP-002"
    topic: "失败尝试上限"
    default: "5 次/60 秒"
    alternatives: ["3 次/60 秒", "5 次/60 秒", "10 次/5 分钟"]
    rationale: "防暴力破解与误锁的平衡"
    category: "behavior"
    requires_confirmation: true
    status: "pending"
  - id: "DP-003"
    topic: "JWT 签名算法"
    default: "RS256"
    alternatives: ["HS256", "RS256", "ES256"]
    rationale: "RS256 非对称，适合多服务验证"
    category: "implementation"
    requires_confirmation: false
    status: "pending"          # 意图确认时默认可授权

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
      - "expires_in 按 DP-001（默认 7 天）"
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
    given: "同一 IP 在 60 秒内连续失败 5 次（按 DP-002）"
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
    - "access_token 使用 RS256 签名（按 DP-003）"
  observability:
    - "每次 authenticate 调用记录 audit log（不含密码）"
```

## 附录 C：决策点摘要示例（意图确认清单）

```
┌─────────────────────────────────────────────────────┐
│  Spec 意图确认清单（auth-service v0.1.0）              │
│  共 3 个决策点，预计 3 分钟完成                         │
│                                                     │
│  【契约类】必须确认                                   │
│  □ DP-001 token 有效期：建议 7 天（备选 1/30 天）     │
│      → 若选 7 天：用户 7 天后需重新登录                │
│      → 若选 1 天：更安全但用户频繁重登                 │
│  【行为类】必须确认                                   │
│  □ DP-002 失败尝试上限：建议 5 次/60 秒               │
│      → 若选 3 次：更安全但误锁风险高                   │
│  【实现类】可授权（默认授权 AI）                       │
│  □ DP-003 JWT 签名算法：建议 RS256                   │
│      → 影响：多服务验证场景下的密钥管理方式             │
│                                                     │
│  操作：逐项选择 确认 / 修改 / 授权 AI                  │
│  全部处理后 → 签署确认记录，spec 冻结                  │
└─────────────────────────────────────────────────────┘
```

---

> **v1.1 最终方案一句话**：双 Loop 闭环——**形成 Loop**（需求→访谈→草稿→SQC 质量检查→决策点意图确认→冻结）保证"做对的事"，**派生 Loop**（冻结 Spec→tests/code/docs→C1-C4 分层检查→收敛）保证"把事做对"，回写通道让 spec 缺陷回到形成 Loop 走完整质量门禁。
