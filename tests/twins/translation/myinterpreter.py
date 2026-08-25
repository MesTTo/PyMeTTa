"""examples/translation/myinterpreter.metta in Python: an interpreter in three lines.

A parameter typed `Atom` receives its argument UNREDUCED, so `myinterpreter`
gets the `(if ...)` term itself and decides when to evaluate it. That is the
whole of MeTTa's quoting story: laziness is declared by the callee, not spelled
at the call site, and the declaration is Python's own annotation. `-> Any` is
the unconstrained result type, so the pair of them is the example's
`(: myinterpreter (-> Atom %Undefined%))` said in Python.

The body compiles too. Announcing the code is `println!` reached at the
function namespace, whose bang the resolver supplies, and the original's `let`
around it is a Python assignment to a name it then ignores. The string is a
MeTTa string literal, because a compiled body's constants are what the stored
equation holds.

Which is why the two `if` terms below are DATA. They are handed to an
Atom-typed parameter and never run as control flow, so the keyword builder is
their spelling: `if_` has the arity the engine's `if` has, and `S.eq` is `==`
at the word door.
"""

from typing import Any

from metta import Atom, S, fn, if_

#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-24: unpriced placeholder, re-pinned by the
#: integrator; commit=8fd49997be43f7909c3582062138c5011df7e811].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 12397 to 12433, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (petta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 12433 to 12446, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 12446 to 12376, on the release tree:
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
BUDGET = 12376


def twin(m):
    """Define an interpreter, then hand it two branches to interpret."""

    @m.define
    def myinterpreter(code: Atom) -> Any:
        # (= (myinterpreter $code)
        #    (let $temp (println! ("Runtime-interpreting code" $code)) (eval $code)))
        _said = fn.println(("Runtime-interpreting code", code))
        return S.eval(code)

    @m.define
    def w():                                   # (= (w) 42)
        return 42

    @m.define
    def v():                                   # (= (v) 43)
        return 43

    assert myinterpreter(if_(S.eq(1, 1), S.w(), S.v())) == [42]   # [42]
    assert myinterpreter(if_(S.eq(1, 2), S.w(), S.v())) == [43]   # [43]
