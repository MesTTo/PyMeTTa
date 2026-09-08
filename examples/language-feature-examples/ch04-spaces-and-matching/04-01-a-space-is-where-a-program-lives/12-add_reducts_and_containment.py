"""examples/ch04-spaces-and-matching/04-01-a-space-is-where-a-program-lives/12-add_reducts_and_containment.metta in Python: answers in, or programs in.

`add-atoms` stores what was written and `add-reducts` stores what it reduces
to, so the two spaces below hold a program and its answers. Both are called
through the function namespace rather than through `space += atom`, because
which of the two doors is being used IS the subject.

`space-contains` asks about UNIFICATION and answers one Bool, which is a
different question from a match: it binds nothing and costs one indexed probe
whatever the space holds.

What each space HOLDS is read through `space[pattern]`, which is what a match
is here, rather than through a collapse of `get-atoms`: a Python list IS the
collapse, so asking for one and then rendering it would be the long way round
to a count.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import S, V, fn


def twin(m):
    """Two write doors, and the containment probe over what each stored."""
    written = m.metta.space(S.written)
    reduced = m.metta.space(S.reduced)
    single = m.metta.space(S.single)
    contains = m.fn["space-contains"]

    # `add-atoms` stores what you wrote, so the space holds CALLS.
    assert m.fn.add_atoms(written, (fn.add(1, 1), fn.mul(2, 3))) == [True]
    assert len(written[fn.add(1, 1)]) == 1
    assert len(written[fn.mul(2, 3)]) == 1

    # `add-reducts` is the same door with the elements reduced first, so the
    # space holds ANSWERS. It is `add-reduct` over a list.
    assert m.fn.add_reducts(reduced, (fn.add(1, 1), fn.mul(2, 3))) == [True]
    assert len(reduced[2]) == 1
    assert len(reduced[6]) == 1
    assert m.fn.add_reduct(single, fn.add(1, 1)) == [True]
    assert len(single[2]) == 1
    assert len(single[fn.add(1, 1)]) == 0

    # Which of the two you want is the difference between a space of FACTS and
    # a space of PROGRAM.
    assert len(written[2]) == 0

    # `space-contains` answers True or False for one atom, and its atom
    # argument is HELD.
    assert contains(reduced, 2) == [True]
    assert contains(reduced, 99) == [False]
    assert contains(written, S["+"](1, 1)) == [True]
    assert contains(written, 2) == [False]

    # It asks about UNIFICATION rather than identity, so a stored atom with a
    # variable in it answers True for every atom that variable could stand for.
    written += S.edge(V.a, V.b)
    assert contains(written, S.edge(S.a, S.b)) == [True]
    assert contains(written, S.edge(V.x, V.y)) == [True]
    assert contains(written, S.node(S.a)) == [False]

    # The difference from a match is what comes back: a match binds and
    # enumerates, this answers one Bool and binds nothing.
    assert len(written[S.edge(V.x, V.y)]) == 1
    assert contains(written, S.edge(S.a, S.b)) == [True]


#: MEASURED on this branch rather than inherited: this twin is new, so there is
#: no earlier pin to move
#: [measured 2026-09-07: 5593 inferences, 0.8445x the example's 6623; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3;
#: fixture=docs/every-atom-has-an-example at its example commits; commit=98397cdd04679cbf40b2d515076dadc09c1b0a32].
#: RE-PINNED 2026-09-08, 5593 to 5561 (-32), the evaluation-fuel scope marker
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
#: RE-PINNED 2026-09-08, 5561 to 5903 (+342), The engine and library predicates
#: now resolve through their owning modules and the explicit engine facade;
#: compiled program lookup crosses the added metta_engine tier [measured
#: 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=ede2ac57e213a0d4502c6bbbca6227f97015b720].
#: RE-PINNED 2026-09-08, 5903 to 6058 (+155), the module boundary merged with
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
BUDGET = 6058
