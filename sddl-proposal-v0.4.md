# Spec-Driven Development Loop (SDDL) 方案 v0.4

> 版本 0.4 | 2026-08-06 | 基于 Round 3 评审（M1-M9）+ 发散 + 搜索验证修订
>
> **变更摘要（vs v0.3）**：
> - 语义检查成本控制：分层投票（快筛→投票→复核）+ 缓存增量（修 M1）
> - 投票模型独立性：独立性矩阵 + golden 锚定 + 偏置降权（修 M2）
> - 判定项生成质量：双重校验 + 可验证性约束 + 判定项集版本化（修 M3/M9）
> - 预算激励修正：修订预算单列 + 首次修订免费（修 M4）
> - C4b 分区：docs 区分 current/planned（修 M5）
> - 投票"不确定"滥用：强制二分 + 证据缺失标注 + 不可靠检测（修 M6）
> - must 覆盖与预算冲突：must 优先 + 人工路径（修 M7）
> - 附录 B 同步字段（修 M8）
>
> **新增搜索证据**：
> - Ensemble Learning for Heterogeneous LLMs (arXiv 2404.xxxx)：异构 LLM 集成 → 异模型投票
> - Efficient Dynamic Ensembling (arXiv 2412.xxxx)：动态集成 → 分层投票
> - Ranked Voting Self-Consistency (arXiv 2505.xxxx)：排序投票 → 投票变体
> - Scoring/Reasoning/Selecting: LLM Peer-Review Ensemble (arXiv 2512.xxxx)：peer-review 集成 → 复核机制

---

## 0. 变更跟踪（v0.4 新增章节）

本方案自 v0.1 起已历 3 轮评审循环，每轮聚焦的问题与解法形成变更日志，供追溯。

| 版本 | 评审焦点 | 核心改进 |
|------|---------|---------|
| v0.1 | 初始草案 | 分层 spec + 分层 checker + 双向 loop |
| v0.2 | P0×4/P1×6/P2×6 | 硬/软分离 + 双区制 + 异模型对抗式 + 预算 + meta-testing |
| v0.3 | N1-N10 | Checklist 二分 + 多数投票 + 影响面分析 + 双预算 + C4b |
| v0.4 | M1-M9 | 分层投票成本控制 + 独立性矩阵 + 判定项质量 + 激励修正 |

---

## 1. 语义检查的投票机制（v0.4，修 M1/M2/M6）

### 1.1 分层投票（修 M1，成本控制）

**不再对全部判定项跑 3 模型投票**，改为三层漏斗：

```
┌─────────────────────────────────────────────────────────────┐
│  L0 快筛（1 模型，全量判定项）                                 │
│    - 模型：checker-model A                                   │
│    - 输出：每项 是/否/证据缺失                                │
│    - 成本：1× 判定项数                                        │
│    ↓                                                         │
│  L1 投票（3 模型，只投快筛"否"或低置信项）                      │
│    - 快筛判"是"的项：默认接受（信任快筛，不重投）               │
│    - 快筛判"否"或证据缺失的项：3 模型投票                     │
│    - 成本：3× 问题项数（通常 ≪ 判定项总数）                    │
│    ↓                                                         │
│  L2 复核（异模型确认，只投投票分裂项）                          │
│    - 投票一致项：采纳                                        │
│    - 投票分裂/不确定项：复核模型逐项确认                        │
│    - 成本：1× 分裂项数（通常更少）                             │
└─────────────────────────────────────────────────────────────┘
```

**成本对比**（20 行为 spec，120 判定项，假设 20% 问题项、5% 分裂项）：

| 方案 | 调用次数/轮 |
|------|-----------|
| v0.3 全量 3 模型投票 | 120×3 = 360 |
| v0.4 分层投票 | 120×1 + 24×3 + 6×1 = **198** |

**增量投票（缓存）**：上轮已共识的判定项（快筛"是"或投票一致）带版本哈希缓存，本轮 spec/code 变更未触及的项**不重投**。只重投变更影响的新判定项。

### 1.2 投票模型独立性（修 M2）

**模型独立性矩阵**（配置期建立）：

```
独立性矩阵（在 golden set 上计算）：
  模型对 (A,B) 的错误相关度 = P(两者同时错 | 至少一个错)
  相关度 > 0.6 → 标记"非独立"，避免同组投票
  
  示例：
  ┌─────┬─────┬─────┬─────┐
  │     │  A  │  B  │  C  │
  ├─────┼─────┼─────┼─────┤
  │  A  │  -  │ 0.2 │ 0.3 │
  │  B  │ 0.2 │  -  │ 0.7 │  ← B,C 高相关，不同组
  │  C  │ 0.3 │ 0.7 │  -  │
  └─────┴─────┴─────┴─────┘
  有效投票组：{A, B} + {A, C}（确保异质）
```

**golden 锚定投票**：每个判定项附带同类型 golden 样本（few-shot），模型先看锚定样本再投票。锚定样本的正确判定是已知的，作为校准参照。

**偏置降权**：模型在 golden set 上**某类判定项**（如 GIVEN 类）错误率 > 阈值时，该类判定项的该模型票权减半（仍投票，但权重低）。

**默认怀疑 + 硬条件兜底**：语义共识只在"确定性检查支持"的方向上采信。若语义判"否"但确定性检查支持实现存在，**以确定性为准**（semantic_only 不阻塞）。

### 1.3 判定项生成质量（修 M3）

**双重校验**：判定项生成器 A 产出 → 校验器 B（不同模型）检查覆盖度：
- 是否覆盖 behavior 的所有 THEN 子句、ERR、SIDE
- 是否遗漏可判定项
- 是否有"不可验证"的项（标注为 non-verifiable，移出判定集）

**可验证性约束**：每个判定项必须引用 behavior 的具体子句（B001-THEN-1），无引用的判定项无效（生成器必须输出引用，校验器检查引用存在）。

**判定项集版本化**（修 M9）：每轮 loop 开始时冻结判定项集（含版本号）。轮内不增删——新增问题 → 下轮新判定项集。共识率的分母固定，不可操纵。

---

## 2. 预算激励修正（v0.4，修 M4）

### 2.1 修订预算单列

**修订不是惩罚，是质量成本。** 修订预算与实现预算分离：

```
budget:
  implementation:                # 实现预算（loop 正常迭代）
    total_token: 15M
    max_sessions: 4
  revision:                      # 修订预算（spec 质量问题，单列）
    total_token: 5M
    L2_revision_cost: 0.10       # 每次 L2 修订消耗修订预算 10%
    L3_revision_cost: 0.25       # 每次 L3 修订消耗修订预算 25%
```

**核算规则**：
- L2/L3 修订消耗**修订预算**，不碰实现预算 → 消除"诚实发现 spec 问题被惩罚"的激励扭曲
- **首次 L3 修订免费**（spec 初始质量差不是 loop 的错，D-M4.3）：首次不消耗修订预算
- 修订预算耗尽 → 停止自动修订，转人工驱动（spec 修订必须人工）
- 实现预算耗尽 → 走降级路径 D1-D5，与修订预算无关

**激励分析**：loop 诚实报告 spec_error 不再有成本代价（修订预算单列 + 首次免费），反而推进了质量。误分类 spec_error 为 implementation_error 的动机消除。

### 2.2 must 覆盖与预算冲突（修 M7）

**must 覆盖优先于一切**：预算耗尽时若 must 未全覆盖 → 不自动降级，转人工。人工决定：加预算 / 降 must 级别 / 接受风险。

```
D2 降级只对 should/could 生效：
  预算耗尽 + must 全覆盖 → D1-D5 降级（should/could 移入风险清单）
  预算耗尽 + must 未全覆盖 → 人工路径（不自动降级）
```

---

## 3. C4b 分区检查（v0.4，修 M5）

### 3.1 docs 分区

```
docs/
├── current/          # 现状文档（描述已实现能力）
│   └── api.md        # 只描述 code 中存在的 API
└── planned/          # 规划文档（描述 roadmap，不查一致性）
    └── roadmap.md    # 未来的 API/能力
```

**C4b-def 只查 current 分区**。planned 分区不参与符号表对比。
**分区标注**：每个 docs 文件头声明 `status: current | planned`。无标注的默认按 current 处理（保守）。

---

## 4. 投票"不确定"滥用防护（v0.4，修 M6）

### 4.1 强制二分 + 证据缺失标注

```
投票选项：是 | 否 | 证据缺失
- "证据缺失" ≠ "不确定"：表示"此项无法从提供材料中判定"（可接受）
- 证据缺失项 → 进复核队列（LLM 复核，不是直接人工）
- 复核仍证据缺失 → 该项标记 non-verifiable，移出判定集（但不阻塞）
```

### 4.2 不可靠模型检测

```
模型在单轮中"证据缺失"率 > 20% → 标记不可靠，降权
模型在连续 2 轮中"证据缺失"率 > 20% → 从投票组移除，触发替补模型
```

---

## 5. 其余章节（v0.2/v0.3 保留）

以下章节与 v0.3 一致，不重复：
- Spec Store 双区制 + 修订分级 + STALE + ping-pong + 审计（§2）
- Spec Schema（§3，boundaries 含 priority）
- 硬条件检查器 C1-def/C2-def/C3/C4b-def（§4.1-4.2）
- 收敛判定框架（§4.4，阈值 golden set 校准）
- 路由三层混合判定 + 影响面分析（§5）
- 成本模型主体（§6，除修订预算调整见 §2）
- Checker meta-testing（§7）
- 机器可读 violation（§8）
- 组件分解（§9）
- 人工审查回流（§10）
- 适用门槛（§12）
- 实施路线（§13）
- 附录 A 证据链

---

## 6. 附录 B（v0.4 更新，修 M8）：完整 Spec 示例

```yaml
meta:
  id: "auth-service"
  version: "0.4.0"
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
    priority: "must"          # ← v0.4 确认保留

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

## 7. 待解决问题（v0.4 更新）

| # | 问题 | v0.4 状态 | 下一步 |
|---|------|----------|--------|
| O1 | 语义检查稳定性 | 分层投票 + 独立性矩阵 + 双重校验 | golden set 校准实验 |
| O2 | 回写冲突 | 双区制 + 修订分级 | 多变更并行测试 |
| O3 | 跨组件行为形式化 | 契约测试 + 分层 | 待实践验证 |
| O4 | L5 质量约束 | 移出 loop + env 标记 | 约束→测试模式库 |
| O5 | Ouroboros 适配 | 概念映射已定义 | Phase 4 |
| O6 | 成本基线 | 双预算 + 分层投票成本模型 | 收集真实数据 |
| O7 | spec gap 检测 | 路由层已定义 | runtime 监控实验 |
| O8 | 变异测试成本 | must_only + 守卫 | 评估实际开销 |
| O9 | 多变更并行冲突 | changes/ 支持 | 需测试 |
| O10 | 判定项模板判别力 | 双重校验 + golden set | 验证 |

---

> v0.4 核心改进一句话：**投票机制从"贵且可能被系统性偏置带偏"变成"分层且独立"**——
> 快筛→投票→复核三层漏斗 + 独立性矩阵 + golden 锚定 + 偏置降权，
> 修订预算单列消除激励扭曲，判定项集版本化保证计票不可操纵。
