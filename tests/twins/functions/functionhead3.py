"""Purpose: examples/functions/functionhead3.metta in Python: one constraint per argument.

`in` keeps a value only when it is a member of a list, and `myplus` chains one
constraint per argument, so the relation runs in BOTH directions: give it two
numbers and it filters, give it variables and it enumerates what is reachable.
The last form runs the whole relation backwards through a guard.

Both definitions are decorated Python functions, and both need the descent
ladder's bottom rung, each for its own reason. `in` is a Python KEYWORD, so no
Python function can carry that name: `name="in"` gives the equation the name
the example uses, and the decorated `is_in` object carries that exact MeTTa
head when another compiled body calls it. `is-member` is
an engine function whose spelling is hyphenated, and `fn.is_member` is its
mention door, rung 4's map applied at the factory.

The variables `myplus` chains over are holes rather than parameters, which
`V.x` and `V.y` say inside the body, and `S.let` names the relational `let`
Python's assignment does not reach.

A call answers what the relation reduces to, whether or not its arguments
carry variables, so running `myplus` backwards is the same Python line as
running it forwards; the bindings those variables took are the parallel row
face on the same view. `collapse` dissolves either way, because the view
already IS the list of answers. Only the last claim evaluates a term instead
of calling, because a `let`-as-guard has to wrap the call.
"""

from metta import TRUE, S, V, fn

#: Inferences this twin spends, its own tripwire.
#: PLACEHOLDER for the twins wave: every budget in the corpus is 1 here and
#: the integrator's single re-pin pass prices them all on the merged tree, so
#: a figure measured in this worktree would price a tree that never ships
#: [assumed: unmeasured here, deliberately; commit=d4e4f9cf0500c00c8f1201a60cbcf54de7c3fa84].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 16050 to 16107, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (petta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 16107 to 16115, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 16115 to 16086, on the release tree:
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
BUDGET = 16086


def twin(m):
    """Constrain both arguments and the result, then run it every way."""

    @m.define(name="in")
    def is_in(x, items):
        # (= (in $x $L) (let True (is-member $x $L) $x))
        return S.let(True, fn.is_member(x, items), x)  # noqa: FBT003  -- True is the ATOM the membership check answers, matched against, not a flag  # rung: let as a guard

    @m.define
    def myplus(a, b):
        # (= (myplus $A $B)
        #    (let $A (in $X (1 2 3))
        #      (let $B (in $Y (2 3))
        #        (in (+ $X $Y) (3 4 5)))))
        return S.let(  # rung: solve(pattern, subject) has no expression-position form inside a compiled body
            a,
            is_in(V.x, (1, 2, 3)),
            S.let(  # rung: solve(pattern, subject) has no expression-position form inside a compiled body
                b, is_in(V.y, (2, 3)), is_in(V.x + V.y, (3, 4, 5))
            ),
        )

    # fine:
    assert myplus(1, 3) == [4]
    # output out of range:
    assert myplus(3, 3) == []
    # input out of range:
    assert myplus(3, 4) == []
    # what can be reached when adding $X to 3:
    assert myplus(V.x, 3) == [4, 5]
    # what can be reached when adding $X to $Y:
    assert myplus(V.x, V.y) == [3, 4, 4, 5, 5]
    # with which $x added to 2 can we reach values above 3?
    guard = S.gt(S.myplus(V.x, 2), 3)
    assert m.eval(S.let(TRUE, guard, V.x)) == [2, 3]  # rung: let as a guard
