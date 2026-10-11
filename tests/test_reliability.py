import unittest
import threading
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch
from video_notes.storage import read, write, digest
from video_notes.delivery import plan, deliver
from video_notes.locks import guarded
from video_notes.path_safety import plain_path

class Reliability(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for name in ('work', 'frames', 'delivery'):
            (self.root / name).mkdir()
        self.work = self.root / 'work'
        self.source = self.work / 'final.docx'
        self.source.write_bytes(b'complete document')
        image = self.root / 'frames' / 'one.jpg'
        image.write_bytes(b'image bytes')
        self.run = {'run_id': 'r', 'workspace': str(self.work), 'frames': str(self.root / 'frames'),
                    'delivery': str(self.root / 'delivery'), 'document': str(self.work / 'document.json'),
                    'category': 'Test', 'content_name': 'Fixture', 'output_name': 'fixture.docx'}
        write(self.run['document'], {'assets': {'one': 'one.jpg'}, 'blocks': [{'type': 'image', 'asset_id': 'one'}]})
        self.build_patch = patch('video_notes.delivery.current_build', return_value={'output': str(self.source), 'output_hash': digest(self.source)})
        self.quality_patch = patch('video_notes.delivery.report', return_value={'decision': 'ready'})
        self.build_patch.start(); self.quality_patch.start()
        self.addCleanup(self.build_patch.stop); self.addCleanup(self.quality_patch.stop)
        proposal = plan(self.run)
        self.target = Path(proposal['files'][0]['target'])
        write(self.work / 'delivery-policy-review.json', {'rules_hash': proposal['rules_hash'],
              'plan_hash': digest(self.work / 'delivery-plan.json'), 'applied_rules': 'Test category and attachment folder'})

    def fail_document_publish(self):
        original = Path.open
        def injected(path, mode='r', *args, **kwargs):
            if path == self.target and mode == 'xb':
                raise OSError('Injected final publication failure')
            return original(path, mode, *args, **kwargs)
        with patch.object(Path, 'open', injected):
            with self.assertRaises(OSError):
                deliver(self.run)

    def test_partial_publish_is_visible_and_explicitly_recoverable(self):
        self.fail_document_publish()
        self.assertFalse(self.target.exists())
        self.assertEqual(read(str(self.target) + '.delivery.json')['status'], 'incomplete')
        self.assertFalse((self.work / 'delivery-result.json').exists())
        self.assertEqual(len(read(self.work / 'delivery-attempt.json')['published']), 1)
        result = deliver(self.run, recover=True)
        self.assertEqual(result['status'], 'delivered')
        self.assertEqual(read(result['marker'])['status'], 'delivered')

    def test_recovery_refuses_user_modified_attachment(self):
        self.fail_document_publish()
        journal = read(self.work / 'delivery-attempt.json')
        Path(journal['published'][0]).write_bytes(b'user changes')
        with self.assertRaisesRegex(ValueError, 'Published file changed'):
            deliver(self.run, recover=True)
        self.assertFalse(self.target.exists())

    def test_source_replacement_during_copy_blocks_publication(self):
        from shutil import copyfileobj
        def changed(source, output):
            if Path(source.name) == self.source:
                self.source.write_bytes(b'replaced document')
            return copyfileobj(source, output)
        with patch('video_notes.delivery.shutil.copyfileobj', changed):
            with self.assertRaisesRegex(ValueError, 'Source changed'):
                deliver(self.run)
        self.assertFalse(self.target.exists())
        self.assertEqual(read(str(self.target) + '.delivery.json')['status'], 'incomplete')

    def test_reparse_components_are_rejected(self):
        with patch.object(Path, 'lstat', return_value=SimpleNamespace(st_mode=0o100644, st_file_attributes=0x400)):
            with self.assertRaisesRegex(ValueError, 'reparse'):
                plain_path(self.source, self.work)

    def test_path_escape_is_rejected(self):
        with self.assertRaises(ValueError):
            plain_path(self.root / 'outside', self.work)

    def test_same_run_cannot_mutate_from_two_threads(self):
        ready, release = threading.Event(), threading.Event()
        failures = []
        @guarded
        def hold(run):
            ready.set()
            release.wait(5)
        def worker():
            try:
                hold(self.run)
            except Exception as error:
                failures.append(error)
        thread = threading.Thread(target=worker)
        thread.start()
        try:
            self.assertTrue(ready.wait(2))
            with self.assertRaises(TimeoutError):
                hold(self.run)
        finally:
            release.set(); thread.join(5)
        self.assertEqual(failures, [])
