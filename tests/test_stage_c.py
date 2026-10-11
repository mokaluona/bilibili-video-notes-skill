import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from video_notes.storage import write, digest
from video_notes.rendering import build_run, current_build
from video_notes.retention import plan

class StageC(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.run = {'workspace': str(self.root), 'frames': str(self.root / 'frames'), 'run_id': 'c', 'document': str(self.root / 'document.json')}
        write(self.run['document'], {'schema_version': 1, 'metadata': {'title': '阶段测试'}, 'blocks': [{'id': 'p', 'type': 'paragraph', 'text': '合成测试正文'}]})

    def test_full_build_requires_sample_review(self):
        with self.assertRaises(ValueError):
            build_run(self.run)

    def test_changed_content_invalidates_sample_build(self):
        build_run(self.run, True)
        current_build(self.run, True)
        write(self.run['document'], {'schema_version': 1, 'blocks': []})
        with self.assertRaises(ValueError):
            current_build(self.run, True)

    def test_cleanup_keeps_unknown_files_and_rejects_credentials(self):
        target = self.root / 'delivered.docx'
        target.write_bytes(b'delivery')
        write(self.root / 'delivery-result.json', {'run_id': 'c', 'status': 'delivered', 'files': [{'target': str(target), 'sha256': digest(target)}]})
        unknown = self.root / 'unknown.mp4'
        unknown.write_bytes(b'unknown')
        write(self.root / 'asset-manifest.json', {'assets': []})
        self.assertEqual(plan(self.run), [])
        self.assertTrue(unknown.exists())
        cookie = self.root / 'bilibili_cookies.txt'
        cookie.write_bytes(b'placeholder')
        write(self.root / 'asset-manifest.json', {'assets': [{'run_id': 'c', 'path': str(cookie), 'category': 'media_temp', 'sha256': digest(cookie)}]})
        with self.assertRaises(ValueError):
            plan(self.run)
