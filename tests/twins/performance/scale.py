"""Purpose: examples/performance/scale.metta in Python: a million atoms, five index shapes.

`addK` bulk-loads a million `(r K (mod K 10))` atoms, and five query shapes then
ask the same store different questions: everything, a bound first argument, a
bound second, both bound, and a variable in HEAD position. The driver runs all
five and reports the counts, which is the claim.

The driver is an ordinary Python function under the decorator: it calls its six
siblings by name through the mention door and builds the report it answers.

Two families stay at the container door, each for a blocker rather than a
preference.

The five queries are `(collapse (match ...))`, and a compiled body has no
spelling for `collapse` at all: `list(...)` and `fn.collapse` are both refused,
and a comprehension over a match lowers to `map-atom`, a different operation,
`(map-atom (match ...) (|-> ($x) $x))`, answering once per solution where
collapse answers once [measured 2026-08-24; commit=8a8b75a1f4052c00c70c29e25e95e4d5a1812cd5]. PERFECT:
`list(space[pattern])` inside a body. Residue P14.4.

`addK` compiles and then cannot run. A compiled `if` wraps its condition in
`py-truthy` and `==` lowers to `py-eq`, so every level of this million-deep
recursion spends reductions the original does not, and the evaluator's default
100,000 stack bound is reached at K=100,000: the compiled `addK` answers
`(Error 75002 StackOverflow)` where the term door completes a million
[measured 2026-08-24; commit=8a8b75a1f4052c00c70c29e25e95e4d5a1812cd5]. `m.limits` bounds inferences and time
and not stack depth, so there is no scope to raise it in and the example states
no pragma to copy. PERFECT: a compiled `if` that leaves an engine-Bool
condition alone, or a stack-depth mode block. Residue P14.4 and P14.14.
"""

from metta import S, V, equation, fn, if_

#: Inferences this twin spends, its own tripwire. PLACEHOLDER: the wave's
#: single re-pin pass prices the whole corpus on the merged tree, because a
#: cost measured in one agent's worktree is a cost measured on a base nothing
#: ships [assumed 2026-08-23: the number is a placeholder, not a measurement;
#: commit=8a8b75a1f4052c00c70c29e25e95e4d5a1812cd5].
BUDGET = 1

#: What a million atoms answer to the five shapes, in the driver's own order.
REPORT = S["all:"](1_000_000, S["first:"], 1, S["second:"], 100_000,
                   S["rel:"], 1, S["both:"], 1)


def twin(m):
    """Load a million atoms, then ask five differently-shaped questions."""
    m += equation(S.addK(V.k)).to(
        if_(S.eq(V.k, 0),  # rung: the compiled body answers StackOverflow at this depth
                S.done,
                S["let*"](((V.k10, V.k % 10),  # rung: as above
                           (V.written, S.add_atom(m, S.r(V.k, V.k10)))),  # rung: as above
                          S.addK(V.k - 1))))

    # Five shapes over one store: nothing bound, first bound, second bound,
    # both bound, and the relation itself a variable.
    m += equation(S.q_all()).to(S.collapse(S.match(m, S.r(V.x, V.y), S.r(V.x, V.y))))  # rung: a compiled body has no spelling for collapse
    m += equation(S.q_first(V.a)).to(S.collapse(S.match(m, S.r(V.a, V.y), S.r(V.a, V.y))))  # rung: as above
    m += equation(S.q_second(V.b)).to(S.collapse(S.match(m, S.r(V.x, V.b), S.r(V.x, V.b))))  # rung: as above
    m += equation(S.q_both(V.a, V.b)).to(S.collapse(S.match(m, S.r(V.a, V.b), S.r(V.a, V.b))))  # rung: as above
    m += equation(S.q_rel(V.r)).to(S.collapse(S.match(m, (V.r, 643, 3), (V.r, 643, 3))))  # rung: as above

    @m.define
    def indexing_demo(k):
        _loaded = fn.addK(k)
        everything = fn.q_all()
        first = fn.q_first(7)
        second = fn.q_second(3)
        rel = fn.q_rel(S.r)
        both = fn.q_both(42, 2)
        return S["all:"](fn.length(everything), S["first:"], fn.length(first),
                         S["second:"], fn.length(second), S["rel:"], fn.length(rel),
                         S["both:"], fn.length(both))

    assert indexing_demo(1_000_000) == [REPORT]
