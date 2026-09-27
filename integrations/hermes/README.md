# Hermes 适配（已单一来源化）

本目录曾是 `skills/sddl/` 的完整副本（SKILL.md + references/ + scripts/ + templates/），
为消除双份维护漂移（历史上两份确实分叉过：2.1.1 的「按序重验架构」内容一度只存在于
本副本），现已**单一来源化为 [`skills/sddl/`](../../skills/sddl/)**，本目录仅保留安装指引。

## Hermes 安装

```bash
cp -r skills/sddl ~/.hermes/skills/software-development/sddl
```

skill 内容平台无关（纯 Markdown + 纯 Python CLI），Hermes 无需任何适配层；
`SKILL.md` frontmatter 的 `metadata.hermes` 标签随 `skills/sddl/SKILL.md` 一并生效。

## 其他平台

- **ZCode**：直接安装本仓库插件（Settings → Plugin Management → Discover 添加本仓库，见根 README 方式 A）
- **Claude Code / OpenCode**：规划中，同样将从 `skills/sddl/` 安装
