"""Thin orchestration around existing tools; never signs a review."""
import shutil
import subprocess
import sys
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from .storage import read, write, now, digest
from .locks import quota
from .reviews import confirmed

def execute(run, name, args):
    workspace = Path(run["workspace"])
    workspace.mkdir(parents=True, exist_ok=True)
    record = {"stage": name, "run_id": run["run_id"], "started_at": now(), "status": "running"}
    log = workspace / f"{name}.log"
    try:
        with quota(run["lock_dir"], "download-cpu", run["execution"]["download_cpu_slots"]):
            environment = dict(os.environ)
            for tool in ('ffmpeg', 'ffprobe'):
                if run.get(tool):
                    environment[tool.upper() + '_BIN'] = run[tool]
            with log.open("w", encoding="utf-8") as output:
                subprocess.run([run.get("python", sys.executable), *args], cwd=workspace,
                               stdout=output, stderr=subprocess.STDOUT, check=True,
                               timeout=run.get("stage_timeout", 3600), env=environment)
        record["status"] = "succeeded"
    except Exception as error:
        record.update(status="failed", error=type(error).__name__, message=str(error))
        raise
    finally:
        record["ended_at"] = now()
        record["log_path"] = str(log)
        write(workspace / f"{name}-state.json", record)

def run_until(run, boundary="candidates"):
    from .config import require
    require(run, boundary)
    workspace = Path(run["workspace"])
    workspace.mkdir(parents=True, exist_ok=True)
    state = workspace / "run-state.json"
    if state.exists() and read(state).get("status") == "completed":
        raise ValueError("Completed runs are terminal")
    repo = Path(run["repository"])
    if boundary == "preflight":
        from .preflight import check
        return check(run)
    if boundary in ('sample', 'final', 'deliver', 'completed'):
        from .continuation import continue_until
        return continue_until(run, boundary)
    if boundary != "candidates":
        raise ValueError("First milestone supports preflight/candidates boundaries only")
    if run["profile"] != "intensive":
        raise ValueError("Only intensive acquisition implemented; other profiles must not download a full video implicitly")
    if run_until(run, "preflight")['status'] != 'preflight_passed':
        raise ValueError('Capability preflight failed; inspect preflight.json')
    cookie = workspace / "bilibili_cookies.txt"
    source = Path(run["cookies_source"])
    if source.resolve() != cookie.resolve():
        shutil.copy2(source, cookie)
    execute(run, "acquire-frames", [str(repo / "scripts" / "extract_frames.py"), run["bvid"],
            "--page", str(run.get("page", 1)), "--mode", "scene", "--subtitle",
            "--backup-interval", "30", "--workspace", str(workspace), "--frames", run["frames"]])
    execute(run, "dedup", [str(repo / "scripts" / "smart_select.py"), str(Path(run["frames"]) / "scene"),
            "--output-dir", str(Path(run["frames"]) / "selected"), "--skip-clustering", "--workspace", str(workspace)])
    from .assets import register
    frames_manifest = read(Path(run['frames']) / 'frames_manifest.json')
    register(run, [Path(run['frames']) / f for f in frames_manifest['files']], 'frame_temp')
    selected_outputs = [Path(run['frames']) / 'selected' / Path(f).name for f in frames_manifest['files']]
    register(run, [p for p in selected_outputs if p.is_file()], 'frame_temp')
    # Exact filename belongs to this acquisition, not a workspace-wide extension scan.
    register(run, [workspace / f"{run['bvid']}_p{run.get('page', 1)}.mp4"], 'media_temp')
    subtitle = workspace / f"{run['bvid']}_p{run.get('page', 1)}_subtitles.txt"
    if subtitle.exists():
        register(run, [subtitle], 'subtitle')
    # Candidate discovery is not a decision that every image belongs in the note.
    write(workspace / "available-frames.json", [{"asset_id": p.stem, "path": str(p.relative_to(run["frames"])),
            "sha256": digest(p)} for p in sorted((Path(run["frames"]) / "selected").glob("*.jpg"))])
    result = {"run_id": run["run_id"], "status": "awaiting_review", "boundary": "candidates",
              "next": "Establish source topics and select candidates.json before requesting visual review"}
    write(state, result)
    return result

def batch(runs, boundary):
    if len({r["workspace"] for r in runs}) != len(runs) or len({r["frames"] for r in runs}) != len(runs):
        raise ValueError("Batch runs must have distinct workspace and frame paths")
    if len({r["lock_dir"] for r in runs}) != 1:
        raise ValueError("Batch runs must share one lock directory")
    if len({r["execution"]["download_cpu_slots"] for r in runs}) != 1:
        raise ValueError("Batch quotas must agree")
    roots = [(r['run_id'], Path(r[k]).resolve()) for r in runs for k in ('workspace', 'frames')]
    for i, (owner, root) in enumerate(roots):
        for other, path in roots[i+1:]:
            if root.is_relative_to(path) or path.is_relative_to(root):
                raise ValueError('Run workspace and frame roots must not overlap')
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(run_until, r, boundary) for r in runs]
        results = []
        for run, future in zip(runs, futures):
            try:
                results.append(future.result())
            except Exception as error:
                results.append({"run_id": run["run_id"], "status": "failed", "message": str(error)})
        return results
