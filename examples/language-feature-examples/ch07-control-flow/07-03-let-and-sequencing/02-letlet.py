"""Purpose: examples/ch07-control-flow/07-03-let-and-sequencing/02-letlet.metta in Python: a destructuring binding.

The `let*` binding here is a PATTERN, `(($f1 $c1 3) (1 2 $d1))`: three
variables and a literal on the left meeting three values on the right, so `$f1`
and `$c1` bind leftwards while `$d1` binds rightwards from the literal 3. The
answer is `(1 2 3)`.

Python spells the left-to-right half `f1, c1, _ = 1, 2, d1`, and a compiled
body refuses even that: "a compiled body binds plain names; destructuring and
attribute assignment have no let* form" [re-measured 2026-08-24;
commit=028b41a056cfd706e516cd0b945cbf69ac066da7]. Nor does `solve`, the `let` door for a pattern that must win
variables, reach into a body: it is a module function and the subset reads only
its own names there. So the equation is stated as the term it is and filed
against P14.4.
Guarantees:
  - every ordered atom assembled in this file passes one iterable to
    Expression [tested: test_expression_assembles_one_ordered_atom_from_an_iterable; commit=028b41a056cfd706e516cd0b945cbf69ac066da7]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import Expression, S, V, equation


def twin(m):
    """Unify a three-element pattern with a three-element value."""
    # The top rung is Python's own destructuring assignment, which IS a
    # `let*` binding whose left side is a pattern:
    #
    #     @m.define
    #     def f():
    #         f1, c1, _three = 1, 2, d1
    #         return f1, c1, d1
    #
    # A compiled body refuses it: "a compiled body binds plain names;
    # destructuring and attribute assignment have no let* form", and even
    # then the assignment carries only the left-to-right half. Residue: P14.4.
    # (= (f) (let* ((($f1 $c1 3) (1 2 $d1))) ($f1 $c1 $d1)))
    m += equation(S.f()).to(
        S["let*"](
            (((V.f1, V.c1, 3), (1, 2, V.d1)),),
            (V.f1, V.c1, V.d1),
        )
    )

    # !(test (f) (1 2 3))
    assert m.eval(S.f()) == [Expression((1, 2, 3))]


#: Why this twin sits below the top rung; see the module docstring.
RUNG = "a `let*` binding whose left side is a PATTERN has no assignment spelling"

#: PLACEHOLDER, never measured in this worktree: the integrator's single
#: re-pin pass prices the whole corpus under the lane's own protocol after the
#: wave merges [assumed: BUDGET states no measured cost; commit=028b41a056cfd706e516cd0b945cbf69ac066da7].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 2922 to 2941, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 2941 to 2942, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 2942 to 2946, on the release tree:
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
#: RE-PINNED 2026-09-01, 2946 to 906 (-2040), the compiled-language batch:
#: try/raise on the error algebra, dict-space literals with lib_dict auto-
#: import, the exact-integer operator family as engine builtins (bit-
#: and/or/xor/not, floor-div, five registration rows moving clause indexing),
#: the implicit-island fallback, the except/error-payload runtime ops replacing
#: seven py- bridges, the variadic door family (transfer, batched remove and
#: eval), the -= drain-law repair, and fourteen twins healed to the arbiter
#: [measured 2026-09-01: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=51b792423cec5787614d1488c0793b8a50eaa6fc].
BUDGET = 906
