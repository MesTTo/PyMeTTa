"""examples/ch07-control-flow/07-01-if-and-booleans/12-implication_and_unifiability.metta in Python: three questions about two atoms.

`implies` is the connective `and`, `or` and `not` leave out. `=?` asks
whether two atoms COULD be made equal without making them so, and
`if-equal2` asks whether they already agree up to a renaming: two different
questions, and the pair that separates them is `(f $x)` against `(f 1)`.

The four relations are a `@m.rules` bundle rather than stacked `@m.define`
clauses, because `age` and `registered?` each have two clauses that COEXIST
and a stacked define reads as first-match. `registered?` and `adult?` and
`may-vote?` carry a `?` Python cannot spell, so they come through the exact
subscript door, which is rung 5 and the one the ladder keeps for a head
outside identifier grammar.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import FALSE, TRUE, S, V, equation, fn


def twin(m):
    """Material implication, unifiability, and alpha-equivalence."""
    # Each handle is resolved ONCE: `m.fn[...]` asks the engine on every
    # access, about 1,200 inferences a name, which is most of a small twin.
    implies, unifiable = m.fn.implies, m.fn["=?"]
    renamed_or_not = m.fn.if_equal2

    # False implies anything, and only a true antecedent with a false
    # consequent is False.
    assert implies(FALSE, FALSE) == [True]
    assert implies(FALSE, TRUE) == [True]
    assert implies(TRUE, TRUE) == [True]
    assert implies(TRUE, FALSE) == [False]

    # Three bundles, one per relation, because `@m.rules` is the door for
    # equations that COEXIST: stacked `@m.define` clauses read as first-match,
    # which would make the second age and the second registration unreachable.
    @m.rules
    def ages():
        """(= (age ann) 30) and (= (age bo) 12)."""
        yield equation(S.age(S.ann)).to(30)
        yield equation(S.age(S.bo)).to(12)

    @m.rules
    def registrations():
        """(= (registered? ann) True) and (= (registered? bo) True)."""
        yield equation(S["registered?"](S.ann)).to(TRUE)
        yield equation(S["registered?"](S.bo)).to(TRUE)

    @m.rules
    def eligibility(person):
        """The guard shape "if this holds then that must too", written once."""
        # (= (adult? $p) (> (age $p) 17))
        yield equation(S["adult?"](person)).to(S.age(person).gt(17))
        # (= (may-vote? $p) (implies (registered? $p) (adult? $p)))
        yield equation(S["may-vote?"](person)).to(
            fn.implies(S["registered?"](person), S["adult?"](person))
        )

    # Resolved after the bundle, because a handle names a function that
    # exists.
    may_vote = m.fn["may-vote?"]
    assert may_vote(S.ann) == [True]
    assert may_vote(S.bo) == [False]

    # `=?` answers whether two atoms COULD be made equal, and binds neither.
    assert unifiable(S.f(V.x), S.f(1)) == [True]
    assert unifiable(S.f(2), S.f(1)) == [False]
    assert unifiable(V.a, V.b) == [True]
    assert unifiable(S.f(V.x), S.g(V.x)) == [False]

    # Nothing is bound, so the same variable answers True against two atoms
    # that cannot both be true of it.
    assert unifiable(S.f(V.x), S.f(1)) == [True] and unifiable(S.f(V.x), S.f(2)) == [True]

    # `if-equal2` is alpha-equivalence rather than unifiability.
    assert renamed_or_not(S.f(V.x), S.f(V.y), S.renamed, S.different) == [S.renamed]
    assert renamed_or_not(S.f(V.x), S.f(1), S.renamed, S.different) == [S.different]
    assert renamed_or_not(S.f(V.x, V.x), S.f(V.y, V.z), S.renamed, S.different) == [S.different]

    # So the two are genuinely different questions, and this is the pair that
    # separates them: (f $x) and (f 1) unify, and are not alpha-equivalent.
    assert unifiable(S.f(V.x), S.f(1)) == [True]
    assert renamed_or_not(S.f(V.x), S.f(1), S.renamed, S.different) == [S.different]


#: MEASURED on this branch rather than inherited: this twin is new, so there is
#: no earlier pin to move
#: [measured 2026-09-07: 12664 inferences, 0.7714x the example's 16417; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3;
#: fixture=docs/every-atom-has-an-example at its example commits; commit=98397cdd04679cbf40b2d515076dadc09c1b0a32].
#: RE-PINNED 2026-09-08, 12664 to 12801 (+137), the merges between this lane's
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
#: RE-PINNED 2026-09-08, 12801 to 12692 (-109), metta_substitute_self/3 probes
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
#: RE-PINNED 2026-09-08, 12692 to 12642 (-50), the evaluation-fuel scope marker
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
BUDGET = 12642
