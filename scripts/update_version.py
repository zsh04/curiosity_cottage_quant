#!/usr/bin/env python3
"""
Auto-versioning script using git tags.

Generates version number from git tags following semantic versioning.
Falls back to VERSION file if git is unavailable.
"""

import subprocess
import re
from pathlib import Path


def get_version_from_git() -> str | None:
    """
    Get version from git tags.

    Returns latest tag in format vX.Y.Z, or None if git unavailable.
    """
    try:
        # Get latest tag
        result = subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0"],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode == 0:
            tag = result.stdout.strip()
            # Remove 'v' prefix if present
            if tag.startswith("v"):
                tag = tag[1:]
            return tag

    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    return None


def get_version_from_file() -> str:
    """
    Get version from VERSION file (fallback).

    Returns:
        str: Version string or "0.0.0-dev" if file doesn't exist
    """
    version_file = Path(__file__).parent.parent / "VERSION"

    if version_file.exists():
        return version_file.read_text().strip()

    return "0.0.0-dev"


def get_version() -> str:
    """
    Get current version (git tag > VERSION file > dev).

    Priority:
    1. Git tag (if available)
    2. VERSION file
    3. "0.0.0-dev" (fallback)

    Returns:
        str: Semantic version string
    """
    # Try git first
    git_version = get_version_from_git()
    if git_version:
        return git_version

    # Fall back to file
    return get_version_from_file()


def write_version_file(version: str):
    """
    Write version to VERSION file.

    Args:
        version: Semantic version string
    """
    version_file = Path(__file__).parent.parent / "VERSION"
    version_file.write_text(version + "\n")
    print(f"✅ Wrote version {version} to VERSION file")


if __name__ == "__main__":
    version = get_version()
    print(f"Current version: {version}")

    # Update VERSION file
    write_version_file(version)
