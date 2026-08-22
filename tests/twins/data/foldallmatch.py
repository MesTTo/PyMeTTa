"""The Python twin of examples/data/foldallmatch.metta: folding two generators.

The generator `foldall` folds can be a `match` over the space or a call, and
both are one form here. `+` is passed as the aggregator, which is why it is
written as the bare symbol `S["+"]`: the operator spelling `a + b` BUILDS an
addition, and what this form wants is the function itself.

The two `(kb ...)` facts go in as plain Python tuples, which is what a tuple
is at the write door: `(S.kb, 1)` IS `(kb 1)`.

`f` drops a rung for the reason foldall.metta's twin records: its two clauses
share a nullary head, so there is no head pattern to tell one `def` from the
other and a second `def f` would REBIND the name. The generator spelling
stores `(= (f) (superpose (1 2)))` instead, which answers the same two
answers, and the residue table records the missing spelling against P14.4.
"""

from petta import S, V

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 4216 to 5583, +1367 (+32.42%), by the wave-4 idiom
#: rewrite moving `f` onto @m.define. COMPILING a definition costs more than
#: STORING one, and the difference is paid once per process plus a little per
#: definition, never per call: four trivial one-parameter definitions in a
#: fresh process measured 2221 / 2986 / 3751 / 4516 inferences through
#: @m.define against 592 / 1164 / 1736 / 2308 through
#: `m += equation(...).to(...)`, so the first compiled definition costs 1,629
#: more and each one after it 193 more. The 262 under that here is the
#: second stored nullary clause the generator spelling replaces.
BUDGET = 5583


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`.
    """
    # (kb 1) (kb 2)
    m += (S.kb, 1)
    m += (S.kb, 2)

    # !(test (foldall + (match &self (kb $n) (+ $n 1)) 0) 5)
    yield m.eval(
        S.test(
            S.foldall(S["+"], S.match(S["&self"], S.kb(V.n), V.n + 1), 0), 5
        )
    )

    @m.define
    def f():
        # (= (f) 1) (= (f) 2), as one generator: yield IS superpose
        yield 1
        yield 2

    # !(test (foldall + (let $x (f) (+ 1 $x)) 0) 5)
    yield m.eval(
        S.test(S.foldall(S["+"], S.let(V.x, S.f(), 1 + V.x), 0), 5)
    )
