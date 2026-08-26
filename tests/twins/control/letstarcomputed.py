"""Purpose: examples/control/letstarcomputed.metta in Python: bindings as a value.

The bindings of a `let*` are usually written out, and then they are syntax:
the form rewrites them into nested `let`s once. They do not have to be written
out. A bindings argument that arrives as a VALUE is rewritten when it arrives,
so a program can decide its own bindings while it runs, which is what lets
`let*` be given another name as an ordinary definition.

That is the shape Python has no word for. An assignment binds a name the
author wrote, so a definition whose bindings ARRIVE has no compiled spelling,
and neither has a binding whose left side is a pattern. Written-out bindings
sit beside handed-over ones here on purpose, so writing half of them as Python
assignments would break the pairing the file exists to show. Filed as residue
against P14.4.

The type declaration is the one place where the same characters mean the same
thing in both languages: `typed(...)` is the colon, `arrow(...)` is the result
arrow, and `%Undefined%` is `metta.Undefined`. Three more things move into
Python: an answer set that is
empty is an empty list, a refusal crosses the seam as a Python exception so
`catch` is `except`, and `repr` of an atom is Python's own `str`.
Guarantees:
  - expected printed output in this twin remains Python str text
    [tested: test_printing_text_is_not_forced_through_the_value_carrier; commit=028b41a056cfd706e516cd0b945cbf69ac066da7]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import Atom, S, Undefined, V, arrow, equation, typed
from metta.errors import MettaOperationError

#: What the unapplied form prints as: expected printing is Python text.
UNAPPLIED = "(partial let* (foo ok))"

#: Why this twin sits below the top rung; see the module docstring.
RUNG = "a `let*` whose bindings arrive as a VALUE has no assignment spelling"

#: PLACEHOLDER, never measured in this worktree: the integrator's single
#: re-pin pass prices the whole corpus under the lane's own protocol after the
#: wave merges [assumed: BUDGET states no measured cost; commit=028b41a056cfd706e516cd0b945cbf69ac066da7].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 11165 to 11275, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (petta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 11275 to 11263, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 11263 to 11267, on the release tree:
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
#: RE-PINNED 2026-08-25, 11267 to 11263, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 11263 to 12889 (+1626), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python bindings/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
BUDGET = 12889


def twin(m):
    """Hand bindings over, write them out, and refuse a list that is not one."""
    # The top rung is a compiled definition whose bindings are assignments:
    #
    #     @m.define
    #     def mylet(bindings, body): ...
    #
    # An assignment binds a name the AUTHOR wrote, so a definition whose
    # bindings arrive as a value has no compiled spelling, and neither has a
    # binding whose left side is a pattern. Residue: P14.4.
    # (: mylet (-> Atom Atom %Undefined%))
    # The body has to reach the definition unevaluated for the bindings to
    # bind anything in it, and `Atom` is the metatype that says so.
    m += typed(S.mylet, arrow(Atom, Atom, Undefined))
    # (= (mylet $bindings $body) (let* $bindings $body))
    m += equation(S.mylet(V.bindings, V.body)).to(S["let*"](V.bindings, V.body))

    written = ((V.x, 1), (V.y, 2))

    # !(test (mylet (($x 1) ($y 2)) (+ $x $y)) 3)
    assert m.eval(S.mylet(written, V.x + V.y)) == [3]

    # Handed over or written out, the same bindings answer the same thing.
    # !(test (let* (($x 1) ($y 2)) (+ $x $y)) 3)
    assert m.eval(S["let*"](written, V.x + V.y)) == [3]

    # A binding is a (pattern value) pair, not only (variable value), and a
    # pattern that does not match gives the whole form no answer.
    # !(test (mylet ((($a $b) (1 2))) $b) 2)
    assert m.eval(S.mylet((((V.a, V.b), (1, 2)),), V.b)) == [2]
    # !(test (mylet ((5 5)) matched) matched)
    assert m.eval(S.mylet(((5, 5),), S.matched)) == [S.matched]
    # !(test (collapse (mylet ((5 6)) matched)) ())
    assert m.eval(S.mylet(((5, 6),), S.matched)) == []

    # Without the `Atom` metatype the arguments evaluate on the way in, so
    # this is the other way to hand bindings over: `noeval` carries them as
    # data, and the body is a variable the same call site wrote.
    # (= (mylet-evaluating $bindings $body) (let* $bindings $body))
    m += equation(S.mylet_evaluating(V.bindings, V.body)).to(S["let*"](V.bindings, V.body))

    # !(test (mylet-evaluating (noeval (($x 1))) $x) 1)
    assert m.eval(S.mylet_evaluating(S.noeval(((V.x, 1),)), V.x)) == [1]

    # Bindings are checked when they arrive, because nothing after that point
    # can check them.
    # !(test (car-atom (catch (mylet-evaluating (noeval ((1 2 3))) done))) Error)
    try:
        m.eval(S.mylet_evaluating(S.noeval(((1, 2, 3),)), S.done))
        refused = None
    except MettaOperationError as error:
        refused = error
    assert refused is not None

    # A bindings argument that is no list at all is not bindings, it is a
    # program using the name as data, and it stays the unapplied form it
    # always was.
    # !(test (repr (let* foo ok)) "(partial let* (foo ok))")
    assert str(m.eval(S["let*"](S.foo, S.ok))[0]) == UNAPPLIED
