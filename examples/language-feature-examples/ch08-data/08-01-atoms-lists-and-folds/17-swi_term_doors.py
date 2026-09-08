"""examples/ch08-data/08-01-atoms-lists-and-folds/17-swi_term_doors.metta in Python: five doors onto SWI's own term operations.

Every name here keeps its Prolog underscore, so every one of them comes
through the exact subscript door: `m.fn["atom_chars"]` and not
`m.fn.atom_chars`, which the host-convention map would read as `atom-chars`,
a name the tree does not ship.

`pretty-atom` takes its operand EVALUATED, so an equation handed to it has to
arrive masked: `fn.noeval(...)` is what the original writes and what the twin
builds.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import Expression, G, S, V, fn


def twin(m):
    """Characters, joining, copying, hashing, groundness and printing."""
    chars, concat = m.fn["atom_chars"], m.fn["atom_concat"]
    copy, term_hash = m.fn["copy_term"], m.fn["term_hash"]
    is_ground, is_var, pretty = m.fn.is_ground, m.fn.is_var, m.fn.pretty_atom

    # A name or a string comes apart into one-character SYMBOLS.
    assert chars(S.abc) == [S.a(S.b, S.c)]
    assert chars(G("abc")) == [S.a(S.b, S.c)]
    assert m.fn.size_atom(chars(123)[0]) == [3]
    # They are symbols, so the answer for 123 is not the three numbers the
    # same source text would read as.
    assert chars(123) != [Expression((1, 2, 3))]
    assert concat(m.fn.car_atom(chars(S.abc)[0])[0], S.bc) == [S.abc]

    # `atom_concat` answers a SYMBOL whatever the operands were.
    assert concat(S.ab, S.cd) == [S.abcd]
    assert concat(G("ab"), S.cd) == [S.abcd]
    assert concat(S.ab, 1) == [S.ab1]
    assert concat(G("ab"), G("cd")) != [G("abcd")]

    # `copy_term` answers the same structure with FRESH variables, and
    # sharing survives: a repeated variable stays one variable.
    assert m.fn["=alpha"](copy(S.foo(V.x, V.y))[0], S.foo(V.a, V.b)) == [True]
    assert m.fn["=?"](*copy(Expression((V.x, V.x)))[0]) == [True]
    assert m.answers(fn["=="](*copy(Expression((V.x, V.y)))[0])) == [False]

    # `term_hash` depends only on the written structure.
    assert term_hash(S.foo(1)) == term_hash(S.foo(1))
    assert term_hash(S.foo(1)) != term_hash(S.foo(2))
    # It is a number, which adding zero to it proves: `+` takes numbers.
    assert m.answers(0 + fn["term_hash"](S.foo(1))) == term_hash(S.foo(1))

    # And it is defined for GROUND terms only: a term with a variable in it
    # leaves the answer unbound rather than inventing a number.
    assert is_ground(S.foo(1)) == [True]
    assert is_ground(S.foo(V.x)) == [False]
    assert is_var(term_hash(S.foo(V.x))[0]) == [True]

    # `pretty-atom` is the writer, and it renames variables to the engine's
    # own numbering, so two alpha-equivalent atoms print the same.
    assert m.answers(fn.pretty_atom(fn.noeval(S["="](S.f(1), S["+"](1, 1))))) == [
        G("(= (f 1) (+ 1 1))")
    ]
    assert m.answers(fn.pretty_atom(fn.noeval(S.f(V.x)))) == m.answers(
        fn.pretty_atom(fn.noeval(S.f(V.y)))
    )
    assert pretty(1) == [G("1")]


#: MEASURED on this branch rather than inherited: this twin is new, so there is
#: no earlier pin to move
#: [measured 2026-09-07: 13305 inferences, 0.8962x the example's 14846; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3;
#: fixture=docs/every-atom-has-an-example at its example commits; commit=98397cdd04679cbf40b2d515076dadc09c1b0a32].
#: RE-PINNED 2026-09-08, 13305 to 13210 (-95), the evaluation-fuel scope marker
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
#: RE-PINNED 2026-09-08, 13210 to 13528 (+318), The engine and library
#: predicates now resolve through their owning modules and the explicit engine
#: facade; compiled program lookup crosses the added metta_engine tier
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=ede2ac57e213a0d4502c6bbbca6227f97015b720].
#: RE-PINNED 2026-09-08, 13528 to 13949 (+421), the module boundary merged with
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
#: RE-PINNED 2026-09-09, 13949 to 14143 (+194), Compile shipped typing
#: decisions and initial vocabulary facts, index vocabulary membership, and
#: reuse the first Python variable binding before indexing additional names;
#: retain type, transaction and variable-identity checks [measured 2026-09-09:
#: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=32650f9ff4d1c4aa0749d8eb8b153e5bb448ee5c].
BUDGET = 14143
