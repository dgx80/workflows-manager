# Implementation Plan: Global Skills + Project Rules Architecture

**Issue**: #6 - feat: Migrate to global Skills + project Rules architecture
**Branch**: `feature/6-global-skills-architecture`
**Date**: 2026-01-31

---

## Executive Summary

Migrate from per-project `.claude/commands/` to global `~/.claude/skills/` with project-specific context via `.claude/rules/`. This enables generic workflows that adapt to each project without copy/sync issues.

---

## Architecture Overview

### Current State
```
project/
├── .claude/commands/cicd-*.md    # Copied per project (sync issues)
└── .cicd/
    ├── core/agents/*.yaml        # Downloaded from release
    └── extends/knowledge/        # Project overrides
```

### Target State
```
~/.claude/
├── skills/cicd-*/SKILL.md        # Global generic workflows
└── cicd.yaml                     # Global config (source repo)

project/
├── .claude/rules/cicd-context.md # Auto-loaded project context
└── .cicd/
    ├── config.yaml               # Project config
    └── extends/knowledge/        # Legacy support
```

---

## New Files Structure

### Global Skills (`~/.claude/skills/`)

```
~/.claude/skills/
├── cicd-analyst/SKILL.md
├── cicd-architect/SKILL.md
├── cicd-builder/SKILL.md
├── cicd-cicd/SKILL.md
├── cicd-coder/SKILL.md
├── cicd-master/SKILL.md
├── cicd-pm/SKILL.md
├── cicd-tester/SKILL.md
└── cicd-maintain/SKILL.md        # NEW: Maintenance skill
```

### Global Config (`~/.claude/cicd.yaml`)

```yaml
# CICD Global Configuration
version: "1.0"
source_repo: "dgx80/cicd-workflow"
installed_version: "v1.0.0"
last_updated: "2026-01-31"

# Future: multi-repo support
# sources:
#   - repo: "dgx80/cicd-workflow"
#     skills: ["cicd-*"]
#   - repo: "company/custom-workflows"
#     skills: ["custom-*"]
```

### Project Rules Template (`.claude/rules/cicd-context.md`)

```markdown
# CICD Project Context

## Stack
<!-- Define your tech stack -->

## Tests
<!-- Define test commands -->

## Conventions
<!-- Define coding conventions -->

## Workflows
<!-- Override or extend workflow behavior -->
```

---

## Implementation Phases

### Phase 1: Core Infrastructure
**Estimated complexity**: Medium

1. **Create skill format converter**
   - Convert `.claude/commands/*.md` → `skills/*/SKILL.md`
   - Preserve all content, adjust paths if needed

2. **Update `workflow_manager.py`**
   - Add `get_global_skills_path()` → `~/.claude/skills/`
   - Add `get_global_config_path()` → `~/.claude/cicd.yaml`
   - Modify `init()` to install skills globally
   - Modify `update()` to update global skills only

3. **Create global config handler**
   - Read/write `~/.claude/cicd.yaml`
   - Track installed version
   - Store source repo config

### Phase 2: CLI Commands
**Estimated complexity**: Low

1. **Modify `cicd init`**
   - Install skills to `~/.claude/skills/cicd-*/`
   - Create `~/.claude/cicd.yaml` if not exists
   - Create `.claude/rules/cicd-context.md` (minimal template)
   - Keep `.cicd/` structure for workflows/knowledge

2. **Modify `cicd update`**
   - Update `~/.claude/skills/` from source repo
   - Update `~/.claude/cicd.yaml` version
   - Never touch `.claude/rules/`

3. **Add `cicd sync`**
   - Force re-download and reinstall skills
   - Useful after manual changes or corruption

### Phase 3: Maintenance Skill
**Estimated complexity**: Medium

Create `/cicd-maintain` skill for editing global skills from this repo:

```markdown
# CICD Maintain - Global Skills Editor

## Purpose
Edit and manage global CICD skills structure from the maintenance repo.

## Capabilities
1. Edit skill files in ~/.claude/skills/cicd-*/
2. Validate skill structure
3. Suggest commits to sync changes back to repo
4. Fast commit flow (no long waits)

## Workflow
1. User invokes /cicd-maintain
2. Show current skills status
3. Allow editing via menu:
   - Edit skill content
   - Add new skill
   - Remove skill
   - Validate all skills
4. On save: suggest git add + commit
5. Remind to push and create release
```

### Phase 4: Migration Support
**Estimated complexity**: Low

1. **Backward compatibility**
   - Detect old `.claude/commands/` structure
   - Offer migration path
   - Keep `.cicd/extends/` working

2. **Migration command**
   - `cicd migrate` - one-time migration helper
   - Moves commands → skills
   - Updates config

---

## File Changes

### New Files
| File | Purpose |
|------|---------|
| `skills/cicd-maintain/SKILL.md` | Maintenance skill for editing global structure |
| `templates/cicd-context.md` | Template for project rules |
| `templates/cicd.yaml` | Template for global config |

### Modified Files
| File | Changes |
|------|---------|
| `cicd/workflow_manager.py` | Add global paths, modify init/update |
| `cicd/cli.py` | Add sync command, update init/update |

### Deprecated (but kept for compatibility)
| File | Status |
|------|--------|
| `.claude/commands/*.md` | Replaced by skills |
| `agents/*.yaml` | Keep for reference, skills are source of truth |

---

## Skills Content Migration

Each skill will follow Claude Code's SKILL.md format:

```markdown
---
description: "Short description for /help"
argument-hint: "optional args"
---

# Skill Name

[Full skill content from current .claude/commands/*.md]

## Project Context

This skill reads project-specific configuration from:
- `.claude/rules/cicd-context.md` (auto-loaded)
- `.cicd/extends/knowledge/` (legacy support)

Adapt behavior based on project context.
```

---

## Testing Plan

1. **Unit tests**
   - `test_global_paths()` - verify path resolution
   - `test_init_creates_skills()` - verify skill installation
   - `test_update_preserves_rules()` - verify rules not touched

2. **Integration tests**
   - Fresh install on new machine
   - Update from old version
   - Migration from commands to skills

3. **Manual validation**
   - Test on Windows (no symlink issues)
   - Test skill invocation via `/cicd-*`
   - Test rules auto-loading

---

## Rollout Strategy

1. **v2.0.0-alpha**: New architecture, parallel to old
2. **v2.0.0-beta**: Migration tooling, deprecation warnings
3. **v2.0.0**: Full release, old structure deprecated
4. **v2.1.0**: Remove deprecated code

---

## Delegation

**Implementation**: Delegate to **CICD Coder** with this plan.

**Order of implementation**:
1. Phase 1: Core Infrastructure (foundation)
2. Phase 2: CLI Commands (user-facing)
3. Phase 3: Maintenance Skill (self-editing capability)
4. Phase 4: Migration Support (backward compat)

---

## Open Questions

1. ~~Maintenance skill invocation~~ → `/cicd-maintain`
2. ~~Global config location~~ → `~/.claude/cicd.yaml`
3. ~~Rules template style~~ → Minimal (maintain skill handles setup)
4. Should we support multiple source repos in v2.0 or defer?

---

## References

- Issue #6: https://github.com/dgx80/cicd-workflow/issues/6
- Claude Code Skills: https://code.claude.com/docs/en/slash-commands
- CLAUDE.md Guide: https://www.builder.io/blog/claude-md-guide
