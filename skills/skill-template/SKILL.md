---
name: skill-template
description: Template starter for creating new Codex skills in this repository. Use when setting up a new skill folder with a valid SKILL.md frontmatter, agent metadata, and optional scripts, references, and assets directories.
---

# Skill Template

Copy this folder to a new skill name, then replace all placeholders.

## Minimal Setup Checklist

1. Rename folder and set `name` in frontmatter to lowercase hyphen-case.
2. Replace `description` with a complete trigger description (what it does + when to use it).
3. Replace this body with concise, task-specific workflow instructions.
4. Keep only resource folders that the new skill actually needs.
5. Set `agents/openai.yaml` `display_name`, `short_description`, and `default_prompt` for the new skill.
6. Run validator:

```bash
python3 /Users/cyberpwn/.codex/skills/.system/skill-creator/scripts/quick_validate.py /path/to/new-skill
```

## Starter Structure

Keep this structure as a baseline for new skills:

- `SKILL.md`: Required instructions and frontmatter.
- `agents/openai.yaml`: UI metadata for skill chips/listing.
- `scripts/`: Deterministic automation scripts.
- `references/`: Optional detailed docs loaded only when needed.
- `assets/`: Optional templates and files used in generated outputs.

## Template Note

Do not use this skill as-is for production tasks; clone it and customize it first.
