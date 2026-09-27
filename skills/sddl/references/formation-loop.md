# 形成 Loop 详细流程（Formation Loop）

> 回答"做什么"：模糊需求 → 冻结 Spec。本文件是 `/sddl:interview` `/sddl:spec` `/sddl:confirm` `/sddl:freeze` 四个命令的详细执行手册。

## 阶段 1：需求访谈（/sddl:interview）

### 目标
把模糊需求转化为结构化需求陈述，为 spec 草稿提供输入。

### 分层提问（防访谈疲劳）

| 层 | 问题类型 | 示例 | 必答 |
|----|---------|------|------|
| L0 目标 | 做什么、为谁、解决什么问题 | "这个系统给谁用？核心价值是什么？" | 是 |
| L1 场景 | 主流程、异常、边界 | "最核心的用户操作是什么？出错时怎么办？" | 是 |
| L2 约束 | 环境、性能、安全、兼容 | "部署环境？并发量级？安全要求？" | 是 |
| L3 细节 | 按需深入（前面有答案后才问） | "密码规则？token 有效期？" | 否 |

**规则**：
- L0-L2 必答，总问题数 ≤ 10（超过 10 个说明范围失控，提醒用户收窄）
- L3 只问与场景直接相关的
- 用户可随时说"你看着办"——未答细节标记为 `deferred`，AI 在草稿阶段做默认决策并标记决策点
- 访谈是**对话式**的，不是表单——用户回答时留意隐含信息（"我们要接入 XX 系统"暗示集成约束）

### 产出：需求陈述（写入 `sddl/requirements.md`）

```markdown
# 需求陈述
## 目标
- 给谁用：...
- 核心价值：...
## 角色
- ...
## 场景清单
- [ ] 主流程：...
- [ ] 异常：...
- [ ] 边界：...
## 约束清单
- 环境：...
- 性能：...
- 安全：...
## 优先级初步排序
- must: ...
- should: ...
- could: ...
## 未决细节（deferred）
- 密码规则（AI 默认：8-64 位含字母数字）
```

### 检查点
- [ ] L0-L2 都有答案
- [ ] 场景清单含主流程 + 至少一个异常 + 至少一个边界
- [ ] 未决细节已标记 deferred

---

## 阶段 2：Spec 草稿生成（/sddl:spec）

### 目标
需求陈述 → L1-L5 结构化 spec 草稿 + 决策点标记。

### 决策点标记（关键！）

**凡是需求陈述中没有明确、需要替用户做选择的地方，必须标记为决策点，不静默决定。**

```yaml
decision_points:
  - id: "DP-001"
    topic: "token 有效期"
    default: "7 天"                 # AI 的默认建议
    alternatives: ["1 天", "30 天", "7 天"]
    rationale: "平衡安全与体验；会话类应用常用 7 天"
    category: "contract"            # contract | behavior | constraint | implementation
    requires_confirmation: true
    status: "pending"               # pending | confirmed | modified | delegated
```

**决策点分类与确认要求**：

| 类别 | 含义 | 确认要求 |
|------|------|---------|
| contract | 接口签名、数据模型字段、错误类型 | **必须确认**（改契约影响最大） |
| behavior | 场景的 GIVEN/WHEN/THEN、优先级 | **必须确认** |
| constraint | 非目标、边界、质量约束 | **必须确认** |
| implementation | 技术选型、性能阈值、内部结构 | 可授权 AI（`delegated`） |

**规则**：
- 需求陈述中明确的 → 直接写入，不标记
- 需求陈述中模糊/缺失的 → 默认决策 + 标记决策点
- 决策点不得内嵌在 spec 正文静默存在——必须在 `decision_points` 登记，正文引用（`then: "expires_in 按 DP-001"`）
- 决策点数量控制：单领域 ≤ 15 个（超过说明 spec 粒度太大，考虑拆分）

### Spec 结构

读 `references/spec-schema.md` 获取五层结构 + 完整示例；用 `templates/spec-template.yaml` 做骨架。

### 产出：`sddl/specs/<domain>/spec.yaml`

### 检查点（SQC-def 骨架）
- [ ] YAML 合法，必填字段齐全
- [ ] behaviors 引用的 interface/model/错误类型都存在
- [ ] THEN 子句无模糊词（"成功""正常""快速"等——见 sqc-checklist.md 模糊词清单）
- [ ] 决策点全部登记（无静默决定）

---

## 阶段 3：决策点确认（/sddl:confirm）

### 目标
让用户确认/修改/授权所有决策点，保证 spec 与真实意图一致。

### 交互方式：clarify 逐项确认

**每个决策点一个 clarify 调用**。自定义输入是**显式设计**，且受工具约束（choices 上限 4，无自动 Other——实测确认）：

```
clarify question: "DP-001 token 有效期：建议 7 天（影响：用户 7 天后需重新登录）。
  其他值（如 30 天）请选『自定义输入』并输入。"
choices:
  - "确认 7 天"                    # 业务选项 ≤3 个
  - "1 天（更安全但频繁重登）"
  - "自定义输入（Other）"           # ← 第 4 位固定为自定义输入，显式可见
```

**choices 结构铁律**：
- **业务选项 ≤3 个**（确认/备选合并计算），第 4 位固定为 `自定义输入（Other）`
- 备选超过 2 个时：合并同类项，或把次要备选写进 question 文本（"其他值如 30 天请自定义输入"）
- 绝不让业务选项占满 4 位把自定义项挤掉

**自定义输入四要素（必须全部落实）**：

1. **question 含提示**：每个 clarify 的 question 末尾附"其他值/其他情况请选『自定义输入』并输入"
2. **choices 第 4 位固定自定义项**：`自定义输入（Other）` 永远在可见位置（不依赖工具自动 Other，实测工具不自动附加）
3. **捕获协议**：用户输入自定义值 → 记录 value + reason（用户原话）→ 同步回 spec 对应字段 → 确认记录标记 `result: modified`（不是 confirmed）
4. **兜底**：若决策点本身是开放式（无法预设选项），直接用**开放式 clarify（无 choices）**，自定义输入天然可达

**分类处理**：
- contract/behavior/constraint 类：**必须逐项 clarify**，禁止默认接受
- implementation 类：**批量授权**（一次 clarify："实现类决策点全部授权 AI 决定？" 是/否，choices 同样第 4 位放自定义）
- 用户选择"自定义输入（Other）" → 走捕获协议（见上）

### 决策点摘要（开场）

确认前先展示摘要（templates/decision-summary.md），让用户有全局观：

```
┌─────────────────────────────────────────────────────┐
│  Spec 意图确认清单（auth-service v0.1.0）              │
│  共 5 个决策点：契约 2 / 行为 2 / 实现 1                 │
│  预计 5 分钟完成                                       │
└─────────────────────────────────────────────────────┘
```

### 产出：`sddl/decisions/<domain>-confirmation.yaml`

```yaml
confirmation_record:
  spec_version: "0.1.0"
  confirmed_by: "用户"
  confirmed_at: "2026-08-06T16:00:00Z"
  decisions:
    - { id: "DP-001", result: "confirmed", value: "7 天" }
    - { id: "DP-002", result: "modified", value: "3 次", reason: "银行系统更保守" }
    - { id: "DP-005", result: "delegated", value: "AI 决定" }
  overall: "approved"
```

### 检查点
- [ ] 所有决策点无 pending（confirmed / modified / delegated）
- [ ] modified 的决策点已同步回 spec
- [ ] 确认记录与 spec 版本绑定

---

## 阶段 4：冻结（/sddl:freeze）

### 目标
SQC 全检 + 确认记录签署 → spec 冻结 → 派生 Loop 开始。

### 冻结条件（全部满足）
1. SQC 无 blocker 级 violation（SQC-def 全过 + SQC-sem 无 blocker）
2. 决策点全部处理（无 pending）
3. 用户签署确认记录（overall: approved）
4. 确认记录与 spec 版本绑定

### 执行
1. 跑 SQC 全检（见 `references/sqc-checklist.md`）→ 写 `checks/sqc-<domain>-v1.json`
2. 检查决策点状态
3. 更新 `specs/<domain>/spec.yaml` 的 `meta.status: frozen`
4. 更新 `state.yaml`：`spec_status: frozen`、`current_phase: derivation`
5. git commit：`feat(sddl): freeze <domain> spec vX.Y.Z`

### 冻结后
- spec 成为派生 Loop 的唯一输入
- 变更走 changes/ 提案制（见下文"变更管理"）
- **冻结即锁定**：派生 Loop 期间 spec 不可静默修改

---

## 变更管理（spec 已冻结后的修改）

### 修订分级

| 级别 | 定义 | 触发重派生 | 需人工审批 |
|------|------|-----------|-----------|
| L1 澄清性 | 不改契约，只补语义（措辞、边界细化） | 否（只更新 docs/注释） | 否 |
| L2 增量 | 改契约但兼容（加可选参数、加错误类型、加行为） | 是（受影响 artifacts 局部重派） | 是（提案制） |
| L3 破坏性 | 改契约且不兼容（删接口、改签名、改数据模型） | 是（全量重派） | **必须** |

### changes/ 提案制

```
sddl/changes/<change-name>/
├── proposal.md             # 意图 + 范围 + 理由
├── specs/<domain>/spec.yaml  # 增量 delta（ADDED/MODIFIED/REMOVED）
├── design.md               # 技术方案（大变更才有）
└── tasks.md                # 实施清单
```

生命周期：`propose → review（人工/AI 审）→ apply → verify → archive`
归档时：增量 delta 合并入 specs/ → 受影响 artifacts 标记 STALE → **按序重验架构**（check_arch + 受影响决策点 + 重冻 architecture.yaml）→ 触发重派生 → 受影响决策点重确认（L2/L3）→ 重新冻结。

### ping-pong 检测

同一领域连续 3 轮内 ≥3 次往返修订（spec→impl→spec）→ 冻结该领域，标记 `needs_human_review`，不再自动往返。

### STALE 标记

L2/L3 修订归档时：影响面分析（见 derivation-loop.md §3.3）确定受影响 artifacts → 标记 STALE（禁止交付）→ 重派 → 验证通过后解除。

### 审计

每次修订更新 `sddl/CHANGELOG.md`：改了什么（diff）、为什么改、谁改的、影响面、是否触发决策点重确认。**回写通道永不静默**。
