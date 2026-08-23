"""Purpose: share primitive-heavy engine workloads between pytest and perf.
Guarantees:
  - every workload checks its public Python result and reports the number of
    semantic operations it completed [tested
    test_primitive_workloads_check_public_results]
  - let-heavy performs bignum arithmetic through one let per iteration
    [tested test_let_workload_checks_its_bignum_result]
  - let-heavy reaches occurs checking and arithmetic
    [source: engine/translator.pl, unify_with_occurs_check in translate_let_dl/6]
  - alpha-unique and sort-atom reach copying, term hashing, and msort
    [source: engine/metta.pl:152-168]
  - digest reaches findall, copying, and msort [source: bindings/python/metta/shim.pl:1304]
  - source loading reaches sort and findall [source: engine/filereader.pl:136]
  - method dispatch reaches sub_atom and term construction [source: engine/metta.pl:428]
  - space-name recognition reaches atom_concat [source: engine/metta.pl:327]
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

import tempfile
from collections.abc import Callable
from typing import Any, TypeAlias

from metta import Expression, MeTTa, S, V

ALPHA_TERMS = 50_000
DIGEST_ATOMS = 20_000
#: The default evaluation fuel is 100,000 reductions, and the two recursive
#: workloads below spend a million, so their spaces raise the bound the way the
#: corpus raises it for (fib 30) in examples/basics/time_and_pragmas.metta. It
#: is set in SETUP rather than inside the measured call, which leaves the
#: measurement unchanged because the limit is read once per fuel scope, on its
#: first step. It became load-bearing on 2026-08-22, when P14.8 gave m.eval the
#: same fuel scope a runnable form already had: before that this door was
#: unbounded and these workloads were relying on that, so they answered
#: (Error ... StackOverflow) the moment the bound started applying.
_UNBOUNDED_DEPTH = "!(pragma! max-stack-depth 100000000)"

LET_ITERATIONS = 1_000_000
LET_ROW_ELEMENTS = 64
LET_SLOPE_SMALL = 100_000
METHOD_CALLS = 10_000
SORT_TERMS = 100_000
SOURCE_FORMS = 1_000
SPACE_NAME_CALLS = 30_000

_BIGNUM = 10**40
_LET_ROW = Expression([_BIGNUM + index for index in range(LET_ROW_ELEMENTS)])

EngineCase: TypeAlias = tuple[MeTTa, Callable[[], int]]


def _space() -> MeTTa:
    return MeTTa().space()


def close_engine_case(state: EngineCase) -> None:
    """Release a workload's space."""
    state[0].drop()


def let_space() -> MeTTa:
    """Create a space containing the recursive let workload."""
    space = _space()
    try:
        space.run(_UNBOUNDED_DEPTH)
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
    values = Expression(
        [S.node(V[f"x{index % 100}"], index % 10) for index in range(terms)]
    )
    space = _space()

    def operation() -> int:
        result = space.eval(S["alpha-unique-atom"](values))
        if len(result) != 1 or not isinstance(result[0], Expression) or len(result[0]) != min(terms, 10):
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
    call = S["py-call"](Expression(S[".upper"], "abc"))
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
    values = Expression(
        [_BIGNUM + (index * 7_919) % terms for index in range(terms)]
    )
    space = _space()

    def operation() -> int:
        result = space.eval(S["sort-atom"](values))
        if len(result) != 1 or not isinstance(result[0], Expression) or len(result[0]) != terms:
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


TYPED_CALLS = 500_000
TYPED_SLOPE_SMALL = 50_000


def typed_space() -> MeTTa:
    """Create a space holding a DECLARED function and a driver that calls it.

    The argument arrives through a let rather than as a literal, because a
    literal's type is settled while the call site compiles and its check is
    dropped outright, which would measure the one path the check never runs on.
    """
    space = _space()
    try:
        space.run(_UNBOUNDED_DEPTH)
        space.run(
            "(: benchmark-typed-abs (-> Number Number))\n"
            "(= (benchmark-typed-abs $x) (if (>= $x 0) $x (* -1 $x)))\n"
            "(= (benchmark-typed-drive $n $acc) "
            "(if (> $n 0) "
            "(let $v (- 0 $n) "
            "(benchmark-typed-drive (- $n 1) (+ $acc (benchmark-typed-abs $v)))) "
            "$acc))"
        )
    except BaseException:
        space.drop()
        raise
    return space


def typed_call(space: MeTTa, calls: int = TYPED_CALLS) -> int:
    """Run one declared call per iteration, argument type unknown until run time.

    This case exists because the INFERENCE counter cannot see what it measures,
    which makes it the one benchmark here whose instruction ceiling is the
    point rather than a companion. A declared call emits a type check per
    argument and one on the result, and those are specialised to a Prolog
    builtin when the declared type is Number, String or Bool. SWI compiles
    number/1 to a VM instruction and does not count it as an inference
    [measured 2026-08-17: 1.0000 inferences per iteration with and without a
    number/1 call], so the specialisation reads as FREE on the counter every
    other benchmark here is gated on, 18.11 inferences per call before and
    10.11 after against a 10.11 undeclared baseline. That would say a declared
    call is now exactly an undeclared one, and in retired instructions it is
    not: disabling the specialisation by one token measures 9,368,378,515
    against 6,590,122,843 with it, +42.2% [measured 2026-08-17, min of 3 under
    --controlled, which is the interval the ceiling in baseline.json gates].
    The gate is known to see that rather than claimed to: with the ceiling as
    it stands, the unspecialised tree exits 1 and the specialised one exits 0.

    Read that ceiling's noise allowance before attributing anything to a change
    here. It is 5.0 rather than the 1.0 every other bench carries, because this
    workload's instruction count moves 3.13% with code LAYOUT alone: ten
    clauses nothing calls, appended to engine/python.pl, move it 200 million
    instructions and removing them move it back, with the inference count
    identical throughout. baseline.json's instruction_noise_comment carries the
    sweep. A change here of a few percent is layout until proven otherwise, and
    the way to prove it is the inference counter, which does not move with
    layout at all.
    """
    expected = calls * (calls + 1) // 2
    result = space.eval(S["benchmark-typed-drive"](calls, 0))
    if result != [expected]:
        raise AssertionError(f"typed-call returned {result!r}, expected {[expected]!r}")
    return calls


__all__ = [
    "ALPHA_TERMS",
    "DIGEST_ATOMS",
    "LET_ITERATIONS",
    "LET_SLOPE_SMALL",
    "METHOD_CALLS",
    "SORT_TERMS",
    "SOURCE_FORMS",
    "SPACE_NAME_CALLS",
    "TYPED_CALLS",
    "TYPED_SLOPE_SMALL",
    "alpha_unique_case",
    "close_engine_case",
    "digest_case",
    "let_heavy",
    "let_space",
    "py_method_case",
    "sort_atom_case",
    "source_load_case",
    "space_name_case",
    "typed_call",
    "typed_space",
]


SAVE_LOAD_ATOMS = 20_000


def save_load_case(format: str, atoms: int = SAVE_LOAD_ATOMS) -> EngineCase:
    """Round-trip a whole space through a file, which is byte work.

    The inference counter cannot see byte copying: `string-join` once moved 4x
    in inferences and 476x in wall clock for the same change. These two
    benchmarks had an inference baseline and no instruction one, so a change
    that doubled the bytes written would have passed the gate silently. Wall
    clock is the other instrument and it is unusable on a loaded box;
    instructions:u sees the copying and does not move with the load.

    The space is rebuilt per case rather than shared, so the file it writes is
    the same size every round.
    """
    directory = tempfile.TemporaryDirectory(prefix="petta-benchmark-")
    source = _space()
    target = _space()
    try:
        source.add(*(S["benchmark-save-node"](index, index + 1) for index in range(atoms)))
        source.run("(= (benchmark-save-next $x) (+ $x 1))")
    except BaseException:
        source.drop()
        target.drop()
        directory.cleanup()
        raise
    path = f"{directory.name}/roundtrip.{format}"
    expected = atoms + 1

    def operation() -> int:
        saved = source.save(path, format=format)
        groups = target.load(path)
        if saved != expected or groups or len(target) != expected:
            raise AssertionError(f"{format} did not round-trip {expected} atoms")
        if target.run("!(benchmark-save-next 41)") != [[42]]:
            raise AssertionError(f"{format} lost the stored equation")
        target.clear()
        target.run("(= (benchmark-save-next $x) (+ $x 1))")
        return saved

    _SAVE_LOAD_HELD[source.name] = (target, directory)
    return (source, operation)


# What close_save_load_case has to release beyond the space close_engine_case
# drops: the second space the round trip loads into, and the directory the
# file lives in. Keyed on the source space's name because EngineCase carries
# exactly one space and one operation, and widening it would touch every
# workload for the benefit of this one.
_SAVE_LOAD_HELD: dict[str, tuple[MeTTa, Any]] = {}


def close_save_load_case(state: EngineCase) -> None:
    """Release a save-load workload: both spaces and the temporary directory."""
    source = state[0]
    held = _SAVE_LOAD_HELD.pop(source.name, None)
    close_engine_case(state)
    if held is not None:
        target, directory = held
        target.drop()
        directory.cleanup()
