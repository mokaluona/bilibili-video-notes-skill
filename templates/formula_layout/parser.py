"""Notation recognition with one diagnostic channel and code-point offsets."""
from .model import Node, Notice, ParseResult
from .domains import RULES
from .operators import OPERATORS

class _SyntaxError(Exception):
    def __init__(self, code, start, end, message):
        self.code, self.start, self.end, self.message = code, start, end, message

def parse(text, domain='mathematics'):
    if not isinstance(text,str): raise TypeError('Formula input must be a string')
    notices = []
    def fail(code,start,end,message): raise _SyntaxError(code,start,end,message)
    def note(code,start,end,message): notices.append(Notice(code,'warning',None,{},(start,end),message))
    if domain not in RULES:
        return ParseResult((Node('text',text),),(Notice('UNKNOWN_DOMAIN','error',None,{},(0,len(text)),'Unknown formula domain: '+domain),))
    rule=RULES[domain]; closing_map={'(':')','[':']','{':'}'}

    def meaningful(nodes):
        return any(n.text.strip() if n.kind=='text' else meaningful(n.children) for n in nodes)

    def argument(i,start,nary=False):
        if i>=len(text): fail('MISSING_SCRIPT',start,i,'Missing script argument')
        if text[i] in closing_map:
            opening=i
            try: nodes,end=sequence(i+1,closing_map[text[i]],opening)
            except _SyntaxError as exc:
                if exc.code=='UNCLOSED_GROUP': exc.start=start
                raise
            if not meaningful(nodes): fail('EMPTY_SCRIPT',start,end,'Script argument must not be empty')
            return nodes,end,True
        if nary and (text[i]=='∞' or ('\u0370' <= text[i] <= '\u03ff' and text[i].isalpha())):
            return (Node('text',text[i]),),i+1,False
        end=i
        while end<len(text) and text[end].isascii() and text[end].isalnum(): end+=1
        if end==i: fail('INVALID_SCRIPT',start,min(i+1,len(text)),'Use braces for the script expression')
        if nary and end-i>1 and not text[i:end].isdigit(): fail('AMBIGUOUS_SCRIPT',start,end,'Separate the limit using braces')
        return (Node('text',text[i:end]),),end,False

    def nary(i):
        start=i; i+=1; limits={}
        while i<len(text) and text[i] in '_^':
            mark=text[i]
            if mark in limits: fail('DUPLICATE_LIMIT',start,i+1,'Duplicate operator limit')
            nodes,i,_=argument(i+1,start,True); limits[mark]=nodes
        if i<len(text) and text[i]=='{':
            try: body,end=sequence(i+1,'}',i)
            except _SyntaxError as exc:
                if exc.code=='UNCLOSED_GROUP': exc.start=start
                raise
            if not meaningful(body): fail('EMPTY_NARY_BODY',start,end,'Write {1} for a unit integrand')
            note('UNSUPPORTED_NARY',start,end,'Operator recognized; native OMML emission is pending')
            return Node('nary',text[start:end],body,limits.get('_'),limits.get('^')),end
        note('LEGACY_NARY_BODY',start,i,'No explicit braced body; preserve legacy text during transition')
        return Node('nary',text[start:i],(),limits.get('_'),limits.get('^')),i

    def sequence(i,closing=None,opening=None):
        nodes,starts=[],[]
        while i<len(text):
            ch=text[i]
            if closing and ch==closing: return tuple(nodes),i+1
            if ch in ')]}': fail('UNEXPECTED_CLOSING',i,i+1,'Unexpected closing delimiter')
            start=i
            if ch in OPERATORS:
                node,i=nary(i); nodes.append(node); starts.append(start)
            elif ch in closing_map:
                inner,i=sequence(i+1,closing_map[ch],i); nodes.append(Node('group',ch+closing_map[ch],inner)); starts.append(start)
            elif ch in '^_':
                if not nodes or (nodes[-1].kind=='text' and not nodes[-1].text.isalnum()): fail('MISSING_OPERAND',i,i+1,'Missing mathematical operand before '+ch)
                base=nodes.pop(); base_start=starts.pop(); arg,end,braced=argument(i+1,base_start)
                argtext=''.join(n.text for n in arg if n.kind=='text')
                try: kind=rule(ch,argtext)
                except ValueError as exc: fail('INVALID_DOMAIN_RULE',base_start,end,str(exc))
                if isinstance(kind,tuple):
                    kind,consumed=kind
                    if not isinstance(consumed,int) or not 0<consumed<=len(argtext): fail('INVALID_DOMAIN_RULE',base_start,end,'Invalid domain consumption')
                    if braced and consumed!=len(argtext): fail('INVALID_DOMAIN_ARGUMENT',base_start,end,'Braced argument must match the entire domain rule')
                    if not braced:
                        remainder=argtext[consumed:]
                        if remainder and not remainder[0].isupper(): fail('AMBIGUOUS_SCRIPT',base_start,end,'Use braces to disambiguate this script')
                        end=i+1+consumed; arg=(Node('text',argtext[:consumed]),)
                elif not braced and ch=='^' and len(argtext)>1 and not argtext.isdigit(): fail('AMBIGUOUS_SCRIPT',base_start,end,'Use braces for a multi-character exponent')
                nodes.append(Node(kind,children=(base,)) if kind else Node('sup' if ch=='^' else 'sub',children=(base,Node('sequence',children=arg))))
                starts.append(base_start); i=end
            else:
                nodes.append(Node('text',ch)); starts.append(i); i+=1
        if closing: fail('UNCLOSED_GROUP',opening,len(text),'Unclosed mathematical group: '+closing)
        return tuple(nodes),i

    if '^' not in text and '_' not in text and not any(c in OPERATORS for c in text): return ParseResult((Node('text',text),),())
    if '^' not in text and all(i==0 or not text[i-1].isalnum() for i,c in enumerate(text) if c=='_'):
        if not any(c in OPERATORS for c in text): return ParseResult((Node('text',text),),())
    try: nodes=sequence(0)[0]
    except _SyntaxError as exc:
        return ParseResult((Node('text',text),),tuple(notices)+(Notice(exc.code,'error',None,{},(exc.start,exc.end),exc.message),))
    return ParseResult(nodes,tuple(notices))
