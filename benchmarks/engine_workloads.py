"""Purpose: share primitive-heavy engine workloads between pytest and perf.
Guarantees:
  - every workload checks its public Python result and reports the number of
    semantic operations it completed [tested
    test_primitive_workloads_check_public_results]
  - let-heavy performs bignum arithmetic through one let per iteration
    [tested test_let_workload_checks_its_bignum_result]
  - let-heavy reaches occurs checking and arithmetic [source: src/translator.pl:550]
  - alpha-unique and sort-atom reach copying, term hashing, and msort
    [source: src/metta.pl:152-168]
  - digest reaches findall, copying, and msort [source: python/petta/shim.pl:1304]
  - source loading reaches sort and findall [source: src/filereader.pl:136]
  - method dispatch reaches sub_atom and term construction [source: src/metta.pl:428]
  - space-name recognition reaches atom_concat [source: src/metta.pl:327]
Decides:
  - default sizes keep each measured engine operation above 0.1 seconds on
    the gate workstation [measured 2026-08-15: 0.101-0.254 seconds]
Owns:
  - each factory returns a fresh space that close_engine_case or the caller
    releases after the operation [tested
    test_primitive_workloads_check_public_results]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeAlias

from petta import Expr, MeTTa, S, V, expr

ALPHA_TERMS = 50_000
DIGEST_ATOMS = 20_000
LET_ITERATIONS = 1_000_000
LET_ROW_ELEMENTS = 64
LET_SLOPE_SMALL = 100_000
METHOD_CALLS = 10_000
SORT_TERMS = 100_000
SOURCE_FORMS = 1_000
SPACE_NAME_CALLS = 30_000

_BIGNUM = 10**40
_LET_ROW = expr(*(_BIGNUM + index for index in range(LET_ROW_ELEMENTS)))

EngineCase: TypeAlias = tuple[MeTTa, Callable[[], int]]


def _space() -> MeTTa:
    return MeTTa().fresh_space()


def close_engine_case(state: EngineCase) -> None:
    """Release a workload's space."""
    state[0].drop()


def let_space() -> MeTTa:
    """Create a space containing the recursive let workload."""
    space = _space()
    try:
        space.run(
            "(= (benchmark-let-heavy $n $acc $row) "
            "(if (> $n 0) "
            "(let $next (cons-atom $n $row) "
            "(benchmark-let-heavy (- $n 1) (+ $acc (car-atom $next)) $row)) "
            "$acc))"
        )
    except BaseException:
        space.drop()
        raise
    return space


def let_heavy(space: MeTTa, iterations: int = LET_ITERATIONS) -> int:
    """Evaluate one let binding a compound and one bignum addition per iteration.

    The bound value is a compound on purpose. A let emits its occurs check
    before evaluating both sides when they share no variable, which is O(1)
    on two unbound variables, and after when they do, where the check walks
    the whole value. Binding a bignum leaves that walk one cell wide, so the
    case measured let dispatch and nothing of the walk: forcing every let
    onto the late path moved it 0.5% in the wrong direction. The row is a
    fixed width rather than an accumulation, so the walk is a constant per
    iteration instead of quadratic over a million of them.

    The walk is over the value's subterms, so its cost is the value's size:
    "All the subterms of the given term are generated on backtracking and
    tested to see if they are identical to the variable" [source: Sterling
    and Shapiro, The Art of Prolog, 2nd ed., p182, Program 10.7].

    Forcing the late path now costs 13,836,204,827 instructions:u against
    5,614,127,276, a factor of 2.46 [measured 2026-08-15, min of 3].
    """
    expected = _BIGNUM + iterations * (iterations + 1) // 2
    result = space.eval(S["benchmark-let-heavy"](iterations, _BIGNUM, _LET_ROW))
    if result != [expected]:
        raise AssertionError(f"let-heavy returned {result!r}, expected {[expected]!r}")
    return iterations


def alpha_unique_case(terms: int = ALPHA_TERMS) -> EngineCase:
    """Build an alpha-equivalence workload over repeated variable shapes."""
    values = expr(*(S.node(V[f"x{index % 100}"], index % 10) for index in range(terms)))
    space = _space()

    def operation() -> int:
        result = space.eval(S["alpha-unique-atom"](values))
        if len(result) != 1 or not isinstance(result[0], Expr) or len(result[0]) != min(terms, 10):
            raise AssertionError(f"alpha-unique returned an invalid result: {result!r}")
        return terms

    return space, operation


def digest_case(atoms: int = DIGEST_ATOMS) -> EngineCase:
    """Build a space whose digest canonicalizes and sorts variable terms."""
    values = tuple(
        S["benchmark-digest-node"](S[f"n{index}"], V[f"x{index % 100}"], _BIGNUM + index)
        for index in range(atoms)
    )
    space = _space()
    try:
        space.add(*values)
    except BaseException:
        space.drop()
        raise

    def operation() -> int:
        digest = space.digest()
        if len(digest) != 64:
            raise AssertionError(f"space digest has invalid length: {digest!r}")
        int(digest, 16)
        return atoms

    return space, operation


def py_method_case(calls: int = METHOD_CALLS) -> EngineCase:
    """Call a converted Python string method through MeTTa's py-call."""
    call = S["py-call"](expr(S[".upper"], "abc"))
    space = _space()

    def operation() -> int:
        result = None
        for _ in range(calls):
            result = space.eval(call)
        if result != [S.ABC]:
            raise AssertionError(f"Python method dispatch returned {result!r}")
        return calls

    return space, operation


def sort_atom_case(terms: int = SORT_TERMS) -> EngineCase:
    """Sort a deterministic permutation of bignums through sort-atom."""
    values = expr(*(_BIGNUM + (index * 7_919) % terms for index in range(terms)))
    space = _space()

    def operation() -> int:
        result = space.eval(S["sort-atom"](values))
        if len(result) != 1 or not isinstance(result[0], Expr) or len(result[0]) != terms:
            raise AssertionError(f"sort-atom returned an invalid result: {result!r}")
        if terms and (result[0][0] != _BIGNUM or result[0][-1] != _BIGNUM + terms - 1):
            raise AssertionError("sort-atom did not order the bignum range")
        return terms

    return space, operation


def source_load_case(forms: int = SOURCE_FORMS) -> EngineCase:
    """Parse and compile many function definitions in one source unit."""
    source = "\n".join(
        f"(= (benchmark-source-{index} $x) (+ $x {index}))" for index in range(forms)
    )
    space = _space()

    def operation() -> int:
        groups = space.run(source)
        if groups:
            raise AssertionError(f"source definitions returned result groups: {groups!r}")
        if forms:
            result = space.eval(S[f"benchmark-source-{forms - 1}"](1))
            if result != [forms]:
                raise AssertionError(f"source workload returned {result!r}, expected {[forms]!r}")
        return forms

    return space, operation


def space_name_case(calls: int = SPACE_NAME_CALLS) -> EngineCase:
    """Recognize a space name repeatedly through is-space."""
    call = S["is-space"](S["&benchmark"])
    space = _space()

    def operation() -> int:
        result = None
        for _ in range(calls):
            result = space.eval(call)
        if result != [True]:
            raise AssertionError(f"space-name recognition returned {result!r}")
        return calls

    return space, operation


__all__ = [
    "ALPHA_TERMS",
    "DIGEST_ATOMS",
    "LET_ITERATIONS",
    "LET_SLOPE_SMALL",
    "METHOD_CALLS",
    "SORT_TERMS",
    "SOURCE_FORMS",
    "SPACE_NAME_CALLS",
    "alpha_unique_case",
    "close_engine_case",
    "digest_case",
    "let_heavy",
    "let_space",
    "py_method_case",
    "sort_atom_case",
    "source_load_case",
    "space_name_case",
]
