"""Purpose: examples/functions/lambda.metta in Python: two kinds of lambda.

The first kind is FAKE, and works in any MeTTa: `(lambda $var $body)` is
ordinary data that `apply` takes apart, substituting through `let` and then
evaluating. The second kind is real, `|->`, a first-class compiled function
that can be mapped over a list, applied directly, passed through a binding,
partially applied, and closed over a preceding binding.

Python's own `lambda` IS the second kind. Inside a compiled body it lowers
straight to `|->`, so `lambda a: 1 + a` stores `(|-> ($a) (+ 1 $a))`, and a
`lambda` that reads a name bound above it closes over that name exactly as the
original's `let*` does. Three of the seven claims are written that way.

What a compiled body will not do is apply a lambda WHERE IT STANDS: `(lambda
...)(arg)` is refused, "a compiled body calls a plain name". So the two forms
that apply an anonymous lambda immediately are built at the term door, where
`|->` is an ordinary head, and the two claims that only bind one are compiled.

`apply` takes the `@m.rules` shape of the definitional decorator, because its
HEAD is a pattern that takes `(lambda $var $body)` apart, which no parameter
list spells. `applyL1` and `applyL2` are ordinary decorated functions whose
bodies build lambda DATA holding `$x` and `$y`: those variables take their
meaning from `apply`'s substitution rather than from anything in scope, and
`V.x` is how a compiled body mints one.

Two operator spellings worth naming, both in the fold that is applied where
it stands. `(or (== 1 $e) $acc)` uses the public `or_` builder and `S.eq` word
table entry, because Python's `or` and `==` operators have host meanings.
Guarantees:
  - every ordered atom assembled in this file passes one iterable to
    Expression [tested: test_expression_assembles_one_ordered_atom_from_an_iterable;
    commit=d4e4f9cf0500c00c8f1201a60cbcf54de7c3fa84]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from typing import Any

from metta import FALSE, Atom, Expression, S, V, arrow, equation, fn, or_, typed

#: Inferences this twin spends, its own tripwire.
#: PLACEHOLDER for the twins wave: every budget in the corpus is 1 here and
#: the integrator's single re-pin pass prices them all on the merged tree, so
#: a figure measured in this worktree would price a tree that never ships
#: [assumed: unmeasured here, deliberately; commit=d4e4f9cf0500c00c8f1201a60cbcf54de7c3fa84].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 45349 to 45444, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (petta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 45444 to 45322, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 45322 to 45297, on the release tree:
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
#: RE-PINNED 2026-08-25, 45297 to 45270, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 45270 to 48408 (+3138), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python bindings/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
BUDGET = 48408


def twin(m):
    """Apply a lambda that is data, then five that are functions."""
    # (: apply (-> Atom %Undefined% %Undefined%))
    # rung: below the ANNOTATION door: the annotation door needs a decorated
    #   function, and `apply`'s head is a pattern (residue, P14.4)
    m += typed(S.apply, arrow(Atom, Any, Any))

    @m.rules
    def fake(var, body, arg):
        # (= (apply (lambda $var $body) $arg) (eval (let $var $arg $body)))
        yield equation(S.apply(S["lambda"](var, body), arg)).to(
            S.eval(S.let(var, arg, body))  # rung: let as substitution
        )

    # The MeTTa names are camel-cased and Python's are not, so `name=` carries
    # the example's own spelling and the Python side stays PEP 8.
    @m.define(name="applyL1")
    def apply_l1():
        # (= (applyL1) (apply (lambda $x (+ $x 1)) 2))
        return S.apply(S["lambda"](V.x, V.x + 1), 2)

    @m.define(name="applyL2")
    def apply_l2():
        # (= (applyL2) (apply (lambda ($x $y) (+ $x $y)) (2 7)))
        return S.apply(S["lambda"]((V.x, V.y), V.x + V.y), (2, 7))

    assert apply_l1() == [3]
    assert apply_l2() == [9]

    # A real lambda, mapped over a list: Python's own lambda IS `|->`.
    @m.define
    def increment_all(items):
        # (= (increment-all $items) (maplist (|-> ($a) (+ 1 $a)) $items))
        return fn.maplist(lambda a: 1 + a, items)

    assert increment_all((1, 2, 3)) == [Expression((2, 3, 4))]

    # Applied where it stands, which a compiled body will not do.
    folding = S["|->"]((V.acc, V.e), or_(S.eq(1, V.e), V.acc))
    assert m.eval((folding, FALSE, 1)) == [True]

    @m.define
    def myfunc(a, b):
        # (= (myfunc $a $b) (cons $a $b))
        return fn.cons(a, b)

    # A lambda over a PARTIAL application bound above it.
    @m.define
    def through_partial():
        # (let $f (myfunc 42) ((|-> ($x) ($f ($x 2 3))) 43))
        f = myfunc(42)
        g = lambda x: f((x, 2, 3))  # noqa: E731  -- the binding IS the point: it stores (|-> ($x) ...)
        return g(43)

    assert through_partial() == [Expression((42, 43, 2, 3))]

    # Partially applied: one argument now, the other later.
    assert m.eval(((S["|->"]((V.x, V.y), (42, V.x, V.y)), 43), 44)) == [
        Expression((42, 43, 44))
    ]

    @m.define
    def myfunc2(mylambda):
        # (= (myfunc2 $mylambda) ($mylambda 43 44))
        return mylambda(43, 44)

    # A lambda CLOSING over a binding above it, which is the original's let*.
    @m.define
    def closed():
        # (let* (($k 45) ($lambda (|-> ($x $y) (42 $x $y $k)))) (myfunc2 $lambda))
        k = 45
        return myfunc2(lambda x, y: (42, x, y, k))

    assert closed() == [Expression((42, 43, 44, 45))]
