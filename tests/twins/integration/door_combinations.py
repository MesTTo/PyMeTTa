"""examples/integration/door_combinations.metta in Python: the nesting matrix.

The example proves the engine half of the matrix; this side carries the host
half, cell by cell, in the design's own frame: a DEFINE body is LOWERED
(references become terms), a RULES body is EXECUTED (references act now
unless they stage), an OP body is HOST (references are plain Python unless
they deliberately cross). The staging split is asserted STRUCTURALLY, by
matching the stored equation bodies, because the law is about what the law
HOLDS, not only what it answers: a call carrying a rule variable stages to
its call term, a ground defined call runs at construction and embeds its one
result, a ground op call fires its effect exactly once at construction, and
an op call staged into a law crosses the host per application.
"""

from metta import G, S, V, fn, rules
from metta import equation as eq


def twin(m):
    """Walk the matrix: each definition kind inside each body kind."""
    # ---- inside a DEFINE body (lowered) ----

    @m.define
    def dc_twice(x):                     # (= (dc-twice $x) (+ $x $x))
        return x + x

    @m.define
    def dc_quad(x):                      # a define inside a define: the
        return dc_twice(dc_twice(x))     # ordinary call term, engine-only

    assert dc_quad(5) == [20]

    @m.define
    def dc_upper(s):                     # a grounded operation inside a
        return fn.py_call(S[".upper"](s))   # define: one host crossing per call

    assert m.eval(S.dc_upper(G("ab"))) == [S.AB]

    # Writing equations FROM a body: add-atom of an (= ...) atom, the
    # self-modification face. The body runs, the space gains the equation,
    # and the new name answers.
    @m.define
    def dc_install():
        return fn.add_atom(fn.context_space(), S["="](S.dc_nine(), 9))

    m.eval(S.dc_install())
    assert m.eval(S.dc_nine()) == [9]

    # Equations are ordinary atoms, so a program can MATCH one: the meta
    # face that makes rules-over-rules lawful.
    assert [row.body for row in m[S["="](S.dc_nine(), V.body)]] == [9]

    # ---- inside a RULES body (executed, with the staging split) ----

    fired = []

    @m.op(effect="writesState")
    def dc_stamp(x: int) -> int:
        fired.append(x)
        return x * 10

    @m.define
    def dc_fib(n):
        if n <= 1:
            return n
        return dc_fib(n - 1) + dc_fib(n - 2)

    @rules
    def dc_cells(value):
        # a defined call with a RULE VARIABLE stages: the law holds the term
        yield eq(S.dc_stage(value)).to(dc_twice(value))
        # a GROUND defined call runs at construction and embeds its result
        yield eq(S.dc_fold()).to(dc_fib(10))
        # an op call with a rule variable stages the OP-CALL TERM, so the
        # law crosses the host per application and no effect fires here
        yield eq(S.dc_op_stage(value)).to(dc_stamp(value))
        # a ground op call runs NOW: the effect fires once, at construction
        yield eq(S.dc_op_ground()).to(dc_stamp(4))

    m.add(*dc_cells)

    # The construction-time record: exactly one effect, the ground one.
    assert fired == [4]

    # The stored bodies say which side of the split each call took,
    # asserted the structural way: the law itself is matched as a pattern.
    assert len(m[S["="](S.dc_stage(V.v), S.dc_twice(V.w))]) == 1
    assert m[S["="](S.dc_fold(), V.b)][0].b == 55
    assert len(m[S["="](S.dc_op_stage(V.v), S.dc_stamp(V.w))]) == 1
    assert m[S["="](S.dc_op_ground(), V.b)][0].b == 40

    # And every law answers.
    assert m.eval(S.dc_stage(6)) == [12]
    assert m.eval(S.dc_fold()) == [55]
    assert m.eval(S.dc_op_stage(6)) == [60]
    assert m.eval(S.dc_op_ground()) == [40]
    # The staged op crossed the host at APPLICATION time, with the bound value.
    assert fired == [4, 6]

    # ---- inside an OP body (host) ----

    @m.op(effect="readOnlyLookup")
    def dc_reenter(x: int) -> int:
        # a define inside an op RE-ENTERS the engine, a full driving-lane
        # call from within a callback
        [answer] = dc_twice(x)
        return answer

    assert m.eval(S.dc_reenter(21)) == [42]

    @m.op(effect="writesState")
    def dc_hostside(x: int) -> int:
        # an op inside an op stays in host: plain Python, zero crossings
        return dc_stamp(x) + 1

    assert m.eval(S.dc_hostside(2)) == [21]
    assert fired == [4, 6, 2]


#: Inferences this twin spends, its own tripwire.
#: PRICED 2026-08-25 on landing, tools/twin_coverage.py on the pair;
#: the release measure re-prices with the corpus.
#: RE-PINNED 2026-08-25, 63350 to 63326, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: ENVELOPED 2026-08-26 by the observe pass: this twin's count is
#: intrinsically multi-valued (allocation-timing jitter moves GC
#: work between runs; ten serial runs of one such twin answered six
#: distinct counts), so a point pin with the +-4 tolerance is a
#: false claim here. Bounds are the exact extrema of 10
#: full-lane observations under 'full-lane/219/workers=32'; a cost outside them
#: is a real finding, and a new mode discovered later extends the
#: envelope with its observation count rather than widening blind.
BUDGET = {
    # Re-measured after operation registration began recording the required
    # five-rank effect contract fact for each host operation.
    "minimum": 65218,
    "maximum": 65274,
    "observations": 10,
    "protocol": "full-lane/219/workers=32",
}
