---
name: sddl
description: "Spec-Driven Development Loop：以结构化 Spec 为单一事实来源，双 Loop（形成 Loop 需求→冻结 Spec，派生 Loop Spec→tests/code/docs）驱动开发。Use when 用户要开始新项目开发、用 AI 写代码、规划系统设计、做需求分析、写测试、写文档、或任何需要"先定义清楚再动手"的开发任务。分阶段命令：/sddl:init /sddl:interview /sddl:spec /sddl:confirm /sddl:freeze /sddl:derive /sddl:verify /sddl:archive。"
version: 1.0.0
author: 小智
license: MIT
metadata:
  hermes:
    tags: [sdd, spec-driven, development-workflow, ai-coding, quality, formation-loop]
    related_skills: [writing-plans, test-driven-development, hermes-agent-skill-authoring]
---

# Spec-Driven Development Loop (SDDL)

> **已开源**：https://github.com/xt-mahh/sddl (2026-08-06, MIT License)
> 完整方法论 + 检查器脚本 + 示例项目见 GitHub 仓库。

## Overview

SDDL 把 AI 编程从"对话驱动"升级为"规格驱动"。核心承诺：**先定义清楚做什么，再动手写代码**——以结构化 Spec 为单一事实来源，双 Loop 闭环保证质量和可审计性。

```
形成 Loop（回答"做什么"）       派生 Loop（回答"怎么做对"）
需求 ──▶ 访谈 ──▶ Spec草稿 ──▶ 冻结 Spec ──▶ tests/code/docs ──▶ 收敛
              └─▶ SQC质量检查 ──┘                  └─▶ C1-C4一致性检查 ─┘
              └─▶ 决策点确认 ──┘
```

**为什么用 SDDL**：对话式编程的痛点——上下文漂移（聊 50 轮忘了第 3 轮的约定）、多 artifact 不同步（代码改了测试/文档没跟上）、验收主观化（"感觉对了"代替"符合规格"）。SDDL 用**稳定可全文加载的 Spec** + **分层一致性检查**解决三者。

## When to Use

**触发**：
- 用户要开始新项目开发、写核心功能、设计系统架构
- 用户说"先规划""先设计""先写规格""这个功能怎么做"
- 用户需要多个 artifact（代码+测试+文档）同步产出的任务
- 项目接口 ≥ 5 个，或 must 级验收 ≥ 5 个，预期生命周期 > 2 周

**不适用（直接写代码，不要用本 skill）**：
- 一次性脚本 / 原型 / POC / 探索性研究代码
- 单文件小工具（接口 < 5，无多 artifact 需求）
- 用户明确说"直接写""快速做"

**分阶段命令**（本 skill 的核心交互方式）：

| 命令 | 阶段 | 做什么 | 产出 |
|------|------|--------|------|
| `/sddl:init` | 初始化 | 建目录结构、读已有代码/需求 | `sddl/` 骨架 + `state.yaml` |
| `/sddl:interview` | 形成 | 分层需求访谈（L0-L2 必答） | 需求陈述 |
| `/sddl:spec` | 形成 | 生成 L1-L5 spec 草稿 + 决策点标记 | `specs/<domain>/spec.yaml` |
| `/sddl:confirm` | 形成 | 决策点摘要 clarify 确认 | `decisions/<domain>-confirmation.yaml` |
| `/sddl:freeze` | 形成 | SQC 检查 + 冻结 | `spec_status: frozen` |
| `/sddl:derive` | 派生 | 从 spec 派生 tests/code/docs | `src/ tests/ docs/` |
| `/sddl:verify` | 派生 | C1-C4 一致性检查 + 收敛判定 | `checks/*.json` + 收敛/路由 |
| `/sddl:archive` | 归档 | 变更归档、spec 合并 | `specs/` 更新 + CHANGELOG |

## 核心原则

1. **Spec 是神谕，但可被质疑**：派生中发现的 spec 缺陷 → 解冻 → 回形成 Loop 修订 → 重新冻结（走完整质量门禁，不绕过）
2. **确定性优先**：能用静态分析/schema/测试执行解决的，绝不用 LLM 猜
3. **收敛是工程系统**：硬条件门禁 + 软条件共识率 + 预算约束 + 人工兜底
4. **决策点不静默**：模糊处 AI 给默认值 + 标记决策点，用户确认后才冻结
5. **进度即目录**：阶段完成 = 文件存在（Convention over Config），中断恢复免费

## 目录即状态（Convention over Config）

**不看状态文件，看目录就知道进度**。这是本 skill 的进度可见性机制（配合 git commit 作为 checkpoint）。

```
<project>/
├── sddl/
│   ├── specs/                    # 存在 = 访谈完成，spec 已生成
│   │   └── <domain>/spec.yaml    # status: frozen = 冻结完成
│   ├── changes/                  # 变更提案（增量开发，可并行）
│   ├── decisions/                # 决策点确认记录
│   │   └── <domain>-confirmation.yaml
│   ├── checks/                   # 检查报告存档（机器可读 JSON）
│   │   ├── sqc-<domain>-v1.json
│   │   └── c1-c4-<domain>-v1.json
│   └── state.yaml                # 唯一元数据：阶段指针 + 预算 + 最近检查
├── src/                          # 派生 Loop 后出现
├── tests/                        # 派生 Loop 后出现
├── docs/                         # 派生 Loop 后出现（含 current/planned 分区）
└── (git commit 在每个阶段完成时)
```

**state.yaml 最小化**（只存指针，不存进度详情）：
```yaml
spec_status: frozen          # interviewing | drafting | reviewing | frozen | evolved
current_phase: derivation    # formation | derivation | complete
budget: { formation: 40%, implementation: 12%, revision: 100% }
last_check: { type: sqc, spec: auth-v0.1.0, result: pass, at: 2026-08-06T16:00 }
```

**恢复规则**：skill 重新加载时扫目录——`specs/` 无 = 从 interview 开始；`specs/` 有但无 decisions/ = 从 confirm 开始；`decisions/` 有但 spec 未 frozen = 从 freeze 开始；`src/` 有但无 checks/ = 从 derive 开始；`checks/` 有 = 从 verify 开始。

**阶段完成 = git commit**（E 辅助）：每个命令成功结束后 commit（`feat(sddl): interview complete`），保证可回溯。

## 双 Loop 流程编排

### 形成 Loop（做对的事）——5 个命令

```
/sddl:interview → /sddl:spec → /sddl:confirm → /sddl:freeze
     │              │              │              │
     └─ 修订 ──────┴──────┴──────┘
       （SQC 不过 / 用户改决策点 → 回上一步，最多 5 轮）
```

| 命令 | 关键动作 | 检查点 |
|------|---------|--------|
| interview | 分层提问 L0-L2（≤10 问必答），产出需求陈述 | 需求陈述完整 |
| spec | 生成 L1-L5 spec + 决策点标记（模糊处登记 DP） | SQC-def 骨架通过 |
| confirm | 决策点摘要 → clarify 逐项确认（含自定义输入） | 决策点无 pending |
| freeze | SQC 全检 + 确认记录签署 | SQC 无 blocker + frozen |

### 派生 Loop（把事做对）——3 个命令

```
/sddl:derive → /sddl:verify → (收敛) → 完成
     │              │
     └─ 路由 ───────┘
       （violation → 重派 code/tests/docs 或 解冻回形成 Loop）
```

| 命令 | 关键动作 | 检查点 |
|------|---------|--------|
| derive | 从 spec 派生 tests/code/docs | artifacts 可运行 |
| verify | C1-C4 分层检查 + 收敛判定 | 硬门禁 + 软共识 + must 覆盖 |
| archive | 变更归档、spec 合并 | CHANGELOG + spec 更新 |

## 检查器脚本（scripts/）——确定性证据，不是语义判断

**脚本只负责确定性证据**（类型检查/测试执行/符号表/YAML），**语义审核由 agent 的 LLM 能力执行**：

```bash
# SQC 确定性检查（形成 Loop 门禁）—— 脚本给出事实
python3 scripts/check_sqc.py sddl/specs/<domain>/spec.yaml --verbose

# C1-C4 确定性检查（派生 Loop 门禁）—— 脚本给出事实
python3 scripts/check_c1_c4.py . --verbose

# 状态恢复（中断后）—— 扫目录输出当前进度 + 下一步命令
python3 scripts/sddl_status.py .
```

- 退出码：0 = pass/converged，1 = fail（可挂 CI）
- `--json` 输出机器可读证据（供 LLM 审核引用）

**分工原则（重要）**：

| 层 | 谁负责 |
|----|--------|
| 确定性证据（硬条件）：schema 合法/接口存在/测试通过/符号表 | **脚本** |
| 语义审核（软条件）：行为覆盖/THEN 可断言/测试真覆盖/文档真实性 | **agent 的 LLM**（见 `references/llm-review.md`） |

**不要用脚本启发式做语义判断**——字符串匹配会假阴性爆炸（T1 实测 C1-sem 0.48）。脚本是证据收集器，agent 是裁判。

## 何时读哪个 Reference

按需加载，不一次全读（渐进披露）：

| 场景 | 读 |
|------|-----|
| 执行 interview | `references/formation-loop.md`（阶段 1） |
| 生成 spec | `references/spec-schema.md` + `templates/spec-template.yaml` |
| SQC 检查 | `references/sqc-checklist.md`（def 用脚本，sem 用 LLM） |
| 决策点确认 | `templates/decision-summary.md` |
| 派生 artifacts | `references/derivation-loop.md`（阶段 1-2） |
| C1-C4 检查 | `references/checker-matrix.md`（def 用脚本，sem 用 LLM） |
| **语义审核操作** | **`references/llm-review.md`（核心：LLM 如何做审核）** |
| 路由/回写/预算 | `references/derivation-loop.md`（阶段 3-5） |
| 变更提案 | `references/formation-loop.md`（变更管理） |

## 预算与降级

- 三预算：formation（2M token / 5 轮）/ implementation（15M / 4 sessions）/ revision（5M，L2 扣 10%、L3 扣 25%、首次 L3 免费）
- 预算记录在 state.yaml，每命令更新
- 预算耗尽 → 转人工驱动，不自动降级（spec 质量是地基）
- 降级路径：D1 语义降级 → D2 should/could 移风险清单 → D3 缩变异 → D4 拆 spec → D5 最佳努力交付

## 体验规范（重要）

1. **分阶段命令**：绝不在一个回复里跑完整个双 Loop——每个命令是独立交互单元，之间有检查点
2. **决策点用 clarify，自定义输入显式可见**：每个决策点一个 clarify，附影响说明；**choices 业务选项 ≤3 个，第 4 位固定放"自定义输入（Other）"**（实测 clarify 无自动 Other、choices 上限 4，必须显式占位）；question 文本提示"其他值请选自定义输入"；用户自定义值走捕获协议（记录 value+reason → 同步 spec → 确认记录标 modified）；开放式决策点直接用无 choices 的 clarify
3. **进度可见**：每个命令开始/结束时报告当前阶段 + 下一步
4. **状态写入**：每个命令结束写 state.yaml + git commit
5. **检查报告**：每次检查（SQC/C1-C4）写 `checks/*.json`，报告可读摘要 + 机器可读详情

## Common Pitfalls

1. **跳过形成 Loop 直接派生**——Spec 没冻结就写代码 = 回到对话式编程。`/sddl:freeze` 是硬边界，未冻结不派生。
2. **决策点静默决定**——模糊处不标记 DP 直接写默认值 = 用户意图失真。任何"替用户选择"必须登记 DP。
3. **检查器自证循环**——信任 AI 贴的标签。C1-def 必须做结构反推（解析测试 AST），不信任标签。
4. **语义检查绝对分数**——LLM 打 0-100 分不可信。用 Checklist 二分 + 投票共识率（客观计票）。
5. **回写绕过质量门禁**——spec_error 直接改 spec = 自我放松标准。必须解冻 → 回形成 Loop → 重新冻结。
6. **状态文件膨胀**——把所有进度写进 state.yaml = 又回到"文档谎言"。state.yaml 只存指针，详情在文件本身。
7. **预算无记录**——不更新 state.yaml 预算 = 成本失控。每命令结束更新。
8. **语义检查用粗糙字符串匹配**——T1 实测：关键词匹配把 C1-sem 打到 0.48（假阴性爆炸）。优先用 Checklist LLM 投票；启发式仅作 fallback，且必须语义化（AST 提取断言 + 结构化关键词），首轮结果不可信，需人工复核。
9. **测试间共享状态泄漏**——T1 实测：内存 store 跨测试共享导致断言失败。派生时必须加隔离 fixture（autouse 重置）；测试断言走公开接口，不直接访问内部 `_store`。
10. **纯查询函数带副作用**——T1 实测：`detectDiscrepancy` 内部改 status 违反 spec B006（应保持 draft）。纯查询接口（返回报告/查询）不得修改状态，C2-sem 应检查。

## Verification Checklist

- [ ] `sddl/` 目录结构正确（specs/changes/decisions/checks/state.yaml）
- [ ] spec.yaml 通过 SQC-def（schema 合法/引用完整/可断言性/决策点覆盖）
- [ ] 决策点全部 confirmed/modified/delegated（无 pending）
- [ ] 确认记录签署（overall: approved）
- [ ] spec_status: frozen 后才进入派生
- [ ] C1-def 做了结构反推（非信任标签）
- [ ] 硬条件（C1-def/C2-def/C3/C4b-def）全过
- [ ] 软条件共识率达标（c1_sem≥0.95 c2_sem≥0.95 c4a≥0.90 c4b_sem≥0.90）
- [ ] must 级验收覆盖 100%
- [ ] state.yaml 预算已更新
- [ ] 阶段完成 git commit 已打

## One-Shot Recipes

### 从零开始新项目
```
/sddl:init → /sddl:interview → /sddl:spec → /sddl:confirm → /sddl:freeze
           → /sddl:derive → /sddl:verify → /sddl:archive
```

### 已有代码回填 spec（改造项目）
```
/sddl:init（读已有代码）→ /sddl:spec（反向提取现状 + 标记决策点）
  → /sddl:confirm → /sddl:freeze → /sddl:verify（验证 spec↔code 一致性）
```

### 增量功能开发（spec 已冻结）
```
/sddl:init → 写 changes/<name>/ 提案 → /sddl:confirm（受影响决策点）
  → /sddl:freeze → /sddl:derive → /sddl:verify → /sddl:archive
```

## 相关 Skill

- `writing-plans`：写实施计划（SDDL 的 changes/tasks.md 可用它）
- `test-driven-development`：TDD 是 SDDL 的验证手段（C3 测试执行）
- `hermes-agent-skill-authoring`：本 skill 自身的创作规范
