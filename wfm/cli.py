"""CLI for wfm - Workflow Manager for Claude Code.

Commands:
    wfm repo add    Add a local repository
    wfm repo remove Remove a repository
    wfm repo list   List configured repositories
    wfm sync        Recreate symlinks for all repos
    wfm list        List all workflows and skills
    wfm status      Show status and configuration
    wfm version     Show installed version
    wfm self-update Update wfm CLI
"""

import argparse
import os
import sys

from wfm import __version__, workflow_manager


def main():
    """Main entry point for wfm CLI."""
    parser = argparse.ArgumentParser(
        prog="wfm",
        description="Workflow Manager for Claude Code - manage skills and workflows via local repos"
    )
    parser.add_argument("-V", "--version", action="version", version=f"wfm {__version__}")

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # sync command (recreate symlinks)
    subparsers.add_parser("sync", help="Recreate all symlinks from configured repos")

    # list command
    subparsers.add_parser("list", help="List all workflows and skills")

    # status command
    subparsers.add_parser("status", help="Show status and configuration")

    # version command
    subparsers.add_parser("version", help="Show wfm version")

    # repo command (multi-repo support)
    repo_parser = subparsers.add_parser("repo", help="Manage workflow repositories")
    repo_subparsers = repo_parser.add_subparsers(dest="repo_command", help="Repository commands")

    # repo add
    repo_add_parser = repo_subparsers.add_parser("add", help="Add a local repository")
    repo_add_parser.add_argument("name", help="Short name for the repo (used as skill prefix)")
    repo_add_parser.add_argument("path", help="Local path to the repository")

    # repo remove
    repo_remove_parser = repo_subparsers.add_parser("remove", help="Remove a repository")
    repo_remove_parser.add_argument("name", help="Name of the repository to remove")

    # repo list
    repo_subparsers.add_parser("list", help="List configured repositories")

    # self-update command
    subparsers.add_parser("self-update", help="Update wfm CLI to the latest release")

    args = parser.parse_args()

    if args.command is None:
        print_help()
        return 0

    if args.command == "sync":
        return cmd_sync(args)
    elif args.command == "list":
        return cmd_list()
    elif args.command == "status":
        return cmd_status()
    elif args.command == "version":
        return cmd_version()
    elif args.command == "repo":
        if args.repo_command == "add":
            return cmd_repo_add(args)
        elif args.repo_command == "remove":
            return cmd_repo_remove(args)
        elif args.repo_command == "list":
            return cmd_repo_list()
        else:
            print("Usage: wfm repo <add|remove|list>")
            return 1
    elif args.command == "self-update":
        return cmd_self_update()
    else:
        print_help()
        return 0


def print_help():
    """Print help message."""
    print("wfm - Workflow Manager for Claude Code")
    print()
    print("Manage skills and workflows via local repositories with symlinks.")
    print("You manage git yourself, wfm just manages the symlinks.")
    print()
    print("Commands:")
    print("  wfm repo add <name> <path>  Add a local repository")
    print("  wfm repo remove <name>      Remove repository and symlinks")
    print("  wfm repo list               List configured repositories")
    print("  wfm sync                    Recreate all symlinks")
    print("  wfm list                    List all skills and workflows")
    print("  wfm status                  Show configuration and status")
    print("  wfm version                 Show wfm version")
    print("  wfm self-update             Update wfm CLI")
    print()
    print("Quick start:")
    print("  wfm repo add cicd C:/Users/me/dev/cicd-workflow")
    print("  wfm sync")
    print()
    print("Architecture:")
    print("  ~/.claude/wfm.json     Config (repos, ignored skills)")
    print("  ~/.claude/skills/      Symlinks to repo skills")
    print("  ~/.claude/workflows/   Symlinks to repo workflows")


def cmd_sync(args):
    """Handle sync command - recreate all symlinks from configured repos."""
    result = workflow_manager.sync_all()

    if result["status"] == "error":
        print(f"[ERROR] {result.get('message', 'Unknown error')}")
        return 1

    # Print sync results
    if result["status"] == "success":
        print(f"[OK] {result['message']}")
    elif result["status"] == "partial":
        print(f"[WARN] {result['message']}")
        for error in result.get("errors", []):
            print(f"  - {error}")

    # Show synced repos
    for repo_result in result.get("results", []):
        if repo_result["status"] == "success":
            skills = repo_result.get("skills_synced", [])
            workflows = repo_result.get("workflows_synced", [])
            print(f"\n  {repo_result['repo_name']}:")
            if skills:
                print(f"    Skills: {', '.join(skills)}")
            if workflows:
                print(f"    Workflows: {', '.join(workflows)}")
            print(f"    Path: {repo_result.get('repo_path', 'N/A')}")

    # Handle orphan skills
    orphan_skills = result.get("orphan_skills", [])
    if orphan_skills:
        print(f"\n[INFO] Detected {len(orphan_skills)} orphan skill(s) (not linked to any repo):")
        repos = list(workflow_manager.get_configured_repos().keys())

        for skill in orphan_skills:
            print(f"\n  Skill: {skill}")
            print(f"  Where to place this skill?")
            for i, repo in enumerate(repos):
                print(f"    {i + 1}. {repo}")
            print(f"    0. Ignore (don't ask again)")
            print(f"    Enter. Skip for now")

            try:
                choice = input("  > ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n  Skipped.")
                continue

            if choice == "0":
                workflow_manager.ignore_skill(skill)
                print(f"  [OK] '{skill}' added to ignored list")
            elif choice.isdigit() and 0 < int(choice) <= len(repos):
                repo_name = repos[int(choice) - 1]
                adopt_result = workflow_manager.adopt_skill(skill, repo_name)
                if adopt_result["status"] == "success":
                    print(f"  [OK] {adopt_result['message']}")
                else:
                    print(f"  [ERROR] {adopt_result['message']}")
            else:
                print(f"  Skipped.")

    # Handle orphan workflows
    orphan_workflows = result.get("orphan_workflows", [])
    if orphan_workflows:
        print(f"\n[INFO] Detected {len(orphan_workflows)} orphan workflow(s):")
        repos = list(workflow_manager.get_configured_repos().keys())

        for wf in orphan_workflows:
            print(f"\n  Workflow: {wf}")
            print(f"  Where to place this workflow?")
            for i, repo in enumerate(repos):
                print(f"    {i + 1}. {repo}")
            print(f"    0. Ignore (don't ask again)")
            print(f"    Enter. Skip for now")

            try:
                choice = input("  > ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n  Skipped.")
                continue

            if choice == "0":
                workflow_manager.ignore_workflow(wf)
                print(f"  [OK] '{wf}' added to ignored list")
            elif choice.isdigit() and 0 < int(choice) <= len(repos):
                repo_name = repos[int(choice) - 1]
                adopt_result = workflow_manager.adopt_workflow(wf, repo_name)
                if adopt_result["status"] == "success":
                    print(f"  [OK] {adopt_result['message']}")
                else:
                    print(f"  [ERROR] {adopt_result['message']}")
            else:
                print(f"  Skipped.")

    print(f"\nSkills: {workflow_manager.get_global_skills_path()}")
    print(f"Workflows: {workflow_manager.get_global_workflows_path()}")

    return 0 if result["status"] == "success" else 1


def cmd_list():
    """Handle list command - list all skills and workflows."""
    from wfm import platform as plat

    repos = workflow_manager.get_configured_repos()

    if not repos:
        print("No repositories configured.")
        print("Use 'wfm repo add <name> <path>' to add one.")
        return 0

    print("Configured Repositories:")
    for name, repo in repos.items():
        repo_path = workflow_manager.get_repo_local_path(name, repo)
        status = "ok" if repo_path.exists() else "path not found"
        print(f"  {name}: {repo} ({status})")
    print()

    # List skills
    skills_path = workflow_manager.get_global_skills_path()
    if skills_path.exists():
        skills = []
        for item in sorted(skills_path.iterdir()):
            if item.is_dir() and (item / "SKILL.md").exists():
                is_link = plat.is_link(item)
                link_marker = "" if is_link else " (orphan)"
                skills.append(f"  /{item.name}{link_marker}")

        if skills:
            print(f"Skills ({len(skills)}):")
            for s in skills:
                print(s)
        else:
            print("No skills installed.")
    else:
        print("No skills installed.")
    print()

    # List workflows
    workflows_path = workflow_manager.get_global_workflows_path()
    if workflows_path.exists():
        workflows = []
        for item in sorted(workflows_path.iterdir()):
            if item.is_dir() and (item / "workflow.md").exists():
                is_link = plat.is_link(item)
                link_marker = "" if is_link else " (orphan)"
                workflows.append(f"  {item.name}{link_marker}")

        if workflows:
            print(f"Workflows ({len(workflows)}):")
            for w in workflows:
                print(w)
        else:
            print("No workflows installed.")
    else:
        print("No workflows installed.")

    return 0


def cmd_status():
    """Handle status command - show configuration and paths."""
    from wfm import platform as plat

    print("=== WFM Status ===")
    print()

    # Paths
    print("Paths:")
    print(f"  Config:    {workflow_manager.get_wfm_config_path()}")
    print(f"  Skills:    {workflow_manager.get_global_skills_path()}")
    print(f"  Workflows: {workflow_manager.get_global_workflows_path()}")
    print()

    # Repos
    repos = workflow_manager.get_configured_repos()
    if repos:
        print(f"Repositories ({len(repos)}):")
        for name, repo in repos.items():
            repo_path = workflow_manager.get_repo_local_path(name, repo)
            if repo_path.exists():
                status = "ok"
            else:
                status = "path not found"
            print(f"  {name}: {repo} [{status}]")
    else:
        print("No repositories configured.")
    print()

    # Count skills and workflows
    skills_path = workflow_manager.get_global_skills_path()
    workflows_path = workflow_manager.get_global_workflows_path()

    skill_count = 0
    orphan_skills = 0
    if skills_path.exists():
        for item in skills_path.iterdir():
            if item.is_dir() and (item / "SKILL.md").exists():
                skill_count += 1
                if not plat.is_link(item):
                    orphan_skills += 1

    workflow_count = 0
    orphan_workflows = 0
    if workflows_path.exists():
        for item in workflows_path.iterdir():
            if item.is_dir() and (item / "workflow.md").exists():
                workflow_count += 1
                if not plat.is_link(item):
                    orphan_workflows += 1

    print(f"Skills: {skill_count} total, {orphan_skills} orphans")
    print(f"Workflows: {workflow_count} total, {orphan_workflows} orphans")

    # Show ignored items
    ignored_skills = workflow_manager.get_ignored_skills()
    ignored_workflows = workflow_manager.get_ignored_workflows()
    if ignored_skills or ignored_workflows:
        print()
        print("Ignored:")
        if ignored_skills:
            print(f"  Skills: {', '.join(ignored_skills)}")
        if ignored_workflows:
            print(f"  Workflows: {', '.join(ignored_workflows)}")

    return 0


def cmd_version():
    """Handle version command."""
    import subprocess
    import json

    print(f"wfm: {__version__}")

    # Get latest wfm release from GitHub
    try:
        result = subprocess.run(
            ["gh", "release", "view", "--repo", "dgx80/workflows-manager", "--json", "tagName"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            latest_wfm = data.get("tagName", "").lstrip("v")
            if __version__ != latest_wfm:
                print(f"Update available: {latest_wfm}")
                print("Run 'wfm self-update' to update.")
    except Exception:
        pass

    return 0


def cmd_self_update():
    """Handle self-update command - update wfm CLI to latest release."""
    import shutil
    import subprocess

    print("Checking for updates...")

    # Get latest version from GitHub
    try:
        result = subprocess.run(
            ["gh", "release", "view", "--repo", "dgx80/workflows-manager", "--json", "tagName"],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode != 0:
            print("[ERROR] Failed to check latest version")
            return 1

        import json
        data = json.loads(result.stdout)
        latest_version = data.get("tagName", "").lstrip("v")
    except Exception as e:
        print(f"[ERROR] Failed to check latest version: {e}")
        return 1

    # Compare with current version
    current_version = __version__
    print(f"Current version: {current_version}")
    print(f"Latest version:  {latest_version}")

    if current_version == latest_version:
        print("[OK] Already at the latest version!")
        return 0

    print()
    print(f"Updating {current_version} -> {latest_version}...")

    # Download wheel from GitHub releases
    import tempfile
    wheel_name = f"workflows_manager-{latest_version}-py3-none-any.whl"

    with tempfile.TemporaryDirectory() as tmpdir:
        wheel_path = os.path.join(tmpdir, wheel_name)

        # Download wheel using gh
        download_cmd = [
            "gh", "release", "download", f"v{latest_version}",
            "--repo", "dgx80/workflows-manager",
            "--pattern", wheel_name,
            "--dir", tmpdir
        ]

        try:
            result = subprocess.run(download_cmd, capture_output=True, text=True, timeout=60)
            if result.returncode != 0:
                print(f"[ERROR] Failed to download wheel: {result.stderr}")
                return 1
        except Exception as e:
            print(f"[ERROR] Failed to download wheel: {e}")
            return 1

        # Install wheel
        if shutil.which("uv"):
            cmd = ["uv", "tool", "install", "--force", wheel_path]
        else:
            cmd = [sys.executable, "-m", "pip", "install", "--upgrade", wheel_path]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode == 0:
                print(f"[OK] Updated to {latest_version}")
                return 0
            else:
                print(f"[ERROR] Update failed: {result.stderr}")
                return 1
        except Exception as e:
            print(f"[ERROR] Update failed: {e}")
            return 1


def cmd_repo_add(args):
    """Handle repo add command - adds a local repo path to config and creates symlinks."""
    from pathlib import Path

    # Resolve the path
    repo_path = Path(args.path).expanduser().resolve()
    if not repo_path.exists():
        print(f"[ERROR] Path does not exist: {repo_path}")
        return 1

    # Add to config (store as forward-slash path for portability)
    result = workflow_manager.add_repo(args.name, str(repo_path).replace("\\", "/"))
    if result["status"] != "success":
        print(f"[ERROR] {result['message']}")
        return 1

    print(f"[OK] {result['message']}")

    # Create symlinks
    sync_result = workflow_manager.sync_repo(args.name, str(repo_path).replace("\\", "/"))

    if sync_result["status"] == "success":
        skills = sync_result.get("skills_synced", [])
        workflows = sync_result.get("workflows_synced", [])
        if skills:
            print(f"  Skills: {', '.join(skills)}")
        if workflows:
            print(f"  Workflows: {', '.join(workflows)}")
        return 0
    else:
        print(f"[ERROR] {sync_result.get('message', 'Sync failed')}")
        return 1


def cmd_repo_remove(args):
    """Handle repo remove command - removes repo config and symlinks."""
    result = workflow_manager.remove_repo(args.name)
    if result["status"] == "success":
        print(f"[OK] {result['message']}")
        removed_skills = result.get("removed_skills", [])
        removed_workflows = result.get("removed_workflows", [])
        if removed_skills:
            print(f"  Removed skill links: {', '.join(removed_skills)}")
        if removed_workflows:
            print(f"  Removed workflow links: {', '.join(removed_workflows)}")
        return 0
    else:
        print(f"[ERROR] {result['message']}")
        return 1


def cmd_repo_list():
    """Handle repo list command."""
    repos = workflow_manager.get_configured_repos()
    if not repos:
        print("No repositories configured.")
        print("Use 'wfm repo add <name> <path>' to add one.")
        return 0

    print("Configured Repositories:")
    for name, repo in repos.items():
        print(f"  {name}: {repo}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
