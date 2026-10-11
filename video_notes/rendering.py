"""Version-bound build and render records; review remains a separate operation."""
import subprocess
from pathlib import Path
from dataclasses import asdict
import uuid
from .storage import read, write, digest
from .document import build, StyleProfile
from .locks import quota

def build_run(run, sample=False):
    from .assets import assert_active, register
    assert_active(run)
    if not sample:
        from .reviews import confirmed
        if not confirmed(run, 'sample_page'):
            raise ValueError('Current sample page review required before full build')
    style = StyleProfile(**read(run['style'])) if run.get('style') else StyleProfile()
    output = Path(run['workspace']) / ('sample.docx' if sample else 'final.docx')
    result = build(read(run['document']), output, run['frames'], style, sample)
    assets = read(run['document']).get('assets', {})
    result.update(document_hash=digest(run['document']), output_hash=digest(output),
                  style=asdict(style), assets={key: digest(Path(run['frames']) / path) for key, path in assets.items()})
    write(Path(run['workspace']) / ('sample-build.json' if sample else 'final-build.json'), result)
    register(run, [output], 'build')
    return result

def current_build(run, sample=False):
    record = read(Path(run['workspace']) / ('sample-build.json' if sample else 'final-build.json'))
    style = StyleProfile(**read(run['style'])) if run.get('style') else StyleProfile()
    if record['document_hash'] != digest(run['document']) or record['output_hash'] != digest(record['output']) or record['style'] != asdict(style):
        raise ValueError('Build record is stale')
    assets = read(run['document']).get('assets', {})
    if record['assets'] != {key: digest(Path(run['frames']) / path) for key, path in assets.items()}:
        raise ValueError('Build assets changed')
    return record

def render(run, sample=False):
    from .assets import assert_active, register
    assert_active(run)
    record = current_build(run, sample)
    folder = Path(run['workspace']) / ('render-sample' if sample else 'render-final') / uuid.uuid4().hex
    folder.mkdir(parents=True, exist_ok=True)
    pdf = folder / 'rendered.pdf'
    # Fresh attempt directory: prior outputs stay registered for Recycle Bin cleanup.
    script = Path(__file__).with_name('render_word.ps1')
    with quota(run['lock_dir'], 'word-render', timeout=run.get('lock_timeout', 120)):
        try:
            subprocess.run([run.get('powershell', 'powershell.exe'), '-NoProfile', '-File', str(script),
                            '-InputDocx', record['output'], '-OutputPdf', str(pdf)],
                           capture_output=True, check=True, timeout=run.get('render_timeout', 180))
        except subprocess.TimeoutExpired as error:
            # subprocess only terminates its own helper; never kill WINWORD globally.
            write(folder / 'failure.json', {'status': 'failed', 'reason': 'Word timeout; owned COM cleanup may need attention'})
            raise TimeoutError('Word export timed out; no successful render record') from error
        from pdf2image import convert_from_path
        pages = convert_from_path(str(pdf), dpi=120, poppler_path=run.get('poppler'))
        paths = []
        for i, page in enumerate(pages, 1):
            path = folder / f'page-{i}.png'
            page.save(path)
            paths.append(str(path))
        if not paths:
            raise ValueError('Render contains no pages')
        artifact = {'schema_version': 1, 'document_path': record['output'], 'document_hash': record['output_hash'],
                    'content_hash': record['document_hash'], 'renderer': 'word', 'pdf': str(pdf), 'pdf_hash': digest(pdf),
                    'pages': len(paths), 'page_images': paths, 'page_hashes': [digest(p) for p in paths]}
        artifact_path = Path(run['workspace']) / ('sample-render.json' if sample else 'final-render.json')
        write(artifact_path, artifact)
        register(run, [pdf, *paths], 'render_temp')
        return artifact

def current_render(run, sample=False):
    record = current_build(run, sample)
    artifact = read(Path(run['workspace']) / ('sample-render.json' if sample else 'final-render.json'))
    if artifact['document_hash'] != record['output_hash'] or artifact['pdf_hash'] != digest(artifact['pdf']):
        raise ValueError('Render record is stale')
    if artifact['pages'] != len(artifact['page_images']) or artifact['page_hashes'] != [digest(p) for p in artifact['page_images']]:
        raise ValueError('Rendered pages changed')
    return artifact
