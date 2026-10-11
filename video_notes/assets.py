"""Register only explicit stage outputs, never arbitrary directory contents."""
from pathlib import Path
from .storage import read, write, digest

def is_credential(run, path):
    path = Path(path).resolve()
    declared = [run.get('cookies_source'), *(run.get('credential_paths', []))]
    declared.append(str(Path(run['workspace']) / 'bilibili_cookies.txt'))
    return path.name in ('bilibili_cookies.txt', '.env') or any(path == Path(p).resolve() for p in declared if p)

def register(run, paths, category):
    manifest_path = Path(run['workspace']) / 'asset-manifest.json'
    manifest = read(manifest_path) if manifest_path.exists() else {'schema_version': 1, 'assets': []}
    known = {a['path']: a for a in manifest['assets']}
    for raw in paths:
        path = Path(raw).resolve()
        roots = [Path(run[x]).resolve() for x in ('workspace', 'frames')]
        if not any(path.is_relative_to(root) for root in roots) or not path.is_file():
            raise ValueError('Stage asset must exist within run roots')
        if is_credential(run, path):
            raise ValueError('Credential may not enter asset registry')
        item = {'run_id': run['run_id'], 'path': str(path), 'category': category, 'sha256': digest(path)}
        old = known.get(str(path))
        if old and old['run_id'] != run['run_id']:
            raise ValueError('Foreign asset registration')
        known[str(path)] = item
    manifest['assets'] = list(known.values())
    write(manifest_path, manifest)
    return manifest

def assert_active(run):
    path = Path(run['workspace']) / 'run-state.json'
    if path.exists() and read(path).get('status') == 'completed':
        raise ValueError('Completed runs are terminal')
