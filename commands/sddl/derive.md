---
description: "SDDL 派生 Loop：双冻结后从 spec+架构派生 tests/code/docs（按并行组分组）"
skills: sddl
---

执行 SDDL **derive 阶段**（派生 Loop 第 1 步）。

1. 硬前置：`spec_status: frozen` 且 `arch_status: frozen`（双冻结门禁，缺一不派生）。
2. 读 skill 的 `references/derivation-loop.md`（阶段 1-2）：先派生测试（must 级行为可断言），再派生代码与文档；多模块项目按 `scripts/check_arch.py . --with-imports --json` 输出的 `facts.parallel_groups` 分组并行派生。
3. 代码按架构 path 落位（tests/<module>/，docs/ 含 current/planned 分区）；非 Python 技术栈按 `references/evidence-contract.md` 先构造项目收集器。
4. 避免 SKILL.md Common Pitfalls：测试加隔离 fixture（autouse 重置）、纯查询函数无副作用、动手前先读真实源码签名。
5. 结束时：更新 state.yaml + git commit，报告下一步：`/sddl:verify`。
