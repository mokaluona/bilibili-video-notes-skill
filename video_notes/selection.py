"""Task-neutral contact sheets, subtitle excerpts and explicit selection."""
from pathlib import Path
import re
import subprocess
from PIL import Image, ImageDraw
from .storage import read, write, digest
from .assets import register, assert_active

def contacts(run):
    assert_active(run)
    items = read(Path(run['workspace']) / 'available-frames.json')
    result = []
    root = Path(run['frames']).resolve()
    for start in range(0, len(items), 16):
        sheet = Image.new('RGB', (1280, 840), '#eeeeee')
        draw = ImageDraw.Draw(sheet)
        for i, item in enumerate(items[start:start+16]):
            path = (root / item['path']).resolve()
            if not path.is_relative_to(root) or digest(path) != item['sha256']:
                raise ValueError('Contact source changed or escapes root')
            with Image.open(path) as source:
                image = source.convert('RGB')
                image.thumbnail((316, 178))
            x, y = (i % 4) * 320, (i // 4) * 210
            sheet.paste(image, (x, y))
            draw.text((x+4, y+180), item['asset_id'], fill='black')
        target = Path(run['workspace']) / f'contact-{start//16+1}.jpg'
        sheet.save(target)
        result.append(str(target))
    register(run, result, 'render_temp')
    return {'contact_sheets': result, 'frames': len(items)}

def excerpt(run, start, end):
    if start < 0 or end <= start:
        raise ValueError('Invalid subtitle interval')
    result = []
    for line in Path(run['subtitle']).read_text(encoding='utf-8-sig').splitlines():
        match = re.match(r'\[(\d+)m(\d+)s\]\s*(.*)', line)
        if match and start <= int(match[1])*60+int(match[2]) < end:
            result.append(line)
    return {'start': start, 'end': end, 'lines': result}

def select(run, plan_path):
    assert_active(run)
    inventory = read(Path(run['workspace']) / 'available-frames.json')
    by_id = {x['asset_id']: x for x in inventory}
    chosen = []
    topic_ids = {t['id'] for t in read(run['topics'])['topics']}
    for choice in read(plan_path)['frames']:
        item = by_id[choice['asset_id']]
        root = Path(run['frames']).resolve()
        path = (root / item['path']).resolve()
        if not path.is_relative_to(root) or not set(choice.get('topic_ids', [])).issubset(topic_ids):
            raise ValueError('Selection path or topic reference invalid')
        if digest(path) != item['sha256'] or not choice.get('reason') or not choice.get('topic_ids'):
            raise ValueError('Selection requires unchanged source, topic IDs and reason')
        chosen.append({'frame_id': item['asset_id'], 'path': item['path'], 'sha256': item['sha256'],
                       'topic_ids': choice['topic_ids'], 'reason': choice['reason']})
    if not chosen or len({x['frame_id'] for x in chosen}) != len(chosen):
        raise ValueError('Selection empty or duplicated')
    write(Path(run['workspace']) / 'candidates.json', chosen)
    return {'selected': len(chosen)}

def supplement(run, seconds):
    assert_active(run)
    if seconds < 0:
        raise ValueError('Negative timestamp')
    video = Path(run['workspace']) / f"{run['bvid']}_p{run.get('page', 1)}.mp4"
    name = f'exact-{seconds:010.3f}'.replace('.', '-')
    folder = Path(run['frames']) / 'supplementary'
    folder.mkdir(exist_ok=True)
    image = folder / f'{name}.jpg'
    if image.exists():
        raise ValueError('Supplement already exists; select it instead')
    subprocess.run([run.get('ffmpeg', 'ffmpeg'), '-nostdin', '-n', '-ss', str(seconds), '-i', str(video),
                    '-frames:v', '1', '-q:v', '2', str(image)], capture_output=True, check=True, timeout=60)
    register(run, [image], 'frame_temp')
    path = Path(run['workspace']) / 'available-frames.json'
    items = read(path)
    items.append({'asset_id': name, 'path': str(image.relative_to(run['frames'])), 'sha256': digest(image), 'seconds': seconds})
    write(path, items)
    return items[-1]
