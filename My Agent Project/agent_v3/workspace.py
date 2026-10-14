from __future__ import annotations

import hashlib
import os
import signal
import subprocess
import threading
from pathlib import Path

IGNORED_DIRS = frozenset({
    ".git", "node_modules", "__pycache__", ".venv", "venv", "env", "dist", "build",
    ".mypy_cache", ".pytest_cache", ".ruff_cache", ".agent_v3", ".idea", ".vscode",
})


def sha12(data: bytes) -> str:
    """First 12 hex chars of SHA-256 over the raw bytes."""
    return hashlib.sha256(data).hexdigest()[:12]


class WorkspacePolicy:
    def __init__(self, root: str | os.PathLike):
        self.root = Path(root).expanduser().resolve()

    def resolve(self, path_str: str) -> Path:
        """Resolve against the root, expand ~, and follow symlinks."""
        p = Path(path_str).expanduser()
        if not p.is_absolute():
            p = self.root / p
        return p.resolve()

    def is_inside(self, p: str | os.PathLike) -> bool:
        # normcase makes this case-insensitive on Windows.
        n = os.path.normcase(str(p))
        r = os.path.normcase(str(self.root)).rstrip(os.sep)
        return n == r or n.startswith(r + os.sep)

    def display(self, p: str | os.PathLike) -> str:
        """Workspace-relative POSIX path for paths inside the workspace, else the absolute path."""
        p = Path(p)
        if self.is_inside(p):
            rel = os.path.relpath(p, self.root)
            return "." if rel == "." else Path(rel).as_posix()
        return str(p)

    def active_ignores(self, search_root: Path) -> frozenset[str]:
        """IGNORED_DIRS, unless the search root itself is inside one of them."""
        parts = Path(os.path.relpath(search_root, self.root)).parts if self.is_inside(search_root) \
            else search_root.parts
        return frozenset() if any(part in IGNORED_DIRS for part in parts) else IGNORED_DIRS


class FileState:
    """Thread-safe map of path → sha of the content the agent last saw or wrote."""

    def __init__(self):
        self._shas: dict[str, str] = {}
        self._lock = threading.Lock()

    @staticmethod
    def _key(path: str | os.PathLike) -> str:
        return os.path.normcase(str(path))

    def get(self, path: str | os.PathLike) -> str | None:
        with self._lock:
            return self._shas.get(self._key(path))

    def set(self, path: str | os.PathLike, sha: str) -> None:
        with self._lock:
            self._shas[self._key(path)] = sha


if os.name == "nt":
    import ctypes
    from ctypes import wintypes

    _k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _ntdll = ctypes.WinDLL("ntdll")
    _CREATE_SUSPENDED = 0x00000004
    _JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
    _JobObjectExtendedLimitInformation = 9

    class _BasicLimits(ctypes.Structure):
        _fields_ = [("PerProcessUserTimeLimit", ctypes.c_int64), ("PerJobUserTimeLimit", ctypes.c_int64),
                    ("LimitFlags", wintypes.DWORD), ("MinimumWorkingSetSize", ctypes.c_size_t),
                    ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", wintypes.DWORD),
                    ("Affinity", ctypes.c_size_t), ("PriorityClass", wintypes.DWORD),
                    ("SchedulingClass", wintypes.DWORD)]

    class _ExtendedLimits(ctypes.Structure):
        _fields_ = [("BasicLimitInformation", _BasicLimits), ("IoInfo", ctypes.c_uint64 * 6),
                    ("ProcessMemoryLimit", ctypes.c_size_t), ("JobMemoryLimit", ctypes.c_size_t),
                    ("PeakProcessMemoryUsed", ctypes.c_size_t), ("PeakJobMemoryUsed", ctypes.c_size_t)]

    _k32.CreateJobObjectW.restype = wintypes.HANDLE
    _k32.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
    _k32.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
    _k32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    _k32.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
    _k32.CloseHandle.argtypes = [wintypes.HANDLE]
    _ntdll.NtResumeProcess.argtypes = [wintypes.HANDLE]

    class _Job:
        """Windows Job Object that kills every member when terminated or closed.

        taskkill /T walks parent PIDs, which fails for Git Bash: MSYS fork/exec leaves children
        (e.g. `sleep`) with a dead parent PID. Job membership is inherited regardless of ancestry.
        """

        def __init__(self):
            self.handle = _k32.CreateJobObjectW(None, None)
            if not self.handle:
                raise OSError(ctypes.get_last_error(), "CreateJobObject failed")
            info = _ExtendedLimits()
            info.BasicLimitInformation.LimitFlags = _JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            if not _k32.SetInformationJobObject(self.handle, _JobObjectExtendedLimitInformation,
                                                ctypes.byref(info), ctypes.sizeof(info)):
                self.close()
                raise OSError(ctypes.get_last_error(), "SetInformationJobObject failed")

        def assign(self, process_handle) -> bool:
            return bool(_k32.AssignProcessToJobObject(self.handle, int(process_handle)))

        def terminate(self) -> None:
            if self.handle:
                _k32.TerminateJobObject(self.handle, 1)

        def close(self) -> None:
            if self.handle:
                _k32.CloseHandle(self.handle)     # KILL_ON_JOB_CLOSE: also kills any stragglers
                self.handle = None


def popen_in_tree(argv: list[str], **kwargs) -> subprocess.Popen:
    """subprocess.Popen whose whole descendant tree can be killed with kill_process_tree().

    POSIX: own session/process group. Windows: new process group plus a Job Object; the child is
    created suspended and resumed only after it joined the job, so no descendant can escape.
    """
    if os.name != "nt":
        return subprocess.Popen(argv, start_new_session=True, **kwargs)
    flags = kwargs.pop("creationflags", 0) | subprocess.CREATE_NEW_PROCESS_GROUP | _CREATE_SUSPENDED
    proc = subprocess.Popen(argv, creationflags=flags, **kwargs)
    job = None
    try:
        try:
            job = _Job()
            if not job.assign(proc._handle):      # e.g. an outer job that forbids nesting
                job.close()
                job = None
        except OSError:
            job = None
    finally:
        _ntdll.NtResumeProcess(int(proc._handle))
    proc._agent_job = job                         # type: ignore[attr-defined]
    return proc


def release_process_tree(proc: subprocess.Popen) -> None:
    """Call when a command finished: closing the job also kills any stray background processes."""
    job = getattr(proc, "_agent_job", None)
    if job is not None:
        job.close()


def kill_process_tree(proc: subprocess.Popen) -> None:
    """Kill `proc` and all its descendants."""
    if os.name == "nt":
        job = getattr(proc, "_agent_job", None)
        if job is not None and job.handle:
            job.terminate()
        else:                                      # not in a job: best effort via the parent-PID tree
            try:
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15)
            except (OSError, subprocess.SubprocessError):
                pass
    else:
        try:
            os.killpg(proc.pid, signal.SIGKILL)   # started with start_new_session=True
        except (ProcessLookupError, PermissionError):
            pass
    try:
        proc.kill()
    except OSError:
        pass


class CancelToken:
    """Cooperative cancel flag that also kills registered child processes and runs registered
    callbacks (e.g. closing a model stream blocked in a network read) immediately."""

    def __init__(self):
        self._event = threading.Event()
        self._procs: set[subprocess.Popen] = set()
        self._callbacks: list = []
        self._lock = threading.Lock()

    @property
    def cancelled(self) -> bool:
        return self._event.is_set()

    def wait(self, timeout: float | None = None) -> bool:
        """Sleep up to `timeout`; True as soon as the token is cancelled."""
        return self._event.wait(timeout)

    def cancel(self) -> None:
        self._event.set()
        with self._lock:
            procs = list(self._procs)
            callbacks = list(self._callbacks)
        for proc in procs:
            kill_process_tree(proc)
        for callback in callbacks:
            try:
                callback()
            except Exception:
                pass

    def add_callback(self, callback) -> None:
        with self._lock:
            self._callbacks.append(callback)
        if self._event.is_set():
            try:
                callback()
            except Exception:
                pass

    def remove_callback(self, callback) -> None:
        with self._lock:
            if callback in self._callbacks:
                self._callbacks.remove(callback)

    def register(self, proc: subprocess.Popen) -> None:
        with self._lock:
            self._procs.add(proc)
        if self._event.is_set():
            kill_process_tree(proc)

    def unregister(self, proc: subprocess.Popen) -> None:
        with self._lock:
            self._procs.discard(proc)


def atomic_write_bytes(path: Path, data: bytes) -> None:
    """Write via a temp file in the same folder, fsync, then os.replace."""
    tmp = path.with_name(f".{path.name}.agent_tmp")
    try:
        with open(tmp, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        if path.exists():
            try:
                os.chmod(tmp, path.stat().st_mode & 0o7777)   # keep e.g. the executable bit
            except OSError:
                pass
        os.replace(tmp, path)
    except BaseException:
        try:
            tmp.unlink()
        except OSError:
            pass
        raise
