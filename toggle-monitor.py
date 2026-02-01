#!/usr/bin/env python3
"""
Toggle Claude Monitor hooks in global settings.
Usage:
    python toggle-monitor.py on     # Active le monitoring
    python toggle-monitor.py off    # Désactive le monitoring
    python toggle-monitor.py status # Affiche le statut actuel
"""

import json
import sys
from pathlib import Path

# Chemin vers les settings globaux de Claude
SETTINGS_PATH = Path.home() / ".claude" / "settings.json"

# Chemin vers le projet claude-monitor (ajuste si nécessaire)
MONITOR_PROJECT = Path("C:/Users/jeanp/dev/vibe/claude-monitor")
HOOKS_PATH = MONITOR_PROJECT / ".claude" / "hooks" / "send_event.py"

# Les hooks de monitoring à ajouter
MONITOR_HOOKS = {
    "PreToolUse": [{
        "hooks": [{
            "type": "command",
            "command": f"uv run {HOOKS_PATH} --source-app \"$CLAUDE_PROJECT_DIR\" --event-type PreToolUse"
        }]
    }],
    "PostToolUse": [{
        "hooks": [{
            "type": "command",
            "command": f"uv run {HOOKS_PATH} --source-app \"$CLAUDE_PROJECT_DIR\" --event-type PostToolUse"
        }]
    }],
    "Stop": [{
        "hooks": [{
            "type": "command",
            "command": f"uv run {HOOKS_PATH} --source-app \"$CLAUDE_PROJECT_DIR\" --event-type Stop --add-chat"
        }]
    }],
    "SubagentStop": [{
        "hooks": [{
            "type": "command",
            "command": f"uv run {HOOKS_PATH} --source-app \"$CLAUDE_PROJECT_DIR\" --event-type SubagentStop"
        }]
    }],
    "UserPromptSubmit": [{
        "hooks": [{
            "type": "command",
            "command": f"uv run {HOOKS_PATH} --source-app \"$CLAUDE_PROJECT_DIR\" --event-type UserPromptSubmit"
        }]
    }]
}


def load_settings():
    """Charge les settings existants ou retourne un dict vide."""
    if SETTINGS_PATH.exists():
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_settings(settings):
    """Sauvegarde les settings."""
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2)


def is_monitor_hook(hook_entry):
    """Vérifie si un hook appartient au monitoring."""
    try:
        for hook in hook_entry.get("hooks", []):
            cmd = hook.get("command", "")
            if "claude-monitor" in cmd and "send_event.py" in cmd:
                return True
    except (AttributeError, TypeError):
        pass
    return False


def is_monitoring_enabled(settings):
    """Vérifie si le monitoring est actif."""
    hooks = settings.get("hooks", {})
    for event_type in MONITOR_HOOKS.keys():
        if event_type in hooks:
            for hook_entry in hooks[event_type]:
                if is_monitor_hook(hook_entry):
                    return True
    return False


def enable_monitoring(settings):
    """Ajoute les hooks de monitoring."""
    if "hooks" not in settings:
        settings["hooks"] = {}

    for event_type, monitor_hooks in MONITOR_HOOKS.items():
        if event_type not in settings["hooks"]:
            settings["hooks"][event_type] = []

        # Vérifie si déjà présent
        already_exists = any(is_monitor_hook(h) for h in settings["hooks"][event_type])

        if not already_exists:
            settings["hooks"][event_type].extend(monitor_hooks)

    return settings


def disable_monitoring(settings):
    """Retire les hooks de monitoring."""
    if "hooks" not in settings:
        return settings

    for event_type in list(settings["hooks"].keys()):
        # Garde seulement les hooks qui ne sont pas du monitoring
        settings["hooks"][event_type] = [
            h for h in settings["hooks"][event_type]
            if not is_monitor_hook(h)
        ]

        # Nettoie les listes vides
        if not settings["hooks"][event_type]:
            del settings["hooks"][event_type]

    # Nettoie si hooks est vide
    if not settings["hooks"]:
        del settings["hooks"]

    return settings


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1].lower()
    settings = load_settings()

    if command == "on":
        settings = enable_monitoring(settings)
        save_settings(settings)
        print("Claude Monitor: ACTIVE")
        print(f"   N'oublie pas de demarrer le serveur!")
        print(f"   cd {MONITOR_PROJECT}")
        print(f"   bun run dev:all")

    elif command == "off":
        settings = disable_monitoring(settings)
        save_settings(settings)
        print("Claude Monitor: DESACTIVE")

    elif command == "status":
        enabled = is_monitoring_enabled(settings)
        if enabled:
            print("Claude Monitor: ACTIVE")
            print("   Dashboard: http://localhost:5173")
        else:
            print("Claude Monitor: DESACTIVE")

    else:
        print(f"Commande inconnue: {command}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
