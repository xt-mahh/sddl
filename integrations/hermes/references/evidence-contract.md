# 证据契约（Evidence Contract）——确定性证据的泛化机制

> 解决的问题：参考检查器（check_sqc / check_arch / check_c1_c4）内置 Python 生态假设
> （`*.py` / `ast` / `src/` 顶层包 / pytest），非 Python 技术栈项目上 `--with-imports`
> 等代码级检查**静默产出空证据**——门禁表面 pass，def 层从未生效，C-arch-sem / C1-sem
> 也拿不到事实可审。这是 dogfooding 实测缺陷（localsub JS 项目，2026-09-20）。

## 三层分工

```
┌─ 第一层：证据契约（框架，稳定不变）────────────────────────┐
│  定义各检查维度的证据 schema 与语义：                       │
│  - C-arch-def2: import_graph = {模块: [依赖首段...]}        │
│  - C-arch-def3: dir_facts = {模块: 存在/缺失/空/外部栈}     │
│  - C1/C3: 测试执行结果 (passed/total/failed/skipped)       │
│  - C2-def/C4b: 符号表 {符号: 是否导出}                     │
│  契约 = schema + 字段语义，与语言无关                       │
├─ 第二层：参考收集器（框架，可选实现）──────────────────────┤
│  scripts/ 下内置的 Python 实现，覆盖最常见场景              │
│  ⚠️ 定位是"参考"，不是"唯一"；边界之外显式降级（见下）       │
├─ 第三层：项目收集器（项目资产，agent 首次构造，git 固化）──┤
│  非内置技术栈时，agent 按 skill 规范现场构造               │
│  → 落盘 sddl/checks/<name>.<ext> → commit → 后续只重跑    │
└──────────────────────────────────────────────────────────┘
```

## 项目收集器构造规范（agent 操作纪律）

**何时构造**：参考收集器显式降级时——check_arch.py 报
`非 Python 技术栈 ... 须按 evidence-contract.md 构造项目收集器`，
或 check_c1_c4.py 找不到可执行的测试套件。

**怎么构造**：
1. 按 evidence-contract 的目标 schema 实现（输出与参考收集器同构的 `--json` 结构）
2. 语言对应的 import 解析：ESM 用 `import ... from '...'` 正则 + 相对路径解析；
   TS 同 ESM；Go 用 `go/parser` 或正则；无法静态解析时输出 `evidence_limited: true` 并注明
3. 落盘 `sddl/checks/collect_evidence.<ext>`（项目根，不进框架）
4. **构造即固化**：立刻 git commit。此后每次 verify 只重跑、**禁止重构**——
   证据必须确定性可复现；要改收集器 = 改判卷题，须在 commit message 说明理由

**为什么禁止每次重构**：C1-def 打破自证循环的根基是"def 层证据确定性可复现"。
若收集器每次现场重写，agent 可（有意或无意）写出漏抓 import 的正则 → "证据"显示
无越界 → def2 假 pass——自证循环从 spec 层转移到收集器层（pitfall #12 变体：
checker 单测绿 ≠ 检查器可靠，何况每次都是新 checker）。

## 显式降级原则（收集器通用纪律）

参考收集器遇到边界外输入，**必须显式 fail 或 warn**，绝不静默产出空证据：

| 情形 | 行为 |
|------|------|
| 模块目录为非 Python 技术栈（有 .js/.ts/.go 等） | `C-arch-def2` fail + 提示构造项目收集器 |
| 目录存在但无任何代码文件 | `C-arch-def3` fail（真问题） |
| 目录不存在 | `C-arch-def3` fail |

## 判决分工不变

收集器（无论参考还是项目级）**只产事实，不做语义判断**。
C-arch-sem 职责内聚、C1-sem 测试真覆盖等软条件仍然全部由 agent LLM 基于
收集器产出的证据裁决（见 llm-review.md）。

## 已知局限

- 参考收集器的 import 解析是"首段对齐"近似（Python 顶层包约定）；
  项目收集器可按自身语言的模块解析规则做更精确的实现
- path 重叠/嵌套在 C-arch-struct 显式 fail（文件归属无判据），要求物理隔离
  （子模块代码移独立子目录）——这是故意的设计约束，不是待修 bug
