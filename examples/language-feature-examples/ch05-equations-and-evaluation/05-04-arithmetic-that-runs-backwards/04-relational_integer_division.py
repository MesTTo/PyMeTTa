"""examples/ch05-equations-and-evaluation/05-04-arithmetic-that-runs-backwards/04-relational_integer_division.metta in Python: truncating against flooring.

`#//` and `#div` have no Python spelling and want none: they are CLP(FD)
constraints rather than evaluations, and running in either direction is the
point. The subscript door names them exactly, because neither is an
identifier and Python's own `//` is a different operation on a different
domain.

Two doors, one per job, the same split `02-relational_arithmetic.py` uses.
`m.fn["#//"]` CALLS the constraint; the static `fn["#//"]` BUILDS the term,
which is what a backward query needs, since what is being solved for has to
reach the engine unevaluated.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import TRUE, S, V, fn


def twin(m):
    """The two integer divisions, forwards, on negatives, and backwards."""
    truncating, flooring = m.fn["#//"], m.fn["#div"]

    # On non-negative operands they agree.
    assert truncating(7, 2) == [3]
    assert flooring(7, 2) == [3]

    # A negative operand is where they part: -3.5 truncates toward zero and
    # floors away from it.
    assert truncating(-7, 2) == [-3]
    assert flooring(-7, 2) == [-4]
    assert truncating(7, -2) == [-3]
    assert flooring(7, -2) == [-4]

    # `#div` and `#mod` round the same way, so quotient times divisor plus
    # remainder reconstructs the dividend. `#//` has no matching remainder in
    # this surface -- there is no `#rem` -- so the same sum is off by the
    # divisor, which is exactly the gap between truncating and flooring.
    # Built rather than computed in Python: `*` and `+` on atoms BUILD the
    # term, which is what makes one claim one engine evaluation.
    assert m.answers(fn["#div"](-7, 2) * 2 + fn["#mod"](-7, 2)) == [-7]
    assert m.answers(fn["#//"](-7, 2) * 2 + fn["#mod"](-7, 2)) == [-5]

    # Backwards: the quotient and the dividend are known, the divisor is not.
    assert m.solve(3, fn["#//"](7, V.d)).d == 2

    # The other direction is a relation rather than a function, because
    # truncation loses information: 6 and 7 both divide to 3. A second
    # constraint decides it, and the two have to be posted and asked inside
    # ONE derivation, which is `(let True <constraint> <question>)`; `m.solve`
    # does not reach it, and the residue table records that guard against
    # P14.4.
    quotient = S.let(3, fn["#//"](V.n, 2), V.n)  # rung: let as a binder
    assert m.answers(S.let(TRUE, fn["#<"](V.n, 7), quotient)) == [6]  # rung: let as a guard
    assert m.answers(S.let(TRUE, fn["#>"](V.n, 6), quotient)) == [7]  # rung: let as a guard


#: MEASURED on this branch rather than inherited: this twin is new, so there is
#: no earlier pin to move
#: [measured 2026-09-07: 8613 inferences, 0.9070x the example's 9496; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3;
#: fixture=docs/every-atom-has-an-example at its example commits; commit=98397cdd04679cbf40b2d515076dadc09c1b0a32].
#: RE-PINNED 2026-09-08, 8613 to 8582 (-31), the evaluation-fuel scope marker
#: is a trailed write (fix/every-intermittent-root-caused, f6e05ca9):
#: `$metta_fuel_scope` is written open with b_setval/2 at scope open and read
#: with b_getval/2 where nb_current/2 used to answer, so an abandoned scope
#: closes itself when an exception unwinds the trail and the cleanup is the
#: fast ordinary exit, and every runnable form pays fewer inferences per scope;
#: a twin drops by about the count of its runnables, and the engine bench reads
#: evaluate and translate 1642 lower each on the same tree. Every twin here re-
#: reads its budget on the merged tree, minimum of three fresh processes
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=3fc65f02ce807c359f1a52026f950f345da2a9af].
#: RE-PINNED 2026-09-08, 8582 to 8688 (+106), The engine and library predicates
#: now resolve through their owning modules and the explicit engine facade;
#: compiled program lookup crosses the added metta_engine tier [measured
#: 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=ede2ac57e213a0d4502c6bbbca6227f97015b720].
#: RE-PINNED 2026-09-08, 8688 to 8829 (+141), the module boundary merged with
#: trunk's later packages (refactor/engine-and-libraries-as-modules at
#: b64291369): every space now resolves through one more chain link, prelude ->
#: metta_engine -> user, the engine's measured export list is imported into the
#: host tier at boot, the closed-sets watch point costs one inference per
#: &metta write, and a cursor opened by a host pays one transaction check at
#: its door; the branch pinned its budgets on its cut, trunk re-pinned the same
#: twins for the packages that landed after that cut, and only the merged tree
#: carries both, so this entry is where the two chains meet [measured
#: 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=f1038acdcaf5230b6431c112f38a719d3dc9ef19].
#: RE-PINNED 2026-09-09, 8829 to 9000 (+171), structured concurrency landed
#: (feat/structured-concurrency merged at f80cc416d): every space mint records
#: its allocation in the library's lifetime rows, every write and run pays the
#: ownership hook and every drop asks the library whether a scope owns the
#: name, measured on a pristine control as 32 per mint, 2 per write and 44 per
#: drop with none per read; measured on the merged tree [measured 2026-09-09:
#: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=WORKTREE].
BUDGET = 9000
