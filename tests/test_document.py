import tempfile
import unittest
from pathlib import Path
from docx import Document
from PIL import Image
from video_notes.document import build, StyleProfile, sample_blocks
from video_notes.legacy import convert

class Writer(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        Image.new('RGB', (400, 200), 'white').save(self.root / 'image.jpg')
        self.doc = {"schema_version": 1, "metadata": {"title": "模块化生成测试", "source": "合成测试素材"},
                    "assets": {"a": "image.jpg"}, "blocks": [
                        {"id": "p", "type": "paragraph", "text": "正文内容用于验证显式字号配置。"},
                        {"id": "t", "type": "table", "headers": ["条件", "结果"], "rows": [["独立", "乘法"]]},
                        {"id": "i", "type": "image", "asset_id": "a", "caption": "图片样本"},
                        {"id": "i2", "type": "image", "asset_id": "a", "caption": "第二图片样本"},
                        {"id": "f", "type": "formula", "text": "P(AB)=P(A)P(B)"}]}

    def test_explicit_sizes_and_no_reviews(self):
        out = self.root / 'test.docx'
        build(self.doc, out, self.root, StyleProfile(body_size=11.5, table_size=9.5))
        doc = Document(out)
        p = next(p for p in doc.paragraphs if p.text.startswith('正文'))
        self.assertEqual(p.runs[0].font.size.pt, 11.5)
        self.assertEqual(doc.tables[0].cell(1, 0).paragraphs[0].runs[0].font.size.pt, 9.5)
        self.assertFalse((self.root / 'reviews').exists())
        self.assertNotIn('本节要点总结', '\n'.join(p.text for p in doc.paragraphs))

    def test_samples_cover_all_types_and_two_images(self):
        selected = sample_blocks(self.doc['blocks'])
        self.assertEqual({b['type'] for b in selected}, {'paragraph', 'table', 'image', 'formula'})
        self.assertEqual(sum(b['type'] == 'image' for b in selected), 2)

    def test_missing_images_fail_before_output(self):
        self.doc['assets']['a'] = 'missing.jpg'
        out = self.root / 'test.docx'
        with self.assertRaises(ValueError):
            build(self.doc, out, self.root, sample=True)
        self.assertFalse(out.exists())

    def test_legacy_summary_is_explicit(self):
        content = convert({'TITLE': '标题', 'SECTIONS': [['body', '正文']], 'SUMMARY': []})
        self.assertEqual(len(content['blocks']), 1)
        with self.assertRaises(ValueError):
            convert({'TITLE': '标题', 'SECTIONS': [['unknown', '内容']]})

    def test_invalid_table_and_formula_rejected(self):
        self.doc['blocks'][1]['rows'] = [['short']]
        with self.assertRaises(ValueError):
            build(self.doc, self.root / 'bad.docx', self.root)

if __name__ == '__main__':
    unittest.main()
