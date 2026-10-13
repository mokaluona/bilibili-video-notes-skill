"""Small, provider-independent formula input contract. No LaTeX parser or renderer."""
import re


def validate_formula(block):
    if not isinstance(block, dict) or block.get('type') != 'formula':
        raise ValueError('Formula requires type=formula')
    fmt = block.get('format', 'plain')
    if fmt not in ('plain', 'latex'):
        raise ValueError('Formula format must be plain or latex')
    text = block.get('text')
    if not isinstance(text, str):
        raise ValueError('Formula text must be a string')
    if fmt == 'latex':
        if not text.strip():
            raise ValueError('LaTeX formula must not be empty')
        if '$' in text or any(x in text for x in (r'\(', r'\)', r'\[', r'\]')):
            raise ValueError('LaTeX field must not contain math delimiters')
        if re.search(r'[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]', text):
            raise ValueError('Chinese explanations belong in prose, not formula fields')
        if re.search(r'\\text\b', text):
            raise ValueError('Mixed text commands are deferred; use prose blocks')
        if re.search(r'[_^]\s*\{\s*\}', text):
            raise ValueError('Empty mathematical script')
    placement = block.get('placement')
    if placement is not None:
        if not isinstance(placement, dict) or set(placement) != {'field', 'index', 'position'}:
            raise ValueError('placement requires field, index, position')
        if placement['field'] not in ('concepts', 'reasoning', 'tables', 'text'):
            raise ValueError('Unknown formula placement field')
        if type(placement['index']) is not int or placement['index'] < 0:
            raise ValueError('Formula placement index must be a nonnegative integer')
        if placement['position'] not in ('before', 'after'):
            raise ValueError('Formula placement position must be before or after')
    return block


def normalize_formulas(values, *, allow_legacy=True):
    """Copy records; legacy strings stay plain, never infer LaTeX or placement."""
    if not isinstance(values, list):
        raise ValueError('formulas must be an array')
    result = []
    for index, value in enumerate(values):
        try:
            if isinstance(value, str) and allow_legacy:
                value = {'type':'formula', 'format':'plain', 'text':value}
            elif not isinstance(value, dict) or value.get('format') != 'latex':
                raise ValueError('New visual formulas require explicit type=formula and format=latex')
            block = dict(validate_formula(value))
            if 'placement' in block:
                block['placement'] = dict(block['placement'])
            result.append(block)
        except ValueError as exc:
            raise ValueError(f'formulas[{index}]: {exc}') from exc
    return result
