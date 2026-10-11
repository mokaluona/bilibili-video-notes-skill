"""Execute automatic stages up to a real review or requested boundary."""
from pathlib import Path
from .storage import read, write
from .assets import assert_active
from .reviews import confirmed, request, inputs
from .rendering import current_build, current_render, build_run, render
from .diagnostics import diagnostic
from .quality import report
from .delivery import plan, deliver, policy_reviewed
from .retention import plan as cleanup_plan, execute as cleanup_execute

def valid(function):
    try:
        function()
        return True
    except (OSError, ValueError, KeyError):
        return False

def pause(run, kind):
    path = Path(run['workspace']) / 'reviews' / f'{kind}-request.json'
    if path.exists() and valid(lambda: inputs(run, kind)) and read(path)['inputs'] == inputs(run, kind):
        req = read(path)
    else:
        req = request(run, kind)
    result = {'run_id': run['run_id'], 'status': 'awaiting_review', 'kind': kind, 'request_id': req['request_id']}
    write(Path(run['workspace']) / 'run-state.json', result)
    return result

def continue_until(run, boundary='final'):
    assert_active(run)
    if run['profile'] != 'intensive':
        raise ValueError('Only intensive continuation implemented')
    from .topics import validate_frozen
    validate_frozen(run)
    for kind in ('vision', 'content'):
        if not confirmed(run, kind):
            return pause(run, kind)
    if not valid(lambda: current_build(run, True)):
        build_run(run, True)
    if not valid(lambda: current_render(run, True)):
        render(run, True)
    if not confirmed(run, 'sample_page'):
        return pause(run, 'sample_page')
    if boundary == 'sample':
        return {'run_id': run['run_id'], 'status': 'succeeded', 'boundary': boundary}
    if not valid(lambda: current_build(run)):
        build_run(run)
    if not valid(lambda: current_render(run)):
        render(run)
    if not confirmed(run, 'page'):
        return pause(run, 'page')
    diagnostic(run)
    quality = report(run)
    if quality['decision'] == 'blocked':
        return {'run_id': run['run_id'], 'status': 'failed', 'quality': quality}
    if boundary == 'final':
        return {'run_id': run['run_id'], 'status': 'succeeded', 'boundary': boundary, 'quality': quality}
    delivered_path = Path(run['workspace']) / 'delivery-result.json'
    if not delivered_path.exists():
        proposed = plan(run)
        if not policy_reviewed(run, proposed):
            return {'run_id': run['run_id'], 'status': 'awaiting_review', 'kind': 'delivery_policy', 'plan': proposed}
        deliver(run)
    if boundary == 'deliver':
        return read(delivered_path)
    # Cleanup is explicit only when caller requests --until completed.
    cleanup_plan(run)
    return cleanup_execute(run)
