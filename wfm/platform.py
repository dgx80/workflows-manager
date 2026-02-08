"""Cross-platform symlink/junction utilities.

Windows: Uses junctions (no admin privileges required)
Unix/Mac: Uses symlinks
"""
from __future__ import annotations

import os
import platform
import subprocess
from pathlib import Path


def create_link(source: Path, target: Path) -> bool:
    """Create a junction (Windows) or symlink (Unix) from target to source.

    Args:
        source: The existing directory to link to (the repo folder)
        target: The link path to create (in ~/.claude/skills/ or workflows/)

    Returns:
        True if successful

    Raises:
        subprocess.CalledProcessError: If junction creation fails on Windows
        OSError: If symlink creation fails on Unix
    """
    # Ensure source exists
    if not source.exists():
        raise FileNotFoundError(f"Source directory does not exist: {source}")

    # Remove existing link/directory if present
    if target.exists() or is_link(target):
        remove_link(target)

    # Ensure parent directory exists
    target.parent.mkdir(parents=True, exist_ok=True)

    if platform.system() == "Windows":
        # Junction - no admin privileges required
        # mklink /J creates a directory junction
        result = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(target), str(source)],
            check=True,
            capture_output=True,
            text=True
        )
        return True
    else:
        # Unix/Mac - use symlink
        os.symlink(source, target)
        return True


def remove_link(path: Path) -> bool:
    """Remove a junction (Windows) or symlink (Unix).

    Args:
        path: The link path to remove

    Returns:
        True if successful, False if path doesn't exist
    """
    if not path.exists() and not is_link(path):
        return False

    if platform.system() == "Windows":
        # rmdir for junction - does NOT delete the target contents
        if is_link(path):
            subprocess.run(
                ["cmd", "/c", "rmdir", str(path)],
                check=True,
                capture_output=True
            )
        else:
            # Regular directory - use rmdir /s /q
            subprocess.run(
                ["cmd", "/c", "rmdir", "/s", "/q", str(path)],
                check=True,
                capture_output=True
            )
        return True
    else:
        # Unix - unlink for symlink, rmdir for directory
        if path.is_symlink():
            os.unlink(path)
        elif path.is_dir():
            import shutil
            shutil.rmtree(path)
        else:
            os.unlink(path)
        return True


def is_link(path: Path) -> bool:
    """Check if path is a junction (Windows) or symlink (Unix).

    Args:
        path: Path to check

    Returns:
        True if path is a junction or symlink
    """
    if not path.exists() and not _path_is_reparse_point(path):
        return False

    if platform.system() == "Windows":
        return _path_is_reparse_point(path)
    else:
        return path.is_symlink()


def _path_is_reparse_point(path: Path) -> bool:
    """Check if path is a Windows reparse point (junction or symlink).

    Uses GetFileAttributesW to check FILE_ATTRIBUTE_REPARSE_POINT (0x400).
    """
    if platform.system() != "Windows":
        return False

    try:
        import ctypes
        attrs = ctypes.windll.kernel32.GetFileAttributesW(str(path))
        if attrs == -1:  # INVALID_FILE_ATTRIBUTES
            return False
        # FILE_ATTRIBUTE_REPARSE_POINT = 0x400
        return bool(attrs & 0x400)
    except Exception:
        return False


def get_link_target(path: Path) -> Path | None:
    """Get the target of a junction/symlink.

    Args:
        path: The link path

    Returns:
        The target path, or None if not a link
    """
    if not is_link(path):
        return None

    if platform.system() == "Windows":
        # Use dir command to get junction target
        try:
            result = subprocess.run(
                ["cmd", "/c", "dir", str(path.parent), "/AL"],
                capture_output=True,
                text=True
            )
            # Parse output to find target
            for line in result.stdout.split("\n"):
                if path.name in line and "[" in line:
                    # Extract target from [target] format
                    start = line.find("[") + 1
                    end = line.find("]")
                    if start > 0 and end > start:
                        return Path(line[start:end])
        except Exception:
            pass
        return None
    else:
        # Unix - use readlink
        try:
            return Path(os.readlink(path))
        except Exception:
            return None
