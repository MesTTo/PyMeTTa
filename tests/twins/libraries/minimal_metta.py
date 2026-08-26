"""Purpose: examples/libraries/minimal_metta.metta in Python: the instruction set, run.

Twenty-eight claims about minimal MeTTa's own instructions: `function` and
`return`, the `unify-mod` matcher, the recursive `mm-switch`, the reduction
loop, `collapse-bind` and `superpose-bind`, the Turing machine, and the partial
function. All of them are the file's subject, so all of them are named.

Each instruction is CALLED, `m.fn.function(...)` and `m.fn.unify_mod(...)`,
and most of them carry a MeTTa variable in an argument, because that is what
an instruction set is made of: `(chain (+ 1 2) $x (return $x))` binds `$x`,
`(unify-mod (p 5) (p $x) (got $x) else)` matches it, `(mm-reduce (step-down 3)
$x $x)` templates it. A call answers what the instruction reduced to whether
or not its arguments carry variables, so the call door says all of them.

Three claims keep a composed term instead, and each names its reason on the
line. `collapse` is one: at the call door `mm-switch` with no matching case
answers the `Empty` atom, where `(collapse ...)` is what PRUNES it, so
`list()` would collect an answer the engine does not give. `return` is the
other: it is an instruction inside `function` rather than a function of its
own, so the namespace has nothing to resolve. The partial-function refusal is
also collapsed because `Empty` means no answer, making the empty answer set the
claim rather than the literal marker.
[source: examples/libraries/minimal_metta.metta:125; commit=f053d9d46aa43b9beec360eae30b9016ffbf231f]

Every name here descends the ladder exactly as far as it has to. Hyphenated
heads take the attribute door, `S.mm_switch` and `S.collapse_bind`, because
rung 4's map is total. The bracket is kept only for what Python's grammar
cannot say: the keywords `return` and `else`, the punctuation heads `:=`,
`...` and `<-`, and `minimal_metta_lib`, whose MeTTa name really does have
underscores.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import FALSE, TRUE, Expression, S, V, equation, lib


def twin(m):
    """Run the minimal evaluator, binding carrier, reducer, and machine."""
    m += lib["minimal_metta_lib"]

    assert m.fn.function(S["return"](42)) == [42]
    # The chain binder receives the WRITTEN atom at this instruction
    # boundary: LeaTTa 9ea9f9d answers the exact form with (+ 1 2), not 3,
    # which is the example's own noeval-pinned row.
    assert m.fn.function(S.chain(S.add(1, 2), V.x, S["return"](V.x))) == [
        S.add(1, 2)
    ]

    returned = S["return"](7)
    assert m.eval(returned) == [returned]  # rung: `return` is an instruction of `function`, not a function of its own

    failed_body = S.foo(S.bar)
    # The diagnostic carries the ORIGINAL function frame, not the bare
    # body: LeaTTa 9ea9f9d answers this exact form the same way.
    assert m.fn.function(failed_body) == [
        S.Error(S.function(failed_body), S.NoReturn)
    ]

    otherwise = S["else"]
    assert m.fn.unify_mod(V.a, S.Empty, S.then, otherwise) == [S.then]
    assert m.fn.unify_mod(V.a, S[":="](S.Empty), S.then, otherwise) == [otherwise]
    assert m.fn.unify_mod(
        S[":="](S.a, S.b), S[":="](V.x, V.y), S.then, otherwise
    ) == [S.then]
    assert m.fn.unify_mod(
        (S.A, S.B, S.C, S.D, S.E),
        (S.A, S["..."], S.D, S["..."]),
        S.matched,
        S.nomatch,
    ) == [S.matched]
    assert m.fn.unify_mod(S.p(5), S.p(V.x), S.got(V.x), otherwise) == [S.got(5)]

    cases = ((1, S.one), (2, S.two))
    assert m.fn.mm_switch(1, cases) == [S.one]
    assert m.fn.mm_switch(2, cases) == [S.two]
    assert m.fn.mm_switch(S.p(5), ((S.p(V.x), S.got(V.x)),)) == [S.got(5)]

    # No case matches, so the switch answers Empty and the collapse prunes it.
    unmatched = S.mm_switch(9, cases)
    assert m.eval(S.collapse(unmatched)) == [Expression(())]  # rung: `collapse` is what drops the Empty marker, and a Python list does not

    @m.define
    def step_down(n):
        # (= (step-down $n) (if (> $n 0) (step-down (- $n 1)) done))
        return step_down(n - 1) if n > 0 else S.done

    # The reduction loop is HANDED the call rather than making it, so these two
    # write `S.step_down(3)`: calling the Symbol builds where calling the
    # definition would evaluate.
    assert m.fn.mm_reduce(S.step_down(3), V.x, V.x) == [S.done]
    assert m.fn.mm_reduce(S.step_down(3), V.x, S.wrapped(V.x)) == [S.wrapped(S.done)]
    assert m.fn.mm_reduce(S.add(1, 2), V.y, V.y) == [3]

    m += S.edge(S.a, S.b)
    m += S.edge(S.a, S.c)
    matched_edges = S.match(m, S.edge(S.a, V.y), S.found(V.y))  # rung: match's space is an ARGUMENT of the instruction under test, and the whole term is what `collapse-bind` is handed
    rows = m.fn.collapse_bind(matched_edges).one()
    assert rows.alpha_eq(
        Expression((
            (S.found(S.b), S.bindings(S["<-"](V.v, S.b))),
            (S.found(S.c), S.bindings(S["<-"](V.v, S.c))),
        ))
    )
    assert m.fn.superpose_bind(rows) == [S.found(S.b), S.found(S.c)]

    restored = S.chain(
        S.collapse_bind(matched_edges),
        V.c,
        S.chain(S.superpose_bind(V.c), V.x, (V.x, V.y)),
    )
    assert m.eval(S.collapse(restored)) == [  # rung: `collapse` gathers the two answers into ONE atom, which the example's own claim compares against
        Expression(((S.found(S.b), S.b), (S.found(S.c), S.c)))
    ]

    m += equation(S.rule(S.S, 0)).to((S.S, 1, S.R))
    m += equation(S.rule(S.S, 1)).to((S.HALT, 1, S.N))

    assert m.fn.mm_tm(S.rule, S.S, ((), 1, ())) == [Expression(((), 1, ()))]
    assert m.fn.mm_tm(S.rule, S.S, ((), 0, (1,))) == [Expression(((1,), 1, ()))]
    assert m.fn.mm_tm(S.rule, S.S, ((), 0, (0, 0, 1))) == [
        Expression(((1, 1, 1), 1, ()))
    ]

    assert m.fn.mm_move(((), 0, (7,)), 1, S.R) == [Expression(((1,), 7, ()))]
    assert m.fn.mm_move(((9,), 0, ()), 1, S.L) == [Expression(((), 9, (1,)))]
    assert m.fn.mm_move(((), 0, ()), 1, S.R) == [Expression(((1,), 0, ()))]
    assert m.fn.mm_move(((1,), 0, (2,)), 9, S.N) == [Expression(((1,), 9, (2,)))]

    assert m.fn.if_partial(TRUE, S.yes) == [S.yes]
    assert m.eval(S.collapse(S.if_partial(FALSE, S.yes))) == [Expression(())]  # rung: collapse prunes Empty into one empty Expression; list() would materialise zero Python answers


#: A PLACEHOLDER, not a measurement. The twins wave re-authored this file and
#: the integrator prices every budget in one pass on the merged tree. This one
#: needs an EMPIRICAL ENVELOPE rather than a point: its cost moved across
#: 204 inferences over the concurrent lane's own observations, because
#: the shared engine's scheduling changes what a concurrent round costs
#: [assumed: this twin's inference cost is unmeasured on this branch;
#: commit=1e264c186c531e69acde5ad03ff6a79210626df4].
#: Until it is measured again, this file's own distribution-budget residue
#: entry, retired 2026-08-22 because the twin declared an envelope, is
#: unbacked: a point budget is not the envelope that retired it.
#: PRICED 2026-08-25 by the corpus pricing pass after the conformance
#: answer updates: tools/twin_coverage.py --measure min-of-3, identical
#: across two fresh rounds on p14-integration at the store-wave merge.
#: RE-PINNED 2026-08-25, 192201 to 192591, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (petta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 192591 to 192578, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 192578 to 192538, on the release tree:
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
#: RE-PINNED 2026-08-25, 192538 to 192540, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 192540 to 195143 (+2603), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python bindings/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-08-26, 195143 to 195133 (-10), at the tabling-seam
#: merge: compiled-image layout from the library's dispatch and
#: reflection clauses, the tens-scale class this file's chain documents
#: [measured: min-of-3 serial fresh processes; command=python
#: bindings/python/tools/twin_coverage.py --measure --rounds 3;
#: fixture=tabling-seam merged tree with engine/reader.so;
#: commit=694c12f70da25a28ffe22f9209f1d75d56921f93].
#: RE-PINNED 2026-08-26, 195133 to 192583 (-2550), by the specializer
#: argument-walk fix this file's own chain named as the follow-up.
#: Planning a specialization grafts a call argument onto the equation's
#: head pattern one position at a time, and that walk metacalled a yall
#: lambda per position, so each fresh process paid '>>'/4's one-time
#: resolution wherever its first binding plan landed and 13 further
#: inferences at every later position. The walk is first-order now, at
#: 4.0 inferences per position against 17.0. [measured: two independent full-lane rounds on this tree agreeing exactly, against one on the unchanged tree and one on the same tree plus an inert never-called clause; command=python bindings/python/tools/twin_coverage.py; fixture=p14-specializer-tax off 694c12f7 with engine/reader.so and the MORK backend; commit=7e7cac85fee08c117032b2efa5a58a40f3b21365].
BUDGET = 192583
