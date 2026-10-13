"""Pure notice context helpers; no DOCX, filesystem, reports or quality gates."""
from dataclasses import replace
from .parser import parse

def merge_text(runs):
    if isinstance(runs,str):return runs
    if isinstance(runs,dict):return runs['text']
    return ''.join(merge_text(run) for run in runs)

def locate(notices,block_id=None,sub_path=None,text_offset=0):
    return tuple(replace(n,block_id=block_id,sub_path=dict(sub_path or {}),
        text_span=(n.text_span[0]+text_offset,n.text_span[1]+text_offset)) for n in notices)

def diagnose_runs(runs,block_id=None,sub_path=None,domain='mathematics'):
    """Concatenate styled runs without spaces; spans refer to that merged text.

    row/col are rendering coordinates (headers row 0, model rows[i] row i+1).
    item is a zero-based list-item index. These coordinates are supplied by the
    caller; this helper never changes rendering or reparses each run separately.
    """
    return locate(parse(merge_text(runs),domain).notices,block_id,sub_path)
