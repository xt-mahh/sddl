# SDDL v1.x → v2.0 迁移指南

> v2.0 把双 Loop 重构为三 Loop：新增**架构 Loop**（功能 spec 冻结后、派生前），产出并冻结 `sddl/architecture.yaml`。本指南帮助 v1.x 老项目手工迁移。**没有自动迁移脚本**（设计决策 DP-002：干净断裂，不背兼容包袱）。

## 什么变了

| 维度 | v1.x | v2.0 |
|------|------|------|
| Loop 数 | 2（形成/派生） | 3（形成/**架构**/派生） |
| 派生前置 | spec frozen | spec frozen **且** arch frozen（双冻结门禁） |
| 新 artifact | — | `sddl/architecture.yaml`（单文件） |
| 新命令 | — | `/sddl:arch` |
| 新检查 | — | C-arch-def1/2/3（check_arch.py）+ C-arch-sem（LLM 内聚复审） |
| 新路由 | — | `arch_error`（解冻架构，不解冻功能 spec） |
| state.yaml | spec_status / current_phase | + `arch_status`；current_phase 增加 architecture 相 |
| 恢复规则 | specs frozen → derive | specs frozen → **/sddl:arch** → arch frozen → derive |

## 迁移步骤（按项目所处阶段）

### A. 已收敛/已交付的 v1.x 项目（不打算继续开发）

不迁移。v1.x 产物自洽，仓库留档即可。下次开新变更时按 B 处理。

### B. spec 已冻结、还在迭代的项目（最常见）

1. 补 `sddl/architecture.yaml`：
   - 多模块：按 `templates/architecture-template.yaml` 填写——从现有 `src/` 目录反向提取模块（name/path/depends_on），domain→模块的 owns 映射照 `sddl/specs/` 填
   - 单模块：只写 `single_module: true` + meta，modules 留空数组
2. 跑 `python3 scripts/check_arch.py <root> --with-imports`，按报告修 depends_on 与目录声明，直到 pass（存量代码的越界 import 会暴露历史债，逐条补声明或重构，不隐藏）
3. 架构决策点（模块划分/技术栈）补登记 + confirm（存量项目可按"现状即决策"批量确认）
4. state.yaml 补两行：`arch_status: frozen`、`current_phase` 按实际改
5. commit：`chore(sddl): migrate to v2.0 architecture layer`

### C. 派生进行中 / 未收敛的项目

同 B，但补完架构并冻结前**暂停派生**——v2.0 的 C-arch-def2（import 图检查）需要在架构冻结后才有效力，边派生边迁移会造成检查基线漂移。

### D. 刚 init / 访谈中的项目

直接删掉重来或继续走完形成 Loop，到 `/sddl:freeze` 后自然进入 v2.0 流程（恢复规则会把你导向 `/sddl:arch`）。

## 检查器变化

```bash
# 新增（v2.0）
python3 scripts/check_arch.py <root> [--with-imports] --json

# sddl_status.py 输出新增阶段：arch / arch_freeze
python3 scripts/sddl_status.py <root>
```

check_sqc.py / check_c1_c4.py 不变（功能 spec 的门禁与 v1.x 完全兼容）。

## 常见问题

**Q：小项目一定要建 architecture.yaml 吗？**
A：是的。`single_module: true` 的空架构也必须生成并冻结——豁免的是模块划分，不是门禁。这让状态机对所有项目统一，恢复规则不出现分叉。

**Q：迁移时发现存量代码有越界 import 怎么办？**
A：这正是 v2.0 的价值——历史架构债显性化。两条路：补 depends_on 声明（承认现状）或重构消除依赖（还债）。**不建议**用 `--with-imports` 之外的开关绕过检查。
