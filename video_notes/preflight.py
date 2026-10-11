"""Local capabilities probe; no downloads or credential contents."""
import subprocess
import sys
import shutil
from pathlib import Path
from .storage import write

def check(run):
    checks = []
    def probe(name, command):
        try:
            result = subprocess.run(command, capture_output=True, timeout=30, check=False)
            checks.append({'check_id': name, 'status': 'pass' if result.returncode == 0 else 'fail'})
        except (OSError, subprocess.TimeoutExpired):
            checks.append({'check_id': name, 'status': 'fail'})
    python = run.get('python', sys.executable)
    probe('python_dependencies', [python, '-c', 'import yt_dlp, PIL, docx, pdf2image, imagehash, rapidocr_onnxruntime, requests'])
    for tool in ('ffmpeg', 'ffprobe'):
        probe(tool, [run.get(tool, shutil.which(tool) or tool), '-version'])
    poppler = run.get('poppler')
    probe('poppler', [str(Path(poppler) / 'pdftoppm.exe') if poppler else 'pdftoppm', '-v'])
    probe('word_com', [run.get('powershell', 'powershell.exe'), '-NoProfile', '-Command',
          '$ErrorActionPreference="Stop"; $w=New-Object -ComObject Word.Application; try {if($w.Documents.Count -ne 0){throw "Unexpected documents"}} finally {if($w.Documents.Count -eq 0){$w.Quit()};[void][Runtime.InteropServices.Marshal]::ReleaseComObject($w)}'])
    checks.append({'check_id': 'cookies_path', 'status': 'pass' if Path(run['cookies_source']).is_file() else 'fail'})
    for name in ('extract_frames.py', 'smart_select.py'):
        checks.append({'check_id': name, 'status': 'pass' if (Path(run['repository']) / 'scripts' / name).is_file() else 'fail'})
    result = {'run_id': run['run_id'], 'scope': 'local_capabilities', 'checks': checks,
              'status': 'preflight_passed' if all(c['status'] == 'pass' for c in checks) else 'failed',
              'format_preflight': 'Performed by existing acquisition tool before download; no network probe here'}
    write(Path(run['workspace']) / 'preflight.json', result)
    return result
