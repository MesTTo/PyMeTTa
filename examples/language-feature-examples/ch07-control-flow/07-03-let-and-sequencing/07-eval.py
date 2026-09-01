"""Purpose: examples/ch07-control-flow/07-03-let-and-sequencing/07-eval.metta in Python: reading a body, then running it.

A `match` over the space answers a definition's BODY as data; it does not
interpret what it answers. Running the body is a second and separate act, and
in Python the two acts are two doors: the query door answers rows, and the
evaluation door takes the atom out of one and reduces it.

Both equations are compiled. `f` is an ordinary computation. `evalCustom`
writes to the running space from inside an equation. A space-bound local now
takes `+=` as `add-atom`, but `-=` deliberately means the one-occurrence
`subtract-atom`; the source asks for the draining `remove-atom`. Naming both
heads therefore keeps the pair parallel while preserving the source's exact
removal grain [tested: test_augmented_assignment_on_a_space_is_the_write_door,
test_remove_atom_drains_every_occurrence; commit=e3787593132a7ece2d300397045f7415709847c9].

The stored equations are deliberately not source-identical. Assignment
lowers `f`'s `let` to a one-binding `let*`. `evalCustom` lowers the source's
multi-binding `let*` to nested one-binding `let*` forms and names the running
space as `(context-space)` instead of the source token `&self`. The digest
lane reports both equations. `f`'s annotations also publish
`(: f (-> %Undefined% Number Number %Undefined%))`.
Guarantees:
  - every ordered atom assembled in this file passes one iterable to
    Expression [tested: test_expression_assembles_one_ordered_atom_from_an_iterable; commit=028b41a056cfd706e516cd0b945cbf69ac066da7]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import Expression, S, V, equation, fn


def twin(m):
    """Read a specialised body out of the space, then evaluate it."""

    @m.define
    def f(li, a: float, b: int):
        # Source: (= (f $L $a $b) (let $result (+ $a $b) (append ($result) $L)))
        # Twin:   (= (f $L $a $b) (let* (($result (+ $a $b))) (append ($result) $L)))
        result = a + b
        return fn.append((result,), li)

    # !(test (let $fbody_specialized (match &self (= (f (42) 40.7 2) $x) $x)
    #          (eval $fbody_specialized))
    #        (42.7 42))
    bodies = m[equation(S.f((42,), 40.7, 2)).to(V.x)]
    assert m.eval(bodies.x[0]) == [Expression((42.7, 42))]

    @m.define(name="evalCustom")
    def eval_custom(body):
        # Source: (= (evalCustom $body)
        #    (let* (($a   (add-atom &self (= (myfunc) $body)))
        #           ($res (reduce (myfunc)))
        #           ($r   (remove-atom &self (= (myfunc) $body))))
        #          $res))
        # Twin: nested one-binding let* forms around add-atom, reduce, and
        # remove-atom, with (context-space) in both write calls.
        # Name the write heads because -= is the one-occurrence
        # subtract-atom door, while this source requires remove-atom's drain.
        _a = S.add_atom(S.context_space(), S["="](S.myfunc(), body))
        res = S.reduce(S.myfunc())
        _r = S.remove_atom(S.context_space(), S["="](S.myfunc(), body))
        return res

    # !(test (evalCustom (match &self (= (f (42) 40.7 2) $x) $x))
    #        (42.7 42))
    assert eval_custom(bodies.x[0]) == [Expression((42.7, 42))]


#: PLACEHOLDER, never measured in this worktree: the integrator's single
#: re-pin pass prices the whole corpus under the lane's own protocol after the
#: wave merges [assumed: BUDGET states no measured cost; commit=028b41a056cfd706e516cd0b945cbf69ac066da7].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 43959 to 43986, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
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
#: ENVELOPED 2026-08-25 by the observe pass: this twin's count is
#: intrinsically multi-valued (allocation-timing jitter moves GC
#: work between runs; ten serial runs of one such twin answered six
#: distinct counts), so a point pin with the +-4 tolerance is a
#: false claim here. Bounds are the exact extrema of 10
#: full-lane observations under 'full-lane/219/workers=32'; a cost outside them
#: is a real finding, and a new mode discovered later extends the
#: envelope with its observation count rather than widening blind.
#: RE-PINNED 2026-09-01 on the operator-protocol tree. Ten fresh full-lane
#: observations had no spread, and the serial min-of-three confirmed the point
#: [measured: twin minimum 17236 inferences; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3
#: examples/ch07-control-flow/07-03-let-and-sequencing/07-eval.metta;
#: fixture=operator-protocol tree after python extensions/python/tools/twin_coverage.py
#: --observe --rounds 10; commit=e3787593132a7ece2d300397045f7415709847c9].
#: RE-PINNED 2026-09-02, 17236 to 17523 (+287), exact numeric annotations
#: retain native operator heads, publish MeTTa type declarations, and leave
#: relational heads only where static proof is unavailable [measured
#: 2026-09-02: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=d0dfff1a3ee6c85472fd9b12d6e4aec007a9c301].
BUDGET = 17523
