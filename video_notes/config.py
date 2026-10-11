from pathlib import Path
from .storage import read

def require(run, stage):
    fields = {'preflight': ('cookies_source',), 'candidates': ('cookies_source', 'bvid'),
              'select': ('topics',), 'supplement': ('bvid',), 'excerpt': ('subtitle',),
              'freeze-topics': ('topics', 'subtitle', 'document'),
              'sample': ('topics', 'subtitle', 'document'), 'final': ('topics', 'subtitle', 'document'),
              'build-run': ('document',), 'render': ('document',), 'diagnose': ('document',),
              'validate': ('document', 'topics', 'subtitle'),
              'delivery-plan': ('document', 'category', 'content_name', 'output_name'),
              'deliver': ('document', 'topics', 'subtitle', 'category', 'content_name', 'output_name'),
              'completed': ('document', 'topics', 'subtitle', 'category', 'content_name', 'output_name')}.get(stage, ())
    missing = [field for field in fields if not run.get(field)]
    if missing:
        raise ValueError(f"Stage {stage} missing fields: {', '.join(missing)}")

def load(path):
    path = Path(path).resolve()
    task = read(path)
    machine = read(path.parent / task["machine_config"]) if task.get("machine_config") else {}
    run = {**machine, **task}
    missing = [field for field in ('workspace', 'frames', 'delivery', 'repository', 'lock_dir') if not run.get(field)]
    if missing:
        raise ValueError('Run configuration missing fields: ' + ', '.join(missing))
    if run.get("schema_version") != 1 or not run.get("run_id"):
        raise ValueError("RunSpec v1 and run_id required")
    if run.get("profile") not in {"intensive", "overview", "summary"}:
        raise ValueError("Invalid profile")
    if run.get("video_type") not in {"lecture", "opinion", "vlog"}:
        raise ValueError("Invalid video_type")
    for name in ("workspace", "frames", "delivery", "repository", "lock_dir"):
        p = Path(run[name])
        run[name] = str((path.parent / p).resolve() if not p.is_absolute() else p.resolve())
    if not run["frames"].isascii():
        raise ValueError("Frame root must contain only ASCII characters")
    if len({run["workspace"], run["frames"], run["delivery"]}) != 3:
        raise ValueError("Workspace, frames and delivery must be distinct")
    for name in ("cookies_source", "topics", "document", "render_artifact", "subtitle", "legacy_config", "style"):
        if run.get(name):
            p = Path(run[name])
            run[name] = str((path.parent / p).resolve() if not p.is_absolute() else p.resolve())
    run["execution"] = {"download_cpu_slots": 2, **run.get("execution", {})}
    run['credential_paths'] = [str((path.parent / Path(p)).resolve()) for p in run.get('credential_paths', [])]
    if run["execution"]["download_cpu_slots"] not in (1, 2):
        raise ValueError("download_cpu_slots must be 1 or 2")
    return run
