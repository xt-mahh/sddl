# SDDL 轻量缺陷修复通道（v2.0）

> 全量 changes/ 提案走双 Loop 是给功能演进的；修 bug 走它 = 杀鸡用牛刀。
> 本通道把「诊断 / 修复 / 验证」分开，产出三态结论：`verified | partial | failed`。
> **缺少验证不算修复成功**（与 C3 硬条件同哲学）。

## 触发条件（满足其一走本通道，否则走标准 changes/ 提案）

- 行为与某个已冻结 behavior 的 THEN 子句不一致（C1/C2/C3 violation）
- 缺陷不影响 spec（不需要解冻）：修代码对齐 spec，而不是改 spec
- 若根因是 spec 错 → **不走本通道**，升级为 spec_error 走解冻回路

## 流程：3 步，产物落 `sddl/bugs/<slug>/`

```
① diagnose（诊断）          ② fix（修复）                ③ verify（验证）
定位根因+受影响面      →    最小修复（禁顺手重构）   →    回归受影响 behaviors
产 diagnosis.md            产 fix.md（diff+理由）        产 report.md（三态结论）
```

### ① diagnose

- 复现路径（命令/输入/期望 vs 实际）
- 根因定位（引用具体文件行号；不接受"大概是"）
- 受影响面：哪些 behaviors / 哪些模块（引用 architecture.yaml 模块名）
- 结论分流：`code-level`（走②）或 `spec-level`（升级 spec_error，终止本通道）

### ② fix

- 最小 diff 原则：只修根因，不顺手重构/优化（发现新问题另开 bug）
- fix.md 记录：改了什么、为什么这样改、对照 diagnosis 的根因

### ③ verify

- **复现验证**：①的复现路径重跑，症状消失
- **回归验证**：受影响 behaviors 的测试全绿（must 级 100%）
- 结论三选一写入 report.md：
  - `verified`：复现消失 + 回归全绿
  - `partial`：复现消失但部分回归未过 → 列出未过项，转标准 verify 流程
  - `failed`：复现未消失或引入新破坏 → 回②，或升级 spec_error

## 门禁（简化但不是没有）

| 标准流程 | 本通道 |
|---------|--------|
| SQC + 双冻结 + C1-C4 全检 | ①复现验证 + ③受影响 behavior 回归 |
| 决策点确认 | 根因属 spec-level 时升级，其余免 |
| git commit | 必须（`fix(sddl-bug): <slug>`） |
| Confluence 报告 | report.md（三态结论 + 证据） |

## 状态恢复

`sddl/bugs/<slug>/` 存在 diagnosis.md 无 fix.md → 从 ② 开始；有 fix.md 无 report.md → 从 ③ 开始；report.md 结论 partial/failed → 未收敛，继续路由。
