import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from video_notes.storage import write, read
from video_notes.assets import register, assert_active
from video_notes.continuation import continue_until
from video_notes.pipeline import batch

class Continuation(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.work = self.root / 'work'
        self.frames = self.root / 'frames'
        self.work.mkdir()
        self.frames.mkdir()
        self.run = {'run_id': 'x', 'profile': 'intensive', 'workspace': str(self.work), 'frames': str(self.frames)}
        self.run.update(document=str(self.work / 'document.json'), topics=str(self.work / 'topics.json'), subtitle=str(self.work / 'subtitle.txt'))
        write(self.run['topics'], {'topics': [{'id': 't', 'topic': '测试主题', 'source_refs': ['subtitle 0-1']}]})
        Path(self.run['subtitle']).write_text('source', encoding='utf-8')
        write(self.work / 'candidates.json', [])
        from video_notes.topics import freeze
        freeze(self.run)

    def test_explicit_registry_does_not_adopt_unknown_files(self):
        unknown = self.frames / 'unknown.jpg'
        output = self.frames / 'output.jpg'
        unknown.write_bytes(b'unknown')
        output.write_bytes(b'output')
        register(self.run, [output], 'frame_temp')
        assets = read(self.work / 'asset-manifest.json')['assets']
        self.assertEqual([a['path'] for a in assets], [str(output.resolve())])

    def test_continuation_pauses_before_automatic_build(self):
        with patch('video_notes.continuation.confirmed', return_value=None), patch('video_notes.continuation.pause', return_value={'status': 'awaiting_review', 'kind': 'content'}) as pause, patch('video_notes.continuation.build_run') as build:
            result = continue_until(self.run)
            pause.assert_called_once_with(self.run, 'vision')
            build.assert_not_called()
            self.assertEqual(result['status'], 'awaiting_review')

    def test_completed_blocks_continuation(self):
        write(self.work / 'run-state.json', {'status': 'completed'})
        with self.assertRaises(ValueError):
            continue_until(self.run)
        with self.assertRaises(ValueError):
            assert_active(self.run)

    def test_nested_batch_directories_rejected(self):
        a = {**self.run, 'lock_dir': str(self.root / 'locks'), 'execution': {'download_cpu_slots': 2}}
        b = {**a, 'run_id': 'y', 'workspace': str(self.work / 'nested'), 'frames': str(self.root / 'second-frames')}
        with self.assertRaises(ValueError):
            batch([a, b], 'final')

    def test_reuses_valid_builds_before_page_review_pause(self):
        with patch('video_notes.continuation.confirmed', side_effect=lambda run, kind: None if kind == 'page' else {'status': 'confirmed'}), patch('video_notes.continuation.current_build'), patch('video_notes.continuation.current_render'), patch('video_notes.continuation.pause', return_value={'status': 'awaiting_review', 'kind': 'page'}), patch('video_notes.continuation.build_run') as build, patch('video_notes.continuation.render') as render:
            self.assertEqual(continue_until(self.run)['kind'], 'page')
            build.assert_not_called()
            render.assert_not_called()
