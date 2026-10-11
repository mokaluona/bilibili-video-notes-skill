"""Shared cross-process quotas. Stale locks are diagnosed, never stolen."""
import os
import time
import threading
from functools import wraps
from contextlib import contextmanager
from pathlib import Path
from .storage import write, now
_LOCAL = threading.local()

def guarded(function):
    """Reentrant for this thread, exclusive against other processes/threads."""
    @wraps(function)
    def call(run, *args, **kwargs):
        root = str(Path(run['workspace']).resolve())
        held = getattr(_LOCAL, 'held', set())
        if root in held:
            return function(run, *args, **kwargs)
        with quota(Path(root) / '.locks', 'mutation', timeout=run.get('run_lock_timeout', 0)):
            _LOCAL.held = held | {root}
            try:
                return function(run, *args, **kwargs)
            finally:
                _LOCAL.held = held
    return call

@contextmanager
def quota(root, resource, slots=1, timeout=120):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + timeout
    acquired = None
    while acquired is None:
        for i in range(slots):
            candidate = root / f"{resource}-{i}.lock"
            try:
                candidate.mkdir()
            except FileExistsError:
                continue
            acquired = candidate
            break
        if acquired is None:
            if time.monotonic() >= deadline:
                raise TimeoutError(f"Quota {resource} unavailable; inspect owners in {root}")
            time.sleep(0.1)
    try:
        write(acquired / "owner.json", {"pid": os.getpid(), "created_at": now()})
        yield
    finally:
        owner = acquired / "owner.json"
        if owner.exists():
            owner.unlink()
        acquired.rmdir()
