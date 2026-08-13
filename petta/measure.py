"""Purpose: the Python face of lib_measure, the weighted-superposition
algebra: install() imports the library into a space, ws() spells a weighted
superposition from Python pairs, pairs() reads one back as (weight, value)
tuples, and weighted_relation() registers any weights-producing callable as
a nondeterministic MeTTa relation answering (weight class) pairs, the shape
every ws- operation composes over. The algebra itself is pure MeTTa
(lib/lib_measure.metta), annotated-disjunction shaped, so the CLI and
Python run the same equations.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

from typing import Any, Callable, Iterable

from .atoms import Atom, Expr, Gnd, Var, decode, encode, expr

__all__ = ["install", "ws", "pairs", "weighted_relation"]


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


def weighted_relation(
    m,
    name: str,
    weights: Callable[[Any], Iterable[Any]],
    classes: Iterable[Any],
) -> str:
    """Register a weights-producing callable as a weighted MeTTa relation.

        measure.weighted_relation(m, "mood", score_moods, [S.calm, S.tense])
        m.run("!(ws-best (collapse (mood today)))")     # argmax class
        m.run("!(mood today calm)")                     # (w calm)

    classes are the relation's answer terms, in order; weights(value) must
    answer one weight per class, each already in its final form (a float,
    or any atom the caller wants carried, a val() tensor included). The
    relation is dual-mode: (name $x) superposes every (weight class) pair,
    and (name $x class) scores the one class, both lib_measure's own shape,
    so ws-best is argmax, ws-sample! the stochastic reading, and rules
    compose over the answers as over any weighted alternatives. This is the
    general mechanism behind pettorch.neural_predicate, DeepProbLog's
    nn-predicate reading, with the network generalised to any callable.
    """
    class_atoms = [encode(c) for c in classes]

    def relation(value, chosen=None):
        answered = list(weights(value))
        if len(answered) != len(class_atoms):
            raise ValueError(
                f"{name}: weights answered {len(answered)} values "
                f"for {len(class_atoms)} classes"
            )
        if chosen is not None and not isinstance(chosen, Var):
            chosen_atom = encode(chosen) if not isinstance(chosen, Atom) else chosen
            for weight, class_atom in zip(answered, class_atoms):
                if class_atom == chosen_atom:
                    yield expr(weight, class_atom)
            return
        for weight, class_atom in zip(answered, class_atoms):
            yield expr(weight, class_atom)

    m.op(relation, name=name, typed=False, pass_atoms=True)
    return name
