"""Reuse literal coverage algorithm against generated DOCX text."""
import importlib.util
import sys
import threading
import zipfile
from pathlib import Path
from xml.etree import ElementTree
from .storage import write, digest
from .rendering import current_build
_IMPORT_LOCK = threading.Lock()

def diagnostic(run):
    build = current_build(run)
    result = {'document_hash': digest(run['document']), 'output_hash': build['output_hash'], 'video_type': run['video_type']}
    if run['video_type'] == 'vlog':
        result.update(status='skipped', reason='vlog')
    elif not run.get('subtitle') or not Path(run['subtitle']).is_file():
        result.update(status='unavailable', reason='subtitle unavailable')
    else:
        with zipfile.ZipFile(build['output']) as archive:
            xml = ElementTree.fromstring(archive.read('word/document.xml'))
        text = '\n'.join(n.text or '' for n in xml.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t'))
        script = Path(run['repository']) / 'scripts' / 'verify_docx.py'
        _IMPORT_LOCK.acquire()
        original = list(sys.path)
        try:
            spec = importlib.util.spec_from_file_location('_legacy_diagnostic', script)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            missing, score, total = module.check_subtitle_coverage(text, run['subtitle'], run['video_type'])
        finally:
            sys.path[:] = original
            _IMPORT_LOCK.release()
        result.update(status='measured' if total else 'not_applicable', score=score if total else None,
                      total=total, missing_count=len(missing), subtitle_hash=digest(run['subtitle']))
    write(Path(run['workspace']) / 'literal-diagnostic.json', result)
    return result
