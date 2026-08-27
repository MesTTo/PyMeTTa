"""Purpose: examples/ch04-spaces-and-matching/04-02-patterns-and-bindings/07-unify.metta in Python: the matching conditional.

`(unify a b then else)` runs the then branch once per binding set under which
a and b match, and the else branch exactly when no binding set exists. The
operands cross unevaluated, all four arguments are typed Atom, and only the
selected branch runs.

`metta.unify` carries both ruled acts. At two arguments it symmetrically
answers bindings over atoms Python already holds. At four arguments it
evaluates the engine conditional in expression position, and a compiled body
lowers the same call directly. A stored marker is asked for with `in`, which
IS match containment, and the space operand is the handle itself, because a
space is a grounded atom and no symbol names it.

Both marker probes are compiled definitions that write from inside their own
equations, over `(context-space)`, which is the space the equation runs in. A
third compiled definition calls four-argument `unify` directly so that the
compiler lowers the conditional rather than executing it while defining the
function. The markers stored are the example's own bare symbols. The Python
write door still refuses one, `m.add(S.then_ran)` answering "a stored atom is a
non-empty expression", where the engine's `add-atom` takes it; the two doors
disagreeing is filed as residue against P14.10.
Guarantees:
  - every ordered atom assembled in this file passes one iterable to
    Expression [tested: test_expression_assembles_one_ordered_atom_from_an_iterable; commit=028b41a056cfd706e516cd0b945cbf69ac066da7]
  - four-argument unify is called directly at expression position and lowers
    from a compiled body [tested: bindings/python/tools/twin_coverage.py
    examples/ch04-spaces-and-matching/04-02-patterns-and-bindings/07-unify.metta; commit=6917bef7ca902671999eafcae3a7a86db8f69723]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import Expression, S, V, ground, unify

#: The two strings the ground decisions compare, carried whole.
STRING_X, STRING_Y = ground("x"), ground("y")


def twin(m):
    """Match ground terms, terms with variables, and a space."""
    # Ground decisions, including numeric promotion: 1 matches 1.0.
    # !(test (unify 1 1 same different) same)
    assert unify(1, 1, S.same, S.different) == [S.same]
    # !(test (unify 1 2 same different) different)
    assert m.eval(S.unify(1, 2, S.same, S.different)) == [S.different]
    # !(test (unify 1 1.0 same different) same)
    assert m.eval(S.unify(1, 1.0, S.same, S.different)) == [S.same]
    # !(test (unify "x" "x" same different) same)
    assert m.eval(S.unify(STRING_X, STRING_X, S.same, S.different)) == [S.same]
    # !(test (unify "x" "y" same different) different)
    assert m.eval(S.unify(STRING_X, STRING_Y, S.same, S.different)) == [S.different]

    # Bindings flow from the match into the branch, both directions at once.
    # !(test (unify (f $x b) (f a $y) (pair $x $y) nope) (pair a b))
    both = S.unify(S.f(V.x, S.b), S.f(S.a, V.y), S.pair(V.x, V.y), S.nope)
    assert m.eval(both) == [S.pair(S.a, S.b)]

    # The occurs check rejects a cyclic binding.
    # !(test (unify $x (f $x) cyclic sound) sound)
    assert m.eval(S.unify(V.x, S.f(V.x), S.cyclic, S.sound)) == [S.sound]

    @m.define
    def then_probe():
        return S.chain(S.add_atom(S.context_space(), S.then_ran), V._, 3)

    @m.define
    def else_probe():
        return S.chain(S.add_atom(S.context_space(), S.else_ran), V._, 4)

    @m.define
    def probe(left, right):
        return unify(left, right, S.then_probe(), S.else_probe())

    # Only the selected branch evaluates: each probe leaves a marker, and
    # exactly one marker lands per query.
    # !(test (unify A A (then-probe) (else-probe)) 3)
    assert probe(S.A, S.A) == [3]
    # !(test (collapse (match &self else-ran hit)) ())
    assert S.else_ran not in m
    # !(test (unify A B (then-probe) (else-probe)) 4)
    assert probe(S.A, S.B) == [4]
    # !(test (collapse (match &self then-ran hit)) (hit))
    assert S.then_ran in m

    # A space is a grounded atom whose custom matching is query, so a space
    # operand routes through match: one then-answer per stored match, the
    # else branch when nothing matches.
    # (friend Bob Alice) (friend Sam Alice)
    m += S.friend(S.Bob, S.Alice)
    m += S.friend(S.Sam, S.Alice)

    # !(test (collapse (unify &self (friend $who Alice) $who no-friends)) (Bob Sam))
    assert m.eval(S.unify(m, S.friend(V.who, S.Alice), V.who, S.no_friends)) == [S.Bob, S.Sam]
    # !(test (unify &self (friend Pol $who) $who no-friends) no-friends)
    assert m.eval(S.unify(m, S.friend(S.Pol, V.who), V.who, S.no_friends)) == [S.no_friends]

    # A variable operand binds the space whole without querying it.
    # !(test (unify $s &self bound queried) bound)
    assert m.eval(S.unify(V.s, m, S.bound, S.queried)) == [S.bound]

    # Empty in a branch is the branch remover: the else here answers nothing
    # at all, so the collapse is the empty expression. The collapsing has to
    # happen in the ENGINE, because `Empty` is what the branch answers and it
    # is the collapse that drops it [re-measured 2026-08-24: `m.eval` of the
    # unify answers `[Empty]` and `Expression(...)` over that is `(Empty)`,
    # where collapsing it first answers `()`; commit=028b41a056cfd706e516cd0b945cbf69ac066da7].
    # !(test (collapse (unify a b then Empty)) ())
    removed = S.unify(S.a, S.b, S.then, S.Empty)
    assert m.eval(S.collapse(removed)) == [Expression(())]  # rung: `collapse` is what drops the Empty marker, and a Python list does not


#: PLACEHOLDER, never measured in this worktree: the integrator's single
#: re-pin pass prices the whole corpus under the lane's own protocol after the
#: wave merges [assumed: BUDGET states no measured cost; commit=028b41a056cfd706e516cd0b945cbf69ac066da7].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 12208 to 12216, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 12216 to 12181, on the release tree:
#: the typed-dispatch question moved engine-side
#: (metta_typed_dispatch_applies/2, one extra frame per direct
#: call), the conformance kit gained the family, source and
#: round-trip laws, extensions gained the spaces([...]) readying
#: moment, and any boot-content change also moves counts a few
#: tens through SWI's clause-indexing shape (qlf_boot.pl's header
#: carries the A/B), so the corpus re-pins once on the exact
#: shipping tree [measured 2026-08-25 through
#: tools/twin_coverage.py --measure min-of-3 after a canonical
#: single-boot QLF regeneration].
#: RE-PINNED 2026-08-25, 12181 to 12186, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 12186 to 13701: the twin now exercises the public
#: expression-position four-argument `unify`, compiles the same spelling in a
#: function body, and mirrors both effectful branch definitions as matchable
#: equations; those required engine crossings replace the old term-only calls
#: [measured: 13701 inferences; command=python
#: bindings/python/tools/twin_coverage.py --measure --rounds 3
#: examples/ch04-spaces-and-matching/04-02-patterns-and-bindings/07-unify.metta; fixture=minimum of three serial runs;
#: commit=6917bef7ca902671999eafcae3a7a86db8f69723].
#: RE-PINNED 2026-08-26, 13701 to 13897 (+196), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python bindings/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-08-26, 13897 to 13917 (+20), on the composed
#: async-scheduler tree: a live operation call pays the six-inference
#: admission probe the baseline's p14_async_scheduler_comment prices,
#: and the scheduler, context-callback and exact-memo lifecycle clauses
#: move compiled-image layout by tens, the class this file's chain
#: documents [measured: min-of-3 serial fresh processes; command=python bindings/python/tools/twin_coverage.py --measure --rounds 3; fixture=merged p14-audit-async composed tree with engine/reader.so; commit=5059173b1767600ce4df0f6b7841d88116ee62d3].
BUDGET = 13917
