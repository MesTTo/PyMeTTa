"""examples/ch10-errors-and-refusals/02-throwing_and_tracing.metta in Python: an error a program makes for itself.

`throw` does not unwind: it PRODUCES the value `(Error (throw R) R)`, so every
claim here compares an atom rather than catching anything, and the Python
spelling is the value the engine answers.

`trace!` prints its first argument and answers its second, so its claims are
about what flows through it. Both of its arguments are held, which is why the
label is built with `S` and never evaluated on the way in.

`half` takes no annotation and builds both of its operators by word,
`fn.truediv` and `fn.mod`. An annotation would publish a type declaration the
original does not have, and `n / 2` without one would store
`(py-operator truediv ...)` and answer 5.0 where the original stores `(/ ...)`
and answers 5.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import G, S, fn


def twin(m):
    """Produce an error, read it, carry it out of a function, and trace."""
    throw, trace = m.fn.throw, m.fn["trace!"]

    ball = S.my_ball(1)
    assert throw(ball) == [S.Error(S.throw(ball), ball)]
    assert throw(G("text")) == [S.Error(S.throw(G("text")), G("text"))]

    # Every form that reads an error reads this one, with no special case for
    # a raised one against a computed one. `return-on-error` answers the
    # error inside minimal MeTTa's own `return` marker.
    assert m.fn.if_error(throw(S.oops)[0], S.caught, S.fine) == [S.caught]
    assert m.fn.if_error(42, S.caught, S.fine) == [S.fine]
    thrown = S.Error(S.throw(S.oops), S.oops)
    assert m.fn["return-on-error"](thrown, S.carried_on) == [S["return"](thrown)]
    assert m.fn["return-on-error"](42, S.carried_on) == [S.carried_on]

    # A reason that is ALREADY an error passes through unchanged rather than
    # being wrapped twice, so rethrowing does not bury the original cause.
    inner = S.Error(S.inner(1), S.because)
    assert throw(inner) == [inner]
    assert throw(throw(S.first)[0]) == [S.Error(S.throw(S.first), S.first)]

    # It travels out of a function the way any answer does, so a guard clause
    # is an ordinary equation.
    @m.define
    def half(n):
        # (= (half $n) (if (== (% $n 2) 0) (/ $n 2) (throw (odd $n))))
        return fn.truediv(n, 2) if fn.eq(fn.mod(n, 2), 0) else fn.throw(S.odd(n))

    assert m.fn.half(10) == [5]
    odd = S.Error(S.throw(S.odd(7)), S.odd(7))
    assert m.fn.half(7) == [odd]
    assert m.fn.if_error(odd, S.refused, 0) == [S.refused]

    # `trace!` prints its first argument and answers its SECOND, so it drops
    # into the middle of an expression without changing what flows through.
    assert trace(G("the answer"), 42) == [42]
    traced = S["trace!"](G("adding one to"), 41)  # rung: trace! answers its SUBJECT, which print() cannot
    assert m.answers(1 + traced) == [42]
    assert trace(m.fn.half(10)[0], m.fn.half(10)[0]) == [5]

    # Both arguments are held, so the label can be any atom and is written as
    # the program spelled it.
    assert trace(S.checking(S.odd(7)), S.ok) == [S.ok]


#: MEASURED on this branch rather than inherited: this twin is new, so there is
#: no earlier pin to move
#: [measured 2026-09-07: 16351 inferences, 1.1505x the example's 14212; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3;
#: fixture=docs/every-atom-has-an-example at its example commits; commit=98397cdd04679cbf40b2d515076dadc09c1b0a32].
#: RE-PINNED 2026-09-08, 16351 to 16411 (+60), the merges between this lane's
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
#: RE-PINNED 2026-09-08, 16411 to 16351 (-60), metta_substitute_self/3 probes
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
#: RE-PINNED 2026-09-08, 16351 to 16292 (-59), the evaluation-fuel scope marker
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
#: RE-PINNED 2026-09-08, 16292 to 16311 (+19), boot content moved: the refusal
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
#: RE-PINNED 2026-09-08, 16292 to 16650 (+358), The engine and library
#: predicates now resolve through their owning modules and the explicit engine
#: facade; compiled program lookup crosses the added metta_engine tier
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=ede2ac57e213a0d4502c6bbbca6227f97015b720].
#: RE-PINNED 2026-09-08, 16650 to 16660 (+10), The engine and library module
#: boundaries retain explicit lookup owners, including host registration and
#: returned callback goals [measured 2026-09-08: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=ede2ac57e213a0d4502c6bbbca6227f97015b720].
#: RE-PINNED 2026-09-08, 16660 to 16873 (+213), the module boundary merged with
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
#: RE-PINNED 2026-09-09, 16873 to 16867 (-6), Compile shipped typing decisions
#: and initial vocabulary facts, index vocabulary membership, and reuse the
#: first Python variable binding before indexing additional names; retain type,
#: transaction and variable-identity checks [measured 2026-09-09: min-of-3
#: serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=32650f9ff4d1c4aa0749d8eb8b153e5bb448ee5c].
BUDGET = 16867
