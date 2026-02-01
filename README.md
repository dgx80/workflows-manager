# workflows-manager (wfm)

> **Note:** This project is under active development and is not ready for production use.

CLI tool to manage workflows, skills and schemas from multiple repositories.

## Overview

`wfm` syncs workflows, skills, and schemas from GitHub repositories to your local `~/.claude/` directory. It supports multiple workflow repositories with custom naming.

## Configuration

Create `~/.claude/wfm.json`:

```json
{
  "repos": {
    "cicd": "dgx80/cicd-workflow",
    "myworkflows": "user/my-workflows"
  }
}
```

## Installation

```bash
pip install workflows-manager
```

Or with uv:

```bash
uv tool install workflows-manager
```

## Usage

```bash
wfm sync          # Sync all repositories
wfm list          # List installed workflows and skills
wfm status        # Show status
```

## License

MIT
