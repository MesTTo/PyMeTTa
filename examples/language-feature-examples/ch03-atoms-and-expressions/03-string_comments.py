"""Purpose: examples/ch03-atoms-and-expressions/03-string_comments.metta in Python: `;` inside a string.

The original is a READER test: a semicolon inside a string starts no comment, a
lone `(` or `)` is a string rather than a paren, and a backslash escape
survives. No Python program can re-run that reader, because it never hands the
engine any text to read, and the residue table records the gap against P14.1
where ch03-atoms-and-expressions/05-parse.metta records it.

What a Python program CAN say is the other half, and it is the half the reader
exists to protect: each of these values crosses into the engine and comes back
as itself, which is the same round trip the original's `!(test "x" "x")` forms
make.

The last form is an ordinary definition whose body is the lowercase symbol
`result`, and `S.result` says that inside a compiled body: a factory mention is
data there, where a bare `result` would be read as a call.
"""

from metta import S, fn, ground


def twin(m):
    """Send nine awkward strings through the engine, then define a function."""
    # A lone paren is a string, not punctuation.
    # !(test ")" ")")
    # !(test "(" "(")
    close, open_ = ground(")"), ground("(")
    assert m.eval(close) == [close]
    assert m.eval(open_) == [open_]

    # A lone semicolon is a string, not the start of a comment.
    # !(test ";" ";")
    semicolon = ground(";")
    assert m.eval(semicolon) == [semicolon]

    # `quote` is an evaluation BARRIER, not a value: `(quote X)` answers X
    # itself, unevaluated, and no wrapper survives -- upstream PeTTa's own
    # meaning, adopted 2026-08-30. The .metta's test passes because `test`
    # evaluates both sides to ";".
    # !(test (quote ";") (quote ";"))
    quoted = fn.quote(semicolon)
    assert m.eval(quoted) == [semicolon]

    # A semicolon in the middle, three of them, one at each end.
    # !(test "foo;bar" "foo;bar")
    # !(test ";;;" ";;;")
    middle, three = ground("foo;bar"), ground(";;;")
    assert m.eval(middle) == [middle]
    assert m.eval(three) == [three]
    # !(test ";start" ";start")
    # !(test "end;" "end;")
    first, last = ground(";start"), ground("end;")
    assert m.eval(first) == [first]
    assert m.eval(last) == [last]

    # An escaped quote, and a backslash.
    # !(test "quote: \"" "quote: \"")
    # !(test "path\\file" "path\\file")
    escaped, backslash = ground('quote: "'), ground("path\\file")
    assert m.eval(escaped) == [escaped]
    assert m.eval(backslash) == [backslash]

    @m.define
    def test_func():
        """(= (test-func) result), whose body is one lowercase symbol."""
        return S.result

    # !(test (test-func) result)
    assert test_func() == [S.result]


#: Inferences this twin spends, its own tripwire. A PLACEHOLDER: the wave's
#: integrator prices all 218 budgets in one pass on the merged tree, so no
#: figure measured in a single agent's worktree is pinned here
#: [assumed: 1 is a placeholder rather than a measurement; commit=e4c861a8c9e8e42b9e5ecb90d9ebf92a946e0163].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 3586 to 3605, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 3605 to 3616, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 3616 to 3550, on the release tree:
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
#: RE-PINNED 2026-08-25, 3550 to 3560, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 3560 to 3583 (+23), on the composed
#: async-scheduler tree: a live operation call pays the six-inference
#: admission probe the baseline's p14_async_scheduler_comment prices,
#: and the scheduler, context-callback and exact-memo lifecycle clauses
#: move compiled-image layout by tens, the class this file's chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=merged p14-audit-async composed tree with engine/reader.so; commit=5059173b1767600ce4df0f6b7841d88116ee62d3].
#: RE-PINNED 2026-09-01, 3583 to 3553 (-30), the compiled-language batch:
#: try/raise on the error algebra, dict-space literals with lib_dict auto-
#: import, the exact-integer operator family as engine builtins (bit-
#: and/or/xor/not, floor-div, five registration rows moving clause indexing),
#: the implicit-island fallback, the except/error-payload runtime ops replacing
#: seven py- bridges, the variadic door family (transfer, batched remove and
#: eval), the -= drain-law repair, and fourteen twins healed to the arbiter
#: [measured 2026-09-01: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=WORKTREE].
BUDGET = 3553
