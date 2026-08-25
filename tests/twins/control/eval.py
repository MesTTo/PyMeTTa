"""Purpose: examples/control/eval.metta in Python: reading a body, then running it.

A `match` over the space answers a definition's BODY as data; it does not
interpret what it answers. Running the body is a second and separate act, and
in Python the two acts are two doors: the query door answers rows, and the
evaluation door takes the atom out of one and reduces it.

Both equations are compiled. `f` is an ordinary computation. `evalCustom`
writes to a space from inside an equation, which is the thing a compiled body
has no spelling for: `space += atom` is a Python STATEMENT over a handle, and
a body is pure atoms, so the write is the head itself over `(context-space)`,
the space the equation is running in. The statement spelling does not merely
refuse there, it MISCOMPILES to arithmetic, which is why naming the head is
the right rung and not a shortcut [measured 2026-08-24: `space += atom` inside
a compiled body stores `(+ $space $atom)` and writes nothing; commit=028b41a056cfd706e516cd0b945cbf69ac066da7].
That stays filed against control/and_then_or_else.metta, where the space is
neither a parameter nor the context space and so cannot be reached at all.
Guarantees:
  - every ordered atom assembled in this file passes one iterable to
    Expression [tested: test_expression_assembles_one_ordered_atom_from_an_iterable; commit=028b41a056cfd706e516cd0b945cbf69ac066da7]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import Expression, S, V, equation, fn

#: PLACEHOLDER, never measured in this worktree: the integrator's single
#: re-pin pass prices the whole corpus under the lane's own protocol after the
#: wave merges [assumed: BUDGET states no measured cost; commit=028b41a056cfd706e516cd0b945cbf69ac066da7].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 43959 to 43986, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (petta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 43986 to 43922, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 43922 to 43897, on the release tree:
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
#: ENVELOPED 2026-08-25 by the observe pass: this twin's count is
#: intrinsically multi-valued (allocation-timing jitter moves GC
#: work between runs; ten serial runs of one such twin answered six
#: distinct counts), so a point pin with the +-4 tolerance is a
#: false claim here. Bounds are the exact extrema of 10
#: full-lane observations under 'full-lane/218/workers=32'; a cost outside them
#: is a real finding, and a new mode discovered later extends the
#: envelope with its observation count rather than widening blind.
BUDGET = {
    # Widened to 43873..43929 by a second ten-round full-lane
    # observe pass; observations count both passes.
    "minimum": 43873,
    "maximum": 43929,
    "observations": 20,
    "protocol": "full-lane/218/workers=32",
}


def twin(m):
    """Read a specialised body out of the space, then evaluate it."""
    @m.define
    def f(li, a, b):
        # (= (f $L $a $b) (let $result (+ $a $b) (append ($result) $L)))
        result = a + b
        return fn.append((result,), li)

    # !(test (let $fbody_specialized (match &self (= (f (42) 40.7 2) $x) $x)
    #          (eval $fbody_specialized))
    #        (42.7 42))
    bodies = m[equation(S.f((42,), 40.7, 2)).to(V.x)]
    assert m.eval(bodies.x[0]) == [Expression((42.7, 42))]

    @m.define(name="evalCustom")
    def eval_custom(body):
        # (= (evalCustom $body)
        #    (let* (($a   (add-atom &self (= (myfunc) $body)))
        #           ($res (reduce (myfunc)))
        #           ($r   (remove-atom &self (= (myfunc) $body))))
        #          $res))
        # The top rung is the write door itself, as a body statement:
        #     here = S.context_space()
        #     here += equation(S.myfunc()).to(body)
        # A compiled body is pure atoms, so `+=` and `equation(...)` have no
        # image there; worse, `+=` COMPILES, to `(+ $here $atom)`, and stores
        # nothing. Residue: P14.4.
        _a = S.add_atom(S.context_space(), S["="](S.myfunc(), body))  # rung: `space += atom` is a Python statement over a handle, and a compiled body is pure atoms
        res = S.reduce(S.myfunc())
        _r = S.remove_atom(S.context_space(), S["="](S.myfunc(), body))  # rung: `space -= atom` the same way
        return res

    # !(test (evalCustom (match &self (= (f (42) 40.7 2) $x) $x))
    #        (42.7 42))
    assert eval_custom(bodies.x[0]) == [Expression((42.7, 42))]
