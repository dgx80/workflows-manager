"""CICD Workflow - CI/CD workflows and agents for Claude Code projects."""

try:
    from importlib.metadata import version
    __version__ = version("workflows-manager")
except Exception:
    __version__ = "0.3.1"
