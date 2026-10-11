import unittest
from tempfile import TemporaryDirectory
from pathlib import Path
from unittest.mock import patch
from video_notes.storage import write, digest
from video_notes.delivery import plan, deliver

class Delivery(unittest.TestCase):
    def test_plan_copy_and_no_overwrite(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            work, frames, delivery = root / 'work', root / 'frames', root / 'delivery'
            work.mkdir(); frames.mkdir(); delivery.mkdir()
            source = work / 'final.docx'
            source.write_bytes(b'fixture output')
            rules = delivery / '目录规范.md'
            rules.write_text('按内容分类，附件放 attachment。', encoding='utf-8')
            doc = work / 'document.json'
            write(doc, {'assets': {}, 'blocks': []})
            run = {'run_id': 'test', 'workspace': str(work), 'frames': str(frames), 'delivery': str(delivery),
                   'document': str(doc), 'category': 'Testing', 'content_name': 'Fixture', 'output_name': 'test.docx'}
            with patch('video_notes.delivery.current_build', return_value={'output': str(source), 'output_hash': digest(source)}), patch('video_notes.delivery.report', return_value={'decision': 'ready'}):
                proposal = plan(run)
                write(work / 'delivery-policy-review.json', {'rules_hash': proposal['rules_hash'],
                      'plan_hash': digest(work / 'delivery-plan.json'), 'applied_rules': 'Testing category; attachments under attachment'})
                result = deliver(run)
                self.assertEqual(digest(result['files'][0]['target']), digest(source))
                with self.assertRaises(ValueError):
                    deliver(run)

    def test_rule_change_blocks_old_acknowledgment(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root / 'delivery-plan.json', {'old': True})
            run = {'workspace': str(root)}
            with patch('video_notes.delivery.report', return_value={'decision': 'ready'}), patch('video_notes.delivery.plan', return_value={'new': True}):
                with self.assertRaises(ValueError):
                    deliver(run)
