import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from PIL import Image
from video_notes.storage import write, digest
from video_notes.selection import contacts, select, excerpt
from video_notes.topics import freeze, validate_frozen

class Selection(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.work, self.frames = root / 'work', root / 'frames'
        self.work.mkdir(); self.frames.mkdir()
        image = self.frames / 'one.jpg'
        Image.new('RGB', (400, 200), 'white').save(image)
        write(self.work / 'available-frames.json', [{'asset_id': 'one', 'path': 'one.jpg', 'sha256': digest(image)}])
        self.run = {'run_id': 's', 'workspace': str(self.work), 'frames': str(self.frames), 'document': str(self.work / 'document.json'),
                    'topics': str(self.work / 'topics.json'), 'subtitle': str(self.work / 'subtitle.txt')}
        Path(self.run['subtitle']).write_text('[0m10s] source one\n[0m20s] source two', encoding='utf-8')
        write(self.run['topics'], {'topics': [{'id': 't', 'topic': '主题', 'source_refs': ['10-20']}]})
        self.plan = self.work / 'selection.json'
        write(self.plan, {'frames': [{'asset_id': 'one', 'topic_ids': ['t'], 'reason': '完整画面'}]})

    def test_contact_and_selection(self):
        self.assertEqual(contacts(self.run)['frames'], 1)
        self.assertEqual(select(self.run, self.plan)['selected'], 1)
        self.assertEqual(excerpt(self.run, 10, 20)['lines'], ['[0m10s] source one'])

    def test_source_freeze_invalidates_on_change(self):
        select(self.run, self.plan)
        freeze(self.run)
        validate_frozen(self.run)
        Path(self.run['subtitle']).write_text('changed', encoding='utf-8')
        with self.assertRaises(ValueError):
            validate_frozen(self.run)

    def test_cannot_freeze_after_authored_content(self):
        select(self.run, self.plan)
        Path(self.run['document']).write_text('{}', encoding='utf-8')
        with self.assertRaises(ValueError):
            freeze(self.run)

    def test_changed_candidate_rejected(self):
        (self.frames / 'one.jpg').write_bytes(b'changed')
        with self.assertRaises(ValueError):
            select(self.run, self.plan)
