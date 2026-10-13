import copy
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from video_notes.formula_input import normalize_formulas, validate_formula
from video_notes.domain import validate_document
from video_notes.document import build

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('formula_draft', ROOT / 'scripts/generate_config_draft.py')
draft = importlib.util.module_from_spec(spec)
spec.loader.exec_module(draft)


def formula(text=r'\overline{A}', index=0, position='after'):
    return {'type':'formula', 'format':'latex', 'text':text,
            'placement':{'field':'concepts', 'index':index, 'position':position}}


class FormulaInput(unittest.TestCase):
    def frame(self):
        return {'theme':'Probability', 'score':8, 'text':'', 'complete':True,
                'concepts':['first', 'second'], 'reasoning':'', 'tables':[],
                'formulas':[formula()], 'error':None}

    def test_legacy_strings_remain_plain_without_inferred_placement(self):
        self.assertEqual(normalize_formulas(['A^c']), [{'type':'formula','format':'plain','text':'A^c'}])
        with self.assertRaisesRegex(ValueError, 'explicit'):
            normalize_formulas(['A^c'], allow_legacy=False)

    def test_normalization_is_non_mutating_and_preserves_source_fields(self):
        a = formula(); a['source_refs'] = [{'frame_id':'x'}]
        before = copy.deepcopy(a)
        b = normalize_formulas([a])[0]
        b['placement']['index'] = 1
        self.assertEqual(a, before)
        self.assertEqual(b['source_refs'], a['source_refs'])

    def test_shape_and_known_silent_failure_checks(self):
        for value in ({}, None, 'formula'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                normalize_formulas(value)
        for text in ('', 'A$B', r'\(x\)', '概率=1', r'\text{otherwise}', 'A^{}', 'A_{ }'):
            with self.subTest(text=text), self.assertRaisesRegex(ValueError, r'formulas\[0\]'):
                normalize_formulas([formula(text)])
        for placement in ({}, {'field':'concepts','index':True,'position':'after'},
                          {'field':'unknown','index':0,'position':'after'}):
            with self.subTest(placement=placement), self.assertRaises(ValueError):
                validate_formula({**formula(), 'placement':placement})

    def test_latex_uses_existing_document_schema_and_renderer_is_not_enabled(self):
        doc = draft.build_document({'frame_0001.jpg':self.frame()}, 'test')
        self.assertEqual(validate_document(doc)['schema_version'], 1)
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)/'out.docx'
            with self.assertRaisesRegex(ValueError, 'not enabled'):
                build(doc, output, tmp)
            self.assertFalse(output.exists())

    def test_native_and_raw_api_shapes_have_identical_formula_blocks(self):
        native = {**self.frame(), 'recognition_source':'agent_native','image_sha256':'a'*64}
        api = {'raw':json.dumps(self.frame()), 'recognition_source':'external_api','image_sha256':'a'*64}
        blocks = []
        for frame in (native, api):
            doc = draft.build_document({'frame_0001.jpg':frame}, 'test')
            block = next(b for b in doc['blocks'] if b['type']=='formula')
            self.assertEqual(block['source_refs'][0]['frame_id'], 'frame_0001.jpg')
            self.assertEqual(block['source_refs'][0]['index'], 0)
            blocks.append({k:v for k,v in block.items() if k!='source_refs'})
        self.assertEqual(*blocks)

    def test_position_and_same_anchor_order_are_exact(self):
        f = self.frame()
        f['formulas'] = [formula('a', 0, 'before'), formula('b'), formula('c'), formula('d', 1)]
        doc = draft.build_document({'frame_0001.jpg':f}, 'test')
        self.assertEqual([b.get('text') for b in doc['blocks'] if b['type'] in ('paragraph','formula')],
                         ['a','first','b','c','second','d'])

    def test_native_review_record_hash_is_retained(self):
        f = self.frame(); f['sha256'] = 'b'*64
        doc = draft.build_document({'frame_0001.jpg':f}, 'test')
        block = next(b for b in doc['blocks'] if b['type']=='formula')
        self.assertEqual(block['source_refs'][0]['image_sha256'], 'b'*64)

    def test_missing_or_invalid_anchor_is_not_inferred(self):
        for fs in ([{'type':'formula','format':'latex','text':'x'}], [formula(index=99)], ['A^c']):
            f = self.frame(); f['formulas'] = fs
            with self.subTest(fs=fs), self.assertRaisesRegex(ValueError, 'no position inferred'):
                draft.build_document({'frame_0001.jpg':f}, 'test')

    def test_new_document_preserves_input_frame_order_not_score_order(self):
        a, b = self.frame(), self.frame(); a['theme']='first frame'; b['theme']='second frame'
        a['score']=1; b['score']=10
        doc = draft.build_document({'frame_0009.jpg':a,'frame_0001.jpg':b}, 'test')
        self.assertEqual([x['text'] for x in doc['blocks'] if x['type']=='heading'], ['first frame','second frame'])
        self.assertIn('human review', doc['metadata']['ordering'])

    def test_legacy_sections_unchanged_by_formula_metadata(self):
        f = self.frame()
        groups = draft.cluster_frames({'frame_0001.jpg':f})
        old = draft.build_sections(groups)
        f['formulas']=[]
        self.assertEqual(old, draft.build_sections(draft.cluster_frames({'frame_0001.jpg':f})))

    def test_document_cli_and_legacy_cli_are_distinct(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); vision=root/'vision.json'; output=root/'document.json'
            vision.write_text(json.dumps({'frame_0001.jpg':self.frame()}), encoding='utf-8')
            cmd=[sys.executable,str(ROOT/'scripts/generate_config_draft.py'),'--vision',str(vision),
                 '--title','test','--source','synthetic','--frames-dir',tmp,'--output',str(output)]
            env={**os.environ, 'PYTHONIOENCODING':'utf-8'}
            result=subprocess.run(cmd+['--output-format','document'],capture_output=True,text=True,encoding='utf-8',env=env)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(json.loads(output.read_text(encoding='utf-8'))['blocks'][2]['format'],'latex')
            result=subprocess.run(cmd,capture_output=True,text=True,encoding='utf-8',env=env)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertIn('SECTIONS',json.loads(output.read_text(encoding='utf-8')))
            self.assertIn('WARNING',result.stdout)

    def test_api_extract_prompt_and_validation_without_network(self):
        # Do not load local credentials during this test.
        with patch.dict(sys.modules, {'dotenv':None}):
            spec=importlib.util.spec_from_file_location('formula_score',ROOT/'scripts/score_frames_concurrent.py')
            score=importlib.util.module_from_spec(spec); spec.loader.exec_module(score)
        self.assertIn('Shared visual formula output contract',score.EXTRACT_PROMPT)
        with tempfile.TemporaryDirectory() as tmp:
            image=Path(tmp)/'frame.jpg'; image.write_bytes(b'synthetic')
            for fs, success in (([formula()],True),(['A^c'],False)):
                response=type('Response',(),{'raise_for_status':lambda s:None,
                    'json':lambda s:{'choices':[{'message':{'content':json.dumps({**self.frame(),'formulas':fs})}}]}})()
                with patch.object(score.requests,'post',return_value=response) as post:
                    _, result=score.process_one_frame(image,'test','https://example.invalid','test',1,1,score.EXTRACT_PROMPT)
                self.assertEqual(result['error'] is None,success)
                self.assertNotIn('response_format',post.call_args.kwargs['json'])
                if success:
                    self.assertEqual(result['recognition_source'],'external_api')
                    self.assertEqual(len(result['image_sha256']),64)


if __name__=='__main__':
    unittest.main()
