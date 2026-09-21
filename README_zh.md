<div align="center">

# 🔄 SDDL — Spec-Driven Development Loop

**以结构化 Spec + 架构为单一事实来源的三 Loop 开发方法论（Agent Skill）**

> **语言切换：** [English](README.md) | [中文](README_zh.md)

> 让 AI 编程从"对话驱动"升级为"规格驱动"——先定义清楚做什么，再动手写代码。

![SDDL Logo](assets/logo.png)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![PyYAML](https://img.shields.io/badge/PyYAML-required-green.svg)](https://pyyaml.org/)
[![GitHub stars](https://img.shields.io/github/stars/xt-mahh/sddl)](https://github.com/xt-mahh/sddl)

*先定义清楚做什么，再动手写代码。*

</div>

---

## 目录

- [为什么需要 SDDL？](#为什么需要-sddl)
- [三 Loop 架构](#三-loop-架构)
- [核心特性](#核心特性)
- [快速开始](#快速开始)
- [Skill 结构](#skill-结构)
- [多平台支持](#多平台支持)
- [项目结构](#项目结构)
- [方法论核心](#方法论核心简述)
- [证据基础](#证据基础)
- [适用门槛](#适用门槛)
- [v1.x 迁移](#v1x-迁移)
- [License](#license)

## 为什么需要 SDDL？

AI 编程时代的四个核心痛点：

| 痛点 | 本质 | 后果 |
|------|------|------|
| **上下文漂移** | 对话越长，AI 越易遗忘早期约定 | 第 N 轮推翻第 3 轮的接口约定 |
| **多 artifact 不同步** | 代码改了，测试/文档没跟上 | "文档谎言"被 AI 时代放大 |
| **架构漂移** | AI 写代码时临场发明模块边界 | 复杂工程里 module 分工、目录结构无人守约 |
| **验收主观化** | "感觉对了"代替"符合规格" | 无法审计、无法复现、无法交接 |

对话式编程的问题在于：**上下文窗口有限，对话越长越容易漂移**。你跟 AI 聊了 50 轮，第 51 轮它已经忘了第 3 轮约定的接口格式；更糟的是，没有任何东西约束它"这个函数该放进哪个模块"。

**SDDL 的答案**：用稳定可全文加载的 Spec 做单一事实来源，用架构层钉死模块分工，用三 Loop 闭环保证质量和可审计性。

## 三 Loop 架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                   形成 Loop（回答"做什么"）                            │
│  需求 ──▶ 访谈 ──▶ Spec草稿 ──▶ SQC质量检查 ──▶ 决策点确认 ──▶ 冻结   │
└───────────────────────────────────────────────┬─────────────────────┘
                                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   架构 Loop（回答"怎么分层"）v2.0                      │
│  冻结 Specs ──▶ 模块划分 ──▶ C-arch检查 ──▶ 决策点确认 ──▶ 冻结架构   │
└───────────────────────────────────────────────┬─────────────────────┘
                                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   派生 Loop（回答"怎么做对"）                           │
│  双冻结 ──▶ tests/code/docs ──▶ C1-C4 + C-arch检查 ──▶ 收敛           │
│        ▲                                        │                    │
│        └──── spec缺陷 ──▶ 解冻回形成Loop ──▶ 重新冻结 ──┘             │
│        └──── 架构缺陷 ──▶ 解冻架构Loop（不动功能spec）──▶ 重冻 ──┘    │
└─────────────────────────────────────────────────────────────────────┘
```

- **形成 Loop**：保证"做对的事"——需求 → 访谈 → Spec 草稿（含决策点标记）→ SQC 质量检查 → 决策点人工确认 → 冻结
- **架构 Loop（v2.0 新增）**：保证"分层做对"——读冻结 specs 按职责内聚划分模块 → architecture.yaml（模块/依赖/目录/技术栈）→ C-arch 静态检查 + LLM 内聚复审 → 冻结
- **派生 Loop**：保证"把事做对"——双冻结（spec + architecture）→ tests/code/docs 三件套同步派生 → C1-C4 + C-arch 分层一致性检查 → 收敛
- **回写通道**：spec 缺陷 → 解冻回形成 Loop；架构缺陷 → 独立解冻架构（层次隔离，不连带功能 spec）；均不绕过质量门禁

## 核心特性

| 特性 | 说明 |
|------|------|
| **决策点机制** | 模糊处 AI 不静默决定，标记为决策点，用户用 clarify 逐项确认（含自定义输入） |
| **SQC 质量检查** | Spec 自身的质量门禁——**脚本确定性检查**（schema 合法/引用完整/可断言性）+ **agent LLM 语义审核**（行为覆盖/矛盾/完整性） |
| **架构 Loop（v2.0）** | 模块划分/依赖/目录/技术栈进入 `architecture.yaml`；C-arch 静态检查（所有权覆盖/import 图/目录落位）+ LLM 内聚复审；双冻结门禁 |
| **证据契约（v2.1）** | 确定性证据泛化到 Python 之外：参考收集器在非 Python 技术栈上**显式降级报错而非静默产出空证据**（空证据 = 假 pass）；agent 按 `references/evidence-contract.md` 构造项目级收集器——构造一次、git 固化、此后只重跑不重构 |
| **C1-C4 + C-arch 分层检查** | artifacts 与 spec+架构的一致性——**脚本确定性证据**（接口对比/测试执行/文档符号表/越界 import）+ **agent LLM 语义审核**（测试是否真覆盖行为？代码是否真符合 spec？模块职责是否内聚？） |
| **目录即状态** | 进度编码在目录结构里，中断恢复免费（配合 git commit 作为 checkpoint） |
| **预算控制** | 形成/架构/实现/修订预算，量化降级路径，修订激励不惩罚诚实 |
| **可审计** | 每个决策点确认记录、每次修订 CHANGELOG、每次检查报告 JSON，全程可追溯 |

## 快速开始（Agent 集成）

### 方式 A：安装为 Agent Skill（推荐）

本项目的核心交付是 **Agent Skill**（位于 [`integrations/`](integrations/)），装好后 agent 就有了 8 个分阶段命令：

```bash
# 1. 把 skill 装进 agent
# Hermes:
cp -r integrations/hermes ~/.hermes/skills/software-development/sddl

# 其他 agent（Claude Code / OpenCode / OpenClaw）：见下方「多平台支持」

# 2. 在对话中触发（自动加载，或显式命令）
/sddl:init        # 初始化项目（建目录结构）
/sddl:interview   # 分层需求访谈
/sddl:spec        # 生成 Spec 草稿 + 决策点标记
/sddl:confirm     # 决策点 clarify 确认（含自定义输入）
/sddl:freeze      # SQC 检查 + 冻结
/sddl:arch        # 生成架构 spec（模块划分/依赖/目录/技术栈）v2.0
/sddl:confirm     # 架构决策点确认
/sddl:freeze      # C-arch 检查 + 冻结架构
/sddl:derive      # 从 spec+架构派生 tests/code/docs
/sddl:verify      # C1-C4 + C-arch 一致性检查 + 收敛判定
/sddl:archive     # 变更归档
```

**完整工作流**：`/sddl:init → /sddl:interview → /sddl:spec → /sddl:confirm → /sddl:freeze → /sddl:arch → /sddl:confirm → /sddl:freeze → /sddl:derive → /sddl:verify → /sddl:archive`

### 方式 B：只用检查器脚本（无 agent 环境）

如果不用 Hermes，检查器脚本也可以独立运行（作为 CI 门禁或手动检查）：

```bash
pip install pyyaml

# SQC 检查（spec 冻结前）
python3 scripts/check_sqc.py sddl/specs/<domain>/spec.yaml --verbose

# C-arch 架构检查（架构冻结前 / verify 时）
python3 scripts/check_arch.py . --verbose                # 冻结前
python3 scripts/check_arch.py . --with-imports --verbose # 派生后（含 import 图/目录检查）

# C1-C4 一致性检查（verify 时）
python3 scripts/check_c1_c4.py . --verbose

# 状态恢复（中断后）
python3 scripts/sddl_status.py .
```

示例输出：

```bash
$ python3 scripts/check_sqc.py sddl/specs/accounting/spec.yaml --verbose
SQC [0.1.1]: ✅ PASS
  ✅ def-schema
  ✅ def-refs
  ✅ def-assertability
  ✅ def-dp
  ✅ sem-coverage
  ✅ sem-contradiction
  ✅ sem-testability

$ python3 scripts/check_c1_c4.py . --verbose
C1-C4 [accounting v0.1.1]: ✅ CONVERGED
  ✅ c1_def
  ✅ c2_def
  ✅ c3
  ✅ c4b_def
  soft: c1_sem=1.0 c2_sem=1.0 c4a=1.0 c4b_sem=1.0 must=1.0
```

完整示例见 [`examples/accounting/`](examples/accounting/)——一个从"帮我做个记账小程序"到收敛交付的完整项目（含 spec、决策点确认、SQC/C1-C4 报告、变更记录）。

## Skill 结构

本项目的 Skill 化版本位于 [`integrations/`](integrations/)：

```
integrations/
├── hermes/                      Hermes Agent Skill（完整版）
│   ├── SKILL.md                 主入口 + 9 个分阶段命令
│   ├── references/ (7个)        渐进披露手册（按需加载，不一次全读）
│   ├── scripts/ (4个)           检查器（与根目录 scripts/ 相同）
│   └── templates/ (3个)         spec/architecture 骨架 + 决策点摘要
├── claude-code/                 （规划中）
└── opencode/                    （规划中）
```

**为什么是 skill 而非普通工具**：SDDL 的 9 个命令是**对话式交互流程**（访谈、确认、检查报告），不是纯 CLI 能表达的。Skill 让 agent 直接执行这套流程，人只需要在关键节点（决策点确认、冻结审批）介入。

## 多平台支持

SDDL 的**方法论核心是平台无关的**——`references/`（方法论手册）、`scripts/`（检查器）、`templates/`（模板）不依赖任何具体 agent：

| 组件 | 平台依赖 | 说明 |
|------|---------|------|
| `references/` 方法论手册 | ❌ 无 | 纯 Markdown，任何 agent 都能读 |
| `scripts/` 检查器 | ❌ 无 | 纯 Python CLI，任何环境都能跑 |
| `templates/` 模板 | ❌ 无 | 纯 YAML/Markdown |
| `integrations/hermes/` | ✅ Hermes | 利用 Hermes 的 skill/斜杠命令/clarify 机制 |
| `integrations/claude-code/` | ✅ Claude Code | 规划中（利用 CLAUDE.md + slash command） |
| `integrations/opencode/` | ✅ OpenCode | 规划中（利用 AGENTS.md） |

**接入原则**：核心方法论 + 检查器一次编写，各平台只需加一层"壳"（把 9 个命令映射到该平台的交互机制）。如果你用的 agent 尚未收录，把 `integrations/hermes/SKILL.md` 的流程抄到你的 agent 规则文件（如 `CLAUDE.md` / `AGENTS.md`）即可，检查器脚本直接复用。

---

## 项目结构

```
sddl/
├── scripts/                     检查器脚本（可直接运行）
│   ├── check_sqc.py             SQC 检查（形成 Loop 门禁）
│   ├── check_arch.py            C-arch 架构检查（架构 Loop 门禁，v2.0）
│   ├── check_c1_c4.py           C1-C4 一致性检查（派生 Loop 门禁）
│   └── sddl_status.py           状态恢复（目录即状态）
├── references/                  方法论手册（渐进披露）
│   ├── formation-loop.md        形成 Loop 详细流程
│   ├── architecture-loop.md     架构 Loop 详细流程（v2.0）
│   ├── derivation-loop.md       派生 Loop 详细流程
│   ├── spec-schema.md           Spec 五层结构
│   ├── sqc-checklist.md         SQC 检查清单
│   ├── checker-matrix.md        C1-C4 + C-arch 检查矩阵
│   └── evidence-contract.md     证据契约与项目级收集器（v2.1）
├── templates/                   spec/architecture 骨架 + 决策点摘要模板
├── examples/                    完整示例项目
│   └── accounting/              记账/对账服务（从零到收敛）
├── integrations/                各平台 Agent 适配器（Hermes 已完成，Claude Code/OpenCode 规划中）
├── docs/                        方案文档 + v1→v2 迁移指南
└── LICENSE
```

## 方法论核心（简述）

### Spec 五层结构

| 层 | 内容 | 机器可消费性 |
|----|------|------------|
| L1 接口契约 | 函数签名、参数、返回、错误类型 | 完全（类型检查/AST） |
| L2 数据模型 | JSON Schema | 完全（schema 验证） |
| L3 行为描述 | GWT 场景 + 优先级 | 半（结构可解析） |
| L4 边界条件 | 极端情况 + 优先级 | 半 |
| L5 质量约束 | 性能/安全/可观测 | 弱（性能类标 env） |

### 收敛判定

```
硬门禁：C1-def ∧ C2-def ∧ C3 ∧ C4b-def ∧ C-arch-def 全过（确定性）
软共识：c1_sem≥0.95 ∧ c2_sem≥0.95 ∧ c4a≥0.90 ∧ c4b_sem≥0.90 ∧ c_arch_sem≥0.90（Checklist 计票）
且 must 覆盖 = 100% 且无 blocker violation → 收敛
```

### 检查矩阵

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

## 证据基础

SDDL 的设计经过文献验证（arXiv 论文）与三轮评审循环打磨：

- **Self-Refine** (arXiv 2303.17651) — self-refine loop 范式源头
- **Pride and Prejudice** (arXiv 2402.11436) — LLM 自反馈放大自偏置 → 异模型检查
- **TICKing All the Boxes** (arXiv 2410.07061) — checklist 生成改善 LLM 评估
- **Calibration Collapse Under Sycophancy** (arXiv 2026-04) — 绝对分数不可信 → 客观计票
- **LLMorpheus** (arXiv 2404.09954) — LLM 变异测试 → 验收反推验证
- **OpenSpec** (Fission-AI) — specs/+changes/+archive 变更管理实践

完整证据链见 [`docs/SDDL-方案-v1.1.md`](docs/SDDL-方案-v1.1.md) 附录 A。

## v1.x 迁移

v2.0 新增架构 Loop（双 Loop → 三 Loop），v1.x 项目手工迁移（无自动脚本，设计决策）：

- **已收敛不再开发**：不迁移，留档即可
- **迭代中**：补 `sddl/architecture.yaml`（可从现有 `src/` 反向提取模块）→ `check_arch.py --with-imports` 修到 pass → 架构决策点补确认 → state.yaml 补 `arch_status: frozen`
- **单模块小项目**：`single_module: true` 空架构也要生成并冻结（豁免划分，不豁免门禁）

详见 [`docs/migration-v1-to-v2.md`](docs/migration-v1-to-v2.md)。

## 适用门槛

| 模式 | 适用 | 成本 |
|------|------|------|
| 完整 SDDL | 接口≥8 且 must 验收≥10 且多 artifact 同步 | 高 |
| 标准 SDDL | 接口 5-8 | 中 |
| 轻量 SDD | 接口<5 但多 artifact | 低 |
| 纯 TDD | 其余 | 最低 |

**不适用**：一次性脚本、原型/POC、探索性研究代码。

## License

MIT License — 见 [LICENSE](LICENSE)

## 致谢

- 方法论经过 3 轮评审循环（35 个问题关闭）+ 2 轮文献验证（arXiv 17 篇 + OpenSpec 实践）
- Hermes Agent Skill 化版本经过 8 个分阶段命令 + 7 个测试场景验证
