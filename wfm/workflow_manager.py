"""Workflow manager for cicd CLI.

Manages installation, update, and resolution of workflows and skills.

Architecture v3.0 (Global Everything):
    ~/.claude/
    ├── skills/cicd-*/SKILL.md   # Global skills
    ├── workflows/               # Global workflows
    ├── wfm.json                 # Repo config
    ├── cicd.yaml                # Global config (source repo, version)
    └── .cicd-version            # Installed version

    project/
    ├── .claude/rules/cicd-context.md  # Auto-loaded project context
    └── .cicd/
        ├── config.yaml     # Project configuration
        ├── extends/        # Project extensions (priority)
        │   ├── workflows/  # Custom workflows or overrides
        │   └── knowledge/  # Project-specific knowledge
        └── output/         # Generated outputs (plans, etc.)

Source repository: https://github.com/dgx80/cicd-workflow
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

import yaml

# GitHub repository for cicd-workflow (default)
CICD_WORKFLOW_REPO = "dgx80/cicd-workflow"


# =============================================================================
# Multi-Repo Config (wfm.json)
# =============================================================================

def get_wfm_config_path() -> Path:
    """Get the wfm.json config path (~/.claude/wfm.json)."""
    return get_global_claude_path() / "wfm.json"


def read_wfm_config() -> dict:
    """Read multi-repo config from ~/.claude/wfm.json.

    Returns:
        dict with 'repos' key containing name->repo mappings
        Example: {"repos": {"cicd": "dgx80/cicd-workflow", "other": "user/other-repo"}}
    """
    config_path = get_wfm_config_path()
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                # Ensure repos key exists
                if "repos" not in config:
                    config["repos"] = {}
                return config
        except (json.JSONDecodeError, OSError):
            return {"repos": {}}
    return {"repos": {}}


def write_wfm_config(config: dict) -> bool:
    """Write multi-repo config to ~/.claude/wfm.json."""
    config_path = get_wfm_config_path()
    try:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
        return True
    except OSError:
        return False


def get_configured_repos() -> dict[str, str]:
    """Get all configured repositories.

    Returns:
        dict mapping repo name to repo path (e.g., {"cicd": "dgx80/cicd-workflow"})
    """
    config = read_wfm_config()
    return config.get("repos", {})


def get_repo_local_path(name: str, repo: str) -> "Path":
    """Get the local path for a repo."""
    return Path(repo).expanduser().resolve()


def add_repo(name: str, repo: str) -> dict:
    """Add a repository to the config.

    Args:
        name: Short name for the repo (used as skill prefix)
        repo: GitHub repo path (e.g., "owner/repo") or local path

    Returns:
        Result dict with status and message
    """
    config = read_wfm_config()

    # Validate name (must be valid as skill prefix)
    if not name or not name.isalnum() and "-" not in name:
        return {
            "status": "error",
            "message": f"Invalid name '{name}'. Use alphanumeric characters only."
        }

    # Check if name already exists
    if name in config["repos"]:
        return {
            "status": "error",
            "message": f"Repository '{name}' already exists. Use 'wfm repo remove {name}' first."
        }

    # Check if repo path is already configured under a different name
    for existing_name, existing_repo in config["repos"].items():
        if existing_repo == repo:
            return {
                "status": "error",
                "message": f"Repository '{repo}' already configured as '{existing_name}'."
            }

    config["repos"][name] = repo

    if write_wfm_config(config):
        return {
            "status": "success",
            "message": f"Added repository '{name}' -> {repo}"
        }
    return {
        "status": "error",
        "message": "Failed to write config"
    }


def remove_repo(name: str) -> dict:
    """Remove a repository from the config, its symlinks, and the cloned repo.

    Args:
        name: Short name of the repo to remove

    Returns:
        Result dict with status and message
    """
    config = read_wfm_config()

    if name not in config["repos"]:
        return {
            "status": "error",
            "message": f"Repository '{name}' not found"
        }

    removed_repo = config["repos"].pop(name)

    # Remove all symlinks for this repo
    links_result = remove_repo_links(name)

    if write_wfm_config(config):
        return {
            "status": "success",
            "message": f"Removed repository '{name}' ({removed_repo})",
            "removed_skills": links_result.get("removed_skills", []),
            "removed_workflows": links_result.get("removed_workflows", []),
        }
    return {
        "status": "error",
        "message": "Failed to write config"
    }


def detect_skill_conflicts() -> dict:
    """Detect potential skill name conflicts across repos.

    Since skills are namespaced by repo prefix, this checks for:
    - Skills that would have the same base name (e.g., cicd-architect and other-architect)

    Returns:
        Dict with conflicts info
    """
    skills_by_base_name: dict[str, list[str]] = {}
    skills = list_global_skills_with_repo()

    for skill_name, info in skills.items():
        # Extract base name (part after the prefix)
        if "-" in skill_name:
            base_name = skill_name.split("-", 1)[1]
        else:
            base_name = skill_name

        if base_name not in skills_by_base_name:
            skills_by_base_name[base_name] = []
        skills_by_base_name[base_name].append(skill_name)

    # Find base names with multiple skills (not conflicts, but overlapping functionality)
    overlapping = {
        base: skill_list for base, skill_list in skills_by_base_name.items()
        if len(skill_list) > 1
    }

    return {
        "status": "success",
        "overlapping_skills": overlapping,
        "has_overlaps": len(overlapping) > 0
    }


# =============================================================================
# Global Paths (v2.0)
# =============================================================================

def get_global_claude_path() -> Path:
    """Get the global ~/.claude/ directory path."""
    return Path.home() / ".claude"



def get_global_skills_path() -> Path:
    """Get the global skills directory path (~/.claude/skills/)."""
    return get_global_claude_path() / "skills"


def get_global_workflows_path() -> Path:
    """Get the global workflows directory path (~/.claude/workflows/)."""
    return get_global_claude_path() / "workflows"




def get_global_config_path() -> Path:
    """Get the global cicd config path (~/.claude/cicd.yaml)."""
    return get_global_claude_path() / "cicd.yaml"


# =============================================================================
# Global Config Handler (v2.0)
# =============================================================================

def read_global_config() -> dict:
    """Read global cicd config from ~/.claude/cicd.yaml."""
    config_path = get_global_config_path()
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except (yaml.YAMLError, OSError):
            return {}
    return {}


def write_global_config(config: dict) -> bool:
    """Write global cicd config to ~/.claude/cicd.yaml."""
    config_path = get_global_config_path()
    try:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(config, f, default_flow_style=False, sort_keys=False)
        return True
    except OSError:
        return False


def get_global_installed_version() -> str | None:
    """Get the globally installed cicd-workflow version."""
    config = read_global_config()
    return config.get("installed_version")


def update_global_config_version(version: str) -> bool:
    """Update the version in global config."""
    from datetime import datetime
    config = read_global_config()
    config["version"] = "1.0"
    config["source_repo"] = CICD_WORKFLOW_REPO
    config["installed_version"] = version
    config["last_updated"] = datetime.now().strftime("%Y-%m-%d")
    return write_global_config(config)


# =============================================================================
# Skills Management (v2.0)
# =============================================================================

def is_skills_installed() -> bool:
    """Check if global skills are installed."""
    skills_path = get_global_skills_path()
    if not skills_path.exists():
        return False
    # Check for at least one cicd-* skill
    cicd_skills = list(skills_path.glob("cicd-*"))
    return len(cicd_skills) > 0


def list_global_skills() -> list[str]:
    """List all installed global skills."""
    skills_path = get_global_skills_path()
    if not skills_path.exists():
        return []
    return [d.name for d in skills_path.iterdir()
            if d.is_dir() and (d / "SKILL.md").exists()]


def list_global_skills_with_repo() -> dict[str, dict]:
    """List all installed global skills with their repo source.

    Returns:
        Dict mapping skill name to info dict with 'repo' key.
        Example: {"cicd-architect": {"repo": "cicd"}, "other-coder": {"repo": "other"}}
    """
    skills_path = get_global_skills_path()
    repos = get_configured_repos()

    if not skills_path.exists():
        return {}

    skills = {}
    for skill_dir in skills_path.iterdir():
        if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
            skill_name = skill_dir.name
            # Determine repo from prefix
            repo_name = "unknown"
            if "-" in skill_name:
                prefix = skill_name.split("-", 1)[0]
                if prefix in repos:
                    repo_name = prefix
            skills[skill_name] = {"repo": repo_name}

    return skills


def install_skills(source_path: Path, version: str | None = None, prefix: str | None = None) -> dict:
    """Install skills from source to ~/.claude/skills/.

    Args:
        source_path: Path to extracted repo
        version: Version string
        prefix: Skill name prefix (e.g., "cicd" for "cicd-architect").
                If None, keeps original skill names.
    """
    skills_path = get_global_skills_path()
    skills_path.mkdir(parents=True, exist_ok=True)

    # Look for skills in source (either skills/ or .claude/commands/)
    source_skills = source_path / "skills"
    source_commands = source_path / ".claude" / "commands"

    installed = []

    if source_skills.exists():
        # New format: skills/{prefix}-*/SKILL.md
        for skill_dir in source_skills.iterdir():
            if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
                # Get base skill name (remove any existing prefix like "cicd-")
                original_name = skill_dir.name
                base_name = original_name
                if "-" in original_name:
                    # Remove existing prefix (e.g., "cicd-architect" -> "architect")
                    base_name = original_name.split("-", 1)[1]

                # Apply new prefix if provided
                if prefix:
                    new_name = f"{prefix}-{base_name}"
                else:
                    new_name = original_name

                dst_dir = skills_path / new_name
                if dst_dir.exists():
                    shutil.rmtree(dst_dir)
                shutil.copytree(skill_dir, dst_dir)
                installed.append(new_name)
    elif source_commands.exists():
        # Legacy format: .claude/commands/*.md -> convert to skills
        for cmd_file in source_commands.glob("*.md"):
            original_name = cmd_file.stem
            base_name = original_name
            if "-" in original_name:
                base_name = original_name.split("-", 1)[1]

            # Apply new prefix if provided
            if prefix:
                skill_name = f"{prefix}-{base_name}"
            else:
                skill_name = original_name

            skill_dir = skills_path / skill_name
            skill_dir.mkdir(parents=True, exist_ok=True)

            # Read command content and convert to SKILL.md format
            content = cmd_file.read_text(encoding="utf-8")
            skill_content = convert_command_to_skill(content, skill_name)

            (skill_dir / "SKILL.md").write_text(skill_content, encoding="utf-8")
            installed.append(skill_name)

    # Update global config
    if version:
        update_global_config_version(version)

    return {
        "status": "success",
        "installed": installed,
        "count": len(installed),
        "prefix": prefix
    }




def convert_command_to_skill(content: str, skill_name: str) -> str:
    """Convert .claude/commands/*.md format to skills/*/SKILL.md format."""
    # Extract first line as description (usually "# Title - Description")
    lines = content.strip().split("\n")
    description = skill_name.replace("cicd-", "CICD ").title()

    if lines and lines[0].startswith("# "):
        title_line = lines[0][2:].strip()
        if " - " in title_line:
            description = title_line.split(" - ", 1)[1]
        else:
            description = title_line

    # Create SKILL.md with frontmatter
    skill_content = f"""---
description: "{description}"
---

{content}

## Project Context

This skill reads project-specific configuration from:
- `.claude/rules/cicd-context.md` (auto-loaded)
- `.cicd/extends/knowledge/` (legacy support)

Adapt behavior based on project context.
"""
    return skill_content


def get_project_cicd_path(project_root: Path | None = None) -> Path:
    """Get the .cicd path for the current project."""
    if project_root is None:
        project_root = Path.cwd()
    return project_root / ".cicd"


def get_installed_version(project_root: Path | None = None) -> str | None:
    """Get the installed cicd-workflow version (legacy - checks local .cicd/core/)."""
    # First check global version
    global_version = get_global_installed_version()
    if global_version:
        return global_version
    # Fallback to legacy local version
    cicd_path = get_project_cicd_path(project_root)
    version_file = cicd_path / "core" / ".version"
    if version_file.exists():
        return version_file.read_text().strip()
    return None



def _get_rules_template() -> str:
    """Return the default cicd-context.md template content."""
    return """# CICD Project Context

This file is automatically loaded by Claude Code and provides context to CICD skills.

## Stack

<!-- Define your tech stack here -->
- Language:
- Framework:
- Database:

## Tests

<!-- Define test commands -->
- Unit tests: `npm test` or `pytest`
- Lint: `npm run lint` or `ruff check`

## Conventions

<!-- Define coding conventions -->
- Code style:
- Commit format: conventional commits (feat:, fix:, etc.)
- Branch naming: feature/{issue}-{slug}

## Workflows

<!-- Override or extend workflow behavior -->
<!-- Example: skip certain validation steps, custom PR template, etc. -->
"""


def sync_repo(name: str, repo: str) -> dict:
    """Sync a single repository by creating symlinks from a local path.

    Args:
        name: Short name for the repo (used as skill prefix)
        repo: Local path to the repository

    Returns:
        Result dict with status and details
    """
    repo_path = get_repo_local_path(name, repo)

    if not repo_path.exists():
        return {
            "status": "error",
            "repo_name": name,
            "repo": repo,
            "message": f"Path does not exist: {repo_path}"
        }

    skills_created = create_skill_links(name, repo_path)
    workflows_created = create_workflow_links(name, repo_path)

    return {
        "status": "success",
        "repo_name": name,
        "repo": repo,
        "repo_path": str(repo_path),
        "skills_synced": skills_created,
        "skills_count": len(skills_created),
        "workflows_synced": workflows_created,
        "workflows_count": len(workflows_created)
    }


def sync_all() -> dict:
    """Sync all configured repositories from wfm.json.

    1. For each repo: clone if missing, then create symlinks
    2. Detect orphan skills/workflows (directories not linked)

    Returns:
        Result dict with status, synced repos, and orphans
    """
    repos = get_configured_repos()

    if not repos:
        return {
            "status": "error",
            "message": "No repositories configured. Use 'wfm repo add <name> <owner/repo>' first."
        }

    results = []
    total_skills = 0
    total_workflows = 0
    errors = []

    for name, repo in repos.items():
        result = sync_repo(name, repo)
        results.append(result)

        if result["status"] == "success":
            total_skills += result.get("skills_count", 0)
            total_workflows += result.get("workflows_count", 0)
        else:
            errors.append(f"{name}: {result.get('message', 'Unknown error')}")

    # Detect orphans
    orphan_skills = detect_orphan_skills()
    orphan_workflows = detect_orphan_workflows()
    ignored_skills = get_ignored_skills()
    ignored_workflows = get_ignored_workflows()

    if errors:
        return {
            "status": "partial",
            "message": f"Synced {total_skills} skills, {total_workflows} workflows with {len(errors)} error(s)",
            "results": results,
            "errors": errors,
            "orphan_skills": orphan_skills,
            "orphan_workflows": orphan_workflows,
            "ignored_skills": ignored_skills,
            "ignored_workflows": ignored_workflows
        }

    return {
        "status": "success",
        "message": f"Synced {total_skills} skills, {total_workflows} workflows from {len(repos)} repo(s)",
        "results": results,
        "repos_count": len(repos),
        "total_skills": total_skills,
        "total_workflows": total_workflows,
        "orphan_skills": orphan_skills,
        "orphan_workflows": orphan_workflows,
        "ignored_skills": ignored_skills,
        "ignored_workflows": ignored_workflows
    }


def list_workflows(project_root: Path | None = None) -> dict:
    """List all available workflows with their source (global/extends)."""
    global_workflows_path = get_global_workflows_path()
    cicd_path = get_project_cicd_path(project_root)
    extends_path = cicd_path / "extends"

    workflows = {}

    # Collect global workflows
    if global_workflows_path.exists():
        for wf_dir in global_workflows_path.iterdir():
            if wf_dir.is_dir() and (wf_dir / "workflow.md").exists():
                workflows[wf_dir.name] = {"source": "global", "overridden": False}

    # Collect extends workflows (override global)
    extends_workflows = extends_path / "workflows"
    if extends_workflows.exists():
        for wf_dir in extends_workflows.iterdir():
            if wf_dir.is_dir() and (wf_dir / "workflow.md").exists():
                is_override = wf_dir.name in workflows
                if is_override:
                    workflows[wf_dir.name]["overridden"] = True
                workflows[wf_dir.name] = {"source": "extends", "overridden": is_override}

    return {
        "status": "success",
        "workflows": workflows,
        "initialized": is_skills_installed(),
        "version": get_global_installed_version()
    }


def status(project_root: Path | None = None) -> dict:
    """Show which workflows are overridden."""
    listing = list_workflows(project_root)

    if listing["status"] != "success":
        return listing

    overridden_workflows = {
        name: info for name, info in listing["workflows"].items()
        if info.get("overridden") or info["source"] == "extends"
    }

    return {
        "status": "success",
        "overridden_workflows": overridden_workflows,
        "total_workflows": len(listing["workflows"]),
        "initialized": listing["initialized"],
        "version": listing["version"]
    }


def _file_hash(path: Path) -> str:
    """Calculate MD5 hash of a file."""
    hasher = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


# =============================================================================
# Migration Support (v2.0)
# =============================================================================

def has_legacy_commands(project_root: Path | None = None) -> bool:
    """Check if project has old .claude/commands/ structure."""
    if project_root is None:
        project_root = Path.cwd()
    commands_path = project_root / ".claude" / "commands"
    if commands_path.exists():
        cicd_commands = list(commands_path.glob("cicd-*.md"))
        return len(cicd_commands) > 0
    return False


def detect_migration_needed(project_root: Path | None = None) -> dict:
    """Detect if migration from old structure is needed."""
    if project_root is None:
        project_root = Path.cwd()

    has_legacy = has_legacy_commands(project_root)
    has_global_skills = is_skills_installed()
    has_project_rules = (project_root / ".claude" / "rules" / "cicd-context.md").exists()

    needs_migration = has_legacy and not has_global_skills

    return {
        "needs_migration": needs_migration,
        "has_legacy_commands": has_legacy,
        "has_global_skills": has_global_skills,
        "has_project_rules": has_project_rules,
        "recommendation": "Run 'cicd migrate' to upgrade to global skills" if needs_migration else None
    }


def migrate(project_root: Path | None = None, remove_legacy: bool = False) -> dict:
    """Migrate from old .claude/commands/ to global skills.

    Steps:
    1. Convert .claude/commands/cicd-*.md to ~/.claude/skills/cicd-*/SKILL.md
    2. Create .claude/rules/cicd-context.md template
    3. Optionally remove old .claude/commands/cicd-*.md files
    """
    if project_root is None:
        project_root = Path.cwd()

    commands_path = project_root / ".claude" / "commands"
    rules_path = project_root / ".claude" / "rules"
    skills_path = get_global_skills_path()

    # Check if migration is needed
    if not has_legacy_commands(project_root):
        return {
            "status": "not_needed",
            "message": "No legacy commands found. Nothing to migrate."
        }

    if is_skills_installed():
        return {
            "status": "already_migrated",
            "message": "Global skills already installed. Use 'cicd sync' to update."
        }

    # Find legacy command files
    legacy_files = list(commands_path.glob("cicd-*.md"))
    if not legacy_files:
        return {
            "status": "not_needed",
            "message": "No cicd-* command files found."
        }

    # Create skills directory
    skills_path.mkdir(parents=True, exist_ok=True)

    migrated = []
    for cmd_file in legacy_files:
        skill_name = cmd_file.stem  # e.g., "cicd-architect"
        skill_dir = skills_path / skill_name
        skill_dir.mkdir(parents=True, exist_ok=True)

        # Read and convert content
        content = cmd_file.read_text(encoding="utf-8")
        skill_content = convert_command_to_skill(content, skill_name)

        # Write SKILL.md
        (skill_dir / "SKILL.md").write_text(skill_content, encoding="utf-8")
        migrated.append(skill_name)

    # Create project rules template
    rules_path.mkdir(parents=True, exist_ok=True)
    cicd_context_file = rules_path / "cicd-context.md"
    if not cicd_context_file.exists():
        cicd_context_file.write_text(_get_rules_template())

    # Create global config
    from datetime import datetime
    write_global_config({
        "version": "1.0",
        "source_repo": CICD_WORKFLOW_REPO,
        "installed_version": "migrated",
        "last_updated": datetime.now().strftime("%Y-%m-%d"),
        "migrated_from": str(project_root)
    })

    # Optionally remove legacy files
    removed = []
    if remove_legacy:
        for cmd_file in legacy_files:
            cmd_file.unlink()
            removed.append(cmd_file.name)

    return {
        "status": "success",
        "message": f"Migrated {len(migrated)} skills to global location",
        "migrated_skills": migrated,
        "rules_created": str(cicd_context_file),
        "removed_files": removed if remove_legacy else [],
        "global_skills_path": str(skills_path)
    }


def migrate_config_to_wfm() -> dict:
    """Migrate from old cicd.yaml single-repo config to wfm.json multi-repo format.

    Converts:
        ~/.claude/cicd.yaml with source_repo: "owner/repo"
    To:
        ~/.claude/wfm.json with repos: {"cicd": "owner/repo"}

    Returns:
        Result dict with status and message
    """
    old_config_path = get_global_config_path()  # ~/.claude/cicd.yaml
    new_config_path = get_wfm_config_path()     # ~/.claude/wfm.json

    # Check if already migrated
    if new_config_path.exists():
        return {
            "status": "already_migrated",
            "message": "wfm.json already exists. No migration needed."
        }

    # Check if old config exists
    if not old_config_path.exists():
        # No old config, create default wfm.json
        default_config = {
            "repos": {
                "cicd": CICD_WORKFLOW_REPO
            }
        }
        if write_wfm_config(default_config):
            return {
                "status": "success",
                "message": f"Created default wfm.json with cicd -> {CICD_WORKFLOW_REPO}"
            }
        return {
            "status": "error",
            "message": "Failed to create wfm.json"
        }

    # Read old config
    old_config = read_global_config()
    source_repo = old_config.get("source_repo", CICD_WORKFLOW_REPO)

    # Create new config with repo named "cicd" (for backward compatibility)
    new_config = {
        "repos": {
            "cicd": source_repo
        },
        "migrated_from": "cicd.yaml",
        "migrated_version": old_config.get("installed_version")
    }

    if write_wfm_config(new_config):
        return {
            "status": "success",
            "message": f"Migrated cicd.yaml to wfm.json: cicd -> {source_repo}",
            "old_config": str(old_config_path),
            "new_config": str(new_config_path)
        }
    return {
        "status": "error",
        "message": "Failed to write wfm.json"
    }


def needs_config_migration() -> bool:
    """Check if migration from cicd.yaml to wfm.json is needed."""
    old_config_path = get_global_config_path()
    new_config_path = get_wfm_config_path()
    return old_config_path.exists() and not new_config_path.exists()


# =============================================================================
# Symlink-based Repo Sync (v3.0)
# =============================================================================


def get_ignored_skills() -> list[str]:
    """Get list of ignored skills from wfm.json."""
    config = read_wfm_config()
    return config.get("ignored_skills", [])


def get_ignored_workflows() -> list[str]:
    """Get list of ignored workflows from wfm.json."""
    config = read_wfm_config()
    return config.get("ignored_workflows", [])


def ignore_skill(skill_name: str) -> None:
    """Add a skill to the ignored_skills list in wfm.json."""
    config = read_wfm_config()
    if "ignored_skills" not in config:
        config["ignored_skills"] = []
    if skill_name not in config["ignored_skills"]:
        config["ignored_skills"].append(skill_name)
    write_wfm_config(config)


def ignore_workflow(workflow_name: str) -> None:
    """Add a workflow to the ignored_workflows list in wfm.json."""
    config = read_wfm_config()
    if "ignored_workflows" not in config:
        config["ignored_workflows"] = []
    if workflow_name not in config["ignored_workflows"]:
        config["ignored_workflows"].append(workflow_name)
    write_wfm_config(config)


def create_skill_links(repo_name: str, repo_path: "Path") -> list[str]:
    """Create symlinks/junctions for skills from a repo.

    Creates links: ~/.claude/skills/{repo_name}-{skill} -> {repo_path}/skills/{skill}

    Args:
        repo_name: Name of the repo (e.g., "cicd")
        repo_path: Path to the repo root

    Returns:
        List of created skill link names
    """
    from wfm import platform as plat

    repo_skills_path = repo_path / "skills"
    global_skills_path = get_global_skills_path()

    created = []

    if not repo_skills_path.exists():
        return created

    # Ensure global skills directory exists
    global_skills_path.mkdir(parents=True, exist_ok=True)

    # Create links for each skill in the repo
    for skill_dir in repo_skills_path.iterdir():
        if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
            # Skip prefix if skill name already starts with repo name
            if skill_dir.name.startswith(f"{repo_name}-"):
                link_name = skill_dir.name
            else:
                link_name = f"{repo_name}-{skill_dir.name}"
            link_path = global_skills_path / link_name

            try:
                plat.create_link(skill_dir, link_path)
                created.append(link_name)
            except Exception as e:
                print(f"Warning: Failed to create link for {link_name}: {e}")

    return created


def create_workflow_links(repo_name: str, repo_path: "Path") -> list[str]:
    """Create symlinks/junctions for workflows from a repo.

    Creates links: ~/.claude/workflows/{repo_name}-{workflow} -> {repo_path}/workflows/{workflow}

    Args:
        repo_name: Name of the repo (e.g., "cicd")
        repo_path: Path to the repo root

    Returns:
        List of created workflow link names
    """
    from wfm import platform as plat

    repo_workflows_path = repo_path / "workflows"
    global_workflows_path = get_global_workflows_path()

    created = []

    if not repo_workflows_path.exists():
        return created

    # Ensure global workflows directory exists
    global_workflows_path.mkdir(parents=True, exist_ok=True)

    # Create links for each workflow in the repo
    for wf_dir in repo_workflows_path.iterdir():
        if wf_dir.is_dir() and (wf_dir / "workflow.md").exists():
            # Skip prefix if workflow name already starts with repo name
            if wf_dir.name.startswith(f"{repo_name}-"):
                link_name = wf_dir.name
            else:
                link_name = f"{repo_name}-{wf_dir.name}"
            link_path = global_workflows_path / link_name

            try:
                plat.create_link(wf_dir, link_path)
                created.append(link_name)
            except Exception as e:
                print(f"Warning: Failed to create link for {link_name}: {e}")

    return created


def remove_repo_links(repo_name: str) -> dict:
    """Remove all symlinks/junctions for a repo.

    Args:
        repo_name: Name of the repo (e.g., "cicd")

    Returns:
        Dict with removed skills and workflows counts
    """
    from wfm import platform as plat

    skills_path = get_global_skills_path()
    workflows_path = get_global_workflows_path()

    removed_skills = []
    removed_workflows = []

    # Remove skill links
    if skills_path.exists():
        for item in skills_path.iterdir():
            if item.name.startswith(f"{repo_name}-") and plat.is_link(item):
                try:
                    plat.remove_link(item)
                    removed_skills.append(item.name)
                except Exception:
                    pass

    # Remove workflow links
    if workflows_path.exists():
        for item in workflows_path.iterdir():
            if item.name.startswith(f"{repo_name}-") and plat.is_link(item):
                try:
                    plat.remove_link(item)
                    removed_workflows.append(item.name)
                except Exception:
                    pass

    return {
        "removed_skills": removed_skills,
        "removed_workflows": removed_workflows
    }


def detect_orphan_skills() -> list[str]:
    """Detect skills that are directories (not symlinks/junctions).

    These are skills created locally (e.g., via builder) that aren't linked to a repo.

    Returns:
        List of orphan skill names
    """
    from wfm import platform as plat

    skills_path = get_global_skills_path()
    orphans = []

    if not skills_path.exists():
        return orphans

    ignored = get_ignored_skills()

    for item in skills_path.iterdir():
        if item.is_dir() and (item / "SKILL.md").exists():
            # Skip if it's a link (managed by wfm)
            if plat.is_link(item):
                continue
            # Skip if ignored
            if item.name in ignored:
                continue
            orphans.append(item.name)

    return orphans


def detect_orphan_workflows() -> list[str]:
    """Detect workflows that are directories (not symlinks/junctions).

    Returns:
        List of orphan workflow names
    """
    from wfm import platform as plat

    workflows_path = get_global_workflows_path()
    orphans = []

    if not workflows_path.exists():
        return orphans

    ignored = get_ignored_workflows()

    for item in workflows_path.iterdir():
        if item.is_dir() and (item / "workflow.md").exists():
            # Skip if it's a link (managed by wfm)
            if plat.is_link(item):
                continue
            # Skip if ignored
            if item.name in ignored:
                continue
            orphans.append(item.name)

    return orphans


def adopt_skill(skill_name: str, repo_name: str) -> dict:
    """Move an orphan skill to a repo and create a symlink back.

    Args:
        skill_name: Name of the skill to adopt
        repo_name: Name of the repo to adopt into

    Returns:
        Result dict with status
    """
    from wfm import platform as plat

    skills_path = get_global_skills_path()
    repos = get_configured_repos()
    repo = repos.get(repo_name, "")

    skill_path = skills_path / skill_name
    repo_path = get_repo_local_path(repo_name, repo)
    repo_skills_path = repo_path / "skills"

    # Validate
    if not skill_path.exists():
        return {"status": "error", "message": f"Skill '{skill_name}' not found"}

    if plat.is_link(skill_path):
        return {"status": "error", "message": f"Skill '{skill_name}' is already a link"}

    if not repo_path.exists():
        return {"status": "error", "message": f"Repository '{repo_name}' not found"}

    target_skill_path = repo_skills_path / skill_name

    # Move skill to repo
    repo_skills_path.mkdir(parents=True, exist_ok=True)

    if target_skill_path.exists():
        return {"status": "error", "message": f"Skill '{skill_name}' already exists in repo '{repo_name}'"}

    shutil.move(str(skill_path), str(target_skill_path))

    # Create link back with repo prefix
    link_name = f"{repo_name}-{skill_name}"
    link_path = skills_path / link_name

    try:
        plat.create_link(target_skill_path, link_path)
    except Exception as e:
        return {"status": "error", "message": f"Failed to create link: {e}"}

    return {
        "status": "success",
        "message": f"Adopted '{skill_name}' into '{repo_name}' as '{link_name}'",
        "original_name": skill_name,
        "new_name": link_name,
        "repo_path": str(target_skill_path)
    }


def adopt_workflow(workflow_name: str, repo_name: str) -> dict:
    """Move an orphan workflow to a repo and create a symlink back.

    Args:
        workflow_name: Name of the workflow to adopt
        repo_name: Name of the repo to adopt into

    Returns:
        Result dict with status
    """
    from wfm import platform as plat

    workflows_path = get_global_workflows_path()
    repos = get_configured_repos()
    repo = repos.get(repo_name, "")

    workflow_path = workflows_path / workflow_name
    repo_path = get_repo_local_path(repo_name, repo)
    repo_workflows_path = repo_path / "workflows"

    # Validate
    if not workflow_path.exists():
        return {"status": "error", "message": f"Workflow '{workflow_name}' not found"}

    if plat.is_link(workflow_path):
        return {"status": "error", "message": f"Workflow '{workflow_name}' is already a link"}

    if not repo_path.exists():
        return {"status": "error", "message": f"Repository '{repo_name}' not found"}

    target_workflow_path = repo_workflows_path / workflow_name

    # Move workflow to repo
    repo_workflows_path.mkdir(parents=True, exist_ok=True)

    if target_workflow_path.exists():
        return {"status": "error", "message": f"Workflow '{workflow_name}' already exists in repo '{repo_name}'"}

    shutil.move(str(workflow_path), str(target_workflow_path))

    # Create link back with repo prefix
    link_name = f"{repo_name}-{workflow_name}"
    link_path = workflows_path / link_name

    try:
        plat.create_link(target_workflow_path, link_path)
    except Exception as e:
        return {"status": "error", "message": f"Failed to create link: {e}"}

    return {
        "status": "success",
        "message": f"Adopted '{workflow_name}' into '{repo_name}' as '{link_name}'",
        "original_name": workflow_name,
        "new_name": link_name,
        "repo_path": str(target_workflow_path)
    }
