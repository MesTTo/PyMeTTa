"""Purpose: classify an operation with a decorator, and read the rank it carries.

One law: THE RANK FOLLOWS THE ANSWER COUNT. An operation that can answer more
than once carries `nondeterministicReadOnly` however structural its computation
is, and one that answers at most once may sit below it.

That is why there are four decorators for five classes. `@m.pure`, `@m.reads`,
`@m.writes` and `@m.io` are `m.op` with `effect=` filled in, so the
classification is a name rather than a string argument. The fifth is DERIVED: a
Python generator is nondeterministic whatever it declares, so the registration
reads that off the function and lifts the class. Declaring it by hand would
restate what the library already worked out.

The engine holds its own builtins to the same law, which is the whole of why
`get-atoms` and `and` sit where they do.

Guarantees:
  - every row of LAW holds: the term answers that many times and carries that
    class, whether it was declared here or shipped by the engine
    [tested: effect_ranks example; commit=WORKTREE]
  - a plan takes the strongest class of the operations it calls
    [tested: effect_ranks example; commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from _common import check, done

from metta import MeTTa, S, V
from metta.vocabularies import EffectClass as E

m = MeTTa()
m.run("(edge a b)  (edge c d)  (edge e f)")


@m.pure
def double(x: int) -> int:
    """Depends only on its argument, so it is cache-safe."""
    return 2 * x


@m.reads
def tally(name: str) -> int:
    """Reads stable state without changing it."""
    return len(list(m.space(name)))


@m.pure
def either(x: int):
    """Declared pure and written as a GENERATOR, which is what decides."""
    yield x
    yield x + 1


#: Each term, how many answers it gives, and the class that follows from that.
#: The first three are declared above, the last three are the engine's own, and
#: one reader answers for both.
LAW = {
    S.double(2): (1, E.pureStructural),
    S.tally("&self"): (1, E.readOnlyLookup),
    S.either(1): (2, E.nondeterministicReadOnly),
    S["car-atom"](S.cons(S.a, S.b)): (1, E.pureStructural),
    S["get-atoms"](S["&self"]): (len(list(m.self)), E.nondeterministicReadOnly),
    S["and"](V.a, V.b): (4, E.nondeterministicReadOnly),
}

for term, (answers, rank) in LAW.items():
    check(f"{term} answers {answers}", len(m.eval(term)), answers)
    check(f"{term} is {rank}", m.self.effect_plan(term).effect, rank)

# A plan takes the strongest class of the operations it calls, so one
# enumerator anywhere in a term lifts the whole plan.
plan = m.self.effect_plan(S["car-atom"](S["get-atoms"](S["&self"])))
check("a plan names each operation", len(plan.operations), 2)
check("and takes the strongest", plan.effect, E.nondeterministicReadOnly)

done("effect_ranks")
