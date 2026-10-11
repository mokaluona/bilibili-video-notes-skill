"""Review-bound delivery plan, with no silent overwrites."""
import shutil
from pathlib import Path
from .storage import read, write, digest
from .quality import report
from .rendering import current_build
from .document import asset_path

def plan(run):
    root = Path(run['delivery']).resolve()
    rules = root / '目录规范.md'
    category, name = run['category'], run['content_name']
    for value in (category, name, run['output_name']):
        if not value or Path(value).name != value or value in ('.', '..') or '/' in value or '\\' in value:
            raise ValueError('Delivery names must be single path components')
    if not run['output_name'].endswith('.docx'):
        raise ValueError('DOCX output name required')
    build = current_build(run)
    files = [{'source': build['output'], 'target': str(root / category / run['output_name']), 'sha256': build['output_hash']}]
    doc = read(run['document'])
    used = {b['asset_id'] for b in doc['blocks'] if b['type'] == 'image'}
    for asset_id in sorted(used):
        source = asset_path(run['frames'], doc['assets'], asset_id)
        files.append({'source': str(source), 'target': str(root / category / 'attachment' / name / source.name), 'sha256': digest(source)})
    if len({f['target'] for f in files}) != len(files):
        raise ValueError('Attachment filename collision')
    for item in files:
        if not Path(item['target']).resolve().is_relative_to(root):
            raise ValueError('Delivery target escapes root through a link')
    result = {'run_id': run['run_id'], 'rules_path': str(rules), 'rules_hash': digest(rules) if rules.exists() else None,
              'rules_text': rules.read_text(encoding='utf-8-sig') if rules.exists() else None, 'files': files}
    write(Path(run['workspace']) / 'delivery-plan.json', result)
    return result

def policy_reviewed(run, proposal):
    try:
        acknowledgment = read(Path(run['workspace']) / 'delivery-policy-review.json')
        return (acknowledgment.get('rules_hash') == proposal['rules_hash']
                and acknowledgment.get('plan_hash') == digest(Path(run['workspace']) / 'delivery-plan.json')
                and bool(acknowledgment.get('applied_rules')))
    except (OSError, ValueError, KeyError):
        return False

def deliver(run):
    from .assets import assert_active
    assert_active(run)
    if report(run)['decision'] == 'blocked':
        raise ValueError('Quality gates blocked delivery')
    proposed = read(Path(run['workspace']) / 'delivery-plan.json')
    actual = plan(run)
    if proposed != actual:
        raise ValueError('Delivery plan changed; review the new plan')
    if not policy_reviewed(run, actual):
        raise ValueError('Current directory rules and delivery plan must be reviewed')
    for item in actual['files']:
        if Path(item['target']).exists():
            raise ValueError('Refusing to overwrite delivery artifact')
    copied = []
    try:
        for item in actual['files']:
            target = Path(item['target'])
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open('xb') as output, Path(item['source']).open('rb') as source:
                shutil.copyfileobj(source, output)
            copied.append(target)
            if digest(target) != item['sha256']:
                raise ValueError('Delivery copy verification failed')
    except Exception:
        write(Path(run['workspace']) / 'delivery-failure.json', {'copied': [str(p) for p in copied]})
        raise
    result = {'run_id': run['run_id'], 'status': 'delivered', 'files': actual['files']}
    write(Path(run['workspace']) / 'delivery-result.json', result)
    return result
