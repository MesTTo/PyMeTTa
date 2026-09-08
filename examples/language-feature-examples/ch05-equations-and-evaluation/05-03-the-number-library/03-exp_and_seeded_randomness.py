"""examples/ch05-equations-and-evaluation/05-03-the-number-library/03-exp_and_seeded_randomness.metta in Python: e, and a repeatable draw.

`exp` and `exp-math` are two names for one operation, so the twin calls both
through the function namespace and compares them.

`with-seed` HOLDS its body, and that is what decides the Python spelling: the
body is built as an ATOM with `S`, never called, and handed over. `S.random_int(0, 100)`
is the expression `(random-int 0 100)` as data, so the scope receives a
program rather than a number the host already drew.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import S

#: The body every seeded claim runs, built once because it is data.
ONE_DRAW = S.random_int(0, 100)

#: A draw NESTED inside another call, so the claim is about the body's whole
#: extent rather than about its outermost operation.
NESTED_DRAW = S.abs_math(S.random_int(-100, 100))


def twin(m):
    """E to a power, and a random draw that repeats."""
    assert m.fn.exp(0) == [1.0]
    assert m.fn.exp(1) == [2.718281828459045]
    assert m.fn.exp(2) == m.fn.exp_math(2)

    # The same seed draws the same number, which is what makes a randomised
    # program testable: the draw stays random and the RUN stops being.
    assert m.fn.with_seed(42, ONE_DRAW) == m.fn.with_seed(42, ONE_DRAW)

    # The scope is the body's whole dynamic extent, so a draw buried inside
    # the body is seeded too.
    assert m.fn.with_seed(7, NESTED_DRAW) == m.fn.with_seed(7, NESTED_DRAW)

    # A different seed is a different sequence, so the seed is doing work
    # rather than switching randomness off.
    assert m.fn.with_seed(42, ONE_DRAW) != m.fn.with_seed(43, ONE_DRAW)

    # One generator serves both draws, so the scope reaches `random-float` too.
    float_draw = S.random_float(0.0, 1.0)
    assert m.fn.with_seed(5, float_draw) == m.fn.with_seed(5, float_draw)


#: MEASURED on this branch rather than inherited: this twin is new, so there is
#: no earlier pin to move. min-of-3 in fresh processes
#: [measured 2026-09-07: 3991 inferences, 0.5639x the example's 7077; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3
#: examples/ch05-equations-and-evaluation/05-03-the-number-library/03-exp_and_seeded_randomness.metta;
#: fixture=docs/every-atom-has-an-example at its example commits; commit=98397cdd04679cbf40b2d515076dadc09c1b0a32].
#: RE-PINNED 2026-09-08, 3991 to 3956 (-35), the evaluation-fuel scope marker
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
#: RE-PINNED 2026-09-08, 3956 to 3989 (+33), The engine and library predicates
#: now resolve through their owning modules and the explicit engine facade;
#: compiled program lookup crosses the added metta_engine tier [measured
#: 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=ede2ac57e213a0d4502c6bbbca6227f97015b720].
#: RE-PINNED 2026-09-08, 3989 to 4158 (+169), the module boundary merged with
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
#: RE-PINNED 2026-09-09, 4158 to 4363 (+205), structured concurrency landed
#: (feat/structured-concurrency merged at f80cc416d): every space mint records
#: its allocation in the library's lifetime rows, every write and run pays the
#: ownership hook and every drop asks the library whether a scope owns the
#: name, measured on a pristine control as 32 per mint, 2 per write and 44 per
#: drop with none per read; measured on the merged tree [measured 2026-09-09:
#: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=WORKTREE].
BUDGET = 4363
