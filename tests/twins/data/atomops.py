"""examples/data/atomops.metta in Python: structure, and what refuses.

The file has two halves and they belong on different rungs. Taking apart an
expression that IS an expression is Python's own work and costs no engine at
all: `e[0]` is the head, `e[1:]` is the rest, `e[i]` is a position, `expr(0,
*e)` builds a new one. Those claims are written that way.

The other half is about what the operations do with an argument they cannot
use, and Python cannot say it: `e[5]` raises IndexError where `index-atom`
answers `()`, and `len(5)` raises TypeError where `size-atom` answers `()`.
Answering rather than raising IS the claim, so those go to the operations
themselves, by name.

The last block is sharper still. An unbound VARIABLE is not a value Python
has, and handing one where an expression is expected used to be answered
instead of refused: `(car-atom $u)` unified its argument with a fresh cons
cell and answered its head. Each of those claims names its own operation
because the refusal belongs to that operation.
"""

from petta import S, V, alpha_eq, expr, val

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 17624 to 8889, -8735 (-49.56%), by the twin-shape
#: rewrite: twenty-six `test` wrappers left the engine for `assert`, and four
#: claims left it entirely: `e[0]`, `e[1:]`, `e[i]` and `expr(0, *e)` are
#: native operations on an atom already held in Python. What stays is the
#: half about refusals, which only the operations themselves can answer.
#: Against the example's 31211 the ratio is 0.2848 [measured 2026-08-22 min-
#: of-3: `twin_coverage.py --measure examples/data/atomops.metta`]. Prior:
#: RE-PINNED at 17624 by the wave-4 idiom rewrite.
BUDGET = 8889


def twin(m):
    """Take an expression apart, then ask what refuses and how."""
    e = expr(1, 2, 3)
    pair = S.A(S.B)
    nothing = [expr()]

    def guarded(call):
        """Whether an operation refuses a call or answers it."""
        return m.eval(S["if-error"](S.catch(call), S.refused, S.answered))

    # Structure, in Python, with no crossing at all.
    assert expr(0, *e) == expr(0, 1, 2, 3)
    assert e[0] == 1
    assert list(e[1:]) == [2, 3]
    assert e[1] == 2

    assert m.fn("id")(5) == 5
    assert alpha_eq(S.Father(V.X), S.Father(V.Y))
    assert not alpha_eq(S.Father(V.X), S.Son(V.X))
    assert m.fn("first-from-pair")(pair) == S.A
    assert m.fn("second-from-pair")(pair) == S.B

    # An argument the operation cannot use is answered, not raised.
    assert m.fn("index-atom").all(e, 5) == nothing
    assert m.fn("index-atom").all(e, S.a) == nothing
    assert m.fn("size-atom").all(5) == nothing
    assert m.fn("sort-atom").all(5) == nothing
    assert m.fn("unique-atom").all(5) == nothing
    assert m.fn("alpha-unique-atom").all(5) == nothing
    assert m.fn("intersection-atom").all(5, S.a()) == nothing

    # Two of them answer an Error that quotes the call instead.
    not_expression = val("Atom is not an ExpressionAtom")
    smallest, largest = S["min-atom"](5), S["max-atom"](5)  # rung: the expected Error QUOTES the call, so each head is written as itself
    assert m.fn("min-atom").all(5) == [S.Error(smallest, not_expression)]
    assert m.fn("max-atom").all(5) == [S.Error(largest, not_expression)]

    # An unbound variable is a program error, and every guarded position
    # refuses it by name rather than solving for it.
    assert guarded(S["car-atom"](V.unbound)) == [S.refused]  # rung: the claim is this operation's own refusal of an unbound argument
    assert guarded(S["size-atom"](V.unbound)) == [S.refused]  # rung: same claim, this operation
    assert guarded(S["sort-atom"](V.unbound)) == [S.refused]  # rung: same claim, this operation
    assert guarded(S["index-atom"](V.unbound, 0)) == [S.refused]  # rung: same claim, this operation
    assert guarded(S["subtraction-atom"](V.unbound, S.a(S.b))) == [S.refused]

    # A bound argument is untouched, which is the half that makes the refusal
    # worth anything.
    assert guarded(S["car-atom"](expr(1, 2))) == [S.answered]  # rung: the same guarded position, now given a real expression
    assert expr(1, 2)[0] == 1

    # The refusal is narrow: index-atom's SECOND argument is relational by
    # design, so an unbound index still enumerates every position in turn.
    assert m.fn("index-atom").all(S.a(S.b, S.c), V.i) == [S.a, S.b, S.c]
