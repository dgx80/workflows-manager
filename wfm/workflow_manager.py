"""Workflow manager for wfm CLI.

Manages skills and workflows from multiple local repositories via symlinks.

Architecture:
    ~/.claude/
    ├── wfm.json       # Repo config (name -> local path)
    ├── skills/        # Symlinks to repo skills
    └── workflows/     # Symlinks to repo workflows
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path


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
        Example: {"repos": {"myrepo": "/path/to/repo", "other": "/path/to/other"}}
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
        dict mapping repo name to local path (e.g., {"myrepo": "/path/to/repo"})
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



# =============================================================================
# Global Paths
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


# =============================================================================
# Symlink-based Repo Sync
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
        repo_name: Name of the repo (e.g., "myrepo")
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
        repo_name: Name of the repo (e.g., "myrepo")
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
        repo_name: Name of the repo (e.g., "myrepo")

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
