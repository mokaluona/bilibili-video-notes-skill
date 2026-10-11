"""Shared cross-process quotas. Stale locks are diagnosed, never stolen."""
import os
import time
from contextlib import contextmanager
from pathlib import Path
from .storage import write, now

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
