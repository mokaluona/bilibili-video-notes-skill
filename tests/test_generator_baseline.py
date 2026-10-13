"""Step 1: observed baselines and fixture integrity, not future feature tests.

Known defects are captured explicitly. Replace their snapshots with diagnostic
assertions in step 2; exercise target OMML fixtures against the writer in step 4.
"""
import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn
from docx.enum.text import WD_ALIGN_PARAGRAPH
from PIL import Image
from video_notes.legacy import convert
from video_notes.document import build, StyleProfile

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).parent / 'fixtures' / 'generator_baseline'

def fixture(name):
    return json.loads((FIXTURES / name).read_text(encoding='utf-8'))

def load(name, path, package=False):
    spec = importlib.util.spec_from_file_location(name, path,
        submodule_search_locations=[str(path.parent)] if package else None)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

FORMULA = load('baseline_formula_layout', ROOT / 'templates/formula_layout/__init__.py', True)
TEMPLATE = load('baseline_template', ROOT / 'templates/gen_docx_dynamic.py')

class GeneratorBaselineTests(unittest.TestCase):
    def test_legacy_config_matches_independent_expected_blocks_and_assets(self):
        self.assertEqual(convert(fixture('legacy_config.json')), fixture('expected_document_v1.json'))

    def test_legacy_position_ids_are_only_build_local(self):
        cfg = fixture('legacy_config.json')
        original = convert(cfg)
        cfg['SECTIONS'].insert(0, ['body', '新增内容'])
        inserted = convert(cfg)
        self.assertEqual(original['blocks'][0]['text'], inserted['blocks'][1]['text'])
        self.assertNotEqual(original['blocks'][0]['id'], inserted['blocks'][1]['id'])

    def test_current_parser_snapshot_explicitly_records_existing_gaps(self):
        observed = {c['id']: c for c in fixture('current_parser_snapshot.json')['cases']}
        cases = fixture('formula_cases.json')['cases']
        self.assertEqual(set(observed), {c['id'] for c in cases})
        for case in cases:
            with self.subTest(case=case['id']):
                domain = case.get('domain', 'mathematics')
                nodes = [asdict(n) for n in FORMULA.parse(case['input'], domain)]
                # JSON roundtrip normalizes immutable tuple children.
                self.assertEqual(json.loads(json.dumps(nodes)), observed[case['id']]['nodes'])
                try:
                    FORMULA.parse(case['input'], domain, strict=True)
                    error = None
                except ValueError as exc:
                    error = str(exc)
                self.assertEqual(error, observed[case['id']]['strict_error'])

    def test_snapshot_separates_missing_support_from_silently_wrong_output(self):
        """Four cases already render wrong output without raising; they are not just unimplemented."""
        cases = {c['id']: c for c in fixture('current_parser_snapshot.json')['cases']}
        spec = {c['id']: c for c in fixture('formula_cases.json')['cases']}
        silently = {i for i, c in cases.items() if c['current_state'] == 'silently_wrong'}
        self.assertEqual(silently, {'empty_sup', 'empty_sub', 'ambiguous_cost', 'ambiguous_power'})
        for i in silently:
            self.assertIsNone(cases[i]['strict_error'], 'silently wrong output is not currently rejected')
        detected = {i for i, c in cases.items() if c['current_state'] == 'detected'}
        for i in detected:
            self.assertIsNotNone(cases[i]['strict_error'])
            self.assertEqual(spec[i]['classification'], 'diagnostic')
        # Every case step 2 has to block is either already rejected or explicitly recorded as silently wrong.
        blocking = {i for i, c in spec.items() if c.get('step2_severity') == 'error'}
        self.assertEqual(blocking, detected | silently)
        self.assertEqual({c['current_state'] for c in cases.values()},
                         {'correct', 'detected', 'silently_wrong', 'unsupported'})

    def test_fixture_exercises_every_legacy_section_kind(self):
        kinds = {item[0] for item in fixture('legacy_config.json')['SECTIONS']}
        self.assertEqual(kinds, {'h1', 'h2', 'h3', 'body', 'bold', 'red',
                                 'bullet', 'why', 'tips', 'formula', 'table', 'img'})

    def test_target_nary_fixtures_have_explicit_body_and_correct_limit_layout(self):
        operators = {'Σ': ('∑', 'undOvr'), '∑': ('∑', 'undOvr'),
                     '∫': ('∫', 'subSup'), '∬': ('∬', 'subSup')}
        cases = [c for c in fixture('formula_cases.json')['cases'] if c['classification'] == 'nary']
        self.assertEqual({c['operator'] for c in cases}, set(operators))
        for c in cases:
            with self.subTest(case=c['id']):
                self.assertEqual((c['chr'], c['limLoc']), operators[c['operator']])
                reconstructed = c['operator']
                if c['lower'] is not None: reconstructed += '_{' + c['lower'] + '}'
                if c['upper'] is not None: reconstructed += '^{' + c['upper'] + '}'
                reconstructed += '{' + c['body'] + '}' + c['trailing']
                self.assertEqual(reconstructed, c['input'])
                self.assertTrue(c['body'])
                self.assertEqual(c['expected_omml']['subHide'], c['lower'] is None)
                self.assertEqual(c['expected_omml']['supHide'], c['upper'] is None)
                self.assertTrue(c['expected_omml']['body_bound_to_m_e'])
                self.assertEqual(c['domain'], 'generic')

    def test_unit_integrand_is_explicit_and_legacy_transition_is_disclosed(self):
        cases = {c['id']: c for c in fixture('formula_cases.json')['cases']}
        self.assertEqual(cases['integral_unit']['body'], '1')
        for name in ('legacy_unit', 'legacy_integral'):
            self.assertEqual(cases[name]['step2_severity'], 'warning')
            self.assertEqual(cases[name]['target_severity'], 'error')
        for c in cases.values():
            if c['classification'] == 'diagnostic':
                self.assertEqual(c['step2_severity'], 'error')

    def test_notice_coordinates_cover_table_header_cell_and_list_item(self):
        f = fixture('notice_locations.json')
        cases = f['cases']
        self.assertEqual([c['sub_path'] for c in cases],
                         [{'row': 1, 'col': 1}, {'row': 0, 'col': 0}, {'item': 1}])
        for c in cases:
            start, end = c['text_span']
            self.assertTrue(0 <= start < end <= len(c['text']))
            self.assertTrue(c['text'][start:end].startswith('A'))
        # Row 0 is the header row, not rows[0]; the illustrative ids must resolve onto the baseline.
        self.assertIn('headers are row 0', f['conventions']['row_semantics'])
        self.assertIn('runs merged', f['conventions']['text_semantics'])
        self.assertTrue(f['block_ids_are_illustrative'])
        by_id = {b['id']: b for b in fixture('expected_document_v1.json')['blocks']}
        for illustrative, real in f['real_block_ids'].items():
            self.assertEqual(by_id[real]['type'], illustrative.split('-')[0])

    def test_provenance_contains_hashes_and_injector_limitations_without_local_paths(self):
        p = fixture('provenance.json')
        self.assertFalse(p['production_code_changed'])
        self.assertEqual(p['source_ref'], 'third-lecture')
        self.assertFalse(p['source_identifier_recorded'])
        self.assertEqual(len(p['legacy_real_sections']), 4)
        self.assertTrue(all(len(h) == 64 for h in p['inputs'].values()))
        self.assertIn('m:e contains a zero-width placeholder, not the integrand', p['temporary_injector_limits'])
        # These fixtures ship in a public fork: no local paths and no source video identifier.
        for path in FIXTURES.glob('*.json'):
            text = path.read_text(encoding='utf-8')
            self.assertNotRegex(text, r'[A-Za-z]:[\\/]')
            self.assertNotRegex(text, r'BV[0-9A-Za-z]{10}')

    def test_template_style_baseline_includes_real_formula_properties(self):
        s = fixture('style_contract.json')['template']
        d = Document()
        TEMPLATE.setup_section(d)
        p = TEMPLATE.add_body(d, '固定正文')
        self.assertAlmostEqual(d.sections[0].left_margin.cm, s['margin_cm'], places=2)
        self.assertEqual(p.runs[0].font.size.pt, s['body_size'])
        self.assertEqual(p.paragraph_format.line_spacing, s['line_spacing'])
        formula = TEMPLATE.add_formula(d, 'x^{n+1}')
        for prop in formula._p.iter(qn('w:rPr')):
            self.assertEqual(prop.find(qn('w:rFonts')).get(qn('w:ascii')), s['formula_font'])
            self.assertEqual(prop.find(qn('w:color')).get(qn('w:val')), s['formula_color'])
            self.assertEqual(prop.find(qn('w:sz')).get(qn('w:val')), str(s['formula_size'] * 2))
        self.assertTrue(list(formula._p.iter(qn('m:sSup'))))
        table = TEMPLATE.add_table(d, ['条件'], [['结果']])
        self.assertIsNone(table.alignment)
        self.assertEqual(table.cell(1, 0).paragraphs[0].alignment, WD_ALIGN_PARAGRAPH.CENTER)
        self.assertEqual(bool(list(table._tbl.iter(qn('w:tblHeader')))), s['repeat_header'])

    def test_both_current_builders_accept_fixture_without_external_assets(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cfg = fixture('legacy_config.json')
            for name in fixture('expected_document_v1.json')['assets'].values():
                Image.new('RGB', (160, 90), 'white').save(root / name)
            cfg.update(OUTPUT_PATH=str(root / 'legacy.docx'), FRAMES_DIR=str(root))
            with contextlib.redirect_stdout(io.StringIO()): TEMPLATE.build_docx(cfg)
            old = Document(root / 'legacy.docx')
            expected = fixture('expected_document_v1.json')
            result = build(expected, root / 'core.docx', root)
            core = Document(root / 'core.docx')
            self.assertEqual(result['block_ids'], [b['id'] for b in expected['blocks']])
            self.assertEqual(len(old.inline_shapes), 2)
            self.assertEqual(len(core.inline_shapes), 2)
            self.assertEqual(len(old.tables), 1)
            self.assertEqual(len(core.tables), 1)
            # Captions carry the old config's own "图 6 " text, so both builders add a second number.
            captions = [b['caption'] for b in expected['blocks'] if b['type'] == 'image']
            self.assertEqual([p.text for p in old.paragraphs if p.text.startswith('图：')],
                             ['图：' + c for c in captions])
            self.assertEqual([p.text for p in core.paragraphs if p.text.startswith('图 ')],
                             [f'图 {i} {c}' for i, c in enumerate(captions, 1)])
            self.assertTrue(list(core.tables[0]._tbl.iter(qn('w:tblHeader'))))

    def test_core_current_style_is_recorded_separately_not_claimed_compatible(self):
        contracts = fixture('style_contract.json')
        s = contracts['core_current']
        profile = StyleProfile()
        for key in ('body_size', 'formula_size', 'margin_cm', 'line_spacing'):
            self.assertEqual(getattr(profile, key), s[key])
        self.assertNotEqual(s['body_size'], contracts['template']['body_size'])
        # Core renders formulas in the body font: record the gap, then show it is real.
        self.assertEqual(s['formula_font'], profile.body_font)
        self.assertNotEqual(s['formula_font'], contracts['template']['formula_font'])
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            document = fixture('expected_document_v1.json')
            for name in document['assets'].values():
                Image.new('RGB', (160, 90), 'white').save(root / name)
            build(document, root / 'core.docx', root)
            core = Document(root / 'core.docx')
            formula = next(p for p in core.paragraphs if p.text.startswith('P(X<1,Y<2)'))
            fonts = {prop.find(qn('w:rFonts')).get(qn('w:ascii')) for prop in formula._p.iter(qn('w:rPr'))}
            self.assertEqual(fonts, {s['formula_font']})

if __name__ == '__main__':
    unittest.main()
