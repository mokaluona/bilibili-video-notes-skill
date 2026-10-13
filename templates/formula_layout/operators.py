"""Domain-independent lexical operators; native nary emission remains pending."""
from dataclasses import dataclass

@dataclass(frozen=True)
class Operator:
    chr: str
    limLoc: str

OPERATORS = {'Σ': Operator('∑', 'undOvr'), '∑': Operator('∑', 'undOvr'),
             '∫': Operator('∫', 'subSup'), '∬': Operator('∬', 'subSup')}
NOTICE_CODES = frozenset({'UNSUPPORTED_NARY', 'LEGACY_NARY_BODY', 'UNCLOSED_GROUP',
    'UNEXPECTED_CLOSING', 'EMPTY_SCRIPT', 'MISSING_OPERAND', 'MISSING_SCRIPT',
    'INVALID_SCRIPT', 'AMBIGUOUS_SCRIPT', 'INVALID_DOMAIN_ARGUMENT',
    'EMPTY_NARY_BODY', 'DUPLICATE_LIMIT', 'UNKNOWN_DOMAIN', 'INVALID_DOMAIN_RULE',
    'UNRENDERED_NOTATION'})
