"""Purpose: examples/control/sealed.metta in Python: freshening an atom's variables.

`sealed` answers an Atom whose variables are fresh, except for the ones named
in its ignore list, and the caller runs that Atom when it wants to. Every
claim in the file is about VARIABLE IDENTITY: which occurrences are the same
variable, which are new, and which keep a binding from outside.

That is why the `let`s here stay terms rather than becoming assignments. The
binding is what `sealed` looks at: in `(let $z 7 (sealed ($z) ($z $w)))` the
ignore list names the very variable the `let` bound, and a Python name has no
identity the engine can be asked about. Where a `let` only names an
intermediate result, it IS an assignment, and the nested case below reads that
way in both languages.

Answers that carry fresh variables are compared modulo renaming, which is what
`=alpha` means and what `a.alpha_eq(b)` does. Where the claim is about two
answers carrying DIFFERENT variables, the gathering has to happen in the
ENGINE rather than in Python, and this is the one place the dissolution
table's `collapse` is `list()` does not hold: evaluating the match answers
`[($_846 ok), ($_846 ok)]` because each answer atom is decoded with its own
variable numbering, while collapsing it first answers
`(($_1734 ok) ($_1716 ok))`, which is the distinctness the claim is about
[re-measured 2026-08-24, all three spellings plus the subscript door in one
fresh process; commit=028b41a056cfd706e516cd0b945cbf69ac066da7]. So the gathering is named as its own compiled
definition, where `collapse` and `match` are both names the subset reads as
MeTTa. Filed as residue against P14.4.
Guarantees:
  - every ordered atom assembled in this file passes one iterable to
    Expression [tested: test_expression_assembles_one_ordered_atom_from_an_iterable; commit=028b41a056cfd706e516cd0b945cbf69ac066da7]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import Expression, G, S, V, equation, match

#: Why this twin sits below the top rung; see the module docstring.
RUNG = "the `let`s here bind the variables whose identity is under test, which a Python name cannot be"

#: PLACEHOLDER, never measured in this worktree: the integrator's single
#: re-pin pass prices the whole corpus under the lane's own protocol after the
#: wave merges [assumed: BUDGET states no measured cost; commit=028b41a056cfd706e516cd0b945cbf69ac066da7].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 13458 to 13496, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (petta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 13496 to 13440, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 13440 to 13409, on the release tree:
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
#: RE-PINNED 2026-08-25, 13409 to 13398, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
BUDGET = 13398


def twin(m):
    """Freshen variables, keep the ignored ones, and run what comes back."""
    # The rename happens when the expression is compiled, not after an outer
    # binding has already consumed the variable.
    # !(test (let $atom (sealed () (let $x 2 $x)) (eval $atom)) 2)
    atom = m.eval(S.sealed((), S.let(V.x, 2, V.x)))[0]
    assert m.eval(atom) == [2]

    # An unbound variable is freshened the same way.
    # !(test (let $atom (sealed () (let $y 5 $y)) (eval $atom)) 5)
    atom = m.eval(S.sealed((), S.let(V.y, 5, V.y)))[0]
    assert m.eval(atom) == [5]

    # The ignore list keeps the surrounding identity. Every other variable in
    # the returned Atom is fresh.
    # !(test (collapse (let $z 7 (sealed ($z) ($z $w)))) ((7 $unbound)))
    kept = m.eval(S.let(V.z, 7, S.sealed((V.z,), (V.z, V.w))))
    assert Expression(kept).alpha_eq(Expression((Expression((7, V.unbound)),)))

    # A ground Atom has no variable to rename.
    # !(test (sealed () 42) 42)
    assert m.eval(S.sealed((), 42)) == [42]

    # Nested sealed forms produce nested data. Each eval consumes one returned
    # layer, and each layer owns a distinct fresh variable. Here the two lets
    # only name intermediate results, so they are assignments.
    # !(test (let $atom (sealed () (let $n 2 (sealed () (let $n 3 $n))))
    #          (let $step (eval $atom) (eval $step)))
    #        3)
    atom = m.eval(S.sealed((), S.let(V.n, 2, S.sealed((), S.let(V.n, 3, V.n)))))[0]
    step = m.eval(atom)[0]
    assert m.eval(step) == [3]

    # A lambda renames its binders on every application; sealed freshens the
    # other variables in its returned Atom. The ignored lambda parameter
    # remains captured, while $fresh does not become another lambda argument.
    # (= (mk-tagger) (|-> ($item) (sealed ($item) (tagged $item $fresh))))
    m += equation(S.mk_tagger()).to(
        S["|->"]((V.item,), S.sealed((V.item,), S.tagged(V.item, V.fresh)))
    )

    # !(test (collapse (let $f (mk-tagger) (superpose (($f 1) ($f 2)))))
    #        ((tagged 1 $a) (tagged 2 $b)))
    tagged = S.let(V.f, S.mk_tagger(), S.superpose(((V.f, 1), (V.f, 2))))
    assert m.eval(S.collapse(tagged))[0].alpha_eq(
        Expression((S.tagged(1, V.a), S.tagged(2, V.b)))
    )

    # An ignored variable keeps its surrounding binding.
    # !(test (collapse (let $outer 7 (sealed ($outer) (both $outer $local))))
    #        ((both 7 $c)))
    outer = m.eval(S.let(V.outer, 7, S.sealed((V.outer,), S.both(V.outer, V.local))))
    assert Expression(outer).alpha_eq(Expression((S.both(7, V.c),)))

    # Freshen a rule's variables before adding it so two stored rules do not
    # share one identity. Evaluating the `sealed` first is what the original's
    # `let` is for: placing it directly under the write would store the
    # sealed expression itself.
    # !(let $rule (sealed () (stored-rule $r ok)) (add-atom &self $rule))
    m += m.eval(S.sealed((), S.stored_rule(V.r, S.ok)))[0]
    m += m.eval(S.sealed((), S.stored_rule(V.r, S.ok)))[0]

    # The top rung reads the space through the subscript door and gathers in
    # Python: `Expression([...])` over `m[S.stored_rule(V.x, V.y)]`. It gives
    # the wrong answer. Each answer atom is decoded with its own variable
    # numbering, so both rows arrive under ONE name where the engine's own
    # collapse answers two, and the DISTINCTNESS is the claim. So the
    # gathering is a compiled definition, where the subset reads both names
    # as MeTTa and the space is the ambient one. Residue: P14.4.
    @m.define
    def sealed_rules():
        # (collapse (match &self (stored-rule $x $y) ($x $y)))
        return collapse(match(S.stored_rule(V.x, V.y), (V.x, V.y)))  # noqa: F821  -- `collapse` is a name a compiled body reads as MeTTa; the package exports it nowhere yet (residue, P14.4)

    # !(test (collapse (match &self (stored-rule $x $y) ($x $y)))
    #        (($p ok) ($q ok)))
    assert sealed_rules()[0].alpha_eq(
        Expression((Expression((V.p, S.ok)), Expression((V.q, S.ok))))
    )

    # The ignored $y keeps its binding; the unignored $x is fresh.
    # !(test (collapse (let $x 1 (let $y 2 (sealed ($y) (pair $x $y)))))
    #        ((pair $fresh 2)))
    paired = m.eval(S.let(V.x, 1, S.let(V.y, 2, S.sealed((V.y,), S.pair(V.x, V.y)))))
    assert Expression(paired).alpha_eq(Expression((S.pair(V.fresh, 2),)))

    # The returned Atom stays inert until eval is asked to run it. The sum is
    # the grounded lift, one atom operand staging `(+ 1 2)` rather than
    # computing 3, which is what gives `sealed` something to hold.
    # !(test (let $atom (sealed () (+ 1 2)) (eval $atom)) 3)
    atom = m.eval(S.sealed((), G(1) + 2))[0]
    assert m.eval(atom) == [3]
