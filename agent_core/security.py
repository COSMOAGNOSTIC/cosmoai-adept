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


def _win_real_path_from_fd(fd: int) -> str:
    """
    Windows has no /proc/self/fd. GetFinalPathNameByHandleW is the real
    equivalent: it asks the kernel for the actual final path behind an
    already-open handle, not a path string this process computed
    earlier - the same property /proc/self/fd/<fd> re-validation relies
    on in safe_open()'s POSIX branch below.
    """
    import ctypes
    import msvcrt

    handle = msvcrt.get_osfhandle(fd)
    buf = ctypes.create_unicode_buffer(32768)
    length = ctypes.windll.kernel32.GetFinalPathNameByHandleW(handle, buf, len(buf), 0)
    if length == 0 or length >= len(buf):
        raise OSError("GetFinalPathNameByHandleW failed to resolve the open handle's real path")
    path = buf.value
    if path.startswith("\\\\?\\"):
        path = path[4:]
    return path


def safe_open(base: str, filename: str, mode: str = "r", encoding: str | None = "utf-8"):
    """
    Open a file within base, closing the symlink-swap TOCTOU race that
    safe_path() alone leaves open (see its docstring). The approach
    differs by platform because the underlying kernel primitives do:

    POSIX: two independent checks, covering different halves of the path.
    1. O_NOFOLLOW on the open() syscall itself. The kernel refuses to
       open the target at all if the *final* path component is a
       symlink - atomically, as part of the same syscall that does the
       open, so there's no window between "check" and "open" to race.
    2. After the fd is open, its actual resolved path - read back via
       /proc/self/fd/<fd>, which reflects what the kernel really
       opened - is re-validated against the sandbox root. This is what
       catches a symlink swapped into an *intermediate* directory
       component (e.g. sandbox/foo/bar.txt where 'foo' itself gets
       replaced by a symlink between the safe_path() check and the
       open); O_NOFOLLOW alone only governs the final component.

    Windows: os.open() has no O_NOFOLLOW equivalent, so there is no way
    to make the open() call itself atomically refuse a symlinked final
    component. Instead, after the handle is open, GetFinalPathNameByHandleW
    reads back the real path the kernel actually resolved to (via
    _win_real_path_from_fd above) and that is re-validated against the
    sandbox root - the same post-open re-check idea as the POSIX branch,
    just without the O_NOFOLLOW half. This is a narrower guarantee than
    POSIX gets: on POSIX the window is fully closed; on Windows there is
    still a brief window between the open() call and the re-check where
    a symlinked target could theoretically be read from before this
    function raises. In practice this is significantly mitigated by
    Windows requiring an elevated privilege (SeCreateSymbolicLinkPrivilege
    - admin, or Developer Mode) just to create a symlink in the first
    place, which most attacker-controlled processes won't have - but
    this function does not claim POSIX-equivalent atomicity on Windows,
    and that gap is documented here rather than silently assumed away.

    Any other platform: raises NotImplementedError rather than silently
    skipping validation.
    """
    base_mode = mode[0] if mode and mode[0] != "b" else mode[1:2]
    if base_mode not in _MODE_FLAGS:
        raise ValueError(f"safe_open() only supports 'r'/'w'/'a' modes, got {mode!r}")

    path = safe_path(base, filename)
    base_real = os.path.realpath(base) + os.sep
    flags = _MODE_FLAGS[base_mode]

    if os.name == "posix":
        flags |= os.O_NOFOLLOW
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

    elif os.name == "nt":
        flags |= getattr(os, "O_BINARY", 0)
        fd = os.open(path, flags, 0o644)
        try:
            actual = _win_real_path_from_fd(fd)
            if not os.path.normcase(actual).startswith(os.path.normcase(base_real)):
                raise ValueError(f"Path escapes sandbox: {filename!r}")
        except BaseException:
            os.close(fd)
            raise

    else:
        raise NotImplementedError(f"safe_open() is not implemented for platform {os.name!r}")

    if "b" in mode:
        return os.fdopen(fd, mode)
    return os.fdopen(fd, mode, encoding=encoding)
