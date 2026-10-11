"""Live gates and structured diagnostics; never cache delivery eligibility."""
from pathlib import Path
from .reviews import confirmed
from .storage import read, write, now, digest
from .rendering import current_build, current_render
from .domain import validate_document

def report(run):
    checks = []
    def gate(name, function):
        try:
            function()
            checks.append({'check_id': name, 'status': 'pass', 'blocking': True})
        except (OSError, ValueError, KeyError) as error:
            checks.append({'check_id': name, 'status': 'fail', 'blocking': True, 'reason': str(error)})
    gate('document_contract', lambda: validate_document(read(run['document'])))
    from .topics import validate_frozen
    gate('source_inventory_frozen', lambda: validate_frozen(run))
    gate('current_build', lambda: current_build(run))
    gate('current_render', lambda: current_render(run))
    for kind in ('vision', 'content', 'sample_page', 'page'):
        result = confirmed(run, kind)
        check = {'check_id': kind + '_review', 'method': 'review_record_validation',
                 'status': 'pass' if result else 'fail', 'blocking': True}
        if result:
            check['reviewer'] = result['reviewer']
            check['observed'] = len(set(result['pages_reviewed'])) if 'pages_reviewed' in result else len(result.get('topics', result.get('records', [])))
        checks.append(check)
    try:
        data = read(Path(run['workspace']) / 'literal-diagnostic.json')
        build = current_build(run)
        if data['document_hash'] != digest(run['document']) or data['output_hash'] != build['output_hash'] or data['video_type'] != run['video_type']:
            raise ValueError('Stale diagnostic')
        if data.get('subtitle_hash') and data['subtitle_hash'] != digest(run['subtitle']):
            raise ValueError('Subtitle changed')
        threshold = .75 if run['video_type'] == 'lecture' else .5
        status = 'skipped' if data['status'] in ('skipped', 'not_applicable') else 'warning' if data['status'] == 'unavailable' or data['score'] < threshold else 'pass'
        checks.append({'check_id': 'literal_match', 'status': status, 'blocking': False,
                       'observed': data.get('score'), 'threshold': None if run['video_type'] == 'vlog' else threshold,
                       'reason': data.get('reason', data['status'])})
    except FileNotFoundError as error:
        checks.append({'check_id': 'literal_match', 'status': 'not_run', 'blocking': True, 'reason': 'Run diagnose; diagnostic or required input missing: ' + str(error)})
    except (OSError, ValueError, KeyError) as error:
        checks.append({'check_id': 'literal_match', 'status': 'fail', 'blocking': True, 'reason': str(error)})
    if run['profile'] != 'intensive':
        checks.append({'check_id': 'profile_support', 'status': 'fail', 'blocking': True, 'reason': 'Only intensive end-to-end implemented'})
    result = {'schema_version': 1, 'run_id': run['run_id'], 'created_at': now(), 'checks': checks,
              'decision': 'blocked' if any(c['blocking'] and c['status'] not in ('pass', 'skipped') for c in checks) else
              'ready_with_disclosure' if any(c['status'] == 'warning' for c in checks) else 'ready'}
    write(Path(run['workspace']) / 'quality-report.json', result)
    return result
