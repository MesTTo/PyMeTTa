"""Purpose: examples/ch07-control-flow/07-01-if-and-booleans/10-and_then_or_else.metta in Python: short-circuiting.

`and-then` and `or-else` are the short-circuiting boolean connectives. They
are special forms rather than functions, which is the whole point: a
function's arguments are evaluated before the call, so a function could not
skip its second one.

Python's own `and` and `or` are those two forms exactly. Inside a compiled
body they lower to a binding plus a test that answers the DECIDING OPERAND,
so `a and b` is `(and-then $a $b)` down to which value comes back, and the
argument that is not chosen is never evaluated, because a compiled body's
arguments are syntax rather than calls.

They are not a second spelling of `and` and `or`. Those are RELATIONAL: they
evaluate both sides and can solve for an unbound argument. Python has no
relational `and`, so that one keeps MeTTa's name through the keyword builder
`and_`, and the last claim's `if` keeps its own through `if_`, whose two-arity
is the engine's and which Python's conditional expression cannot spell.

The original opens a second space to keep its two experiments apart. Python
keeps them apart with a slice of the context space, so `note2` records beside
`note` and the two equations really are the same equation twice, which is what
the original's two are once the space is factored out.

The write is the space container protocol inside a compiled body. Binding
`S.context_space()` to a local and applying `+=` lowers to `add-atom`, so the
equation stores its marker without a grounded host operation.
Guarantees:
  - TRUE and FALSE used here are package values rather than local
    reconstructions [tested: test_the_canonical_atoms_are_public_values;
    commit=028b41a056cfd706e516cd0b945cbf69ac066da7]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import FALSE, TRUE, S, V, and_, if_


def twin(m):
    """Skip a branch, take a branch, and prove which one ran."""
    @m.define
    def note(tag):
        # (= (note $tag) (let $_ (add-atom &ran (ran $tag)) True))
        space = S.context_space()
        space += S.ran(tag)
        return True

    @m.define
    def note2(tag):
        # (= (note2 $tag) (let $_ (add-atom &ran2 (ran $tag)) True))
        space = S.context_space()
        space += S.ran(tag)
        return True

    @m.define
    def both(a, b):
        # (and-then $a $b)
        return a and b

    @m.define
    def either(a, b):
        # (or-else $a $b)
        return a or b

    # !(test (and-then True yes) yes)
    assert both(TRUE, S.yes) == [S.yes]
    # !(test (and-then False yes) False)
    assert both(FALSE, S.yes) == [False]
    # !(test (or-else True no) True)
    assert either(TRUE, S.no) == [True]
    # !(test (or-else False fallback) fallback)
    assert either(FALSE, S.fallback) == [S.fallback]

    # They take expressions, not just literals. An argument that is a term
    # reduces on the way in, which is what the original's do too. The
    # comparison is built by its WORD, because `>` between two atoms is the
    # engine's total order rather than a term.
    # !(test (and-then (> 2 1) (> 3 2)) True)
    assert both(S.gt(2, 1), S.gt(3, 2)) == [True]
    # !(test (or-else (> 1 2) (> 3 2)) True)
    assert either(S.gt(1, 2), S.gt(3, 2)) == [True]

    @m.define
    def gated(flag, tag):
        # (and-then $flag (note $tag)): the note is a call the body COMPILES,
        # so whether it runs is the engine's decision, not Python's
        return flag and note(tag)

    @m.define
    def fallback(flag, tag):
        # (or-else $flag (note $tag))
        return flag or note(tag)

    # Each form is run by READING its answer: creating the answer view does no
    # engine work, so a call whose result is dropped never reaches the engine
    # and the skipping this file is about would be unobservable.
    # !(and-then False (note skipped-by-and-then))
    assert gated(FALSE, S.skipped_by_and_then) == [False]
    # !(or-else True (note skipped-by-or-else))
    assert fallback(TRUE, S.skipped_by_or_else) == [True]
    # !(and-then True (note taken-by-and-then))
    assert gated(TRUE, S.taken_by_and_then) == [True]
    # !(or-else False (note taken-by-or-else))
    assert fallback(FALSE, S.taken_by_or_else) == [True]

    # !(test (collapse (get-atoms &ran))
    #        ((ran taken-by-and-then) (ran taken-by-or-else)))
    assert m[S.ran(V.t)].t == [S.taken_by_and_then, S.taken_by_or_else]

    # The contrast, in one place: `and` does NOT skip, so its second argument
    # runs even though the first is False. Both forms are written the same way
    # so the pair stays comparable, and the relational `and` is the keyword
    # builder, PEP 8's own escape for a name Python's grammar has taken.
    # The original opens `&ran2` to keep this experiment apart. This twin
    # keeps it apart by slicing the context-space matches after the first
    # experiment.
    already = len(m[S.ran(V.t)].t)
    # !(and False (note2 and-runs-it))
    m.eval(and_(FALSE, S.note2(S.and_runs_it)))
    # !(and-then False (note2 and-then-skips-it))
    m.eval(S.and_then(FALSE, S.note2(S.and_then_skips_it)))

    # !(test (collapse (get-atoms &ran2)) ((ran and-runs-it)))
    assert m[S.ran(V.t)].t[already:] == [S.and_runs_it]

    # And the other side of the trade: and-then cannot be solved backwards,
    # where `and` can. The one-armed `if_` is the engine's own filter arity,
    # which is exactly why the keyword builder exists.
    # !(test (collapse (if (and-then (or-else $p True) $q) ($p $q))) ())
    unsolved = S.and_then(S.or_else(V.p, TRUE), V.q)
    assert m.eval(if_(unsolved, (V.p, V.q))) == []


#: PLACEHOLDER, never measured in this worktree: the integrator's single
#: re-pin pass prices the whole corpus under the lane's own protocol after the
#: wave merges [assumed: BUDGET states no measured cost; commit=028b41a056cfd706e516cd0b945cbf69ac066da7].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 30258 to 30467, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 30467 to 30478, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 30478 to 30430, on the release tree:
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
#: RE-PINNED 2026-08-25, 30430 to 30440, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 30440 to 30810 (+370), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-08-26, 30810 to 30832 (+22), on the composed
#: async-scheduler tree: a live operation call pays the six-inference
#: admission probe the baseline's p14_async_scheduler_comment prices,
#: and the scheduler, context-callback and exact-memo lifecycle clauses
#: move compiled-image layout by tens, the class this file's chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=merged p14-audit-async composed tree with engine/reader.so; commit=5059173b1767600ce4df0f6b7841d88116ee62d3].
#: RE-PINNED 2026-09-01, 30832 to 19171 (-11661), the compiled-language batch:
#: try/raise on the error algebra, dict-space literals with lib_dict auto-
#: import, the exact-integer operator family as engine builtins (bit-
#: and/or/xor/not, floor-div, five registration rows moving clause indexing),
#: the implicit-island fallback, the except/error-payload runtime ops replacing
#: seven py- bridges, the variadic door family (transfer, batched remove and
#: eval), the -= drain-law repair, and fourteen twins healed to the arbiter
#: [measured 2026-09-01: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=51b792423cec5787614d1488c0793b8a50eaa6fc].
#: RE-PINNED 2026-09-01, 19171 to 19126 (-45), the subtract-atom primitive and
#: the Counter grain for -=: a new engine head shifts every twin's load
#: structure, and the removal doors changed meaning where a twin spells one
#: [measured 2026-09-01: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c6a40460b1db341198a6150e3600f502831a6e83].
#: RE-PINNED 2026-09-01, 19126 to 19204 (+78), generic Python operators now
#: dispatch through live protocols while source twins explicitly name
#: relational engine heads [measured 2026-09-01: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=WORKTREE].
BUDGET = 19204
