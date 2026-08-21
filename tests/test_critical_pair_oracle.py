"""Purpose: this repository's critical-pair enumerator is checked against a
    kernel-checked one. engine/trs.pl's overlaps/2 and confluence_check/3 mirror
    MeTTaILProofs/CPExecutable.lean's criticalPairs, oneSteps, boundedJoin? and
    checkConfluence, definition for definition, and this runs both over one
    corpus and requires the same family of pairs and the same verdict on each.
    Agreement is the criterion rather than "it runs", and a disagreement is
    diagnosable because the Lean side names the pair.
    WHAT IT COVERS: REWRITING. A critical pair is an overlap between two rules
    of a rewrite relation; MeTTa's evaluation narrows, and neither enumerator
    says anything about that.
Assumes:
  - the oracle lives at a fixed local path outside this repository, the same
    assumption tests/conformance/leatta.py documents; CI never has it, so the
    agreement tests skip rather than fail where it is absent.
  - every corpus system has non-variable left-hand sides and no
    right-hand-side variable its left-hand side does not bind. Both sides need
    the second (it is the Lean theorems' own RhsVarsInLhs); the first keeps the
    bounded search finite, since a variable left-hand side rewrites every
    subterm of everything.
Guarantees:
  - the two sides are compared as SORTED line multisets per system, because the
    two enumerators nest their loops differently and the family is what is
    being compared, not the visiting order [measured 2026-08-19: the orders
    genuinely differ, the families do not].
  - the comparator is exercised where the oracle is absent, by the
    planted-divergence test, which needs no Lean.
  - the corpus mixes hand-written systems chosen for the shapes that separate
    the two enumerators (root overlap, inner overlap, overlap under a variable,
    self overlap, non-left-linear, deep position, growing right-hand side) with
    a seeded random batch, so the agreement is not an agreement about the cases
    one author thought of.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import os
import random
import subprocess
from pathlib import Path

import pytest

_ORACLE_ROOT = Path(os.environ.get("LEATTA_PATH", "/home/user/Dev/LeaTTa"))
_ORACLE_PROOF = _ORACLE_ROOT / "MeTTaILProofs" / "CPExecutable.lean"

needs_oracle = pytest.mark.skipif(
    not _ORACLE_PROOF.exists(),
    reason="the LeaTTa critical-pair checker is a fixed local checkout outside "
    "this repository; agreement is enforced only where it exists, as with "
    "tests/conformance/leatta.py",
)

FUEL = 4

# A term is ("v", n) for a variable or ("a", name, args) for an application.
# Two spellings of the same thing, one per side, are what this module exists to
# compare, so the corpus itself is written in neither.


def V(n: int) -> tuple:  # noqa: D103, N802  -- pytest discovers or injects this callable; its descriptive name states the contract; the symbolic test spelling mirrors the notation whose translation is under test
    return ("v", n)


def A(name: str, *args: tuple) -> tuple:  # noqa: D103, N802  -- pytest discovers or injects this callable; its descriptive name states the contract; the symbolic test spelling mirrors the notation whose translation is under test
    return ("a", name, list(args))


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


def _lean_term(term: tuple) -> str:
    if term[0] == "v":
        return f"(.var {term[1]})"
    inner = ", ".join(_lean_term(a) for a in term[2])
    return f'(.app "{term[1]}" [{inner}])'


_LEAN_PRELUDE = """import MeTTaILProofs.CPExecutable
open MeTTaIL.CP

partial def varsOf : FOTerm → List Nat
  | .var x => [x]
  | .app _ args => args.flatMap varsOf

partial def dedupNat : List Nat → List Nat
  | [] => []
  | x :: xs => x :: dedupNat (xs.filter (· != x))

def posOf : List Nat → Nat → Nat
  | [], _ => 0
  | y :: ys, x => if y == x then 0 else 1 + posOf ys x

partial def renderWith (order : List Nat) : FOTerm → String
  | .var x => "?" ++ toString (posOf order x)
  | .app f [] => f
  | .app f args =>
      "(" ++ f ++ " " ++ String.intercalate " " (args.map (renderWith order)) ++ ")"

def verdictOf (R : List (Prod FOTerm FOTerm)) (fuel : Nat)
    (cp : ComputedCriticalPair) : String :=
  match boundedJoin? R fuel cp.left cp.right with
  | some _ => "joined"
  | none =>
      if oneSteps R cp.left = [] ∧ oneSteps R cp.right = [] ∧ cp.left ≠ cp.right
      then "counterexample" else "unknown"

def systemReport (name : String) (R : List (Prod FOTerm FOTerm)) (fuel : Nat) : String :=
  let lines := (criticalPairs R).map (fun cp =>
    let order := dedupNat (varsOf cp.left ++ varsOf cp.right)
    renderWith order cp.left ++ "\\t" ++ renderWith order cp.right ++ "\\t"
      ++ verdictOf R fuel cp)
  "=== " ++ name ++ "\\n"
    ++ String.join (lines.map (fun l => l ++ "\\n"))
    ++ "### " ++ (if (checkConfluence R fuel).isCertified then "certified"
                  else "not-certified") ++ "\\n"
"""


def _lean_script(systems, fuel: int) -> str:
    entries = []
    for name, rules in systems:
        written = ", ".join(
            f"({_lean_term(left)}, {_lean_term(right)})" for left, right in rules
        )
        entries.append(f'("{name}", [{written}])')
    body = ",\n   ".join(entries)
    return (
        _LEAN_PRELUDE
        + "\ndef systems : List (Prod String (List (Prod FOTerm FOTerm))) :=\n"
        + f"  [ {body} ]\n\n"
        + "#eval IO.print (String.join "
        + f"(systems.map (fun s => systemReport s.1 s.2 {fuel})))\n"
    )


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


def _run_lean(script: Path, fuel: int) -> str:  # noqa: ARG001  -- the test reflects this callable signature, so every declared parameter must remain visible
    finished = subprocess.run(
        ["lake", "env", "lean", str(script)],
        capture_output=True,
        text=True,
        timeout=280,
        check=True,
        cwd=_ORACLE_ROOT,
    )
    return finished.stdout


@pytest.fixture(scope="module")
def prolog_report(repo_root, tmp_path_factory):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    corpus = tmp_path_factory.mktemp("cp") / "corpus.pl"
    corpus.write_text(_prolog_corpus(ALL_SYSTEMS))
    return _parse(_run_prolog(repo_root, corpus, FUEL))


@pytest.fixture(scope="module")
def lean_report(tmp_path_factory):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    script = tmp_path_factory.mktemp("cp") / "corpus.lean"
    script.write_text(_lean_script(ALL_SYSTEMS, FUEL))
    return _parse(_run_lean(script, FUEL))


def test_the_prolog_enumerator_covers_every_corpus_system(prolog_report):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    assert sorted(prolog_report) == sorted(name for name, _ in ALL_SYSTEMS)


@needs_oracle
def test_the_two_enumerators_compute_the_same_critical_pairs(  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    prolog_report, lean_report
):
    ours = {name: pairs for name, (pairs, _) in prolog_report.items()}
    theirs = {name: pairs for name, (pairs, _) in lean_report.items()}
    assert ours == theirs


@needs_oracle
def test_the_two_checkers_agree_on_confluence(prolog_report, lean_report):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    ours = {name: verdict for name, (_, verdict) in prolog_report.items()}
    theirs = {name: verdict for name, (_, verdict) in lean_report.items()}
    assert ours == theirs


@needs_oracle
def test_the_corpus_exercises_all_three_verdicts(lean_report):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    verdicts = {
        line.split("\t")[2] for pairs, _ in lean_report.values() for line in pairs
    }
    assert verdicts == {"joined", "counterexample", "unknown"}


def test_the_oracle_lane_catches_a_planted_divergence():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
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
