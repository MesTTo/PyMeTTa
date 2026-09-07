"""examples/ch08-data/08-01-atoms-lists-and-folds/19-decons_and_substitution.metta in Python: one step apart, one value in.

`decons-atom` answers the head and the tail together, which Python reads as
an unpackable pair, so the twin destructures it the way any Python program
destructures a two-element answer.

`atom-subst`'s second operand is a BINDER position, held as written, and the
refusal for a non-binder is an error ATOM, so the twin compares it as data
rather than catching anything.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import S, V, fn


def twin(m):
    """Take an expression apart, put it back, and substitute into it."""
    # COST, recorded rather than hidden: 10771 against the example's 8541,
    # past the 10% band with no compiled definition to earn its per-definition
    # credit. The gap is the Python boundary -- twenty calls cross it where
    # the example's twelve forms compile into one program -- and it is the
    # library's to close, not this twin's [measured 2026-09-07: python
    # extensions/python/tools/twin_coverage.py --measure --rounds 3].
    decons_atom, decons = m.fn.decons_atom, m.fn["decons"]
    substitute = m.fn.atom_subst

    # One call does what car-atom and cdr-atom do in two, and the pair
    # destructures.
    [head, tail] = decons_atom((S.a, S.b, S.c))[0]
    assert (head, tail) == (S.a, (S.b, S.c))
    [only, rest] = decons_atom((S.a,))[0]
    assert (only, rest) == (S.a, ())
    # The pair is what a `let` destructures in MeTTa, and what a Python
    # unpacking destructures here.
    assert m.answers(fn.car_atom(tail)) == [S.b]

    # `decons` is the same operation under its un-suffixed name, and `cons`
    # puts back what it took apart.
    assert decons((S.a, S.b, S.c)) == decons_atom((S.a, S.b, S.c))
    assert m.fn.cons_atom(head, tail) == [(S.a, S.b, S.c)]
    assert m.fn.cons_atom(only, rest) == [(S.a,)]

    # The head comes back AS WRITTEN: taking a list apart is not evaluating
    # it, so a call sitting in head position stays a call.
    [call, others] = decons((S.f(1), S.b))[0]
    assert (call, others) == (S.f(1), (S.b,))

    # `atom-subst` puts a value where a named variable stands: value first,
    # the variable second, the term third. Every occurrence goes.
    assert substitute(1, V.x, S.foo(V.x, V.x)) == [S.foo(1, 1)]
    assert substitute(S.g(2), V.x, S.foo(V.x, S.bar(V.x))) == [S.foo(S.g(2), S.bar(S.g(2)))]

    # Only the variable named is touched; the others stay free.
    assert m.fn["=alpha"](substitute(1, V.y, S.foo(V.x, V.y))[0], S.foo(V.a, 1)) == [True]

    # The binder position is HELD, so a call that would reduce to a variable
    # is refused as the non-binder it is rather than evaluated into one.
    refused = S.Error(S.atom_subst(1, S.car_atom((V.x,)), S.foo(V.x)), S.NoReturn)
    # Compared up to renaming, because the engine mints its own variable for
    # the one the refusal carries.
    assert m.fn["=alpha"](substitute(1, S.car_atom((V.x,)), S.foo(V.x))[0], refused) == [True]

    # A term with nothing to substitute comes back unchanged.
    assert substitute(1, V.x, S.foo(S.bar)) == [S.foo(S.bar)]


#: MEASURED on this branch rather than inherited: this twin is new, so there is
#: no earlier pin to move
#: [measured 2026-09-07: 10771 inferences, 1.2611x the example's 8541; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3;
#: fixture=docs/every-atom-has-an-example at its example commits; commit=98397cdd04679cbf40b2d515076dadc09c1b0a32].
#: RE-PINNED 2026-09-08, 10771 to 10727 (-44), the evaluation-fuel scope marker
#: is a trailed write (fix/every-intermittent-root-caused, f6e05ca9):
#: `$metta_fuel_scope` is written open with b_setval/2 at scope open and read
#: with b_getval/2 where nb_current/2 used to answer, so an abandoned scope
#: closes itself when an exception unwinds the trail and the cleanup is the
#: fast ordinary exit, and every runnable form pays fewer inferences per scope;
#: a twin drops by about the count of its runnables, and the engine bench reads
#: evaluate and translate 1642 lower each on the same tree. Every twin here re-
#: reads its budget on the merged tree, minimum of three fresh processes
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=WORKTREE].
BUDGET = 10727

#: OVERRUN 2026-09-08, 1400: the twin reads 10771 against a ceiling of 9395 (the
#: example's 8541 plus 10%, no definition to author), and the floor any Python
#: twin of this example can reach is 10239, above the ceiling: the band is
#: tighter than the library's floor for a program that takes expressions
#: apart and substitutes through the structured evaluation door. The 532
#: above the floor is this twin's own program [measured 2026-09-08: one fresh
#: process per side; command=python
#: extensions/python/benchmarks/probes/twin_floor.py; commit=08f6f4df19a283bb84ba5f679c83944b42685b2e].
OVERRUN = 1400
