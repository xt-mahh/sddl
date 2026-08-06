# 派生 Loop 详细流程（Derivation Loop）

> 回答"怎么做对"：冻结 Spec → tests/code/docs → C1-C4 收敛。本文件是 `/sddl:derive` `/sddl:verify` `/sddl:archive` 三个命令的详细执行手册。

## 阶段 1：派生（/sddl:derive）

### 目标
从冻结 Spec 派生 tests / code / docs，保持三者与 spec 锁步。

### 派生顺序（重要）

```
1. tests（先写测试——测试是 spec 的可执行投影）
2. code（实现到测试通过）
3. docs（描述已实现的能力，含 current/planned 分区）
```

**为什么先测试**：测试先行 = 每个 behavior 的可执行定义。先写测试能暴露 spec 的二义性（写不出来 = spec 不清）。

### 测试派生规则
- 每个 `acceptance: true` 的 behavior 至少一个测试
- must 级验收：测试必须覆盖 THEN 全部子句（用 L3 变异验证兜底）
- 测试命名：`test_<interface>_<scenario>`（如 `test_authenticate_valid`）
- 测试标签映射：`@pytest.mark.behavior("B001")` 或文件命名约定——**仅作索引，不信任**（C1-def L2 会反推）
- **测试隔离（T1 实测坑）**：内存 store/全局状态必须在每个测试前重置（autouse fixture）；测试断言走公开接口，不直接访问内部状态（如 `_store`）——访问内部状态会耦合实现细节，且 C2-def 会把它当越界 API
- **纯查询接口无副作用**：只返回报告/查询的接口（如 detectDiscrepancy）不得修改状态（T1 实测：detectDiscrepancy 改 status 违反 spec B006）

### 代码派生规则
- 实现 spec 声明的全部接口（C2-def 检查）
- 不实现 non_goals（越界 = C2-def violation）
- 实现细节自由（内部结构不写死），但公开面必须匹配 spec

### 文档派生规则
- `docs/current/`：描述已实现能力（必须与 code 一致——C4b-def 检查）
- `docs/planned/`：描述 roadmap（不参与一致性检查）
- 每个 docs 文件头部标注 `status: current | planned`

### 产出
```
src/  tests/  docs/
├── current/
└── planned/
```

### 检查点
- [ ] tests 可运行（至少能发现失败）
- [ ] code 能编译/运行
- [ ] docs 分区标注正确

---

## 阶段 2：验证（/sddl:verify）

### 目标
C1-C4 分层检查 + 收敛判定。

### 执行顺序
1. 硬条件：C1-def → C2-def → C3 → C4b-def（任一失败 → 停止，先修硬伤）
2. 软条件：C1-sem / C2-sem / C4a / C4b-sem（Checklist 投票）
3. 收敛判定（见 checker-matrix.md §收敛判定）
4. 写 `checks/c1-c4-<domain>-v1.json` + Convergence Report

### 硬条件快速失败
```
C1-def 失败 → 测试缺失/造假 → 路由 test_error
C2-def 失败 → 代码缺接口/签名错 → 路由 implementation_error
C3 失败 → 测试红 → 路由 test_error 或 implementation_error
C4b-def 失败 → docs 声明的 API 不存在 → 路由 doc_error
```

### 收敛判定后
- **收敛** → 输出 Convergence Report → `/sddl:archive`
- **未收敛** → violation 列表 → 路由（见下）

---

## 阶段 3：路由（未收敛时）

### 三层混合判定

```
第一层：确定性预筛（规则）
  - 测试失败但 spec 明确规定 → implementation_error
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

### 路由矩阵

| 分类 | 动作 | 需人工 |
|------|------|--------|
| spec_error | 解冻 → 回形成 Loop 修订（SQC + 决策点重确认 + 重新冻结） | 是（必须） |
| spec_gap | 解冻 → 受影响决策点重确认 | 是（提案制） |
| implementation_error | 重派 code | 否 |
| test_error | 重派 tests | 否 |
| doc_error | 重派 docs | 否 |

### 影响面分析（L2/L3 修订时）

| 变更元素 | 受影响集合 |
|---------|-----------|
| interface | 所有调用方代码 + 该接口测试 + 文档引用 |
| model | 所有读写该模型的代码 + 测试 fixture + 文档 |
| behavior | 该行为的测试（标签追踪辅助）+ 文档引用 |
| boundary | 该边界的测试 |

规则：接口/模型变更走引用图精确局部重派；引用图分析不到的保守标记 STALE（宁多勿漏）；L3 全量重派不依赖影响面分析。**跨组件引用**：组件 A 接口变更 → 组件 B 引用该接口的决策点/行为要重确认。

---

## 阶段 4：预算与降级

### 三预算（记录在 state.yaml）

```
budget:
  formation:     { total: 2M,  max_iterations: 5,  used: 0.4M }
  implementation:{ total: 15M, max_sessions: 4,    used: 1.2M }
  revision:      { total: 5M,  L2_cost: 0.10, L3_cost: 0.25, first_L3_free: true, used: 0 }
```

**激励设计**：修订预算单列 + 首次 L3 免费 → loop 诚实报告 spec_error 无成本代价，不扭曲行为。

### 降级路径（预算/轮数耗尽，按顺序）

```
D1: 语义检查降级（快筛 1 模型，投票只在 must 级跑）    [省 ~60% 语义成本]
D2: 缩小收敛目标（must 不变，should/could 移风险清单）  [省 ~30% 派生成本]
D3: 缩小变异测试范围（只跑 P0 验收）                    [省 ~70% 变异成本]
D4: 拆分 spec（按领域拆，每领域独立 loop）              [线性化成本]
D5: 交付"最优可行解 + 已知 violation 清单"（最佳努力态）
```

**must 覆盖优先于一切**：预算耗尽 + must 未全覆盖 → 不自动降级，转人工（人工决定：加预算 / 降 must / 接受风险）。

每次降级生成 Degradation Report。

---

## 阶段 5：归档（/sddl:archive）

### 目标
变更归档、spec 合并、状态更新。

### 执行
1. 增量 delta 合并入 `specs/<domain>/spec.yaml`（如为变更提案）
2. 更新 `specs/` 版本 + CHANGELOG（diff、原因、影响面）
3. 解除 STALE 标记
4. 更新 `state.yaml`：`current_phase: complete`
5. git commit：`feat(sddl): archive <domain> change`

### 归档后
- spec 成为新真相
- 新变更走新的 changes/ 提案
- 派生 Loop 收敛产物（tests/code/docs）与 spec 版本绑定
