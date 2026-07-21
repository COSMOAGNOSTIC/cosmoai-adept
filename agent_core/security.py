import os


def safe_path(base: str, filename: str) -> str:
    """
    Resolve a path within base, rejecting any attempt to escape via
    '..' sequences, absolute paths, or symlinks pointing outside base.
    This is a mechanical wall - the tool layer, not the prompt layer.
    """
    path = os.path.realpath(os.path.join(base, filename))
    base_real = os.path.realpath(base) + os.sep
    if not path.startswith(base_real):
        raise ValueError(f"Path escapes sandbox: {filename!r}")
    return path
