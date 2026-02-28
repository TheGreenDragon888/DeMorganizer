
"""Boolean algebra utilities for applying DeMorgan's theorem.

Syntax supported by this module:
- Variables: start with uppercase, then lowercase/digits/_ (e.g. A, Foo, X2, Var_1)
- NOT: apostrophe after an expression, e.g. A', (A+B)'
- AND: adjacency, e.g. AB means A*B
- OR: plus sign, e.g. A+B
- Parentheses for grouping
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List


class ParseError(ValueError):
    """Raised when an expression cannot be parsed."""


@dataclass(frozen=True)
class Node:
    kind: str
    children: tuple["Node", ...] = ()
    name: str = ""


class Parser:
    def __init__(self, text: str) -> None:
        self.text = text.replace(" ", "")
        self.i = 0

    def parse(self) -> Node:
        if not self.text:
            raise ParseError("Expression is empty")
        node = self._parse_expr()
        if self.i != len(self.text):
            raise ParseError(f"Unexpected token at index {self.i}: {self.text[self.i]!r}")
        return node

    def _peek(self) -> str:
        if self.i >= len(self.text):
            return ""
        return self.text[self.i]

    def _consume(self, ch: str) -> None:
        if self._peek() != ch:
            raise ParseError(f"Expected {ch!r} at index {self.i}")
        self.i += 1

    def _parse_expr(self) -> Node:
        # OR level: term (+ term)*
        terms = [self._parse_term()]
        while self._peek() == "+":
            self.i += 1
            terms.append(self._parse_term())
        if len(terms) == 1:
            return terms[0]
        return Node("or", tuple(terms))

    def _parse_term(self) -> Node:
        # AND by adjacency: factor factor ...
        factors: List[Node] = []
        while True:
            ch = self._peek()
            if not ch or ch in "+)":
                break
            factors.append(self._parse_factor())
        if not factors:
            raise ParseError(f"Expected term at index {self.i}")
        if len(factors) == 1:
            return factors[0]
        return Node("and", tuple(factors))

    def _parse_factor(self) -> Node:
        base = self._parse_primary()
        while self._peek() == "'":
            self.i += 1
            base = Node("not", (base,))
        return base

    def _parse_primary(self) -> Node:
        ch = self._peek()
        if ch == "(":
            self.i += 1
            node = self._parse_expr()
            self._consume(")")
            return node
        return self._parse_var()

    def _parse_var(self) -> Node:
        ch = self._peek()
        if not ch or not ch.isalpha() or not ch.isupper():
            raise ParseError(
                f"Invalid variable start at index {self.i}. "
                "Variables must start with a capital letter."
            )
        start = self.i
        self.i += 1
        while True:
            nxt = self._peek()
            if not nxt:
                break
            if nxt.islower() or nxt.isdigit() or nxt == "_":
                self.i += 1
                continue
            break
        return Node("var", name=self.text[start:self.i])


def _flatten(kind: str, children: List[Node]) -> List[Node]:
    out: List[Node] = []
    for child in children:
        if child.kind == kind:
            out.extend(child.children)
        else:
            out.append(child)
    return out


def simplify(node: Node) -> Node:
    """Flatten nested AND/OR and simplify double-negation."""
    if node.kind == "var":
        return node
    if node.kind == "not":
        inner = simplify(node.children[0])
        if inner.kind == "not":
            return simplify(inner.children[0])
        return Node("not", (inner,))
    kids = [simplify(c) for c in node.children]
    kids = _flatten(node.kind, kids)
    if len(kids) == 1:
        return kids[0]
    return Node(node.kind, tuple(kids))


def apply_demorgan(node: Node) -> Node:
    """Push NOT inward using DeMorgan's theorem recursively."""
    if node.kind == "var":
        return node
    if node.kind == "not":
        inner = apply_demorgan(node.children[0])
        if inner.kind == "not":
            return apply_demorgan(inner.children[0])
        if inner.kind == "and":
            return apply_demorgan(Node("or", tuple(Node("not", (c,)) for c in inner.children)))
        if inner.kind == "or":
            return apply_demorgan(Node("and", tuple(Node("not", (c,)) for c in inner.children)))
        return Node("not", (inner,))
    return Node(node.kind, tuple(apply_demorgan(c) for c in node.children))


def _precedence(node: Node) -> int:
    if node.kind == "or":
        return 1
    if node.kind == "and":
        return 2
    if node.kind == "not":
        return 3
    return 4


def to_string(node: Node, parent_prec: int = 0) -> str:
    if node.kind == "var":
        return node.name
    if node.kind == "not":
        child = node.children[0]
        s = to_string(child, _precedence(node))
        if child.kind in ("and", "or"):
            if not (s.startswith("(") and s.endswith(")")):
                s = f"({s})"
        return s + "'"
    op = "+" if node.kind == "or" else ""
    current_prec = _precedence(node)
    rendered = op.join(to_string(c, current_prec) for c in node.children)
    if current_prec < parent_prec:
        return f"({rendered})"
    return rendered


def process_string(expression: str) -> str:
    """Parse expression and return a DeMorgan-equivalent expression.

    We use E = (E')' and push the inner NOT inward via DeMorgan so the
    returned expression stays equivalent to the original input.
    """
    tree = Parser(expression).parse()
    transformed = apply_demorgan(Node("not", (tree,)))
    transformed = Node("not", (transformed,))
    simplified = simplify(transformed)
    return to_string(simplified)
