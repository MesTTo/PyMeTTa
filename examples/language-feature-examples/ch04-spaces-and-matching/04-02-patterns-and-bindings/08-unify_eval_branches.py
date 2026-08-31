"""Purpose: examples/ch04-spaces-and-matching/04-02-patterns-and-bindings/08-unify_eval_branches.metta in Python: branches evaluate.

Space-based `unify` evaluates the branch it selects, both of them. Without
that, the then branch of a matched case would answer `(+ 1 2)` instead of 3,
and a nested `unify` in an else branch would come back unrun. The shape is
pverify's: an `Error` atom when a declaration already exists, and a nested
check in the else branch when it does not.

`unify` keeps MeTTa's name, for the reason unify.metta gives: Python has no
expression that matches two terms and chooses a branch. What is ordinary
Python here is the knowledge: two facts go in through the write door, the
space operand is the handle itself, the arithmetic branches are the grounded
lift, and the strings the errors carry are named once and carried whole.

`lib_he` takes the bracket. The factory's attribute map is total, so
`S.lib_he` is the atom `lib-he` and the import would look for a library of
that name; the library on disk is `lib/lib_he/lib_he.metta`.
Guarantees:
  - every ordered atom assembled in this file passes one iterable to
    Expression [tested: test_expression_assembles_one_ordered_atom_from_an_iterable; commit=028b41a056cfd706e516cd0b945cbf69ac066da7]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import Expression, G, S, ground, lib

#: The strings the knowledge and the errors carry, carried whole rather than
#: parsed: `$c` and `$v` are metamath's constant and variable markers, and the
#: two sentences are the messages the errors are made of.
CONSTANT, VARIABLE = ground("$c"), ground("$v")
DECLARED = ground("already declared")
CONFLICT = ground("active variable conflict")


def twin(m):
    """Take a then branch, an else branch, and a nested else branch."""
    # !(import! &self (library lib_he))
    m += lib.he

    # (Constant wff (Type "$c"))
    m += S.Constant(S.wff, S.Type(CONSTANT))
    # (Var x 0 (Type "$v"))
    m += S.Var(S.x, 0, S.Type(VARIABLE))

    nothing = Expression(())

    # Test 1: then-branch needs eval (expression in matched case)
    # !(test (unify &self (Constant wff (Type "$c"))
    #          (Error (Constant wff) "already declared") ())
    #        (Error (Constant wff) "already declared"))
    already = S.Error(S.Constant(S.wff), DECLARED)
    assert m.eval(S.unify(m, S.Constant(S.wff, S.Type(CONSTANT)), already, nothing)) == [already]

    # Test 2: else-branch needs eval (fallthrough to nested unify)
    # !(test (unify &self (Constant y (Type "$c")) (Error (Constant y) "already declared")
    #          (unify &self (Var y 0 (Type "$v")) (Error (Var y) "active variable conflict") ()))
    #        ())
    y_conflict = S.unify(m, S.Var(S.y, 0, S.Type(VARIABLE)), S.Error(S.Var(S.y), CONFLICT), nothing)
    y_declared = S.Error(S.Constant(S.y), DECLARED)
    assert m.eval(S.unify(m, S.Constant(S.y, S.Type(CONSTANT)), y_declared, y_conflict)) == [nothing]

    # Test 3: else-branch nested unify hits (real conflict chain)
    # !(test (unify &self (Constant x (Type "$c")) (Error (Constant x) "already declared")
    #          (unify &self (Var x 0 (Type "$v")) (Error (Var x) "active variable conflict") ()))
    #        (Error (Var x) "active variable conflict"))
    x_conflicted = S.Error(S.Var(S.x), CONFLICT)
    x_conflict = S.unify(m, S.Var(S.x, 0, S.Type(VARIABLE)), x_conflicted, nothing)
    x_declared = S.Error(S.Constant(S.x), DECLARED)
    assert m.eval(S.unify(m, S.Constant(S.x, S.Type(CONSTANT)), x_declared, x_conflict)) == [x_conflicted]

    # Test 4: arithmetic in branches (minimal reproducer)
    # !(test (unify &self (Constant wff (Type "$c")) (+ 1 2) 0) 3)
    assert m.eval(S.unify(m, S.Constant(S.wff, S.Type(CONSTANT)), G(1) + 2, 0)) == [3]

    # Test 5: arithmetic in else-branch
    # !(test (unify &self (Constant NOSUCH (Type "$c")) 0 (+ 10 20)) 30)
    assert m.eval(S.unify(m, S.Constant(S.NOSUCH, S.Type(CONSTANT)), 0, G(10) + 20)) == [30]


#: PLACEHOLDER, never measured in this worktree: the integrator's single
#: re-pin pass prices the whole corpus under the lane's own protocol after the
#: wave merges [assumed: BUDGET states no measured cost; commit=028b41a056cfd706e516cd0b945cbf69ac066da7].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 5897 to 5916, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 5916 to 5917, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 5917 to 5919, on the release tree:
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
#: RE-PINNED 2026-08-25, 5919 to 5921, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: RE-PINNED 2026-09-01, 5921 to 6407 (+486), the compiled-language batch:
#: try/raise on the error algebra, dict-space literals with lib_dict auto-
#: import, the exact-integer operator family as engine builtins (bit-
#: and/or/xor/not, floor-div, five registration rows moving clause indexing),
#: the implicit-island fallback, the except/error-payload runtime ops replacing
#: seven py- bridges, the variadic door family (transfer, batched remove and
#: eval), the -= drain-law repair, and fourteen twins healed to the arbiter
#: [measured 2026-09-01: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=51b792423cec5787614d1488c0793b8a50eaa6fc].
BUDGET = 6407
