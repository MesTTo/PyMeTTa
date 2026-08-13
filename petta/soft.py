"""Purpose: the Python face of lib_soft, weak unification in Sessa's sense.
install() imports the library into a space; similar() declares symbol
closeness as ordinary (similar a b degree) facts the equations read;
link_store() materializes those facts from an EmbeddingStore's cosine
neighborhoods, the neural-theorem-proving move with the similarities kept
inspectable in the space rather than buried in a vector index; score() is a
fast Python mirror of (soft-score ...), differentially fuzzed against the
MeTTa one so the two can never quietly drift; and prove()/prove_all() are
goal-directed soft REASONING: backward chaining over the space's facts and
Horn-shaped equations with soft unification at every step, degrees
aggregated by minimum, answering Proof objects that carry the bindings, the
overall similarity, and every step. That is the shape of End-to-End
Differentiable Proving (Rocktaschel and Riedel, arXiv 1705.11040) and Braid
(Kalyanpur et al., arXiv 2011.13354), running over the same (similar ...)
facts and embedding links the rest of lib_soft reads.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass
from typing import Any, Iterator, Mapping

from .atoms import Atom, Expr, Gnd, Sym, Var, expr

__all__ = [
    "install",
    "similar",
    "link_store",
    "score",
    "prove",
    "prove_all",
    "Proof",
    "ProofStep",
]


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


# ----------------------------------------------------- goal-directed proving


@dataclass(frozen=True)
class ProofStep:
    """One inference: what the current goal soft-unified with (a stored
    fact, an equation's head, or an evaluated guard), at which degree."""

    kind: str  # "fact" | "rule" | "guard"
    goal: Atom
    against: Atom
    similarity: float


@dataclass(frozen=True)
class Proof:
    """One way the goal holds: the bindings its variables took, the overall
    similarity (the minimum over every step, the fuzzy t-norm), and the
    steps themselves, printable for audit."""

    goal: Atom
    substitutions: Mapping[str, Atom]
    similarity: float
    steps: tuple[ProofStep, ...]

    @property
    def depth(self) -> int:
        return len(self.steps)

    def __str__(self) -> str:
        lines = [
            f"Goal: {self.goal}",
            f"Substitutions: {{{', '.join(f'{k} -> {v}' for k, v in self.substitutions.items())}}}",
            f"Similarity: {self.similarity}",
            "Steps:",
        ]
        for step in self.steps:
            lines.append(
                f"  [{step.kind} {step.similarity}] {step.goal}  ~  {step.against}"
            )
        return "\n".join(lines)


_FRESH = itertools.count(1)


def _soft_unify(
    a: Atom,
    b: Atom,
    table: Mapping[tuple[str, str], float],
    bindings: dict[str, Atom],
) -> float:
    """TWO-WAY soft unification, the prover's own: a variable on either
    side binds (through the shared bindings, rule variables renamed apart),
    expressions recurse under minimum, symbols are close to their declared
    degree, grounded values crisp. score() stays one-way on purpose, the
    pattern-against-data reading; goals against rule heads need both
    directions, Sessa's weak mgu."""
    while isinstance(a, Var) and a.name in bindings:
        a = bindings[a.name]
    while isinstance(b, Var) and b.name in bindings:
        b = bindings[b.name]
    if isinstance(a, Var):
        if not (isinstance(b, Var) and b.name == a.name):
            bindings[a.name] = b
        return 1.0
    if isinstance(b, Var):
        bindings[b.name] = a
        return 1.0
    if isinstance(a, Expr) and isinstance(b, Expr):
        if len(a) != len(b):
            return 0.0
        degree = 1.0
        for x, y in zip(a.children, b.children):
            degree = min(degree, _soft_unify(x, y, table, bindings))
            if degree == 0.0:
                return 0.0
        return degree
    if isinstance(a, Sym) and isinstance(b, Sym):
        if a.name == b.name:
            return 1.0
        return max(
            0.0,
            table.get((a.name, b.name), 0.0),
            table.get((b.name, a.name), 0.0),
        )
    return 1.0 if a == b else 0.0


def _reify(atom: Atom, bindings: Mapping[str, Atom]) -> Atom:
    if isinstance(atom, Var):
        bound = bindings.get(atom.name)
        return atom if bound is None else _reify(bound, bindings)
    if isinstance(atom, Expr):
        return Expr([_reify(c, bindings) for c in atom.children])
    return atom


def _rename(atom: Atom, suffix: str) -> Atom:
    if isinstance(atom, Var):
        return Var(f"{atom.name}{suffix}")
    if isinstance(atom, Expr):
        return Expr([_rename(c, suffix) for c in atom.children])
    return atom


def _conjuncts(body: Atom) -> list[Atom]:
    if isinstance(body, Expr) and isinstance(body.head, Sym) and body.head.name in ("and", ","):
        return list(body.args)
    return [body]


def _knowledge(m) -> tuple[list[Atom], list[tuple[Atom, Atom]], dict, set]:
    """The space read once per call: plain facts, (head, body) rules, the
    (similar a b d) table lib_soft's sym-sim reads, and the rule heads,
    which the guard branch must never re-evaluate through the engine."""
    facts: list[Atom] = []
    rules: list[tuple[Atom, Atom]] = []
    table: dict[tuple[str, str], float] = {}
    rule_heads: set[str] = set()
    for atom in m.atoms():
        if not isinstance(atom, Expr) or not isinstance(atom.head, Sym):
            continue
        name = atom.head.name
        if name == "=" and len(atom) == 3:
            rules.append((atom[1], atom[2]))
            head = atom[1]
            if isinstance(head, Expr) and isinstance(head.head, Sym):
                rule_heads.add(head.head.name)
        elif name == "similar" and len(atom) == 4:
            a, b, degree = atom[1], atom[2], atom[3]
            if isinstance(a, Sym) and isinstance(b, Sym) and isinstance(degree, Gnd):
                table[(a.name, b.name)] = float(degree.value)
        elif name == ":":
            continue
        else:
            facts.append(atom)
    return facts, rules, table, rule_heads


def prove_all(
    m,
    goal: Any,
    threshold: float = 0.5,
    max_depth: int = 10,
    similarities: Mapping[tuple[str, str], float] | None = None,
) -> list[Proof]:
    """Every proof of the goal at or above the threshold, best first.

    Backward chaining: a goal holds if it soft-unifies with a stored fact,
    or with a rule's head whose body conjuncts then hold in turn; a ground
    guard whose head is an engine function evaluates through the engine and
    holds at degree one when it answers true. Degrees aggregate by minimum
    down the whole proof, and every soft unification must clear the
    threshold, Braid's rule. Proofs come back sorted by similarity.
    """
    from .atoms import parse

    goal_atom = goal if isinstance(goal, Atom) else (
        parse(goal) if isinstance(goal, str) else expr(goal)
    )
    facts, rules, table, rule_heads = _knowledge(m)
    if similarities:
        table.update(similarities)
    proofs: list[Proof] = []
    goal_vars = [n for n in _variables_of(goal_atom) if n != "_"]

    for bindings, similarity, steps in _solve(
        m, goal_atom, facts, rules, table, rule_heads, threshold, max_depth, {}
    ):
        substitutions = {
            name: _reify(Var(name), bindings)
            for name in goal_vars
            if not isinstance(_reify(Var(name), bindings), Var)
        }
        proofs.append(Proof(goal_atom, substitutions, similarity, tuple(steps)))
    proofs.sort(key=lambda p: -p.similarity)
    return proofs


def prove(
    m,
    goal: Any,
    threshold: float = 0.5,
    max_depth: int = 10,
    similarities: Mapping[tuple[str, str], float] | None = None,
) -> Proof | None:
    """The best proof of the goal, or None: tensor-theorem-prover's own
    contract, the highest-similarity proof among all found."""
    proofs = prove_all(m, goal, threshold, max_depth, similarities)
    return proofs[0] if proofs else None


def _variables_of(atom: Atom) -> list[str]:
    from .atoms import variables

    return variables(atom)


def _solve(
    m,
    goal: Atom,
    facts: list[Atom],
    rules: list[tuple[Atom, Atom]],
    table: Mapping[tuple[str, str], float],
    rule_heads: set,
    threshold: float,
    depth: int,
    bindings: dict[str, Atom],
) -> Iterator[tuple[dict, float, list[ProofStep]]]:
    if depth <= 0:
        return
    current = _reify(goal, bindings)

    # A conjunction proves conjunct by conjunct, bindings threading, the
    # same reading a rule body gets, so (and g1 g2) is a goal in its own
    # right rather than something only a rule may contain.
    if (
        isinstance(current, Expr)
        and isinstance(current.head, Sym)
        and current.head.name in ("and", ",")
    ):
        yield from _solve_conjuncts(
            m, _conjuncts(current), facts, rules, table, rule_heads,
            threshold, depth, dict(bindings), 1.0, [],
        )
        return

    for fact in facts:
        attempt = dict(bindings)
        degree = _soft_unify(current, fact, table, attempt)
        if degree >= threshold:
            yield attempt, degree, [ProofStep("fact", current, fact, degree)]

    for head, body in rules:
        suffix = f"-r{next(_FRESH)}"
        fresh_head, fresh_body = _rename(head, suffix), _rename(body, suffix)
        attempt = dict(bindings)
        degree = _soft_unify(current, fresh_head, table, attempt)
        if degree < threshold:
            continue
        step = ProofStep("rule", current, head, degree)
        yield from _solve_conjuncts(
            m, _conjuncts(fresh_body), facts, rules, table, rule_heads,
            threshold, depth - 1, attempt, degree, [step],
        )

    if not isinstance(current, Expr) or not isinstance(current.head, Sym):
        return
    if (
        _is_ground(current)
        and current.head.name not in rule_heads
        and (m.is_function(current.head.name) or m.is_function_here(current.head.name))
    ):
        # A guard: the engine's own answer decides, at degree one. Both
        # checks matter: builtins like > are in the global registry but not
        # asserted in the space module, space-local defines the reverse.
        answers = m.eval(current)
        if any(a == True for a in answers):  # noqa: E712  Gnd(True) equality
            yield dict(bindings), 1.0, [ProofStep("guard", current, current, 1.0)]


def _solve_conjuncts(
    m, goals, facts, rules, table, rule_heads, threshold, depth, bindings,
    degree, steps
) -> Iterator[tuple[dict, float, list[ProofStep]]]:
    if not goals:
        yield bindings, degree, steps
        return
    first, rest = goals[0], goals[1:]
    for attempt, sub_degree, sub_steps in _solve(
        m, first, facts, rules, table, rule_heads, threshold, depth, bindings
    ):
        yield from _solve_conjuncts(
            m, rest, facts, rules, table, rule_heads, threshold, depth,
            attempt, min(degree, sub_degree), steps + sub_steps,
        )


def _is_ground(atom: Atom) -> bool:
    from .atoms import is_ground

    return is_ground(atom)
