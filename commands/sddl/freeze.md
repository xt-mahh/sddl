---
description: "SDDL 冻结门禁：SQC / C-arch 全检通过后冻结 spec 或 architecture（phase 感知）"
skills: sddl
---

执行 SDDL **freeze 阶段**（形成 Loop 第 4 步 / 架构 Loop 第 3 步，phase 感知）。

1. 判定当前冻结对象：`architecture.yaml` 不存在或未冻结 → 冻结功能 spec；spec 已冻结 → 冻结架构。
2. 冻结 spec：读 `references/sqc-checklist.md`，运行 `scripts/check_sqc.py sddl/specs/<domain>/spec.yaml --json` 收集确定性证据；sem 项按 checklist 由 LLM 审核。SQC 无 blocker 且决策点全部确认后，置 `spec_status: frozen`。
3. 冻结架构：读 `references/architecture-loop.md`（阶段 4），运行 `scripts/check_arch.py . --json`（struct + def1）。C-arch-def 全过 + 架构决策点确认后，置 `arch_status: frozen`。
4. 检查报告写入 `sddl/checks/`（sqc-/arch- 前缀 JSON），提交 git commit，报告下一步：spec 冻结后 `/sddl:arch`；架构冻结后进入派生 `/sddl:derive`（双冻结门禁）。

注意：双冻结齐备前不得派生任何代码；小项目 `single_module: true` 豁免的是模块划分，不是门禁本身。
