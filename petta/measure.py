"""Purpose: the Python face of lib_measure, the weighted-superposition
algebra: install() imports the library into a space, ws() spells a weighted
superposition from Python pairs, and pairs() reads one back as (weight,
value) tuples. The algebra itself is pure MeTTa (lib/lib_measure.metta),
annotated-disjunction shaped, so the CLI and Python run the same equations.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

from typing import Any, Iterable

from .atoms import Atom, Expr, Gnd, decode, encode, expr

__all__ = ["install", "ws", "pairs"]


def install(m) -> None:
    """The measure algebra into this space: ws-total, ws-normalize,
    ws-softmax, ws-best, ws-top, ws-sample!, ws-collapse, ws-expect,
    ws-choose, ws-filter, ws-flip."""
    m.run("!(import! (context-space) (library lib_measure))")


def ws(*weighted: tuple[float, Any]) -> Expr:
    """A weighted superposition from (weight, value) pairs.

        measure.ws((0.7, S.high), (0.3, S.low))    # ((0.7 high) (0.3 low))
    """
    return expr(*[expr(float(w), encode(v)) for w, v in weighted])


def pairs(atom: Atom) -> list[tuple[float, Any]]:
    """A weighted superposition read back: [(weight, value), ...], grounded
    values unwrapped."""
    out: list[tuple[float, Any]] = []
    for pair in atom:
        weight, value = pair[0], pair[1]
        out.append(
            (float(decode(weight)), decode(value) if isinstance(value, Gnd) else value)
        )
    return out
