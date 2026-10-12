from dataclasses import dataclass

@dataclass(frozen=True)
class Node:
    kind: str
    text: str = ''
    children: tuple = ()
