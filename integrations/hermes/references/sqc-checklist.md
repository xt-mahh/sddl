# SQC 质量检查清单（Spec Quality Check）

> `/sddl:freeze` 时对 spec **自身**质量的检查（不是 artifacts vs spec 的一致性——那是 C1-C4）。SQC 是形成 Loop 的门禁。

## 检查项总览

| 检查 | 性质 | 内容 |
|------|------|------|
| SQC-def-1 schema 合法 | 硬 | YAML 结构合法、必填字段齐全、类型正确 |
| SQC-def-2 引用完整 | 硬 | behaviors 引用的 interface/model/错误类型都存在；non_goals 不与 interfaces 冲突 |
| SQC-def-3 可断言性 | 硬 | THEN 子句无模糊词；GIVEN 无不可构造的前置 |
| SQC-def-4 决策点登记 | 硬 | 正文中所有"需用户选择"处都有对应决策点；决策点字段完整 |
| SQC-sem-1 行为覆盖 | 软 | happy path + 主要错误路径 + 边界是否都有行为场景；must 不能全是 happy path |
| SQC-sem-2 行为矛盾 | 软 | 行为间 GIVEN/THEN 是否有冲突 |
| SQC-sem-3 完整性缺口 | 软 | 需求陈述提及但 spec 未覆盖的场景 |
| SQC-sem-4 可测性判定 | 软 | THEN 是否可转化为具体断言（"响应快速"→ 不可测，需量化） |

## SQC-def（确定性检查，逐项执行）

### SQC-def-1 schema 合法
- [ ] YAML 可解析
- [ ] meta.id / version / domain / status 存在
- [ ] interfaces 有 name / signature / errors
- [ ] behaviors 有 id / interface / priority / given / when / then
- [ ] boundaries 有 condition / expectation
- [ ] decision_points 存在（可为空数组）

### SQC-def-2 引用完整
- [ ] 每个 behavior 的 interface 在 interfaces 中存在
- [ ] 每个 interface 的签名参数类型/返回类型在 data_models 中存在（或为原生类型）
- [ ] 每个 interface 的 errors 都有定义（在 behaviors 的错误场景或独立错误定义中）
- [ ] non_goals 不与 interfaces 冲突（如 non_goal "不做注册" 但 interface 有 register）
- [ ] behaviors 引用的 decision_point id 在 decision_points 中存在

### SQC-def-3 可断言性（模糊词检测）
THEN 子句逐条正则匹配模糊词：

```
模糊词正则：成功|正常|正确|尽快|快速|高效|友好|合理|适当|必要时|等|等等|其他|相关|相应|尽可能|大概|大约|左右|一些|若干|部分|某些
```

命中 → 警告 + 要求量化（"返回成功" → "返回 AuthResult 且 HTTP 200"）。

GIVEN 不可构造检查（语义，配合 SQC-sem-4）：
- "天气好""网络通畅" 类不可控前置 → 必须改为可控（"mock 网络正常"）

### SQC-def-4 决策点登记
- [ ] 正文出现"建议/默认/暂定/按经验"等推测性词 → 检查是否有对应 DP
- [ ] 每个 DP 有 id / topic / default / category / requires_confirmation / status
- [ ] DP 数量 ≤ 15（超限 → 建议拆分 spec）

## SQC-sem（语义检查，Checklist 判定）

复用派生 Loop 的 Checklist 投票机制（见 checker-matrix.md §2）：
- 生成判定项（每个检查项一个二分问题）
- 分层投票（快筛 1 模型 → 投票 3 模型 → 复核）
- 共识率 = 采纳项 / 总项

### SQC-sem-1 行为覆盖
判定项示例：
```
[COV-1] spec 是否包含 happy path 行为？          （至少 1 个 must）
[COV-2] spec 是否包含主要错误路径行为？          （至少 1 个 must）
[COV-3] spec 是否包含至少 1 个边界行为？         （boundaries 非空）
[COV-4] must 级行为是否覆盖了核心用户价值？      （must 不全在边角）
```

### SQC-sem-2 行为矛盾
判定项示例：
```
[CON-1] 是否存在两个 behavior 的 GIVEN 重叠但 THEN 冲突？（如同条件一个说 200 一个说 400）
[CON-2] 是否存在 behavior 与 non_goals 冲突？
[CON-3] 是否存在 behavior 与 boundaries 冲突？
```

### SQC-sem-3 完整性缺口
判定项示例：
```
[GAP-1] 需求陈述的场景清单是否都有对应 behavior？
[GAP-2] 需求陈述的约束清单是否都有对应 quality_constraint？
[GAP-3] deferred 细节是否都有决策点或已写入 spec？
```

### SQC-sem-4 可测性判定
判定项示例：
```
[TEST-1] 每个 THEN 是否可转化为具体断言（无模糊词、有具体值/类型）？
[TEST-2] 每个 GIVEN 是否可构造（有明确的 fixture/mock 路径）？
```

## 输出

写 `checks/sqc-<domain>-v1.json`（机器可读）：
```json
{
  "check_type": "sqc",
  "spec_version": "0.1.0",
  "def": {
    "schema_ok": true,
    "refs_ok": true,
    "assertability": {"pass": true, "warnings": ["B003-THEN-1 含模糊词'快速'"]},
    "dp_ok": true
  },
  "sem": {
    "consensus_rates": {"coverage": 1.0, "contradiction": 1.0, "gap": 0.8, "testability": 1.0},
    "blockers": []
  },
  "verdict": "pass | fail",
  "blockers": []
}
```

## 判定

- **blocker**：SQC-def 任一失败 / SQC-sem 任一 blocker（矛盾、严重缺口）→ 不冻结，回 `/sddl:spec` 修订
- **warning**：模糊词警告、coverage 偏低 → 记录，可冻结（进风险清单）
- **通过**：SQC-def 全过 + SQC-sem 无 blocker → 可进入决策点确认
