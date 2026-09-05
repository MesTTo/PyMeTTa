"""Purpose: classify an operation with a decorator, and read the rank it carries.

The lattice has TWO axes and one meeting point. What an operation touches gives
the ordering, structural then reads then writes then oracle; how many answers
it gives sets a FLOOR. Answering more than once forces at least
`nondeterministicReadOnly`, however structural the computation is. Above that
floor the state axis governs alone, so `note` writes and answers exactly once
and still outranks a generator.

That floor is why there are four decorators for five classes. `@m.pure`, `@m.reads`,
`@m.writes` and `@m.io` are `m.op` with `effect=` filled in, so the
classification is a name rather than a string argument. The fifth is DERIVED: a
Python generator is nondeterministic whatever it declares, so the registration
reads that off the function and lifts the class. Declaring it by hand would
restate what the library already worked out.

The engine holds its own builtins to the same law, which is the whole of why
`get-atoms` and `and` sit where they do.

Guarantees:
  - every row of LATTICE holds: the term answers that many times and carries
    that class, whether it was declared here or shipped by the engine, and a
    single-answer operation still outranks a generator when it writes
    [tested: effect_ranks example; commit=75827a539a6928d1a737edf4cb044c5019fcb044]
  - a plan takes the strongest class of the operations it calls
    [tested: effect_ranks example; commit=75827a539a6928d1a737edf4cb044c5019fcb044]
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
    """Declared pure and written as a GENERATOR, which is what lifts it."""
    yield x
    yield x + 1


@m.writes
def note(x: int) -> int:
    """Changes state and answers once, which is the floor's other side."""
    return x


@m.io
def clock() -> int:
    """Observes an oracle, the top of the ordering."""
    return 7


#: Each term, how many answers it gives, and the class it carries. Read the
#: middle column against the right one: rows three, six and seven are lifted BY
#: their answer count, and rows four and five outrank them on one answer, which
#: is the floor and the ordering doing different jobs. The first five terms are
#: declared above and the last three are the engine's own; one reader answers
#: for both.
LATTICE = {
    S.double(2): (1, E.pureStructural),
    S.tally("&self"): (1, E.readOnlyLookup),
    S.either(1): (2, E.nondeterministicReadOnly),
    S.note(1): (1, E.writesState),
    S.clock(): (1, E.oracleIO),
    S["car-atom"](S.cons(S.a, S.b)): (1, E.pureStructural),
    S["get-atoms"](S["&self"]): (len(list(m.self)), E.nondeterministicReadOnly),
    S["and"](V.a, V.b): (4, E.nondeterministicReadOnly),
}

for term, (answers, rank) in LATTICE.items():
    check(f"{term} answers {answers}", len(m.eval(term)), answers)
    check(f"{term} is {rank}", m.self.effect_plan(term).effect, rank)

# A plan takes the strongest class of the operations it calls, so one
# enumerator anywhere in a term lifts the whole plan.
plan = m.self.effect_plan(S["car-atom"](S["get-atoms"](S["&self"])))
check("a plan names each operation", len(plan.operations), 2)
check("and takes the strongest", plan.effect, E.nondeterministicReadOnly)

done("effect_ranks")
