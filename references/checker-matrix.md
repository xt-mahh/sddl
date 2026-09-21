# Checker Matrix（C1-C4 一致性检查）

> `/sddl:verify` 时检查 **artifacts vs spec** 的一致性。这是派生 Loop 的门禁。SQC 查 spec 自身，本文件查 artifacts。

## 检查矩阵

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

| 检查 | 性质 | 内容 |
|------|------|------|
| C1-def | 硬 | 验收覆盖映射 + 结构反推 |
| C1-sem | 软 | 测试实际断言 ↔ 行为语义（Checklist） |
| C2-def | 硬 | 接口/签名/模型/错误类型静态对比 |
| C2-sem | 软 | 代码行为 ↔ 行为语义（Checklist） |
| C3 | 硬 | 测试执行 + 覆盖率 + 无跳过 |
| C4a | 软 | spec ↔ docs（Checklist） |
| C4b-def | 硬 | code ↔ docs 符号表对比（docs 声明的 API 在 code 中存在） |
| C4b-sem | 软 | docs 描述的行为在 code 中可实现（Checklist） |
| C-arch-def1/2/3 | 硬 | 模块↔domain 所有权覆盖 / import 图 = 声明依赖 / 模块落目录（check_arch.py；非 Python 技术栈显式降级 → 项目收集器接管，见 evidence-contract.md） |
| C-arch-sem | 软 | 职责内聚性：模块职责与 owns 的行为分布一致（Checklist，v2.0 新增） |

> v2.0：C-arch 检查 `artifacts + architecture.yaml`，位于 C2-def 之后、软条件之前执行。检查器：`python3 scripts/check_arch.py <root> --with-imports --json`。

## 硬条件检查（确定性，逐项执行）

### C1-def：验收覆盖 + 结构反推（打破自证循环）

**不信任生成方贴的标签**。三层验证：

```
L1 标签索引：B001 → test_auth.py        （仅作索引；失败不判 violation）
L2 结构反推：解析测试 AST，提取实际断言
    - 构造了什么输入
    - assert 了什么（返回值/异常/副作用）
    - 覆盖了 GIVEN/WHEN/THEN 的哪部分
    - L1 失败 → 强制 L2；L2 无法确认 → violation
L3 变异验证（must 级验收 + C3 通过后执行）：
    对实现做变异（改比较符/删 guard/反转布尔/改返回值/改循环边界）
    变异被杀 = 测试真的在测该行为；变异存活 = 测试是假的/弱的 → violation
```

执行方式：
- L1：解析测试文件命名/装饰器/标记，建立 behavior → test 映射
- L2：用语言 AST（Python `ast` / Go `go/ast`）解析测试断言，与 THEN 子句结构比对
- L3：只对 must 级验收做，且在 C3 通过后（半成品实现不做变异，避免误报）

### C2-def：接口/签名/模型/错误对比

- [ ] 所有 interfaces 在代码中存在（符号表对比）
- [ ] 函数签名（参数名/类型/返回）匹配
- [ ] data_models 与代码类型定义一致（schema → 类型映射）
- [ ] 错误类型与 spec 枚举一致
- [ ] 无超出 spec 的公开 API（公开符号集合对比）

⚠️ **符号提取实现坑（h3chain 项目 8/31 实测修两处）**：
1. `ast.FunctionDef` 不含异步函数——FastAPI 路由几乎全是 `async def`，漏了会误报"接口未实现"。必须 `(ast.FunctionDef, ast.AsyncFunctionDef)`。
2. 不能用 `ast.walk` 提取公开符号——它会把类方法/嵌套函数也收进来，类方法被误判为越界公开 API。正确做法：只遍历 `tree.body` 顶层定义；FastAPI 前端路由函数改 `_index` 私有名或 spec 补录接口。

### C3：测试执行

- [ ] 测试全部通过（pytest / go test）
- [ ] 覆盖率达标（阈值在 state.yaml 或 spec 中定义）
- [ ] 无跳过/禁用测试（`@pytest.mark.skip` / `t.Skip`）

⚠️ **C3 通过 ≠ 满足 spec**——测试本身可能漏了或错了。C3 是必要非充分条件。

### C4b-def：docs ↔ code 符号表

- [ ] docs 的 `current` 分区声明的 API 在 code 中存在（符号表对比）
- [ ] docs 分区标注正确（`status: current | planned`；planned 分区不参与检查）

## 软条件：LLM 语义审核

> **软条件（C1-sem / C2-sem / C4a / C4b-sem）由 agent 的 LLM 能力审核，不是脚本启发式。**
> 脚本提供确定性证据（AST 提取断言、符号表、测试执行），LLM 基于证据做语义判断。
> 完整操作指南见 `llm-review.md`。

### 判定项生成（从 behavior 派生）

```
对每个 behavior B：
  [B-GIVEN]  测试/代码是否构造了 B 的 GIVEN 前置条件？
  [B-WHEN]   测试/代码是否调用了 B 声明的接口？
  [B-THEN-1] 测试/代码是否断言/实现了 THEN 子句 1？
  [B-THEN-N] ...
  [B-ERR]    测试/代码是否覆盖了 B 关联的错误类型？
  [B-SIDE]   测试/代码是否验证了 B 的副作用约束？
```

质量约束：
- **判定项集版本化**：每轮 verify 开始冻结判定项集，轮内不增删——共识率分母固定，不可操纵
- **证据要求**：每个判定必须附证据（spec 行号 + code/test 行号 + 原文，或脚本输出引用）

### LLM 审核流程（主路径）

```
1. 脚本收集确定性证据（check_sqc.py --json / check_c1_c4.py --json）
2. agent 基于证据逐项审核（读测试逻辑、读实现、对比 spec）
3. 对抗式立场：默认"找不一致"，找到证据才报，找不到报 "no evidence found"
4. 输出结构化判定（covered / partial / not_covered / non_verifiable）
5. 共识率 = 采纳的 covered / 总判定项（客观计票）
```

### 分层投票（多模型可用时，成本控制）

```
L0 快筛（1 模型，全量判定项）→ 判"是"的项默认接受
  ↓ 判"否"或证据缺失的项
L1 投票（3 模型）→ 一致项采纳
  ↓ 分裂项
L2 复核（异模型确认）→ 确认/否决
  ↓ 复核仍无法确认
人工
```

成本：20 行为 spec（120 判定项）→ 360 次调用/轮（全量）vs 198 次/轮（分层漏斗）。
**单 agent 环境**：跳过 L0-L2，由 agent 直接完成全量审核（相当于快筛+自我复核，注意自偏置——见下）。

### 投票模型独立性（防系统性偏置）

- **独立性矩阵**：在 golden set 上计算模型两两错误相关度；相关度 > 0.6 → 不安排同组投票。投票组必须异质（不同供应商/生态）。
- **golden 锚定**：每个判定项附带同类型 golden 样本（few-shot），模型先校准再投票。
- **偏置降权**：模型在 golden set 上某类判定项错误率超阈值 → 该类票权减半。
- **确定性锚点**：语义判"否"但确定性检查支持实现存在 → 以确定性为准（semantic_only 不阻塞收敛）。
- **单 agent 自偏置（重要）**：单个 LLM 审核自己的生成产物有自偏置（Pride and Prejudice 2402.11436）。缓解：
  - 审核 prompt 用对抗式立场（见 llm-review.md §对抗式审核）
  - 关键判定（spec_error / 行为矛盾）过第二遍独立复核
  - 确定性锚点兜底：语义结论不推翻确定性事实

### 不确定滥用防护

- 投票选项强制：`是 | 否 | 证据缺失`（无"不确定"）
- "证据缺失" ≠ "不确定"：无法从材料判定；进 LLM 复核队列
- 复核仍证据缺失 → 标记 non-verifiable，移出判定集（不阻塞）
- 单轮证据缺失率 > 20% → 模型降权；连续 2 轮 > 20% → 移出投票组

## 收敛判定

```python
def judge(spec, arch, tests, code, docs):
    hard = {c1_def, c2_def, c3, c4b_def, c_arch_def}
    if not all(h.passed for h in hard.values()):
        return NotConverged(...)          # 门禁：硬条件全过才谈收敛

    consensus = {
        "c1_sem": 0.95, "c2_sem": 0.95,   # 客观计票（非 LLM 评分）
        "c4a": 0.90, "c4b_sem": 0.90,
        "c_arch_sem": 0.90,               # v2.0：架构内聚共识率
    }
    must_covered = coverage_of(spec.behaviors, priority="must")

    converged = (
        consensus >= thresholds and
        must_covered == 1.0 and
        no_blocker_violations()
    )
```

**阈值初值**：c1_sem/c2_sem ≥ 0.95，c4a/c4b_sem ≥ 0.90，must 覆盖 = 100%。
**校准**：golden set（已知正确/错误样本 ≥10 对）记录假阳性/假阴性率，调至无假阳性（宁可漏报不可误报）。

## Convergence Report（收敛证明）

写 `checks/c1-c4-<domain>-v1.json`，分两节：
- `deterministic_evidence`：可重跑（含命令 + 输入哈希）
- `semantic_evidence`：可审计不可复现（模型/温度/seed/判定项集版本/投票原始记录）

## Violation 路由（verify 未收敛时）

| 分类 | 触发 | 动作 |
|------|------|------|
| spec_error | spec 内部矛盾/不可实现 | 解冻 → 回形成 Loop 修订 |
| spec_gap | 实现暴露未定义情况 | 解冻 → 受影响决策点重确认 |
| arch_error | 架构缺陷：职责冲突/依赖方向错/划分不合理（v2.0 新增） | 解冻 architecture.yaml → 修订 → check_arch + 受影响决策点重确认 → 重冻 → 受影响模块重派。**不解冻功能 spec**（层次隔离；根因在 domain 划分时走 spec_error 上溯） |
| implementation_error | 代码偏离 spec / 越界 import（C-arch-def2） | 重派 code（对齐架构） |
| test_error | 测试缺失/错误 | 重派 tests |
| doc_error | 文档不同步 | 重派 docs |

**三层判定**：确定性预筛（规则）→ 语义裁决（LLM + 证据要求）→ 人工升级（spec_error 必须人工；连续 2 轮未解决；置信度 < 0.7）。

**改 spec 永远比改代码重**：提案 + SQC + 决策点确认 + 审批 + 归档。防止 loop 自我放松标准。
