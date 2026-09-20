# 架构 Loop 详细流程（Architecture Loop）

> 回答"怎么分层"：冻结的功能 specs → 系统级 architecture.yaml → 冻结。本文件是 `/sddl:arch` 命令的详细执行手册，以及 `/sddl:freeze` `/sddl:verify` 在架构阶段的 phase 感知规则。

## 定位

```
形成 Loop（做什么）        架构 Loop（怎么分层）         派生 Loop（怎么做对）
interview→spec→confirm→freeze ──▶ arch→confirm→freeze ──▶ derive→verify→archive
       按 domain                  单文件 architecture.yaml     按 module
```

**双冻结门禁**：`specs/<domain>/spec.yaml` 全部 frozen **且** `sddl/architecture.yaml` frozen，才可进入派生。缺一即回到对应 Loop。

**DP-001（已确认）**：架构以冻结的功能 spec 为输入——架构尊重功能边界，不反过来切分需求。架构阶段发现 domain 切分不合理 → 走 `spec_error` 路由解冻上游 domain，修订重冻后再回来。

## 阶段 1：生成（/sddl:arch）

### 输入检查（硬前置）

- `sddl/specs/` 下全部 spec 的 `meta.status = frozen`（有任何一个非 frozen → 拒绝执行，提示先完成形成 Loop）
- 小项目豁免：预期只有一个模块时，直接生成 `single_module: true` 的空 modules 架构（仍需走完确认与冻结——豁免的是划分，不是门禁）

### 生成流程

1. 通读全部冻结 specs 的 `interfaces` / `data_models` / `behaviors`
2. 按**职责内聚**划分模块：一个模块 = 一组高内聚的 behaviors + 其支撑接口
3. 每个模块登记：`responsibilities`（≥1 条，C-arch-sem 审点）、`owns`（拥有的 domain，一 domain 一 owner）、`depends_on`（调用方向，禁止环）、`path`（代码目录）
4. 技术栈选型、模块划分方案本身 → 全部登记为决策点（category=contract/implementation），**不静默决定**
   - **调研触发（v2.0）**：contract 级决策点 alternatives ≥ 3 时，按 `references/research-notes.md` 写 `sddl/research/<topic>.md`（≥3 维度对比表 + 可复查数据来源 + constitution 冲突检查）
5. 跨模块数据流写入 `data_flows`（供内聚复审佐证）
6. 产出 `sddl/architecture.yaml`（用 templates/architecture-template.yaml）

### 划分启发式（供生成时参考，不是规则）

- behaviors 引用关系密的 domain 归入同一模块
- 跨 domain 的 behavior（`cross_component: true`）= 模块边界的天然证据，两边模块都必须显式依赖声明
- 拿不准切几块 → 登记决策点给用户选，不要替用户定架构

### 检查点

- [ ] `python3 scripts/check_arch.py <root>` 通过（C-arch-struct + C-arch-def1）
- [ ] 全部决策点已登记（选型/划分/豁免）

## 阶段 2：确认（复用 /sddl:confirm）

- architecture.yaml 的决策点与 spec 决策点**共用编号池**（同一项目内 DP-xxx 唯一）
- 逐项 clarify 确认（同一体验规范：≤3 业务选项 + 第 4 位自定义输入）
- 用户改模块划分 → 回阶段 1 修订，重新过检查

## 阶段 3：冻结（/sddl:freeze 的 phase 感知）

`/sddl:freeze` 按 `state.yaml: current_phase` 决定冻结对象：

| current_phase | 冻结对象 | 门禁 |
|---------------|---------|------|
| formation | 各 domain spec | check_sqc.py（不变） |
| architecture | architecture.yaml | check_arch.py + 决策点无 pending |

冻结成功写 `state.yaml`：

```yaml
spec_status: frozen          # 功能 spec 状态（沿用）
arch_status: frozen          # 新增：architecture 状态
current_phase: derivation    # 双冻结齐备后推进
```

**架构修订回路**（与 spec 修订平行）：派生中发现架构缺陷 → 路由 `arch_error` → 解冻 architecture.yaml → 修订 → 重过 check_arch + 受影响决策点重确认 → 重冻 → 受影响模块重派。**注意**：架构解冻不解冻功能 spec（层次隔离），除非缺陷根因在 domain 划分（→ 走 spec_error 上溯）。

## 阶段 4：派生中的 C-arch 维度（/sddl:verify 扩展）

- `check_arch.py --with-imports <root>`：C-arch-def2（import 图 = 声明依赖）+ C-arch-def3（模块落目录）作为**硬条件**加入收敛判定（位于 C2-def 之后、软条件之前）
- **并行派生组（v2.0）**：`check_arch.py --json` 的 `facts.parallel_groups` 给出依赖图拓扑分层——同层模块互不依赖，可安全多 agent 并行派生（第 1 层先行，逐层推进；单模块豁免项目为单组）
- C-arch-sem（职责内聚性）：软条件，LLM Checklist 投票（见 llm-review.md §架构内聚复审），共识率门槛 0.90
- 路由：C-arch-def2/def3 violation → `implementation_error`（改代码对齐架构）；C-arch-sem 低分 → 人工裁决（改代码 or 改架构，后者走架构解冻）

## 状态恢复（目录即状态，增量规则）

在 v1.x 恢复规则基础上插入一条（位置：specs frozen 检查之后）：

- `specs/` 全 frozen 但无 `sddl/architecture.yaml` → 从 `/sddl:arch` 开始
- `architecture.yaml` 有但 `arch_status != frozen` → 从架构 freeze 开始
- 双 frozen 但无 `src/` → 从 `/sddl:derive` 开始

## 常见坑（v2.0 新增）

1. **跳过架构 Loop 直接派生**——单模块小项目也必须生成 `single_module: true` 并冻结，否则双冻结门禁永不满足。
2. **architecture.yaml 先于 spec 冻结**——违反 DP-001 确认的顺序，架构没有功能佐证会拍脑袋；check_arch 不拦（时序是流程纪律），/sddl:arch 的输入检查拦。
3. **模块划分静默决定**——划分方案本身是最高影响的决策点，不登记 DP 直接冻结 = 架构失真。
4. **架构修订顺手改 spec**——层次隔离：arch_error 只解冻 architecture.yaml，动功能 spec 必须显式走 spec_error 上溯回路。
5. **responsibilities 写成技术名词堆**——它是 C-arch-sem 的唯一审点，要写"这个模块对外承担什么职责"（业务语言），不是"用了什么库"。
