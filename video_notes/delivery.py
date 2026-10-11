"""Review-bound delivery plan, with no silent overwrites."""
import shutil
import uuid
import json
from pathlib import Path
from .storage import read, write, digest
from .quality import report
from .rendering import current_build
from .document import asset_path
from .locks import guarded
from .path_safety import plain_path

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

@guarded
def deliver(run, recover=False):
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
    workspace = Path(run['workspace'])
    journal_path = workspace / 'delivery-attempt.json'
    marker = Path(actual['files'][0]['target'] + '.delivery.json')
    root = Path(run['delivery']).absolute()
    plain_path(marker, root)
    if recover:
        journal = read(journal_path)
        if journal['plan'] != actual or journal['run_id'] != run['run_id'] or (workspace / 'delivery-result.json').exists():
            raise ValueError('Only matching unfinished delivery may be recovered')
        if not marker.exists():
            raise ValueError('No publication claim for this attempt; recovery requires a marker from the same attempt. Re-run deliver without --recover')
        if read(marker).get('attempt_id') != journal['attempt_id']:
            raise ValueError('Publication claim belongs to another run; inspect it before deciding, never take it over')
    else:
        for item in actual['files']:
            if Path(item['target']).exists():
                raise ValueError('Refusing to overwrite delivery artifact')
        if marker.exists():
            raise ValueError('Delivery marker exists; use explicit recovery for incomplete attempt')
        journal = {'run_id': run['run_id'], 'attempt_id': uuid.uuid4().hex, 'plan': actual,
                   'status': 'staging', 'published': [], 'staged': []}
    def save(status, reason=None):
        journal['status'] = status
        if reason:
            journal['reason'] = reason
        write(journal_path, journal)
        plain_path(marker, root)
        if marker.exists() and read(marker).get('attempt_id') != journal['attempt_id']:
            raise ValueError('Foreign delivery marker; refusing overwrite')
        write(marker, {'run_id': run['run_id'], 'attempt_id': journal['attempt_id'], 'status': status,
                       'message': 'Only delivered means complete', 'published': journal['published']})
    stage_dir = workspace / 'delivery-staging' / journal['attempt_id']
    stage_dir.mkdir(parents=True, exist_ok=True)
    if not recover:
        # Journal first records intent; the marker then grants publication right.
        # Dying between the two leaves a preparation record with no claim, which is
        # diagnosable. A marker is never adopted or removed on another attempt's behalf.
        write(journal_path, journal)
        marker.parent.mkdir(parents=True, exist_ok=True)
        plain_path(marker, root)
        try:
            with marker.open('x', encoding='utf-8') as output:
                json.dump({'attempt_id': journal['attempt_id'], 'run_id': run['run_id'], 'status': 'staging'}, output)
        except FileExistsError:
            raise ValueError('Another attempt holds the publication claim; inspect the existing marker, do not take it over')
    try:
        save('staging')
        for i, item in enumerate(actual['files']):
            staged = stage_dir / f'{i}.bin'
            if i >= len(journal['staged']):
                if staged.exists():
                    if digest(staged) != item['sha256']:
                        raise ValueError('Unverified partial staging file; inspect before recovery')
                else:
                    with staged.open('xb') as output, Path(item['source']).open('rb') as source:
                        shutil.copyfileobj(source, output)
                if digest(staged) != item['sha256']:
                    raise ValueError('Source changed during staging')
                journal['staged'].append({**item, 'staged': str(staged)})
                write(journal_path, journal)
        if len(journal['staged']) != len(actual['files']):
            raise ValueError('Incomplete staging; do not publish partial bundle')
        # Re-check current evidence after source copies, before publishing.
        if report(run)['decision'] == 'blocked' or plan(run) != actual:
            raise ValueError('Inputs changed while staging')
        save('publishing')
        ordered = journal['staged'][1:] + journal['staged'][:1]
        for item in ordered:
            target = plain_path(item['target'], root)
            if digest(item['staged']) != item['sha256']:
                raise ValueError('Staging asset changed')
            if str(target) in journal['published']:
                if digest(target) != item['sha256']:
                    raise ValueError('Published file changed; recovery will not overwrite')
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            plain_path(target, root)
            with target.open('xb') as output, Path(item['staged']).open('rb') as source:
                shutil.copyfileobj(source, output)
            if digest(target) != item['sha256']:
                raise ValueError('Delivery copy verification failed')
            journal['published'].append(str(target))
            save('publishing')
        for item in actual['files']:
            plain_path(item['target'], root)
            if digest(item['target']) != item['sha256']:
                raise ValueError('Published bundle changed')
        save('delivered')
    except Exception as error:
        try:
            save('incomplete', str(error))
        except Exception as logging_error:
            # Preserve the primary exception even if the delivery directory is unwritable.
            try:
                write(workspace / 'delivery-failure.json', {'primary_error': str(error),
                      'recording_error': str(logging_error), 'attempt_id': journal['attempt_id']})
            except Exception:
                pass
            if hasattr(error, 'add_note'):
                error.add_note('Incomplete marker could not be updated: ' + str(logging_error))
        raise
    result = {'run_id': run['run_id'], 'status': 'delivered', 'files': actual['files'],
              'marker': str(marker), 'attempt_id': journal['attempt_id']}
    from .assets import register
    try:
        register(run, [x['staged'] for x in journal['staged']], 'render_temp')
    except Exception as error:
        # Bundle is already verified and published. Cleanup bookkeeping is not delivery failure.
        result['warnings'] = [{'check_id': 'staging_registration', 'reason': str(error),
                               'action': 'Inspect staging; unregistered files are retained'}]
    write(Path(run['workspace']) / 'delivery-result.json', result)
    return result
