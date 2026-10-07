"""Filesystem checks for private transcript inventory output."""

from pathlib import Path


def private_map_destination(path: Path, *repository_roots: Path) -> Path:
    """Resolve a map destination and reject writes into either checkout."""
    destination = path.resolve()
    if any(destination.is_relative_to(root.resolve()) for root in repository_roots):
        raise ValueError("private source map must be outside the repository")
    return destination
