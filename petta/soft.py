"""Purpose: the Python face of lib_soft, weak unification in Sessa's sense.
install() imports the library into a space; similar() declares symbol
closeness as ordinary (similar a b degree) facts the equations read;
link_store() materializes those facts from an EmbeddingStore's cosine
neighborhoods, the neural-theorem-proving move with the similarities kept
inspectable in the space rather than buried in a vector index; and score()
is a fast Python mirror of (soft-score ...), differentially fuzzed against
the MeTTa one so the two can never quietly drift.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

from typing import Any, Mapping

from .atoms import Atom, Expr, Gnd, Sym, Var, expr

__all__ = ["install", "similar", "link_store", "score"]


def install(m) -> None:
    """lib_measure and lib_soft into this space; soft-match and soft-best
    become available wherever the space's programs run."""
    m.run(
        "!(import! (context-space) (library lib_measure))\n"
        "!(import! (context-space) (library lib_soft))"
    )


def similar(m, a: Any, b: Any, degree: float) -> None:
    """Declare two symbols close to a degree; sym-sim reads both ways."""
    m.add(expr(Sym("similar"), _sym(a), _sym(b), float(degree)))


def _sym(value: Any) -> Sym:
    return value if isinstance(value, Sym) else Sym(str(value))


def link_store(m, store, threshold: float = 0.5, top_k: int = 5) -> int:
    """Materialize (similar ...) facts from an embedding store: for every
    stored key, its top_k cosine neighbors at or above the threshold.
    Answers how many facts landed. The similarities become space atoms any
    rule can read, soft-match's sym-sim first among them."""
    count = 0
    for key in store.keys():
        for neighbor, degree in store.ranked(key, top_k + 1):
            if neighbor == key or degree < threshold:
                continue
            similar(m, key, neighbor, degree)
            count += 1
    return count


def score(
    pattern: Atom,
    atom: Atom,
    similarities: Mapping[tuple[str, str], float] | None = None,
    _bindings: dict[str, Atom] | None = None,
) -> float:
    """(soft-score pattern atom) in Python: a variable binds at one and its
    LATER occurrences stand as what it bound, soft recursion included,
    exactly as the engine's let leaves the variable bound; expressions
    recurse under minimum, symbols consult the similarity map both ways
    (identity is one), grounded values stay crisp. Kept exactly equivalent
    to the MeTTa equations by a differential fuzz."""
    table = similarities or {}
    bindings = _bindings if _bindings is not None else {}
    if isinstance(pattern, Var):
        bound = bindings.get(pattern.name)
        if bound is None:
            bindings[pattern.name] = atom
            return 1.0
        return score(bound, atom, table, bindings)
    if isinstance(pattern, Expr) and isinstance(atom, Expr):
        if len(pattern) != len(atom):
            return 0.0
        degree = 1.0
        for p, a in zip(pattern.children, atom.children):
            degree = min(degree, score(p, a, table, bindings))
            if degree == 0.0:
                return 0.0
        return degree
    if isinstance(pattern, Sym) and isinstance(atom, Sym):
        if pattern.name == atom.name:
            return 1.0
        return max(
            0.0,
            table.get((pattern.name, atom.name), 0.0),
            table.get((atom.name, pattern.name), 0.0),
        )
    return 1.0 if pattern == atom else 0.0
