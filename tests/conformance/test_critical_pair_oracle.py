"""Purpose: pin this repository's critical-pair enumerator over a corpus built
    to separate enumerators. engine/trs.pl's overlaps/2 and confluence_check/3
    are what run, and the corpus mixes hand-written systems chosen for the
    shapes that separate implementations (root overlap, inner overlap, overlap
    under a variable, self overlap, non-left-linear, deep position, growing
    right-hand side) with a seeded random batch.
    WHAT IT COVERS: REWRITING. A critical pair is an overlap between two rules
    of a rewrite relation; MeTTa's evaluation narrows, and this says nothing
    about that.

    This was an AGREEMENT lane once, run against a kernel-checked enumerator in
    Lean and requiring the same family of pairs and the same verdict on each.
    That half is gone (user, 2026-08-31: "there should not be any leatta
    tests"), with the rest of the outside-arbiter machinery. What is lost is
    named rather than glossed: nothing now cross-checks overlaps/2 against an
    independent implementation, so this lane pins that the enumerator RUNS over
    every corpus system and that its report parser is exact, and no longer that
    its answers match another checker's.
Assumes:
  - every corpus system has non-variable left-hand sides and no
    right-hand-side variable its left-hand side does not bind. The second is
    what makes the systems well-formed; the first keeps the bounded search
    finite, since a variable left-hand side rewrites every subterm of
    everything.
Guarantees:
  - the report parser is exact about pair families, verdicts and the certified
    marker, and rejects a malformed report [tested:
    test_the_report_parser_is_exact]
  - the enumerator answers for every system in the corpus [tested:
    test_the_prolog_enumerator_covers_every_corpus_system]
Open Obligations:
  To Do: an independent cross-check of overlaps/2. The Lean lane was the only
    one and it is gone; a second enumerator in this repository would be a
    different thing from an outside arbiter and is the honest replacement.
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import random
import subprocess
from pathlib import Path

import pytest

FUEL = 4

# A term is ("v", n) for a variable or ("a", name, args) for an application.
# Two spellings of the same thing, one per side, are what this module exists to
# compare, so the corpus itself is written in neither.


def variable_term(n: int) -> tuple:
    """Build the corpus representation of a variable."""
    return ("v", n)


def application_term(name: str, *args: tuple) -> tuple:
    """Build the corpus representation of an application."""
    return ("a", name, list(args))


# Keep the corpus visually aligned with the V/A constructors in the Lean
# oracle while the helpers retain descriptive Python names.
V = variable_term
A = application_term


CORPUS: list[tuple[str, list[tuple[tuple, tuple]]]] = [
    # The projection rule: one overlap, with itself, joinable by reflexivity.
    ("proj", [(A("f", V(0)), V(0))]),
    # Two rules whose left-hand sides unify at the root and disagree.
    ("root_clash", [(A("f", A("a")), A("b")), (A("f", V(0)), A("c"))]),
    # The same, but agreeing, so the overlap is harmless.
    ("root_agree", [(A("f", A("a")), A("b")), (A("f", V(0)), A("b"))]),
    # An overlap strictly below the root.
    ("inner", [(A("f", A("g", V(0))), A("a")), (A("g", A("b")), A("c"))]),
    # An overlap two levels down, which separates a position-aware enumerator
    # from one that only looks at the root.
    ("deep", [(A("f", A("g", A("h", V(0)))), A("a")), (A("h", A("b")), A("c"))]),
    # No overlap at all: different roots, nothing nested.
    ("disjoint", [(A("f", V(0)), A("a")), (A("g", V(0)), A("b"))]),
    # A variable position is NOT an overlap. Both sides must skip it.
    ("variable_position", [(A("f", V(0)), A("a")), (A("b"), A("c"))]),
    # Non-left-linear: the repeated variable makes the unifier do work.
    ("non_left_linear", [(A("f", V(0), V(0)), A("a")), (A("f", V(0), V(1)), A("b"))]),
    # A pair that needs more than one step on each branch to rejoin.
    (
        "join_in_two",
        [
            (A("f", A("a")), A("g", A("a"))),
            (A("f", V(0)), A("h", V(0))),
            (A("g", V(0)), A("k")),
            (A("h", V(0)), A("k")),
        ],
    ),
    # A right-hand side that grows, so the bounded search is what stops it.
    ("growing", [(A("f", V(0)), A("f", A("s", V(0))))]),
    # A growing system WITH a genuine disagreement underneath it, which is the
    # case where `unknown` and `counterexample` must not be confused.
    (
        "growing_clash",
        [
            (A("f", A("a")), A("f", A("s", A("a")))),
            (A("f", V(0)), A("b")),
        ],
    ),
    # Idempotence: the classic self-overlap of f(f(x)) with itself at depth one.
    ("idempotent", [(A("f", A("f", V(0))), A("f", V(0)))]),
    # Triska's own test rules: f(f(x)) -> g(x) has one non-trivial overlap.
    ("triska_1", [(A("f", A("f", V(0))), A("g", V(0)))]),
    (
        "triska_2",
        [(A("f", A("f", V(0))), A("f", V(0))), (A("g", A("g", V(0))), A("f", V(0)))],
    ),
    # Three rules, so the ordered pairing is exercised beyond two.
    (
        "three_rules",
        [
            (A("f", A("a")), A("b")),
            (A("f", A("c")), A("d")),
            (A("f", V(0)), A("e")),
        ],
    ),
    # A constant rule, which is an application of arity zero on both sides.
    ("constant", [(A("a"), A("b")), (A("f", A("a")), A("c"))]),
    # Two rules whose left-hand sides are the same term, the sharpest ordering
    # question there is.
    ("identical_lhs", [(A("f", V(0)), A("a")), (A("f", V(0)), A("b"))]),
    # An overlap that unifies two different constructors, so the unifier must
    # fail and no pair is produced.
    ("no_unifier", [(A("f", A("a")), A("b")), (A("f", A("c")), A("d"))]),
    # Nested same symbol: the occurs check has to hold.
    ("nested_same", [(A("f", A("f", V(0))), A("a")), (A("f", A("b")), A("c"))]),
    # Two-argument overlap where only one argument unifies.
    (
        "partial_args",
        [
            (A("f", A("a"), V(0)), A("p", V(0))),
            (A("f", V(0), A("b")), A("q", V(0))),
        ],
    ),
    # A rule set with a cycle, which makes every branch reach the other.
    ("cycle", [(A("f", V(0)), A("g", V(0))), (A("g", V(0)), A("f", V(0)))]),
    # A rewrite that discards its argument, so a reduct loses variables.
    ("discard", [(A("f", V(0)), A("c")), (A("f", A("g", V(0))), A("d"))]),
    # Overlap inside the second argument.
    (
        "second_argument",
        [
            (A("f", V(0), A("g", V(1))), A("a", V(0), V(1))),
            (A("g", A("b")), A("c")),
        ],
    ),
    # Two-level growth with a joinable pair, so `joined` is reached late.
    (
        "late_join",
        [
            (A("f", A("a")), A("g", A("g", A("a")))),
            (A("f", V(0)), A("g", A("g", V(0)))),
        ],
    ),
]

_SIGNATURE = [("a", 0), ("b", 0), ("c", 0), ("f", 1), ("g", 1), ("h", 2)]


def _random_term(rng: random.Random, depth: int, variables: list[int]) -> tuple:
    if depth <= 0 or (variables and rng.random() < 0.35):
        if variables:
            return V(rng.choice(variables))
        return A(rng.choice([n for n, k in _SIGNATURE if k == 0]))
    name, arity = rng.choice(_SIGNATURE)
    return A(name, *[_random_term(rng, depth - 1, variables) for _ in range(arity)])


def _random_system(rng: random.Random) -> list[tuple[tuple, tuple]]:
    """A small system with non-variable left-hand sides and no extra variables.

    Both restrictions are the corpus assumptions in this module's header: a
    variable left-hand side rewrites every subterm of everything and makes the
    bounded search useless, and an extra variable is outside the Lean theorems'
    own RhsVarsInLhs hypothesis.
    """
    rules = []
    for _ in range(rng.randint(1, 3)):
        variables = list(range(rng.randint(0, 2)))
        name, arity = rng.choice([s for s in _SIGNATURE if s[1] > 0])
        left = A(name, *[_random_term(rng, 1, variables) for _ in range(arity)])
        bound = _variables_of(left)
        right = _random_term(rng, 2, sorted(bound))
        rules.append((left, right))
    return rules


def _variables_of(term: tuple) -> set[int]:
    if term[0] == "v":
        return {term[1]}
    return set().union(set(), *(_variables_of(a) for a in term[2]))


def _random_corpus(count: int) -> list[tuple[str, list[tuple[tuple, tuple]]]]:
    rng = random.Random(20260819)
    return [(f"random_{i}", _random_system(rng)) for i in range(count)]


ALL_SYSTEMS = CORPUS + _random_corpus(60)


def _prolog_term(term: tuple, rule: int) -> str:
    if term[0] == "v":
        return f"_R{rule}V{term[1]}"
    if not term[2]:
        return term[1]
    inner = ", ".join(_prolog_term(a, rule) for a in term[2])
    return f"{term[1]}({inner})"


def _prolog_corpus(systems) -> str:
    lines = []
    for name, rules in systems:
        written = ", ".join(
            f"{_prolog_term(left, i)} ==> {_prolog_term(right, i)}"
            for i, (left, right) in enumerate(rules)
        )
        lines.append(f"system({name}, [{written}]).")
    return "\n".join(lines) + "\n"


def _parse(text: str) -> dict[str, tuple[list[str], str]]:
    """One report into {system: (sorted pair lines, certified marker)}."""
    result: dict[str, tuple[list[str], str]] = {}
    name: str | None = None
    pairs: list[str] = []
    for line in text.splitlines():
        if line.startswith("=== "):
            name = line[4:].strip()
            pairs = []
        elif line.startswith("### "):
            if name is None:
                msg = f"verdict before any system: {line!r}"
                raise ValueError(msg)
            result[name] = (sorted(pairs), line[4:].strip())
            name = None
        elif line.strip():
            if name is None:
                msg = f"pair outside a system: {line!r}"
                raise ValueError(msg)
            pairs.append(line)
    if name is not None:
        msg = f"system {name} has no verdict line"
        raise ValueError(msg)
    return result


def _run_prolog(repo_root: Path, corpus: Path, fuel: int) -> str:
    finished = subprocess.run(
        [
            "swipl",
            "-q",
            str(repo_root / "tests" / "conformance" / "critical_pairs_run.pl"),
            "--",
            "--corpus",
            str(corpus),
            "--fuel",
            str(fuel),
        ],
        capture_output=True,
        text=True,
        timeout=280,
        check=True,
        cwd=repo_root / "tests" / "conformance",
    )
    return finished.stdout


@pytest.fixture(scope="module")
def prolog_report(repo_root, tmp_path_factory):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    corpus = tmp_path_factory.mktemp("cp") / "corpus.pl"
    corpus.write_text(_prolog_corpus(ALL_SYSTEMS))
    return _parse(_run_prolog(repo_root, corpus, FUEL))


def test_the_prolog_enumerator_covers_every_corpus_system(prolog_report):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    assert sorted(prolog_report) == sorted(name for name, _ in ALL_SYSTEMS)


def test_the_report_parser_is_exact():
    """Pair order does not matter, verdict and certified marker do.

    This outlived the agreement lane it was written for: the parser reads the
    enumerator's own report, so its exactness is this lane's, not the departed
    oracle's.
    """
    report = "=== s\na\tb\tjoined\n### certified\n"
    assert _parse(report) == {"s": (["a\tb\tjoined"], "certified")}
    assert _parse(report) != _parse("=== s\na\tb\tcounterexample\n### certified\n")
    assert _parse(report) != _parse("=== s\na\tb\tjoined\n### not-certified\n")
    assert _parse("=== s\nb\ta\tjoined\na\tb\tjoined\n### certified\n") == _parse(
        "=== s\na\tb\tjoined\nb\ta\tjoined\n### certified\n"
    )
    with pytest.raises(ValueError):
        _parse("a\tb\tjoined\n")
    with pytest.raises(ValueError):
        _parse("=== s\na\tb\tjoined\n")
