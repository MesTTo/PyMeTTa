"""Purpose: examples/ch09-types/12-types_dependent.metta in Python: a type computed by a program.

`get-type` is an ordinary function, so a program may add equations to it, and
these two compute a type from the VALUE: an even number is an `EvenNumber`, and
an expression of them is an `EvenNumberList`. The declared parameter types of
`f` and `g` then accept arguments nothing declared, because the computed
answer is what the check reads.

Both extensions land as the equations they are, because the head IS `get-type`
and no `@m.define` may name a function the space already answers. The first has
a plain variable head, so it goes through the write door as one atom; the
second's head is the STRUCTURE `(cons $head $tail)`, which is what `@m.rules`
is for. `EvenNumber` and `EvenNumberList` are Python classes so that `f` and
`g` say their signatures as annotations.

The comparison is `=alpha` and not `==` throughout, for the example's own
reason: each comparison crosses KNOWN and different types, which `==` refuses
by name, and `=alpha` is the comparison that takes anything. Because its Atom
parameters hold their operands, each computed value is named by `let` before
the comparison receives it.
[source: examples/ch09-types/12-types_dependent.metta:6; commit=f053d9d46aa43b9beec360eae30b9016ffbf231f]
"""

from metta import UNIT, Expression, S, V, equation, fn, if_


class EvenNumber:
    """The computed type of an even number, named for `f`'s signature."""


class EvenNumberList:
    """The computed type of an expression of even numbers."""


def twin(m):
    """Teach get-type two new answers, then use them as declared types."""
    alpha, kind = fn["=alpha"], fn.get_type

    # The body is a ONE-ARMED if, the filtering form that answers nothing
    # where its condition fails, which `if_` takes beside the three-armed
    # conditional. `%` on an atom builds the term Python's own operator means.
    # (= (get-type $x)
    #    (catch (let $remainder (% $x 2)
    #             (if (=alpha $remainder 0) EvenNumber))))
    m += equation(kind(V.x)).to(
        fn.catch(
            S.let(  # rung: this stored equation has no Python statement position for assignment
                V.remainder,
                V.x % 2,
                if_(alpha(V.remainder, 0), S.EvenNumber),
            )
        )
    )

    @m.define
    def f(x: EvenNumber, y: EvenNumber) -> EvenNumber:
        """(: f (-> EvenNumber EvenNumber EvenNumber)), (= (f $x $y) (+ $x $y))."""
        return x + y

    # !(test (f 2 4) 6)
    assert f(2, 4) == [6]

    @m.rules
    def walk(head, tail):
        """The structured second clause: a list of even numbers, elementwise."""
        # (= (get-type (cons $head $tail))
        #    (let $head-type (get-type $head)
        #      (if (=alpha $head-type EvenNumber)
        #          (if (=alpha $tail ()) EvenNumberList (get-type $tail)))))
        yield equation(kind(S.cons(head, tail))).to(
            S.let(  # rung: this rules generator builds the stored let where no Python statement position exists
                V.head_type,
                kind(head),
                if_(
                    alpha(V.head_type, S.EvenNumber),
                    if_(alpha(tail, UNIT), S.EvenNumberList, kind(tail)),
                ),
            )
        )

    @m.define
    def g(items: EvenNumberList) -> bool:  # noqa: ARG001  -- the parameter is what the signature declares; the body answers a constant
        """(: g (-> EvenNumberList Bool)), (= (g $L) True)."""
        return True

    # !(test (g (2 4 6)) True)
    assert g(Expression((2, 4, 6))) == [True]


#: Inferences this twin spends, its own tripwire. A PLACEHOLDER: the wave's
#: integrator prices all 218 budgets in one pass on the merged tree, so no
#: figure measured in a single agent's worktree is pinned here
#: [assumed: 1 is a placeholder rather than a measurement; commit=e4c861a8c9e8e42b9e5ecb90d9ebf92a946e0163].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 27827 to 28730, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 28730 to 28741, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 28741 to 28671, on the release tree:
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
#: RE-PINNED 2026-08-25, 28671 to 28789, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 28789 to 30341 (+1552), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-08-26, 30341 to 30363 (+22), on the composed
#: async-scheduler tree: a live operation call pays the six-inference
#: admission probe the baseline's p14_async_scheduler_comment prices,
#: and the scheduler, context-callback and exact-memo lifecycle clauses
#: move compiled-image layout by tens, the class this file's chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=merged p14-audit-async composed tree with engine/reader.so; commit=5059173b1767600ce4df0f6b7841d88116ee62d3].
#: RE-PINNED 2026-08-26, 30363 to 28923 (-1440), by the specializer
#: argument-walk fix this file's own chain named as the follow-up.
#: Planning a specialization grafts a call argument onto the equation's
#: head pattern one position at a time, and that walk metacalled a yall
#: lambda per position, so each fresh process paid '>>'/4's one-time
#: resolution wherever its first binding plan landed and 13 further
#: inferences at every later position. The walk is first-order now, at
#: 4.0 inferences per position against 17.0. [measured: two independent full-lane rounds on this tree agreeing exactly, against one on the unchanged tree and one on the same tree plus an inert never-called clause; command=python extensions/python/tools/twin_coverage.py; fixture=p14-specializer-tax off 694c12f7 with engine/reader.so and the MORK backend; commit=7e7cac85fee08c117032b2efa5a58a40f3b21365].
BUDGET = 28923
