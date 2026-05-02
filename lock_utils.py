import os
import threading
from contextlib import contextmanager

if os.name == 'nt':  # pragma: no cover - Windows specific
    import msvcrt
else:  # pragma: no cover - POSIX specific
    import fcntl


class CrossProcessFileLock:
    """
    Minimal cross-platform advisory lock built on OS primitives so CSV writes
    remain safe even when multiple processes attempt to write simultaneously.
    """

    def __init__(self, target_path):
        self.lock_path = f"{target_path}.lock"
        self._handle = None
        self._thread_lock = threading.RLock()

    def acquire(self):
        os.makedirs(os.path.dirname(self.lock_path) or ".", exist_ok=True)
        self._thread_lock.acquire()
        self._handle = open(self.lock_path, "a+b")
        if os.name == 'nt':
            self._handle.seek(0)
            self._handle.write(b"\0")
            self._handle.flush()
            msvcrt.locking(self._handle.fileno(), msvcrt.LK_LOCK, 1)
        else:
            fcntl.flock(self._handle, fcntl.LOCK_EX)

    def release(self):
        try:
            if not self._handle:
                return
            if os.name == 'nt':
                msvcrt.locking(self._handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(self._handle, fcntl.LOCK_UN)
            self._handle.close()
        finally:
            self._handle = None
            self._thread_lock.release()

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.release()


@contextmanager
def file_lock(path):
    lock = CrossProcessFileLock(path)
    lock.acquire()
    try:
        yield
    finally:
        lock.release()


__all__ = ["file_lock", "CrossProcessFileLock"]


