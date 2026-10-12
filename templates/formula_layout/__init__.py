"""Shared formula layout: domain rules -> expression tree -> Word OMML.

Default mathematics notation: A^c / A^{c} -> overbar; (AB)^c -> group
overbar; A_i / A_{ij} -> subscript; x^2 / x^{n+1} -> superscript.
Use domain='generic' when c is an exponent rather than a complement.
Ordinary malformed notation is preserved literally. strict=True reports invalid
notation with the source text. Math glyphs use Cambria Math; name applies to prose.
See FORMULA_NOTATION.md for authoring and extension contracts.
This is a scoped notation parser, not a full LaTeX engine.
"""
from .parser import parse
from .word import append_nodes
from .domains import register_domain

def add_text(paragraph, text, name='宋体', size=13, bold=False, red=False, domain='mathematics', strict=False):
    append_nodes(paragraph, parse(text, domain, strict=strict), name, size, bold, red)
