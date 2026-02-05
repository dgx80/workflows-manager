"""CLI for cicd-workflow.

Commands:
    cicd init       Initialize workflows and global skills
    cicd update     Update global skills and core workflows
    cicd sync       Force re-download global skills
    cicd list       List all workflows, agents, and skills
    cicd status     Show extended workflows and skills info
    cicd version    Show installed and latest version
    cicd monitor    Real-time workflow visualization dashboard
"""

import argparse
import os
import sys

from wfm import __version__, workflow_manager


def main():
    """Main entry point for cicd CLI."""
    parser = argparse.ArgumentParser(
        prog="cicd",
        description="CI/CD workflows and agents for Claude Code projects"
    )
    parser.add_argument("-V", "--version", action="version", version=f"cicd-workflow {__version__}")

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # init command
    init_parser = subparsers.add_parser("init", help="Initialize workflows in project")
    init_parser.add_argument("--force", "-f", action="store_true", help="Reinitialize even if exists")
    init_parser.add_argument("--version", "-v", dest="release_version", help="Specific version (e.g., v0.1.0)")

    # update command
    update_parser = subparsers.add_parser("update", help="Update global skills and core workflows")
    update_parser.add_argument("--version", "-v", dest="release_version", help="Specific version (e.g., v0.1.0)")

    # sync command (v2.0)
    sync_parser = subparsers.add_parser("sync", help="Force re-download global skills")
    sync_parser.add_argument("--version", "-v", dest="release_version", help="Specific version (e.g., v0.1.0)")
    sync_parser.add_argument("--branch", "-b", help="Download from branch instead of release (e.g., feature/6-global-skills-architecture)")

    # migrate command (v2.0)
    migrate_parser = subparsers.add_parser("migrate", help="Migrate from old commands to global skills")
    migrate_parser.add_argument("--remove", "-r", action="store_true", help="Remove legacy command files after migration")

    # list command
    subparsers.add_parser("list", help="List all workflows, agents, and skills")

    # status command
    subparsers.add_parser("status", help="Show extended workflows")

    # version command (show installed vs latest)
    subparsers.add_parser("version", help="Show installed and latest version")

    # monitor command
    monitor_parser = subparsers.add_parser("monitor", help="Real-time workflow visualization")
    monitor_parser.add_argument("--serve", "-s", action="store_true", help="Start the monitor server")
    monitor_parser.add_argument("--open", "-o", action="store_true", help="Open dashboard in browser")
    monitor_parser.add_argument("--emit", "-e", action="store_true", help="Emit an event")
    monitor_parser.add_argument("--agent", "-a", help="Agent name (for --emit)")
    monitor_parser.add_argument("--action", help="Action: start, end, error (for --emit)")
    monitor_parser.add_argument("--workflow", "-w", help="Workflow name (for --emit)")
    monitor_parser.add_argument("--port", "-p", type=int, default=8000, help="Server port (default: 8000)")

    # repo command (multi-repo support)
    repo_parser = subparsers.add_parser("repo", help="Manage workflow repositories")
    repo_subparsers = repo_parser.add_subparsers(dest="repo_command", help="Repository commands")

    # repo add
    repo_add_parser = repo_subparsers.add_parser("add", help="Add a repository")
    repo_add_parser.add_argument("name", help="Short name for the repo (used as skill prefix)")
    repo_add_parser.add_argument("repo", help="GitHub repo path (e.g., owner/repo)")

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

    if args.command == "init":
        return cmd_init(args)
    elif args.command == "update":
        return cmd_update(args)
    elif args.command == "sync":
        return cmd_sync(args)
    elif args.command == "migrate":
        return cmd_migrate(args)
    elif args.command == "list":
        return cmd_list()
    elif args.command == "status":
        return cmd_status()
    elif args.command == "version":
        return cmd_version()
    elif args.command == "monitor":
        return cmd_monitor(args)
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
    print("Commands:")
    print("  wfm init        Initialize global skills and project workflows")
    print("  wfm update      Update global skills and core workflows")
    print("  wfm sync        Sync all configured repositories")
    print("  wfm migrate     Migrate from old commands to global skills")
    print("  wfm list        List all workflows, agents, and skills")
    print("  wfm status      Show extended workflows and skills info")
    print("  wfm version     Show installed and latest version")
    print("  wfm self-update Update wfm CLI to latest release")
    print("  wfm repo        Manage workflow repositories")
    print("  wfm monitor     Real-time workflow visualization")
    print()
    print("Repository commands:")
    print("  wfm repo add <name> <owner/repo>  Add a repository")
    print("  wfm repo remove <name>            Remove a repository")
    print("  wfm repo list                     List configured repositories")
    print()
    print("Options (init/update/sync):")
    print("  --force, -f     Reinitialize even if exists (init only)")
    print("  --version, -v   Install specific version (e.g., -v v0.1.0)")
    print()
    print("Migration options:")
    print("  --remove, -r    Remove legacy command files after migration")
    print()
    print("Monitor options:")
    print("  --serve, -s     Start the monitor server")
    print("  --open, -o      Open dashboard in browser")
    print("  --emit, -e      Emit an event to the server")
    print("  --agent, -a     Agent name (architect, coder, etc.)")
    print("  --action        Action type (start, end, error)")
    print("  --workflow, -w  Workflow name")
    print()
    print("Architecture:")
    print("  ~/.claude/wfm.json   Repository configuration")
    print("  ~/.claude/skills/    Global skills ({repo}-*)")
    print("  ~/.claude/workflows/ Global workflows")
    print("  .claude/rules/       Project context (auto-loaded)")
    print("  .cicd/extends/       Project extensions (priority)")
    print()
    print(f"Default source: {workflow_manager.CICD_WORKFLOW_URL}")


def cmd_init(args):
    """Handle init command."""
    result = workflow_manager.init(
        force=args.force,
        version=getattr(args, 'release_version', None)
    )
    print_result(result)
    return 0 if result["status"] in ("success", "already_initialized") else 1


def cmd_update(args):
    """Handle update command."""
    result = workflow_manager.update(
        version=getattr(args, 'release_version', None)
    )
    print_result(result)
    return 0 if result["status"] in ("success", "up_to_date") else 1


def cmd_sync(args):
    """Handle sync command - sync all configured repositories."""
    branch = getattr(args, 'branch', None)
    version = getattr(args, 'release_version', None)

    if branch:
        print(f"Syncing from branch: {branch}")

    # Use sync_all for multi-repo support
    result = workflow_manager.sync_all(version=version, branch=branch)

    if result["status"] == "success":
        print(f"[OK] {result['message']}")
        for repo_result in result.get("results", []):
            skills = repo_result.get("skills_synced", [])
            if skills:
                print(f"  {repo_result['repo_name']}: {', '.join(skills)}")
        print(f"\nLocation: {workflow_manager.get_global_skills_path()}")
        return 0
    elif result["status"] == "partial":
        print(f"[WARN] {result['message']}")
        for error in result.get("errors", []):
            print(f"  - {error}")
        return 1
    else:
        print(f"[ERROR] {result.get('message', 'Unknown error')}")
        return 1


def cmd_migrate(args):
    """Handle migrate command - migrate from old commands to global skills."""
    # First check if migration is needed
    detection = workflow_manager.detect_migration_needed()

    if not detection["needs_migration"]:
        if detection["has_global_skills"]:
            print("[INFO] Global skills already installed. Use 'cicd sync' to update.")
        else:
            print("[INFO] No legacy commands found. Nothing to migrate.")
        return 0

    print("Migration detected:")
    print(f"  Legacy commands: {detection['has_legacy_commands']}")
    print(f"  Global skills: {detection['has_global_skills']}")
    print()

    # Perform migration
    result = workflow_manager.migrate(remove_legacy=args.remove)
    print_result(result)

    if result["status"] == "success":
        skills = result.get("migrated_skills", [])
        if skills:
            print(f"\nMigrated skills: {', '.join(skills)}")
            print(f"Location: {result.get('global_skills_path')}")
            if result.get("rules_created"):
                print(f"Rules template: {result.get('rules_created')}")
            if result.get("removed_files"):
                print(f"Removed legacy files: {', '.join(result['removed_files'])}")

    return 0 if result["status"] in ("success", "not_needed", "already_migrated") else 1


def cmd_list():
    """Handle list command."""
    result = workflow_manager.list_workflows()

    # Show version info
    global_version = workflow_manager.get_global_installed_version()
    local_version = result.get("version")

    if global_version:
        print(f"Global version: {global_version}")
    if local_version and local_version != global_version:
        print(f"Project version: {local_version}")
    if not global_version and not local_version:
        print("[WARN] Not initialized. Run 'wfm init'")
    print()

    # Show configured repos
    repos = workflow_manager.get_configured_repos()
    if repos:
        print("Configured Repositories:")
        for name, repo in repos.items():
            print(f"  {name}: {repo}")
        print()

    # List global skills with repo source
    skills = workflow_manager.list_global_skills_with_repo()
    if skills:
        print("Global Skills (~/.claude/skills/):")
        for skill_name in sorted(skills.keys()):
            info = skills[skill_name]
            repo = info.get("repo", "unknown")
            print(f"  [{repo:8}] /{skill_name}")
    else:
        print("No global skills installed.")
    print()

    # List workflows
    workflows = result.get("workflows", {})
    if workflows:
        print("Workflows (.cicd/core/):")
        for name, info in sorted(workflows.items()):
            source = info["source"]
            marker = " (override)" if info.get("overridden") else ""
            print(f"  [{source:7}] {name}{marker}")
    else:
        print("No workflows found.")

    print()

    # List agents
    agents = result.get("agents", {})
    if agents:
        print("Agents:")
        for name, info in sorted(agents.items()):
            source = info["source"]
            marker = " (override)" if info.get("overridden") else ""
            print(f"  [{source:7}] {name}{marker}")
    else:
        print("No agents found.")

    return 0


def cmd_status():
    """Handle status command."""
    result = workflow_manager.status()

    # Show version info (v2.0)
    global_version = workflow_manager.get_global_installed_version()
    local_version = result.get("version")

    if not global_version and not result.get("initialized"):
        print("[WARN] Not initialized. Run 'wfm init'")
        return 1

    print("=== WFM Status ===")
    print()

    # Show configured repos
    repos = workflow_manager.get_configured_repos()
    print(f"Configured Repositories: {len(repos)}")
    for name, repo in repos.items():
        print(f"  {name}: {repo}")
    print()

    # Global skills info by repo
    skills_by_repo = workflow_manager.list_global_skills_with_repo()
    skills = workflow_manager.list_global_skills()

    # Count skills per repo
    repo_counts = {}
    for skill_name, info in skills_by_repo.items():
        repo = info.get("repo", "unknown")
        repo_counts[repo] = repo_counts.get(repo, 0) + 1

    print(f"Global Skills: {len(skills)} installed")
    for repo_name, count in sorted(repo_counts.items()):
        print(f"  {repo_name}: {count} skills")

    if global_version:
        print(f"Global Version: {global_version}")
    print(f"Skills Path: {workflow_manager.get_global_skills_path()}")
    print()

    # Project info
    if result.get("initialized"):
        print(f"Project Version: {local_version or 'unknown'}")

        overridden_wf = result.get("overridden_workflows", {})
        overridden_ag = result.get("overridden_agents", {})
        total_wf = result.get("total_workflows", 0)
        total_ag = result.get("total_agents", 0)

        print(f"Workflows: {len(overridden_wf)} extended / {total_wf} total")
        print(f"Agents:    {len(overridden_ag)} extended / {total_ag} total")

        if overridden_wf:
            print()
            print("Extended workflows:")
            for name in sorted(overridden_wf.keys()):
                print(f"  - {name}")

        if overridden_ag:
            print()
            print("Extended agents:")
            for name in sorted(overridden_ag.keys()):
                print(f"  - {name}")
    else:
        print("Project: not initialized (global skills only)")

    # Check for project rules
    rules_path = workflow_manager.get_project_cicd_path().parent / ".claude" / "rules" / "cicd-context.md"
    if rules_path.exists():
        print()
        print(f"Project Rules: {rules_path}")
    else:
        print()
        print("Project Rules: not configured (run 'wfm init' to create template)")

    return 0


def cmd_version():
    """Handle version command."""
    import subprocess
    import json

    # WFM CLI version
    print(f"wfm CLI:       {__version__}")

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
            print(f"wfm Latest:    {latest_wfm}")
            if __version__ != latest_wfm:
                print()
                print("Update available! Run 'wfm self-update'")
        else:
            print(f"wfm Latest:    unknown")
    except Exception:
        print(f"wfm Latest:    unknown")

    print()

    # Workflow skills version
    global_version = workflow_manager.get_global_installed_version()
    latest_skills = workflow_manager.get_latest_version()

    print(f"Skills:        {global_version or 'not installed'}")
    print(f"Skills Latest: {latest_skills or 'unknown'}")

    if global_version and latest_skills and global_version != latest_skills:
        print()
        print("Skills update available! Run 'wfm update'")

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
    print(f"Updating {current_version} → {latest_version}...")

    # Install from GitHub (not PyPI)
    github_url = f"git+https://github.com/dgx80/workflows-manager@v{latest_version}"

    # Determine install method (uv or pip)
    if shutil.which("uv"):
        cmd = ["uv", "tool", "install", "--force", github_url]
    else:
        cmd = [sys.executable, "-m", "pip", "install", "--upgrade", github_url]

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
    """Handle repo add command."""
    result = workflow_manager.add_repo(args.name, args.repo)
    if result["status"] == "success":
        print(f"[OK] {result['message']}")
        print(f"Run 'wfm sync' to download skills from this repository.")
        return 0
    else:
        print(f"[ERROR] {result['message']}")
        return 1


def cmd_repo_remove(args):
    """Handle repo remove command."""
    result = workflow_manager.remove_repo(args.name)
    if result["status"] == "success":
        print(f"[OK] {result['message']}")
        return 0
    else:
        print(f"[ERROR] {result['message']}")
        return 1


def cmd_repo_list():
    """Handle repo list command."""
    repos = workflow_manager.get_configured_repos()
    if not repos:
        print("No repositories configured.")
        print("Use 'wfm repo add <name> <owner/repo>' to add one.")
        return 0

    print("Configured Repositories:")
    for name, repo in repos.items():
        print(f"  {name}: {repo}")
    return 0


def cmd_monitor(args):
    """Handle monitor command."""
    from wfm import monitor

    if args.emit:
        # Emit an event
        if not args.agent:
            print("[ERROR] --agent is required for --emit")
            return 1
        if not args.action:
            print("[ERROR] --action is required for --emit")
            return 1

        # Force enable for CLI emit command
        os.environ["CICD_MONITOR"] = "1"
        emitter = monitor.EventEmitter(port=args.port)
        result = emitter.emit(
            agent=args.agent,
            action=args.action,
            workflow=args.workflow,
        )

        if result["status"] == "success":
            print(f"[OK] Event emitted: {args.agent} → {args.action}")
        elif result["status"] == "offline":
            print(f"[WARN] {result['message']}")
        else:
            print(f"[ERROR] {result.get('message', 'Unknown error')}")
        return 0

    if args.serve:
        # Start the FastAPI server with uvicorn
        import shutil
        import subprocess
        import sys
        from pathlib import Path

        print(f"Starting CICD Monitor server on port {args.port}...")

        if args.open:
            # Open browser after a short delay
            import threading
            import time
            def open_browser():
                time.sleep(2.0)
                monitor.open_dashboard(args.port)
            threading.Thread(target=open_browser, daemon=True).start()

        # Find backend directory
        backend_dir = Path(__file__).parent.parent / "backend"
        if not backend_dir.exists():
            print("[ERROR] Backend directory not found. Please install from source.")
            return 1

        # Run uvicorn (prefer uv if available)
        try:
            if shutil.which("uv"):
                subprocess.run(
                    ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", str(args.port)],
                    cwd=str(backend_dir),
                    check=True,
                )
            else:
                subprocess.run(
                    [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", str(args.port)],
                    cwd=str(backend_dir),
                    check=True,
                )
        except KeyboardInterrupt:
            print("\nServer stopped.")
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] Server failed: {e}")
            return 1
        return 0

    if args.open:
        # Just open the dashboard
        print(f"Opening dashboard at http://localhost:{args.port}")
        monitor.open_dashboard(args.port)
        return 0

    # Default: show help for monitor
    print("cicd monitor - Real-time workflow visualization")
    print()
    print("Usage:")
    print("  cicd monitor --serve          Start the monitor server")
    print("  cicd monitor --serve --open   Start server and open dashboard")
    print("  cicd monitor --open           Open dashboard in browser")
    print("  cicd monitor --emit ...       Emit an event")
    print()
    print("Emit event example:")
    print("  cicd monitor --emit --agent architect --action start --workflow design-feature")
    return 0


def print_result(result: dict):
    """Print command result."""
    status = result.get("status", "unknown")

    if status == "success":
        print(f"[OK] {result.get('message', 'Success')}")
    elif status == "up_to_date":
        print(f"[OK] {result.get('message', 'Up to date')}")
    elif status == "already_initialized":
        print(f"[INFO] {result.get('message', 'Already initialized')}")
    elif status == "not_initialized":
        print(f"[WARN] {result.get('message', 'Not initialized')}")
    else:
        print(f"[ERROR] {result.get('message', 'Unknown error')}")


if __name__ == "__main__":
    sys.exit(main())
