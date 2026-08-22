"""The Python twin of examples/functions/functionhead.metta: an argument constrained to be a call's OUTPUT.

An equation HEAD cannot carry the constraint, because a head is a pattern and a
pattern is matched structurally at every depth: `(= (h (myfunc (10) $B) $C) ...)`
asks for a first argument that IS the three-element expression, not for one the
call can produce. So the constraint goes in the BODY, where `let` unifies the
argument with what the call produces and the call runs backwards, and `$B`
comes out bound.

`myfunc` is an ordinary Python function. `h` and `h_old` take the `@rules`
shape of the definitional decorator, because both bodies mint a variable that
is not a parameter: `$B` is the constraint's output, and a compiled body has no way to
introduce a MeTTa variable of its own (a free lowercase name there is a call it
cannot resolve, and an assignment binds a fresh name to a VALUE rather than
leaving a hole to unify against). In the `@rules` shape it is simply another
parameter, scoped to the generator, which is what the language calls it too.
The residue table records the gap against P14.4.

`h_old`'s test is a `=` term, MeTTa's unification, and `equation(a).to(b)` is
the builder for exactly that atom; the newer `h` says the same thing with
`let`.
"""

from petta import S, equation, rules

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 6376 to 8240, +1864 (+29.24%), all of it definition
#: installation and split in two. `myfunc` costs 1084 as an equation atom and
#: 2929 through `@m.define`, +1845, and it is the FIRST decorated definition
#: in this process so it carries the one-time setup as well as its own
#: compile (2244 against the atom door's 600 for one equation the first time,
#: 793 against 600 after). The `h_old`/`h` pair now enters through one
#: `m.add` instead of two `m +=`, 3391 to 3410, +19, the fixed cost of the
#: many-wire add. Both runnable forms are unchanged, because both doors land
#: the same three equations. The lane's parity reads 0.61 of the original.
#: Prior: ADDED 2026-08-22 at 6376 by 7f15dc1's wave-3 baseline.
BUDGET = 8240


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    append = m.fn("append")

    @m.define
    def myfunc(a, b):
        # (= (myfunc $A $B) (append (append (42) $A) $B))
        return append(append((42,), a), b)

    @rules
    def constrained(a, c, b):
        # (= (h_old $A $C) (if (= $A (myfunc (10) $B)) ($B $C) (empty)))
        yield equation(S.h_old(a, c)).to(
            S["if"](equation(a).to(S.myfunc((10,), b)), (b, c), S.empty())
        )
        # (= (h $A $C) (let $A (myfunc (10) $B) ($B $C)))
        yield equation(S.h(a, c)).to(S.let(a, S.myfunc((10,), b), (b, c)))

    m.add(*constrained)

    # !(test (h (42 10 40) 42000) ((40) 42000))
    yield m.eval(S.test(S.h((42, 10, 40), 42000), ((40,), 42000)))

    # !(test (h_old (42 10 40) 42000) ((40) 42000))
    yield m.eval(S.test(S.h_old((42, 10, 40), 42000), ((40,), 42000)))
