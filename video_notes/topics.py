"""Freeze source inventory before authored document exists; not a semantic proof."""
from pathlib import Path
from .storage import read, write, digest, now
from .assets import assert_active

def freeze(run):
    assert_active(run)
    if Path(run['document']).exists():
        raise ValueError('Freeze source topics before creating authored document')
    topics = read(run['topics'])['topics']
    if not topics or len({x['id'] for x in topics}) != len(topics):
        raise ValueError('Source topics must be nonempty and unique')
    if any(not x.get('source_refs') or not x.get('topic') for x in topics):
        raise ValueError('Topic labels and source references required')
    candidates = Path(run['workspace']) / 'candidates.json'
    result = {'topics_hash': digest(run['topics']), 'subtitle_hash': digest(run['subtitle']),
              'candidates_hash': digest(candidates), 'created_at': now(), 'run_id': run['run_id']}
    write(Path(run['workspace']) / 'topics-frozen.json', result)
    return result

def validate_frozen(run):
    record = read(Path(run['workspace']) / 'topics-frozen.json')
    if record['run_id'] != run['run_id'] or record['topics_hash'] != digest(run['topics']) or record['subtitle_hash'] != digest(run['subtitle']) or record['candidates_hash'] != digest(Path(run['workspace']) / 'candidates.json'):
        raise ValueError('Source inventory changed; explicitly restart source planning')
    return record
