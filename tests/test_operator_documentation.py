"""Purpose: pin Phase 9 item P9.6: every term-building operator on atoms is
documented in one table, derived from the class rather than maintained by
hand, and the one operator that is deliberately NOT symbolic (`==`, whose
term is spelled `.eq()`) is called out. Before this, `S.x + S.y` built a
term and no page in website/ showed the form at all [measured 2026-08-19].
Assumes:
    - Python's operator dunders are a closed universe, so enumerating a
      fixed list of them IS deriving the surface: a new overload lands in
      this list or it is not an operator
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

from pathlib import Path

from petta import S, V

DOC = Path(__file__).resolve().parents[3] / "website" / "guide" / "atoms-terms.md"

BINARY_DUNDERS = [
    "__add__", "__sub__", "__mul__", "__truediv__", "__mod__", "__pow__",
    "__matmul__", "__and__", "__or__", "__xor__",
    "__lt__", "__le__", "__gt__", "__ge__",
    "__floordiv__", "__lshift__", "__rshift__",
]


def _head(expr) -> str:
    return str(next(iter(expr)))


def test_every_operator_is_documented_including_the_non_symbolic_one():
    """Build each operator's term live and require its MeTTa symbol in the
    doc's table, so the table cannot drift from the class: an operator
    added tomorrow is in Python's fixed dunder universe, builds a term
    here, and fails this test until the table names it.
    """
    text = DOC.read_text(encoding="utf-8")
    built: dict[str, str] = {}
    for dunder in BINARY_DUNDERS:
        method = getattr(type(S.x), dunder, None)
        if method is None or getattr(object, dunder, None) is method:
            continue
        term = method(S.x, V.y)
        built[dunder] = _head(term)
    # The unary and the two spelled methods.
    built["__invert__"] = _head(~S.x)
    built["eq"] = _head(S.x.eq(V.y))
    built["ne"] = _head(S.x.ne(V.y))

    undocumented = sorted(
        f"{dunder} -> {symbol}"
        for dunder, symbol in built.items()
        if f"`({symbol} " not in text.replace("\\|", "|")
    )
    assert not undocumented, (
        f"term-building operators missing from the table in {DOC.name}: "
        f"{undocumented}"
    )
    # The deliberate exception is stated, not implied: equality's TERM is a
    # method because == itself is structural equality.
    assert ".eq(" in text and "structurally" in text, (
        "the doc no longer says == is structural and the term is .eq()"
    )
    # And == really is the non-operator: it answers a bool, not a term.
    assert (S.x == S.x) is True and (S.x == S.y) is False
