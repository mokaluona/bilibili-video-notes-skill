from .model import Node
from .domains import RULES

def parse(text, domain='mathematics', strict=False):
    if domain not in RULES:
        raise ValueError('Unknown formula domain: ' + domain)
    rule = RULES[domain]
    def sequence(i, closing=None):
        nodes = []
        while i < len(text):
            ch = text[i]
            if closing and ch == closing:
                return tuple(nodes), i + 1
            if ch in '([{':
                close = {'(': ')', '[': ']', '{': '}'}[ch]
                inner, end = sequence(i + 1, close)
                nodes.append(Node('group', ch + close, inner)); i = end
            elif ch in '^_':
                if not nodes or (nodes[-1].kind == 'text' and (not nodes[-1].text.isalnum())):
                    raise ValueError('Missing mathematical operand before ' + ch)
                base = nodes.pop(); i += 1
                if i >= len(text):
                    raise ValueError('Missing script argument')
                if text[i] in '{([':
                    argument_close = {'{': '}', '(': ')', '[': ']'}[text[i]]
                    argument, i = sequence(i + 1, argument_close)
                    argtext = ''.join(n.text for n in argument if n.kind == 'text')
                    kind = rule(ch, argtext)
                    if isinstance(kind, tuple):
                        kind, consumed = kind
                        # Braces delimit the argument, so a rule cannot consume only part of it.
                        if consumed != len(argtext):
                            raise ValueError('Braced script must match the complete domain argument')
                else:
                    start = i
                    while i < len(text) and text[i].isascii() and text[i].isalnum():
                        i += 1
                    if start == i:
                        raise ValueError('Invalid script argument; use braces for expressions')
                    # Consult the rule once, with the whole run, so the consumption it declares
                    # and the node kind it returns cannot disagree.
                    kind = rule(ch, text[start:i])
                    if isinstance(kind, tuple):
                        kind, consumed = kind
                        if not isinstance(consumed, int) or not 0 < consumed <= i - start:
                            raise ValueError('Invalid domain rule consumption')
                        i = start + consumed
                    argument = (Node('text', text[start:i]),)
                nodes.append(Node(kind, children=(base,)) if kind else Node('sup' if ch == '^' else 'sub', children=(base, Node('sequence', children=argument))))
            else:
                nodes.append(Node('text', ch)); i += 1
        if closing:
            raise ValueError('Unclosed mathematical group: ' + closing)
        return tuple(nodes), i
    # Plain prose and unmatched prose brackets are untouched when no notation occurs.
    if '^' not in text and '_' not in text:
        return (Node('text', text),)
    try:
        return sequence(0)[0]
    except ValueError as error:
        if strict:
            raise ValueError(f'{error}; input={text!r}') from error
        return (Node('text', text),)
