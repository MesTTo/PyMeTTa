"""examples/ch20-extending-the-engine/20-02-metta-written-in-metta/12-interpret_and_metta_thread.metta in Python: three evaluator doors, two answers.

All three take the atom, a type and the space to run it in, and the atom
arrives HELD, so every subject here is built with `S` and never called from
Python. The space is a handle, which is what `m` and the second space are.

They part on a body whose answer is itself reducible: `interpret` and `metta`
hand back the carrier they stepped, and `metta-thread` runs to a fixpoint.
The held-call answers are read through `str`, because `m.fn.repr` EVALUATES
its operand -- it would print 3 where the point is that the answer is still
`(+ 1 2)` -- and because Python's own `1 + 2` is 3 rather than a term.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import S, arrow, fn

UNDEFINED = S["%Undefined%"]


def twin(m):
    """One step against a fixpoint, over the same three arguments."""
    interpret = m.fn.interpret
    metta_ = m.fn.metta
    threaded = m.fn["metta-thread"]

    @m.define
    def twice(x: int) -> int:
        # (= (twice $x) (* 2 $x))
        return 2 * x

    # On an ordinary call all three agree, because one step is all it takes.
    assert metta_(S.twice(5), UNDEFINED, m) == [10]
    assert interpret(S.twice(5), UNDEFINED, m) == [10]
    assert threaded(S.twice(5), UNDEFINED, m) == [10]
    assert interpret(fn.add(1, 2), S.Number, m) == [3]

    # They agree on nondeterminism too: each answers once per branch rather
    # than collapsing.
    @m.define
    def gen():
        # (= (gen) (superpose (1 2)))
        return fn.superpose((1, 2))

    assert interpret(S.gen(), UNDEFINED, m) == [1, 2]
    assert threaded(S.gen(), UNDEFINED, m) == [1, 2]

    # They part on a body whose ANSWER is itself reducible.
    @m.define
    def held():
        # (= (held) (noeval (+ 1 2)))
        return fn.noeval(1 + 2)

    assert str(interpret(S.held(), UNDEFINED, m)[0]) == "(+ 1 2)"
    assert str(metta_(S.held(), UNDEFINED, m)[0]) == "(+ 1 2)"
    assert threaded(S.held(), UNDEFINED, m) == [3]

    # A function frame is the same story: `return` hands one value back to
    # the frame and the two step-at-a-time doors stop there.
    @m.define
    def framed():
        # (= (framed) (function (return (+ 1 2))))
        return fn.function(S["return"](1 + 2))

    assert str(interpret(S.framed(), UNDEFINED, m)[0]) == "(+ 1 2)"
    assert threaded(S.framed(), UNDEFINED, m) == [3]

    # An atom nothing reduces is its own answer through every one of them.
    assert interpret(S.nosuchhead, UNDEFINED, m) == [S.nosuchhead]
    assert threaded(S.nosuchhead, UNDEFINED, m) == [S.nosuchhead]

    # Two are declared and the third is not, which is why the first two mask
    # their atom argument and the third is a bare operation.
    stepper = arrow(S.Atom, S.Type, S.SpaceType, S.Atom)
    assert m.type(S.interpret) == stepper
    assert m.type(S.metta) == stepper
    assert m.type(S.metta_thread) == UNDEFINED

    # The space argument is the point of all three: an atom evaluates against
    # the equations of the space it is handed, not of the caller's.
    elsewhere = m.metta.space(S.elsewhere)
    elsewhere += S["="](S.twice(V_X), 1000 + V_X)
    assert interpret(S.twice(5), UNDEFINED, elsewhere) == [1005]
    assert threaded(S.twice(5), UNDEFINED, elsewhere) == [1005]
    assert interpret(S.twice(5), UNDEFINED, m) == [10]


from metta import V  # noqa: E402  -- the one variable the elsewhere equation binds

V_X = V.x

#: MEASURED on this branch rather than inherited: this twin is new, so there is
#: no earlier pin to move
#: [measured 2026-09-07: 30158 inferences, 1.0577x the example's 28514; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3;
#: fixture=docs/every-atom-has-an-example at its example commits; commit=98397cdd04679cbf40b2d515076dadc09c1b0a32].
#: RE-PINNED 2026-09-08, 30158 to 30301 (+143), the merges between this lane's
#: burn-down base (dfd5003f) and the tree that merged it, placed by a first-
#: parent ladder through the lane's own driver over ten twins at f8c4b672,
#: 4af59757, 90c08119, ad762ee7, 72f9cdf2 and 249389cb (ai-
#: tmp/integrator-849a9e/mergeTW-twin-ladder.log): the catalog-types merge
#: (1a3579fa) moves every twin by a lookup-and-layout step of about +5 for a
#: twin that makes no typed call and about +35 for one that does, plus about +6
#: per compiled definition through the argument-delivery check at the write
#: (the authoring fit re-measured 1370+1307 to 1406+1309), and +1411 for the
#: catalog twin that enumerates the 280 new rows; the two-sided-fragments merge
#: (4af59757) moves the sequence-variable twins by what their fixed rows now
#: compute (+2604 for the two-sided fragments, -217 for the fence, +19 for
#: restricted spaces); the every-atom merge (90c08119) re-authored the reading-
#: forms twin into the sread half (+3017) and added forty-six twins pinned on
#: its own base 31d54e19, which the merges since moved by the same clusters;
#: the gate-hygiene merge (ad762ee7) makes the tabling twins cheaper by the wfs
#: library no longer loading eagerly. Every twin here re-reads its budget on
#: the merged tree, minimum of three fresh processes [measured 2026-09-08: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=08f6f4df19a283bb84ba5f679c83944b42685b2e].
#: RE-PINNED 2026-09-08, 30301 to 30183 (-118), metta_substitute_self/3 probes
#: the term for the text &self before walking it, one C write and one C
#: substring probe, where the twins-lane merge's one-equation door (08f6f4df)
#: walked every natively added equation in a named space unconditionally, so
#: every twin that adds or defines an equation in a named space drops by about
#: that equation's size in inferences; the same probe now guards the reader's
#: per-form door (record_translated_from/4), the deferred door's fallback
#: (stored_equation_source/4), a batch's arriving equations
#: (mark_or_translate_equation/5) and the removal probe (remove_equation/6),
#: where the walk is new and skipped for a term that never says &self, and a
#: twin that only removes or re-adds such equations pays the two-inference
#: probe per door crossing instead. Every twin here re-reads its budget on this
#: tree, minimum of three fresh processes [measured 2026-09-08: min-of-3 serial
#: fresh processes; command=python extensions/python/tools/twin_coverage.py
#: --repin; commit=856434d7c1d381b3f3d7cbbd008f46c0d41b61aa].
#: RE-PINNED 2026-09-08, 30183 to 30132 (-51), the evaluation-fuel scope marker
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
#: RE-PINNED 2026-09-08, 30132 to 30158 (+26), boot content moved: the refusal
#: table and the typing point are modules this package did not have, three
#: convert doors became one, per-library faces are projections, and the engine
#: gained a catalog watch point, and SWI clause-indexing shape shifts a twin
#: count by tens whenever boot content moves, the mechanism every earlier entry
#: in these chains names. The watch point itself is one inference per &metta
#: write, which a twin that defines a function pays three of (2239 against 2236
#: on ch03 01-comments with the two announcement clauses taken out), and the
#: (limit ...) rows it exists for cost nothing at all: 2239 either way with
#: every row-backed bound removed, because boot seeds the mirror those bounds
#: are read from [measured 2026-09-08: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=c26b6a4d28ef8fb50742440feed2c0578ebb0f58].
#: RE-PINNED 2026-09-08, 30132 to 30328 (+196), The engine and library
#: predicates now resolve through their owning modules and the explicit engine
#: facade; compiled program lookup crosses the added metta_engine tier
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=ede2ac57e213a0d4502c6bbbca6227f97015b720].
#: RE-PINNED 2026-09-08, 30328 to 30338 (+10), The engine and library module
#: boundaries retain explicit lookup owners, including host registration and
#: returned callback goals [measured 2026-09-08: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=ede2ac57e213a0d4502c6bbbca6227f97015b720].
#: RE-PINNED 2026-09-08, 30338 to 30524 (+186), the module boundary merged with
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
#: RE-PINNED 2026-09-08, 30158 to 30193 (+35), The typed host door catalog is
#: published before user code. Its declarations change catalog lookup indexes;
#: generated public names bind directly to their existing bodies [measured
#: extensions/python/tools/twin_coverage.py --repin; commit=b615b5a33b43252ef9826e5387da7c9bd7f6b543].
BUDGET = 30193
