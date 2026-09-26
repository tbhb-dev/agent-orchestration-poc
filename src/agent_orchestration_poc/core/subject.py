"""Validate plain bus subject names without side effects."""


def valid(name: str) -> bool:
    """Return whether name is a plain bus subject of at most 255 bytes."""
    if not name or len(name.encode("utf-8")) > 255:
        return False
    for token in name.split("."):
        if not token:
            return False
        for char in token:
            if not ("a" <= char <= "z" or "0" <= char <= "9" or char in "-_"):
                return False
    return True
