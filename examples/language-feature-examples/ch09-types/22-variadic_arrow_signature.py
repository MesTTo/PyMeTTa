"""Purpose: examples/ch09-types/22-variadic_arrow_signature.metta in Python.

The declaration and equation atoms are the rung below compiled def, whose
parameter syntax does not admit a segment. S[":seg"] builds type syntax;
seg(V.args) builds the pattern's variable capture.
[tested: variadic_arrows; commit=6031c83ab3002b5703cb6fcb10e70a60a89f4ad7]
"""

from metta import Expression, S, V, arrow, equation, seg, typed


def twin(m):
    """Call the same declared run at zero through three arguments."""
    signature = arrow(S[":seg"](S.Bool), arrow())
    m += typed(S.do2, signature)
    m += equation(S.do2(seg(V.args))).to(Expression())  # rung: compiled def has no segment parameter
    for count in range(4):
        effects = [S["println!"](name) for name in (S.one, S.two, S.three)[:count]]  # rung: print() returns None before dispatch; the Bool-valued effect must run as the typed operand
        assert m.fn.do2(*effects) == [Expression()]
    assert m.type(S.do2) == signature

    m += equation(S.undeclared_do(seg(V.args))).to(S.got(V.args))  # rung: as above
    assert m.fn.undeclared_do(S.a, S.b) == [S.got(Expression(S.a, S.b))]
    assert m.fn.undeclared_do() == [S.got(Expression())]


#: The initial 16,386-inference price includes
#: once-per-arity segment compilation and positional type diagnostics; the no-
#: work compiled-call matrix matches fixed callees and no allowance is widened
#: [measured 2026-09-09: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=6031c83ab3002b5703cb6fcb10e70a60a89f4ad7].
#: RE-PINNED 2026-09-09, 16386 to 16435 (+49), The fixed diagnostic reader now
#: consumes parameter and argument spines together, and segment families
#: compile once per shape. Fixed-arrow presentation and warmed single-run
#: callees keep their controls. Fused syntax admission adds 44 inferences for a
#: cold prepare/admit type shape versus the old annotation scan and eight per
#: source-preflight declaration; repeated shapes reuse the analysis. The
#: authoring control moves by -16 once, with its per-definition slope
#: unchanged. Cold family generation is included. See
#: docs/journal/2026-09-09-the-splice-in-an-arrow.md [measured 2026-09-09: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=6031c83ab3002b5703cb6fcb10e70a60a89f4ad7].
#: RE-PINNED 2026-09-11, 16435 to 16651 (+216), end-of-wave re-pin on the
#: merged tree after FROM's reference rows and four engine units, the closed-
#: set derivations and two host services, BINDING's one native evaluation entry
#: and boot import, W-OBSERVE's observer guard, PERF's receipts batching and
#: cursor retirement, and the three REDS repairs (derived runtime resources and
#: the shared loader, the tool-lane repairs, the corpus example); serial
#: minimum of three fresh processes through the lane's run_twin with
#: file_search_cache_time=9223372036854775807 set before child boot [measured
#: 2026-09-11: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=57f84148ba2684015f052d533f3197eca07b1f7b].
#: RE-PINNED 2026-09-18, 16435 to 17208 (+773), the branch's landings since the
#: 09-10 pins, re-taken on the tip f06186a96: the compiled call law (e59104ace:
#: an Atom argument enters as written, a Python object crosses as a value, a
#: positional call of a bound callee is the plain application and a compiled
#: lambda is bare where it is applied), the one codec at the grounded call
#: (fd0af38f7, whose read of a call site's written keyword tail costs about six
#: inferences per translated site, read once since 7cc8fb863), the runnable
#: cache's dependency index written by the producer (a9e2c06d3, which takes
#: back the walk of the generated code 5416e741d charged at every miss), the
#: host patches of 09-17 and the class units of 09-13 to 09-16 the ladder in
#: docs/journal/2026-09-14-runnable-artifact-dependencies.md places; serial
#: minimum of three fresh processes through the lane's run_twin with
#: file_search_cache_time=9223372036854775807 set before child boot [measured
#: 2026-09-18: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=6944d06ce96fdbcd1faefb640f15dbfa0cf286dd].
BUDGET = BUDGET = 17208
