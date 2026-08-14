# LLM 审核操作指南（语义层主路径）

> **核心原则**：SDDL 的语义审核（SQC-sem / C1-sem / C2-sem / C4a / C4b-sem）由 **agent 的 LLM 能力**执行，不是脚本启发式。
> 脚本只负责**确定性证据**（类型检查/测试执行/符号表/YAML），LLM 基于证据做**语义判断**。

## 为什么 LLM 审核而不是脚本

| 能力 | 脚本启发式 | LLM 审核 |
|------|-----------|----------|
| 判断"THEN 是否可断言" | 模糊词正则（假阴性爆炸，T1 实测 0.48） | 理解语义：可转化为具体断言？ |
| 判断"测试是否真覆盖行为" | 关键词匹配（错位/遗漏） | 读测试逻辑：真的在测这个行为？ |
| 判断"行为是否矛盾" | GIVEN 完全相等才触发（漏判） | 理解两个行为在什么条件下冲突 |
| 判断"spec 是否完整" | 需求词匹配（误报） | 对比需求陈述与 spec 覆盖 |
| 判断"docs 是否描述真实能力" | API 符号表（只查存在） | 理解 docs 宣称 vs 实现行为 |

**结论**：语义理解是 LLM 的本职，脚本不该假装会。脚本的价值在**提供事实**，不是**下判断**。

## 审核流程（每次语义检查）

### 1. 收集证据（脚本执行）

```
python3 scripts/check_sqc.py sddl/specs/<domain>/spec.yaml --json
python3 scripts/check_c1_c4.py . --json
```

- 脚本输出**事实**：schema 是否合法、引用是否完整、测试是否通过、接口是否存在
- 这些是**确定性证据**，LLM 审核时引用（不重复判断）

### 2. LLM 逐项审核（agent 执行）

对每个软条件检查项，agent 基于证据 + 自身理解判断：

```
【C1-sem 审核】测试是否真正覆盖了 spec 的验收标准？

证据（来自脚本）：
- B003 对应测试 test_detectDiscrepancy_none，断言 has_discrepancy is False
- B004 对应测试 test_detectDiscrepancy_found，断言 has_discrepancy is True

你的判断（LLM 语义理解）：
- B003 的 THEN "has_discrepancy=false, differences 为空" → 测试断言了 has_discrepancy，
  但没断言 differences 为空 → 部分覆盖（缺 differences 断言）
- B004 的 THEN "has_discrepancy=true, differences 包含差异条目" → 测试断言了 len>0，
  但没断言具体条目内容 → 部分覆盖
→ 判定：C1-sem 未完全达标，B003/B004 需补差异断言
```

### 3. 输出结构化判定（LLM 产出）

```json
{
  "layer": "c1_sem",
  "items": [
    {
      "id": "B001-THEN-1",
      "verdict": "covered | partial | not_covered | non_verifiable",
      "evidence": "test_xxx 断言了 ...",
      "gap": "缺 ... 断言"
    }
  ],
  "summary": "8/13 完全覆盖，3 部分覆盖，2 未覆盖",
  "blockers": ["B007 无测试"]
}
```

## 对抗式审核（防自证循环）

**审核 prompt 的默认立场**：不是"确认一致"，而是"找不一致"。

```
你是一个 adversarial reviewer。你的任务是找出 spec 与 artifacts 之间的不一致。
不要试图确认它们一致——你的工作假设是它们一定不一致，需要找到证据。

审核要点：
1. 测试真的在测 spec 说的行为吗？（还是测了别的、或测了个空壳？）
2. 代码真的实现了 spec 的所有 THEN 子句吗？（还是跳过了某些？）
3. docs 描述的能力 code 真的有吗？（还是文档超前于实现？）
4. 行为之间有没有隐藏冲突？

如果你经过彻底检查后确实找不到不一致，才报告 "no evidence found"。
注意：找不到证据 ≠ 一致——那是"未发现"，不是"已验证"。
```

## 审核分级

| 判定 | 含义 | 动作 |
|------|------|------|
| `covered` | 明确覆盖 | 计通过 |
| `partial` | 部分覆盖（缺某子句断言） | 计通过但进风险清单；must 级 → 要求补 |
| `not_covered` | 未覆盖 | 计失败，路由 |
| `non_verifiable` | 无法从材料判断 | 标记，不阻塞（进风险清单） |
| `evidence_missing` | 无法判断且无证据 | 要求补证据（读更多代码/测试） |

## 与脚本的接口

```
脚本（确定性）           LLM（语义）
─────────────────────────────────────────────
C1-def L1/L2    ────▶    C1-sem 覆盖判断
（标签/断言提取）           （断言是否真覆盖行为）
C2-def          ────▶    C2-sem 行为一致性
（接口/签名存在）           （实现是否真符合行为）
C3              ────▶    （测试通过是硬事实，LLM 不重复判断）
（测试执行）
C4b-def         ────▶    C4a/C4b-sem 文档真实性
（符号表存在）              （文档宣称 vs 实际能力）
SQC-def         ────▶    SQC-sem 质量判断
（schema/引用/模糊词）      （覆盖/矛盾/完整性）
```

## 审计

LLM 审核产出写入 `checks/*.json`：
- `deterministic_evidence`：脚本事实（可重跑）
- `semantic_evidence`：LLM 判定（记录模型/审核 prompt 版本/判定项集版本——可审计不可复现）

**审核不是黑盒**：每个判定必须附证据（引用了哪个文件哪行、或引用脚本哪条输出）。无证据的判定无效。
