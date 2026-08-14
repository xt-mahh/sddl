<div align="center">

# 🔄 SDDL — Spec-Driven Development Loop

**Agent Skill: A dual-loop development methodology with a structured Spec as the single source of truth**

> **Languages:** [English](README.md) | [中文](README_zh.md)

![SDDL Logo](assets/logo.png)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![PyYAML](https://img.shields.io/badge/PyYAML-required-green.svg)](https://pyyaml.org/)
[![GitHub stars](https://img.shields.io/github/stars/xt-mahh/sddl)](https://github.com/xt-mahh/sddl)

*Define clearly what to build, then write the code.*

</div>

---

## Table of Contents

- [Why SDDL?](#why-sddl)
- [Dual-Loop Architecture](#dual-loop-architecture)
- [Core Features](#core-features)
- [Quick Start (Agent Integration)](#quick-start-agent-integration)
- [Skill Structure](#skill-structure)
- [Multi-Platform Support](#multi-platform-support)
- [Project Structure](#project-structure)
- [Methodology Core](#methodology-core)
- [Evidence Base](#evidence-base)
- [When to Use](#when-to-use)
- [License](#license)

---

## Why SDDL?

Three core pain points of AI-powered programming:

| Pain Point | Essence | Consequence |
|------------|---------|-------------|
| **Context Drift** | The longer the conversation, the more the AI forgets early agreements | Round 51 overrides the interface contract agreed in Round 3 |
| **Artifact Desync** | Code changes but tests/docs lag behind | "Documentation lies" amplified in the AI era |
| **Subjective Acceptance** | "Feels right" replaces "matches spec" | Not auditable, not reproducible, not handover-able |

The problem with conversational programming: **context windows are finite, and the longer you chat, the more it drifts**. Chat with an AI for 50 rounds, and by round 51 it has forgotten the interface format agreed in round 3.

**SDDL's answer**: use a stable, fully-loadable Spec as the single source of truth, and guarantee quality and auditability through a dual-loop closed loop.

## Dual-Loop Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                   Formation Loop (answering "what")                  │
│  Requirements ─▶ Interview ─▶ Spec Draft ─▶ SQC Check ─▶ Decision    │
│  Points Confirmation ─▶ Freeze                                      │
└───────────────────────────────────────────────┬─────────────────────┘
                                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   Derivation Loop (answering "how")                  │
│  Frozen Spec ─▶ tests/code/docs ─▶ C1-C4 Consistency Checks ─▶      │
│  Converged                                                          │
│        ▲                                        │                    │
│        └──── spec defects ─▶ unfreeze ─▶ back to Formation Loop ─┘  │
└─────────────────────────────────────────────────────────────────────┘
```

- **Formation Loop**: guarantees "doing the right thing" — requirements → interview → spec draft (with decision-point markers) → SQC quality check → human confirmation of decision points → freeze
- **Derivation Loop**: guarantees "doing the thing right" — frozen spec → synchronized derivation of tests/code/docs → C1-C4 layered consistency checks → convergence
- **Write-back channel**: spec defects found during implementation → unfreeze → back to Formation Loop for revision → re-freeze (never bypassing the quality gate)

## Core Features

| Feature | Description |
|---------|-------------|
| **Decision Points** | Where requirements are ambiguous, the AI doesn't silently decide — it marks a decision point and the user confirms it via interactive prompts (with custom input support) |
| **SQC Quality Check** | Quality gate for the spec itself — **deterministic checks by scripts** (schema validity / reference integrity / assertability) **+ semantic review by agent LLM** (behavior coverage / contradictions / completeness) |
| **C1-C4 Layered Checks** | Consistency between artifacts and spec — **deterministic evidence by scripts** (interface comparison / test execution / doc symbol table) **+ semantic review by agent LLM** (does the test really cover the behavior? does the code really match the spec?) |
| **Directory-as-State** | Progress is encoded in directory structure — interruption recovery is free (with git commits as checkpoints) |
| **Budget Control** | Three budgets (formation/implementation/revision), quantified degradation paths, revision incentives that don't punish honesty |
| **Auditable** | Every decision-point confirmation record, every revision CHANGELOG, every check report JSON — fully traceable |

## Quick Start (Agent Integration)

### Option A: Install as an Agent Skill (Recommended)

The core deliverable is an **Agent Skill** (in [`integrations/`](integrations/)). Once installed, the agent gains 8 staged commands:

```bash
# Hermes:
cp -r integrations/hermes ~/.hermes/skills/software-development/sddl

# Other agents (Claude Code / OpenCode / OpenClaw): see "Multi-Platform Support" below
```

Trigger in conversation (auto-loaded, or explicit commands):

```
/sddl:init        # Initialize project (create directory structure)
/sddl:interview   # Layered requirements interview
/sddl:spec        # Generate spec draft + decision-point markers
/sddl:confirm     # Confirm decision points interactively (with custom input)
/sddl:freeze      # SQC check + freeze
/sddl:derive      # Derive tests/code/docs from the spec
/sddl:verify      # C1-C4 consistency checks + convergence verdict
/sddl:archive     # Archive changes
```

**Full workflow**: `/sddl:init → /sddl:interview → /sddl:spec → /sddl:confirm → /sddl:freeze → /sddl:derive → /sddl:verify → /sddl:archive`

### Option B: Use Checker Scripts Only (No Agent Environment)

If you're not using Hermes, the checker scripts run standalone (as CI gates or manual checks):

```bash
pip install pyyaml

# SQC check (before spec freeze)
python3 scripts/check_sqc.py sddl/specs/<domain>/spec.yaml --verbose

# C1-C4 consistency check (at verify time)
python3 scripts/check_c1_c4.py . --verbose

# State recovery (after interruption)
python3 scripts/sddl_status.py .
```

Example output:

```bash
$ python3 scripts/check_sqc.py sddl/specs/accounting/spec.yaml --verbose
SQC [0.1.1]: ✅ PASS
  ✅ def-schema
  ✅ def-refs
  ✅ def-assertability
  ✅ def-dp
  ✅ sem-coverage
  ✅ sem-contradiction
  ✅ sem-testability

$ python3 scripts/check_c1_c4.py . --verbose
C1-C4 [accounting v0.1.1]: ✅ CONVERGED
  ✅ c1_def
  ✅ c2_def
  ✅ c3
  ✅ c4b_def
  soft: c1_sem=1.0 c2_sem=1.0 c4a=1.0 c4b_sem=1.0 must=1.0
```

A complete example is in [`examples/accounting/`](examples/accounting/) — a full project from "build me a bookkeeping app" to converged delivery (including spec, decision-point confirmations, SQC/C1-C4 reports, and change history).

## Skill Structure

The Skill version lives in [`integrations/`](integrations/):

```
integrations/
├── hermes/                      Hermes Agent Skill (complete)
│   ├── SKILL.md                 Main entry + 8 staged commands
│   ├── references/ (5)          Progressive-disclosure guides (loaded on demand, not all at once)
│   ├── scripts/ (3)             Checkers (identical to root scripts/)
│   └── templates/ (2)           Spec skeleton + decision summary
├── claude-code/                 (planned)
└── opencode/                    (planned)
```

**Why a skill rather than a plain tool**: SDDL's 8 commands are **conversational interaction flows** (interview, confirmation, check reports) — not something a pure CLI can express. The skill lets the agent execute this workflow directly, with humans stepping in only at key checkpoints (decision-point confirmation, freeze approval).

## Multi-Platform Support

SDDL's **methodology core is platform-agnostic** — `references/` (methodology guides), `scripts/` (checkers), and `templates/` (templates) don't depend on any specific agent:

| Component | Platform-Dependent | Description |
|-----------|-------------------|-------------|
| `references/` methodology guides | ❌ No | Pure Markdown, readable by any agent |
| `scripts/` checkers | ❌ No | Pure Python CLI, runs in any environment |
| `templates/` templates | ❌ No | Pure YAML/Markdown |
| `integrations/hermes/` | ✅ Hermes | Leverages Hermes' skill/slash-command/clarify mechanisms |
| `integrations/claude-code/` | ✅ Claude Code | Planned (CLAUDE.md + slash commands) |
| `integrations/opencode/` | ✅ OpenCode | Planned (AGENTS.md) |

**Integration principle**: write the methodology core + checkers once; each platform only needs a thin "shell" (mapping the 8 commands to that platform's interaction mechanisms). If your agent isn't listed yet, copy the workflow from `integrations/hermes/SKILL.md` into your agent's rules file (e.g., `CLAUDE.md` / `AGENTS.md`) — the checker scripts are directly reusable.

## Project Structure

```
sddl/
├── scripts/                     Checker scripts (directly runnable)
│   ├── check_sqc.py             SQC check (Formation Loop gate)
│   ├── check_c1_c4.py           C1-C4 consistency check (Derivation Loop gate)
│   └── sddl_status.py           State recovery (directory-as-state)
├── references/                  Methodology guides (progressive disclosure)
│   ├── formation-loop.md        Formation Loop detailed workflow
│   ├── derivation-loop.md       Derivation Loop detailed workflow
│   ├── spec-schema.md           Spec 5-layer structure
│   ├── sqc-checklist.md         SQC check checklist
│   └── checker-matrix.md        C1-C4 check matrix
├── templates/                   Spec skeleton + decision summary templates
├── examples/                    Complete example projects
│   └── accounting/              Bookkeeping/reconciliation service (zero to converged)
├── integrations/                Per-platform agent adapters (Hermes done; Claude Code/OpenCode planned)
├── docs/                        Final methodology (v1.1)
└── LICENSE
```

## Methodology Core

### Spec 5-Layer Structure

| Layer | Content | Machine-Consumable |
|-------|---------|-------------------|
| L1 Interface Contract | Function signatures, params, returns, error types | Fully (type checking / AST) |
| L2 Data Models | JSON Schema | Fully (schema validation) |
| L3 Behavior Description | GWT scenarios + priority | Partially (structure parseable) |
| L4 Boundary Conditions | Explicit edge cases + priority | Partially |
| L5 Quality Constraints | Performance/security/observability | Weakly (perf marked as env) |

### Convergence Verdict

```
Hard gate: C1-def ∧ C2-def ∧ C3 ∧ C4b-def all pass (deterministic)
Soft consensus: c1_sem≥0.95 ∧ c2_sem≥0.95 ∧ c4a≥0.90 ∧ c4b_sem≥0.90 (checklist voting)
And must coverage = 100%, no blocker violations → converged
```

### Check Matrix

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

## Evidence Base

SDDL's design is validated by literature (arXiv papers) and three rounds of review loops:

- **Self-Refine** (arXiv 2303.17651) — origin of the self-refine loop paradigm
- **Pride and Prejudice** (arXiv 2402.11436) — LLM self-feedback amplifies self-bias → cross-model checking
- **TICKing All the Boxes** (arXiv 2410.07061) — checklist generation improves LLM evaluation
- **Calibration Collapse Under Sycophancy** (arXiv 2026-04) — absolute scores unreliable → objective vote counting
- **LLMorpheus** (arXiv 2404.09954) — LLM mutation testing → acceptance reverse verification
- **OpenSpec** (Fission-AI) — specs/+changes/+archive change management practice

Full evidence chain in [`docs/SDDL-方案-v1.1.md`](docs/SDDL-方案-v1.1.md) Appendix A (Chinese).

## When to Use

| Mode | Applicability | Cost |
|------|---------------|------|
| Full SDDL | ≥8 interfaces and ≥10 must-level acceptances, multi-artifact sync | High |
| Standard SDDL | 5-8 interfaces | Medium |
| Light SDD | <5 interfaces but multi-artifact | Low |
| Pure TDD | everything else | Lowest |

**Not for**: one-off scripts, prototypes/POCs, exploratory research code.

## License

MIT License — see [LICENSE](LICENSE)

## Acknowledgements

- Methodology refined through 3 review loops (35 issues closed) + 2 rounds of literature validation (17 arXiv papers + OpenSpec practice)
- The Hermes Agent Skill version validated through 8 staged commands + 7 test scenarios
