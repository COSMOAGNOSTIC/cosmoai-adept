import errno
import os


def safe_path(base: str, filename: str) -> str:
    """
    Resolve a path within base, rejecting any attempt to escape via
    '..' sequences, absolute paths, or symlinks pointing outside base.
    This is a mechanical wall - the tool layer, not the prompt layer.

    This validates and returns a path *string* - it does not open
    anything. If a caller resolves a path here and opens it later with a
    plain open(path), there is a TOCTOU window between this check and
    that open() call: something could swap a symlink into place in
    between and the plain open() would follow it, and safe_path() would
    never see it happen. safe_open() below closes that window; use it
    whenever the goal is an open file handle, not just a validated path
    string (list_files() in tools/files.py is a legitimate safe_path()-only
    caller, since it never opens the names it lists).
    """
    path = os.path.realpath(os.path.join(base, filename))
    base_real = os.path.realpath(base) + os.sep
    if not path.startswith(base_real):
        raise ValueError(f"Path escapes sandbox: {filename!r}")
    return path


_MODE_FLAGS = {
    "r": os.O_RDONLY,
    "w": os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
    "a": os.O_WRONLY | os.O_CREAT | os.O_APPEND,
}


def safe_open(base: str, filename: str, mode: str = "r", encoding: str | None = "utf-8"):
    """
    Open a file within base, closing the symlink-swap TOCTOU race that
    safe_path() alone leaves open (see its docstring). Two independent
    checks close it, because they cover different halves of the path:

    1. O_NOFOLLOW on the open() syscall itself. The kernel refuses to
       open the target at all if the *final* path component is a
       symlink - atomically, as part of the same syscall that does the
       open, so there's no window between "check" and "open" to race.
    2. After the fd is open, its actual resolved path - read back via
       /proc/self/fd/<fd>, which reflects what the kernel really
       opened, not a path string this process computed - is
       re-validated against the sandbox root. This is what catches a
       symlink swapped into an *intermediate* directory component
       (e.g. sandbox/foo/bar.txt where 'foo' itself gets replaced by a
       symlink between the safe_path() check and the open); O_NOFOLLOW
       alone does not cover that, since O_NOFOLLOW only governs the
       final component of the path it's given.

    Together these mean: whatever file descriptor this function hands
    back either points inside the sandbox, or the function has already
    raised - there's no path through here that hands back a live fd
    pointing outside the sandbox root.

    Only implemented for POSIX (relies on /proc/self/fd for check #2);
    raises NotImplementedError elsewhere rather than silently skipping
    that half of the check.
    """
    if os.name != "posix":
        raise NotImplementedError("safe_open() requires /proc/self/fd (POSIX only)")

    base_mode = mode[0] if mode and mode[0] != "b" else mode[1:2]
    if base_mode not in _MODE_FLAGS:
        raise ValueError(f"safe_open() only supports 'r'/'w'/'a' modes, got {mode!r}")

    path = safe_path(base, filename)
    base_real = os.path.realpath(base) + os.sep
    flags = _MODE_FLAGS[base_mode] | os.O_NOFOLLOW

    try:
        fd = os.open(path, flags, 0o644)
    except OSError as e:
        if e.errno == errno.ELOOP:
            raise ValueError(f"Path escapes sandbox (symlink): {filename!r}") from e
        raise

    try:
        actual = os.path.realpath(f"/proc/self/fd/{fd}")
        if not actual.startswith(base_real):
            raise ValueError(f"Path escapes sandbox: {filename!r}")
    except BaseException:
        os.close(fd)
        raise

    if "b" in mode:
        return os.fdopen(fd, mode)
    return os.fdopen(fd, mode, encoding=encoding)
