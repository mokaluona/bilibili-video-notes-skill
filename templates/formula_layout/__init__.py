"""parse returns ParseResult; add_text returns notices. No strict exception mode.

Recognized nary operators remain literal until later OMML implementation.
"""
from dataclasses import replace
from .model import Node, Notice, ParseResult
from .parser import parse
from .word import append_nodes
from .domains import register_domain
from .notices import locate

def _renderable(node):
    if node.kind=='nary':
        # Temporary compatibility for Greek Sigma, which the old parser emitted
        # using existing sub/sup nodes. Remove when native nary emission lands.
        if node.text.startswith('Σ') and (node.lower is not None or node.upper is not None):
            base=Node('text','Σ')
            if node.lower is not None:
                base=Node('sub',children=(base,Node('sequence',children=tuple(_renderable(n) for n in node.lower))))
            if node.upper is not None:
                base=Node('sup',children=(base,Node('sequence',children=tuple(_renderable(n) for n in node.upper))))
            body=(Node('group','{}',tuple(_renderable(n) for n in node.children)),) if node.children else ()
            return Node('sequence',children=(base,)+body)
        return Node('text',node.text)
    return replace(node,children=tuple(_renderable(c) for c in node.children))

def add_text(paragraph,text,name='宋体',size=13,bold=False,red=False,domain='mathematics',block_id=None,sub_path=None,text_offset=0):
    result=parse(text,domain)
    append_nodes(paragraph,tuple(_renderable(n) for n in result.nodes),name,size,bold,red)
    return locate(result.notices,block_id,sub_path,text_offset)
