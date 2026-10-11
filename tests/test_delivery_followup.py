from pathlib import Path
from unittest.mock import patch
from test_reliability import Reliability
from video_notes.delivery import deliver
from video_notes.storage import read, write
import unittest

def load_tests(loader, tests, pattern):
    # Reuse fixture without counting inherited/imported reliability tests twice.
    return unittest.TestSuite(Followup(name) for name in (
        'test_registration_failure_is_warning_after_success',
        'test_marker_failure_does_not_mask_primary_failure',
        'test_crash_before_claim_leaves_intent_without_publication_right',
        'test_existing_marker_is_not_adopted_or_removed',
        'test_lost_claim_race_does_not_take_over_marker'))

class Followup(Reliability):
    # Shared fixture and existing fault tests also exercise the updated implementation.
    def marker(self):
        return Path(str(self.target) + '.delivery.json')

    def test_registration_failure_is_warning_after_success(self):
        with patch('video_notes.assets.register', side_effect=OSError('staging unavailable')):
            result = deliver(self.run)
        self.assertEqual(result['status'], 'delivered')
        self.assertEqual(result['warnings'][0]['check_id'], 'staging_registration')
        self.assertEqual(read(self.work / 'delivery-result.json')['status'], 'delivered')
        self.assertEqual(read(result['marker'])['status'], 'delivered')

    def test_marker_failure_does_not_mask_primary_failure(self):
        from video_notes.storage import write
        original_open = Path.open
        def fail_publish(path, mode='r', *args, **kwargs):
            if path == self.target and mode == 'xb':
                raise OSError('PRIMARY publish failure')
            return original_open(path, mode, *args, **kwargs)
        def fail_marker(path, value):
            if str(path).endswith('.delivery.json') and value.get('status') == 'incomplete':
                raise OSError('SECONDARY marker failure')
            return write(path, value)
        with patch.object(Path, 'open', fail_publish), patch('video_notes.delivery.write', fail_marker):
            with self.assertRaisesRegex(OSError, 'PRIMARY publish failure'):
                deliver(self.run)
        failure = read(self.work / 'delivery-failure.json')
        self.assertIn('SECONDARY', failure['recording_error'])

    def test_crash_before_claim_leaves_intent_without_publication_right(self):
        # Journal is written first, so a death before the exclusive claim leaves a
        # preparation record that grants nothing and is not silently recoverable.
        original_open = Path.open
        def crash(path, mode='r', *args, **kwargs):
            if str(path).endswith('.delivery.json') and mode == 'x':
                raise OSError('simulated crash before claiming')
            return original_open(path, mode, *args, **kwargs)
        with patch.object(Path, 'open', crash):
            with self.assertRaises(OSError):
                deliver(self.run)
        self.assertTrue((self.work / 'delivery-attempt.json').exists())
        self.assertFalse(self.marker().exists())
        self.assertFalse((self.work / 'delivery-result.json').exists())
        with self.assertRaisesRegex(ValueError, 'No publication claim'):
            deliver(self.run, recover=True)
        self.assertEqual(deliver(self.run)['status'], 'delivered')

    def test_existing_marker_is_not_adopted_or_removed(self):
        # An orphan marker has unknown ownership; refuse and leave it untouched.
        marker = self.marker()
        write(marker, {'run_id': 'other', 'attempt_id': 'foreign', 'status': 'publishing'})
        with self.assertRaisesRegex(ValueError, 'marker exists'):
            deliver(self.run)
        self.assertEqual(read(marker)['attempt_id'], 'foreign')
        self.assertFalse((self.work / 'delivery-attempt.json').exists())

    def test_lost_claim_race_does_not_take_over_marker(self):
        # Marker appears between the pre-check and the exclusive create.
        marker = self.marker()
        write(marker, {'run_id': 'racer', 'attempt_id': 'racer', 'status': 'staging'})
        original_exists, original_open = Path.exists, Path.open
        def hide(path):
            return False if path == marker else original_exists(path)
        def claim(path, mode='r', *args, **kwargs):
            if path == marker and mode == 'x':
                raise FileExistsError('claim taken by another attempt')
            return original_open(path, mode, *args, **kwargs)
        with patch.object(Path, 'exists', hide), patch.object(Path, 'open', claim):
            with self.assertRaisesRegex(ValueError, 'publication claim'):
                deliver(self.run)
        self.assertEqual(read(marker)['attempt_id'], 'racer')
        self.assertFalse((self.work / 'delivery-result.json').exists())
