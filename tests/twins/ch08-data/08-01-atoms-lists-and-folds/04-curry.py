"""Purpose: examples/ch08-data/08-01-atoms-lists-and-folds/04-curry.metta in Python: too few arguments, and too many.

Calling a function with FEWER arguments than it takes answers a partial
application, which prints as `(partial f (1))` and can be called again later.
Calling one with too many is an error, and the error is an ANSWER: nothing
catches it and the form after it still runs.

Four of the five definitions are ordinary Python functions. `h` names the
engine's `append` through the static function namespace, `fn.append`, and
passes `(a,)`, a one-element Python tuple, which is the one-element expression
`($A)` the original writes. `show` names the engine's own `repr` the same way:
Python's builtin `repr` is bridged into a compiled body as `py-repr`, so
`fn.repr` is what stores the equation the original stores.

`map-atom` dissolves the way the table says: a comprehension builds the three
applications and ONE evaluation runs them, which is the crossing rule as well
as the spelling, since applying a partial per element from Python would cross
three times.

Two spellings Python's operators cannot give. A PARTIAL application of an
operator, `(+ 1)`, has no operator spelling, because `+` needs both operands
to be an operator at all; it is written by CALLING the symbol, `S.add(1)`,
which is what builds an expression out of a head and its arguments. And
`(+ 1 2 3)` is the same story from the other side, because Python's
`1 + 2 + 3` left-associates into `(+ (+ 1 2) 3)` and would compute 6 before
the engine saw anything.

`overloaded-curry` is two STACKED clauses of different arity under one name,
which the decorator dispatches independently. The first Python name reaches
`overloaded-curry` through the naming ladder's own underscore map; the second
cannot, because `overloaded_curry_3` would map to a different head, so that
one door states the exact name.
Guarantees:
  - expected printed output in this twin remains Python str text
    [tested: test_printing_text_is_not_forced_through_the_value_carrier;
    commit=d4e4f9cf0500c00c8f1201a60cbcf54de7c3fa84]
  - every ordered atom assembled in this file passes one iterable to
    Expression [tested: test_expression_assembles_one_ordered_atom_from_an_iterable;
    commit=d4e4f9cf0500c00c8f1201a60cbcf54de7c3fa84]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import Expression, S, fn


def twin(m):
    """Apply four functions with too few arguments, and three with too many."""

    @m.define
    def f(a, b):
        # (= (f $a $b) (+ $a $b))
        return a + b

    @m.define
    def g(a, b, c):
        # (= (g $a $b $c) (+ $c (+ $a $b)))
        return c + (a + b)

    @m.define
    def show():
        # (= (show) (repr (f 1)))
        return fn.repr(f(1))

    assert m.fn.repr(S.f(1)) == ["(partial f (1))"]
    assert m.eval((S.f(1), 2)) == [3]
    assert m.fn.repr(S.g(1, 2)) == ["(partial g (1 2))"]

    @m.define
    def h(a, b):
        # (= (h $A $B) (append ($A) $B))
        return fn.append((a,), b)

    assert m.eval((S.h(42), (1, 2, 3))) == [Expression((42, 1, 2, 3))]
    assert m.fn.repr(S.h(42)) == ["(partial h (42))"]

    # (map-atom (1 2 3) (+ 1)): a comprehension builds the applications and
    # one evaluation runs them.
    add_one = S.add(1)
    assert m.eval(tuple((add_one, x) for x in (1, 2, 3))) == [Expression((2, 3, 4))]

    # Too many arguments are an error, both for compiled and for
    # runtime-dispatched calls, and the error is an ANSWER: no catch stands
    # between the call and it. A head nothing TYPES is left as written
    # instead, because there is no arity to be wrong about.
    too_many = S.add(1, 2, 3)
    wrong_count = S.Error(too_many, S.IncorrectNumberOfArguments)
    assert m.eval(too_many) == [wrong_count]
    assert m.eval(S.reduce(too_many)) == [wrong_count]
    assert m.eval(S.empty(1, 2)) == [S.empty(1, 2)]

    # A gap between overloaded arities is still a valid partial application.
    # (= (overloaded-curry $a) $a)
    @m.define
    def overloaded_curry(a):
        return a

    # (= (overloaded-curry $a $b $c) (+ $a (+ $b $c)))
    @m.define(name="overloaded-curry")
    def overloaded_curry_3(a, b, c):
        return a + (b + c)

    assert m.fn.repr(S.overloaded_curry(1, 2)) == [
        "(partial overloaded-curry (1 2))"
    ]


#: Inferences this twin spends, its own tripwire.
#: PLACEHOLDER for the twins wave: every budget in the corpus is 1 here and
#: the integrator's single re-pin pass prices them all on the merged tree, so
#: a figure measured in this worktree would price a tree that never ships
#: [assumed: unmeasured here, deliberately; commit=d4e4f9cf0500c00c8f1201a60cbcf54de7c3fa84].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 25258 to 25372, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 25372 to 25383, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 25383 to 25325, on the release tree:
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
#: RE-PINNED 2026-08-25, 25325 to 25335, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 25335 to 27005 (+1670), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python bindings/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-08-26, 27005 to 27027 (+22), on the composed
#: async-scheduler tree: a live operation call pays the six-inference
#: admission probe the baseline's p14_async_scheduler_comment prices,
#: and the scheduler, context-callback and exact-memo lifecycle clauses
#: move compiled-image layout by tens, the class this file's chain
#: documents [measured: min-of-3 serial fresh processes; command=python bindings/python/tools/twin_coverage.py --measure --rounds 3; fixture=merged p14-audit-async composed tree with engine/reader.so; commit=5059173b1767600ce4df0f6b7841d88116ee62d3].
#: RE-PINNED 2026-08-26, 27027 to 25580 (-1447), by the specializer
#: argument-walk fix this file's own chain named as the follow-up.
#: Planning a specialization grafts a call argument onto the equation's
#: head pattern one position at a time, and that walk metacalled a yall
#: lambda per position, so each fresh process paid '>>'/4's one-time
#: resolution wherever its first binding plan landed and 13 further
#: inferences at every later position. The walk is first-order now, at
#: 4.0 inferences per position against 17.0. [measured: two independent full-lane rounds on this tree agreeing exactly, against one on the unchanged tree and one on the same tree plus an inert never-called clause; command=python bindings/python/tools/twin_coverage.py; fixture=p14-specializer-tax off 694c12f7 with engine/reader.so and the MORK backend; commit=7e7cac85fee08c117032b2efa5a58a40f3b21365].
BUDGET = 25580
