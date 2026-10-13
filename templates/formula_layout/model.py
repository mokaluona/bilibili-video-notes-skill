from dataclasses import dataclass

@dataclass(frozen=True)
class Node:
    kind: str
    text: str = ''
    children: tuple = ()
    lower: tuple | None = None
    upper: tuple | None = None

@dataclass(frozen=True)
class Notice:
    code: str
    severity: str
    block_id: str | None
    sub_path: dict
    text_span: tuple[int, int]
    message: str

@dataclass(frozen=True)
class ParseResult:
    nodes: tuple[Node, ...]
    notices: tuple[Notice, ...]
