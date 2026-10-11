"""Individual, registered temporary files only; unknown files always retained."""
import subprocess
from pathlib import Path
from .storage import read, write, digest
from .path_safety import plain_path
from .locks import guarded

def plan(run):
    delivered = read(Path(run['workspace']) / 'delivery-result.json')
    if delivered['run_id'] != run['run_id'] or delivered['status'] != 'delivered':
        raise ValueError('Successful delivery required')
    if delivered.get('marker'):
        marker = read(delivered['marker'])
        if marker.get('status') != 'delivered' or marker.get('attempt_id') != delivered['attempt_id']:
            raise ValueError('Delivery completion marker missing or changed')
    for item in delivered['files']:
        if digest(item['target']) != item['sha256']:
            raise ValueError('Delivery missing or changed')
    roots = [plain_path(Path(run[x]).absolute(), Path(run[x]).absolute()) for x in ('workspace', 'frames')]
    targets = []
    manifest = read(Path(run['workspace']) / 'asset-manifest.json')
    for item in manifest['assets']:
        if item.get('category') not in ('media_temp', 'frame_temp', 'render_temp'):
            continue
        if item['run_id'] != run['run_id']:
            raise ValueError('Foreign asset')
        raw = Path(item['path']).absolute()
        matching = [root for root in roots if raw.is_relative_to(root)]
        if not matching:
            raise ValueError('Cleanup asset outside run roots')
        path = plain_path(raw, matching[0])
        if not any(path.is_relative_to(root) and path != root for root in roots) or path.is_symlink() or not path.is_file():
            raise ValueError('Invalid cleanup target')
        from .assets import is_credential
        if is_credential(run, path):
            raise ValueError('Credential cleanup prohibited')
        if digest(path) != item['sha256']:
            raise ValueError('Asset changed')
        targets.append({'path': str(path), 'sha256': item['sha256']})
    write(Path(run['workspace']) / 'cleanup-plan.json', targets)
    return targets

@guarded
def execute(run):
    path = Path(run['workspace']) / 'cleanup-plan.json'
    previous = read(path)
    if previous != plan(run):
        raise ValueError('Cleanup plan changed')
    try:
        subprocess.run([run.get('powershell', 'powershell.exe'), '-NoProfile', '-File', str(Path(__file__).with_name('recycle.ps1')),
                        '-Plan', str(path)], check=True, capture_output=True, timeout=120)
    except Exception as error:
        write(Path(run['workspace']) / 'cleanup-result.json', {'status': 'warning', 'reason': str(error)})
        raise
    result = {'status': 'completed', 'recycled': len(previous)}
    write(Path(run['workspace']) / 'cleanup-result.json', result)
    write(Path(run['workspace']) / 'run-state.json', {'run_id': run['run_id'], 'status': 'completed'})
    return result
