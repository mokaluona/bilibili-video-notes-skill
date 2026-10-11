import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from video_notes.pipeline import execute
from video_notes.domain import validate_identity
from video_notes.storage import read, write, digest
from video_notes.delivery import policy_reviewed
from video_notes.config import require
from video_notes.assets import register

class ReviewFixes(unittest.TestCase):
    def test_stage_files_are_distinct_and_error_state_is_saved(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            run = {'run_id': 'r', 'workspace': str(root), 'lock_dir': str(root / 'locks'),
                   'execution': {'download_cpu_slots': 2}, 'ffmpeg': 'configured', 'ffprobe': 'configured'}
            with patch('video_notes.pipeline.subprocess.run'):
                execute(run, 'acquire-frames', ['fake'])
                execute(run, 'dedup', ['fake'])
            self.assertEqual(read(root / 'acquire-frames-state.json')['stage'], 'acquire-frames')
            self.assertEqual(read(root / 'dedup-state.json')['stage'], 'dedup')
            self.assertFalse((root / 'ffprobe-state.json').exists())
            with patch('video_notes.pipeline.subprocess.run', side_effect=RuntimeError('test failure')):
                with self.assertRaises(RuntimeError):
                    execute(run, 'failed-stage', ['fake'])
            self.assertEqual(read(root / 'failed-stage-state.json')['status'], 'failed')

    def test_agent_cannot_claim_independent_review(self):
        with self.assertRaises(ValueError):
            validate_identity({'kind': 'agent', 'id': 'a', 'independence': 'independent'})
        validate_identity({'kind': 'agent', 'id': 'a', 'independence': 'self_review'})

    def test_policy_checks_all_fields(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            run = {'workspace': str(root)}
            proposal = {'rules_hash': 'rules'}
            write(root / 'delivery-plan.json', proposal)
            write(root / 'delivery-policy-review.json', {'plan_hash': digest(root / 'delivery-plan.json')})
            self.assertFalse(policy_reviewed(run, proposal))
            write(root / 'delivery-policy-review.json', {'plan_hash': digest(root / 'delivery-plan.json'), 'rules_hash': 'rules', 'applied_rules': 'category and attachments'})
            self.assertTrue(policy_reviewed(run, proposal))

    def test_missing_fields_name_the_stage(self):
        with self.assertRaisesRegex(ValueError, 'Stage deliver missing fields'):
            require({}, 'deliver')

    def test_renamed_declared_credentials_are_rejected(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            secret = root / 'renamed.txt'
            secret.write_text('placeholder')
            run = {'workspace': str(root), 'frames': str(root), 'run_id': 'r', 'cookies_source': str(secret)}
            with self.assertRaises(ValueError):
                register(run, [secret], 'media_temp')
