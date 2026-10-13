"""Small, provider-independent formula input contract. No LaTeX parser or renderer."""
import re


def check_groups(text):
    """Check only unescaped brace balance, not LaTeX command semantics."""
    openings = []
    index = 0
    while index < len(text):
        char = text[index]
        if char == '\\':
            if index + 1 == len(text):
                raise ValueError(f'Dangling LaTeX escape at offset {index}')
            index += 2
            continue
        if char == '%':
            raise ValueError('LaTeX comments are not supported in formula fields; escape a literal percent')
        if char in '_^' and not text[index + 1:].strip():
            raise ValueError('Missing mathematical script argument')
        if char == '{':
            openings.append(index)
        elif char == '}':
            if not openings:
                raise ValueError(f'Unmatched LaTeX closing group at offset {index}')
            openings.pop()
        index += 1
    if openings:
        raise ValueError(f'Unclosed LaTeX group at offset {openings[-1]}')


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
        check_groups(text)
        if re.search(r'[_^]\s*\{\s*\}', text):
            raise ValueError('Empty mathematical script')
    placement = block.get('placement')
    if 'placement' in block:
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
            if isinstance(value, str):
                if not allow_legacy:
                    raise ValueError('Legacy string formula requires an explicit type=formula, format=latex object; no automatic conversion')
                value = {'type':'formula', 'format':'plain', 'text':value}
            elif not isinstance(value, dict) or value.get('format') != 'latex':
                raise ValueError('New visual formulas require explicit type=formula and format=latex')
            validated = validate_formula(value)
            block = {key: validated[key] for key in ('type', 'format', 'text') if key in validated}
            if 'placement' in validated:
                block['placement'] = dict(validated['placement'])
            if 'source_refs' in validated:
                refs = validated['source_refs']
                if not isinstance(refs, list) or any(not isinstance(ref, dict) for ref in refs):
                    raise ValueError('source_refs must be an array of objects')
                source_fields = ('frame_id', 'field', 'index', 'recognition_source', 'image_sha256', 'agent')
                block['source_refs'] = [{key: ref[key] for key in source_fields if key in ref} for ref in refs]
            result.append(block)
        except ValueError as exc:
            raise ValueError(f'formulas[{index}]: {exc}') from exc
    return result
