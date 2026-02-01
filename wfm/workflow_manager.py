"""Workflow manager for cicd CLI.

Manages installation, update, and resolution of workflows and skills.

Architecture v3.0 (Global Everything):
    ~/.claude/
    ├── skills/cicd-*/SKILL.md   # Global skills
    ├── workflows/               # Global workflows
    ├── schemas/                 # Global schemas
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
import tempfile
import zipfile
from pathlib import Path

import yaml

# GitHub repository for cicd-workflow
CICD_WORKFLOW_REPO = "dgx80/cicd-workflow"
CICD_WORKFLOW_URL = f"https://github.com/{CICD_WORKFLOW_REPO}"


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


def get_global_schemas_path() -> Path:
    """Get the global schemas directory path (~/.claude/schemas/)."""
    return get_global_claude_path() / "schemas"


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
    """List all installed global cicd skills."""
    skills_path = get_global_skills_path()
    if not skills_path.exists():
        return []
    return [d.name for d in skills_path.iterdir()
            if d.is_dir() and d.name.startswith("cicd-") and (d / "SKILL.md").exists()]


def install_skills(source_path: Path, version: str | None = None) -> dict:
    """Install skills from source to ~/.claude/skills/."""
    skills_path = get_global_skills_path()
    skills_path.mkdir(parents=True, exist_ok=True)

    # Look for skills in source (either skills/ or .claude/commands/)
    source_skills = source_path / "skills"
    source_commands = source_path / ".claude" / "commands"

    installed = []

    if source_skills.exists():
        # New format: skills/cicd-*/SKILL.md
        for skill_dir in source_skills.iterdir():
            if skill_dir.is_dir() and skill_dir.name.startswith("cicd-"):
                dst_dir = skills_path / skill_dir.name
                if dst_dir.exists():
                    shutil.rmtree(dst_dir)
                shutil.copytree(skill_dir, dst_dir)
                installed.append(skill_dir.name)
    elif source_commands.exists():
        # Legacy format: .claude/commands/cicd-*.md -> convert to skills
        for cmd_file in source_commands.glob("cicd-*.md"):
            skill_name = cmd_file.stem  # e.g., "cicd-architect"
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
        "count": len(installed)
    }


def install_core(source_path: Path, version: str | None = None) -> dict:
    """Install workflows and schemas from source to ~/.claude/."""
    workflows_path = get_global_workflows_path()
    schemas_path = get_global_schemas_path()

    installed_workflows = []
    installed_schemas = []

    # Install workflows
    source_workflows = source_path / "workflows"
    if source_workflows.exists():
        if workflows_path.exists():
            shutil.rmtree(workflows_path)
        shutil.copytree(source_workflows, workflows_path)
        installed_workflows = [d.name for d in workflows_path.iterdir() if d.is_dir()]

    # Install schemas
    source_schemas = source_path / "schemas"
    if source_schemas.exists():
        if schemas_path.exists():
            shutil.rmtree(schemas_path)
        shutil.copytree(source_schemas, schemas_path)
        installed_schemas = [f.name for f in schemas_path.iterdir() if f.is_file()]

    # Write version file
    version_file = get_global_claude_path() / ".cicd-version"
    version_file.write_text(version or "unknown")

    return {
        "status": "success",
        "workflows": installed_workflows,
        "schemas": installed_schemas,
        "workflows_count": len(installed_workflows),
        "schemas_count": len(installed_schemas)
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


def get_latest_version() -> str | None:
    """Get the latest release version from GitHub."""
    try:
        result = subprocess.run(
            ["gh", "release", "view", "--repo", CICD_WORKFLOW_REPO, "--json", "tagName"],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return data.get("tagName")
    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
        pass
    return None


def download_release(version: str | None = None, target_dir: Path | None = None) -> dict:
    """Download a cicd-workflow release from GitHub."""
    if target_dir is None:
        target_dir = Path(tempfile.mkdtemp())

    # Build gh release download command
    cmd = ["gh", "release", "download", "--repo", CICD_WORKFLOW_REPO, "--archive", "zip", "--dir", str(target_dir)]
    if version:
        cmd.insert(3, version)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            return {
                "status": "error",
                "message": f"Failed to download release: {result.stderr}"
            }

        # Find the downloaded zip file
        zip_files = list(target_dir.glob("*.zip"))
        if not zip_files:
            return {
                "status": "error",
                "message": "No zip file found after download"
            }

        # Extract the zip
        zip_path = zip_files[0]
        extract_dir = target_dir / "extracted"
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(extract_dir)

        # Find the extracted directory
        extracted_dirs = [d for d in extract_dir.iterdir() if d.is_dir()]
        if not extracted_dirs:
            return {
                "status": "error",
                "message": "No directory found in extracted archive"
            }

        # Get version from the downloaded release
        actual_version = version
        if not actual_version:
            actual_version = get_latest_version()

        return {
            "status": "success",
            "path": extracted_dirs[0],
            "version": actual_version,
            "temp_dir": target_dir
        }

    except subprocess.TimeoutExpired:
        return {
            "status": "error",
            "message": "Download timed out"
        }
    except FileNotFoundError:
        return {
            "status": "error",
            "message": "gh CLI not found. Install GitHub CLI: https://cli.github.com/"
        }


def download_branch(branch: str, target_dir: Path | None = None) -> dict:
    """Download cicd-workflow from a specific branch on GitHub."""
    if target_dir is None:
        target_dir = Path(tempfile.mkdtemp())

    # Use gh api to download branch archive (pipe to file)
    zip_path = target_dir / f"{branch.replace('/', '-')}.zip"

    try:
        # gh api outputs binary to stdout, redirect to file
        with open(zip_path, 'wb') as f:
            result = subprocess.run(
                ["gh", "api", f"/repos/{CICD_WORKFLOW_REPO}/zipball/{branch}"],
                stdout=f,
                stderr=subprocess.PIPE,
                timeout=60
            )

        if result.returncode != 0:
            return {
                "status": "error",
                "message": f"Failed to download branch '{branch}': {result.stderr.decode()}"
            }

        if not zip_path.exists() or zip_path.stat().st_size == 0:
            return {
                "status": "error",
                "message": f"No zip file found after download"
            }

        # Extract the zip
        extract_dir = target_dir / "extracted"
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(extract_dir)

        # Find the extracted directory
        extracted_dirs = [d for d in extract_dir.iterdir() if d.is_dir()]
        if not extracted_dirs:
            return {
                "status": "error",
                "message": "No directory found in extracted archive"
            }

        return {
            "status": "success",
            "path": extracted_dirs[0],
            "version": f"branch:{branch}",
            "temp_dir": target_dir
        }

    except subprocess.TimeoutExpired:
        return {
            "status": "error",
            "message": "Download timed out"
        }
    except FileNotFoundError:
        return {
            "status": "error",
            "message": "gh CLI not found. Install GitHub CLI: https://cli.github.com/"
        }


def is_initialized(project_root: Path | None = None) -> bool:
    """Check if cicd is initialized globally."""
    # v3.0: Check global installation
    if is_skills_installed() and get_global_workflows_path().exists():
        return True
    # Legacy: check local .cicd/core/
    cicd_path = get_project_cicd_path(project_root)
    core_path = cicd_path / "core"
    return core_path.exists() and (core_path / "workflows").exists()


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


def init(project_root: Path | None = None, force: bool = False, version: str | None = None) -> dict:
    """Initialize workflows in a project.

    v3.0: Installs everything globally to ~/.claude/
    - skills/ (skill definitions)
    - workflows/ (workflow definitions)
    - schemas/ (JSON schemas)

    Creates minimal project structure in .cicd/ and .claude/rules/
    """
    if project_root is None:
        project_root = Path.cwd()

    cicd_path = get_project_cicd_path(project_root)
    extends_path = cicd_path / "extends"
    output_path = cicd_path / "output"
    rules_path = project_root / ".claude" / "rules"

    # Check if already initialized (global installation)
    global_installed = is_skills_installed()
    rules_file = rules_path / "cicd-context.md"

    if global_installed and not force:
        installed_version = get_global_installed_version()

        # Even if initialized, create rules template if missing
        if not rules_file.exists():
            rules_path.mkdir(parents=True, exist_ok=True)
            rules_file.write_text(_get_rules_template())
            return {
                "status": "success",
                "message": f"Created project rules template ({installed_version or 'unknown'})",
                "version": installed_version,
                "project_rules_path": str(rules_file)
            }

        return {
            "status": "already_initialized",
            "message": f"Already initialized ({installed_version or 'unknown'}). Use --force to reinitialize.",
            "version": installed_version
        }

    # Download from GitHub
    download_result = download_release(version=version)
    if download_result["status"] != "success":
        return download_result

    source_path = download_result["path"]
    installed_version = download_result["version"]

    # ==========================================================================
    # v3.0: Install everything globally to ~/.claude/
    # ==========================================================================
    skills_result = install_skills(source_path, installed_version)
    skills_installed = skills_result.get("count", 0)

    core_result = install_core(source_path, installed_version)
    workflows_installed = core_result.get("workflows_count", 0)

    # ==========================================================================
    # Create minimal project directory structure
    # ==========================================================================
    extends_path.mkdir(parents=True, exist_ok=True)
    output_path.mkdir(parents=True, exist_ok=True)
    (extends_path / "workflows").mkdir(exist_ok=True)
    (extends_path / "knowledge").mkdir(exist_ok=True)

    # Create default config.yaml if it doesn't exist
    config_file = cicd_path / "config.yaml"
    if not config_file.exists():
        config_file.write_text("""# Project Configuration
# Loaded by all workflows at runtime

user_name: ""
communication_language: "en"
output_folder: ".cicd/output"

# Git settings
git:
  auto_stage: false
  default_branch: "main"
  co_author: "Claude <noreply@anthropic.com>"
""")

    # ==========================================================================
    # v3.0: Create project rules template
    # ==========================================================================
    rules_path.mkdir(parents=True, exist_ok=True)
    if not rules_file.exists():
        rules_file.write_text(_get_rules_template())

    # Cleanup temp directory
    if download_result.get("temp_dir"):
        shutil.rmtree(download_result["temp_dir"], ignore_errors=True)

    return {
        "status": "success",
        "message": f"Initialized ({skills_installed} skills, {workflows_installed} workflows, {installed_version})",
        "skills_installed": skills_installed,
        "workflows_installed": workflows_installed,
        "version": installed_version,
        "global_path": str(get_global_claude_path()),
        "project_rules_path": str(rules_path)
    }


def update(project_root: Path | None = None, version: str | None = None) -> dict:
    """Update global skills, workflows, and schemas from GitHub.

    v3.0: Updates everything in ~/.claude/
    Never touches .claude/rules/ (user customization)
    """
    # Check if anything is installed
    global_installed = is_skills_installed()

    if not global_installed:
        return {
            "status": "not_initialized",
            "message": "Not initialized. Run 'cicd init' first."
        }

    # Get current version
    current_version = get_global_installed_version()

    # Check if update is needed
    if version is None:
        latest_version = get_latest_version()
        if latest_version and latest_version == current_version:
            return {
                "status": "up_to_date",
                "message": f"Already at latest version ({current_version})",
                "version": current_version
            }

    # Download from GitHub
    download_result = download_release(version=version)
    if download_result["status"] != "success":
        return download_result

    source_path = download_result["path"]
    new_version = download_result["version"]

    # ==========================================================================
    # v3.0: Update everything globally
    # ==========================================================================
    skills_result = install_skills(source_path, new_version)
    skills_updated = skills_result.get("count", 0)

    core_result = install_core(source_path, new_version)
    workflows_updated = core_result.get("workflows_count", 0)

    # Cleanup temp directory
    if download_result.get("temp_dir"):
        shutil.rmtree(download_result["temp_dir"], ignore_errors=True)

    return {
        "status": "success",
        "message": f"Updated {current_version} → {new_version}: {skills_updated} skills, {workflows_updated} workflows",
        "previous_version": current_version,
        "version": new_version,
        "skills_updated": skills_updated,
        "workflows_updated": workflows_updated
    }


def sync(version: str | None = None, branch: str | None = None) -> dict:
    """Force re-download and reinstall everything globally.

    v3.0: Useful after manual changes or corruption.
    Reinstalls skills, workflows, and schemas to ~/.claude/

    Args:
        version: Specific release version (e.g., v0.2.0)
        branch: Download from a branch instead of release (e.g., feature/6-global-skills-architecture)
    """
    # Download from GitHub (branch or release)
    if branch:
        download_result = download_branch(branch=branch)
    else:
        download_result = download_release(version=version)

    if download_result["status"] != "success":
        return download_result

    source_path = download_result["path"]
    new_version = download_result["version"]

    # Remove existing skills
    skills_path = get_global_skills_path()
    if skills_path.exists():
        for skill_dir in skills_path.glob("cicd-*"):
            if skill_dir.is_dir():
                shutil.rmtree(skill_dir)

    # Reinstall skills and core
    skills_result = install_skills(source_path, new_version)
    core_result = install_core(source_path, new_version)

    # Cleanup temp directory
    if download_result.get("temp_dir"):
        shutil.rmtree(download_result["temp_dir"], ignore_errors=True)

    return {
        "status": "success",
        "message": f"Synced {skills_result['count']} skills, {core_result['workflows_count']} workflows ({new_version})",
        "skills_synced": skills_result.get("installed", []),
        "workflows_synced": core_result.get("workflows", []),
        "version": new_version
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
