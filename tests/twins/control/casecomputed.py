"""examples/control/casecomputed.metta in Python: cases as a value.

The cases of a `case` are usually written out, and then they are syntax: the
form compiles one nested conditional out of them once. They do not have to be
written out. A cases argument that arrives as a VALUE is compiled when it
arrives, so the branches can be decided while the program runs, and that is
what lets `case` be given another name as an ordinary definition.

`case` over branches a program computes is the one shape Python has no word
for at all. Python's `match` statement is a statement whose arms are SYNTAX,
so no Python spelling takes them as an argument, and the compiled subset has
no lowering for the statement either (P14.4). Written-out cases are stated
beside handed-over ones here on purpose, so writing half of them as Python
`if`s would break the very pairing the file exists to show.

Two things do move into Python. `cons-atom` onto a tail is writing the
expression, so `numbered-cases` says the pair list it builds; and a refusal
crosses the seam as a Python exception, so `catch` is `except` and the branch
that reads what came back is Python's own.
"""

from petta import S, V, equation
from petta.errors import MettaOperationError

#: Why this twin sits below the top rung; see the module docstring.
RUNG = "a `case` whose branches arrive as a VALUE has no Python spelling: match's arms are syntax"

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 10558 to 9636, -922 (-8.7%), by the twin contract
#: change: eleven `test` wrappers, two collapses and one `car-atom`/`catch`
#: LEFT the engine for `assert`, an empty list and Python's `except`; nothing
#: entered, because a `case` over branches a program computes has no Python
#: spelling to enter as. Measured min-of-3 over fresh processes with the MORK
#: backend linked in, which the artefact-free worktree omits and which moves
#: a compiled twin by about 10 inferences per definition; against the
#: example's 21371 the ratio is 0.4509. Prior: 10558, the transliterated twin
#: this replaces.
BUDGET = 9636


def twin(m):
    """Write cases out, hand them over, and refuse a list that is not one."""
    numbers = ((1, S.one), (2, S.two))
    with_default = ((1, S.one), (S.Empty, S.none))

    # (= (switch $value $cases) (case $value $cases))
    m += equation(S.switch(V.value, V.cases)).to(S.case(V.value, V.cases))

    # !(test (switch 2 ((1 one) (2 two))) two)
    assert m.eval(S.switch(2, numbers)) == [S.two]

    # Handed over or written out, the same cases answer the same thing.
    # !(test (case 2 ((1 one) (2 two))) two)
    assert m.eval(S.case(2, numbers)) == [S.two]

    # Cases the program builds are cases too.
    # (= (numbered-cases) (cons-atom (1 one) ((2 two))))
    m += equation(S["numbered-cases"]()).to(numbers)

    # !(test (switch 1 (numbered-cases)) one)
    assert m.eval(S.switch(1, S["numbered-cases"]())) == [S.one]
    # !(test (switch 2 (numbered-cases)) two)
    assert m.eval(S.switch(2, S["numbered-cases"]())) == [S.two]

    # `Empty` is the branch a key with NO ANSWERS takes, and it means that on
    # both paths. Here the key is `(empty)`, so the default answers.
    # (= (key-of-nothing $cases) (case (empty) $cases))
    m += equation(S["key-of-nothing"](V.cases)).to(S.case(S.empty(), V.cases))

    # !(test (key-of-nothing ((1 one) (Empty none))) none)
    assert m.eval(S["key-of-nothing"](with_default)) == [S.none]
    # !(test (case (empty) ((1 one) (Empty none))) none)
    assert m.eval(S.case(S.empty(), with_default)) == [S.none]

    # A key that answers but matches no branch is a different thing, and it
    # answers nothing whether an `Empty` branch is there or not.
    # !(test (collapse (switch 9 ((1 one) (Empty none)))) ())
    assert m.eval(S.switch(9, with_default)) == []
    # !(test (collapse (case 9 ((1 one) (Empty none)))) ())
    assert m.eval(S.case(9, with_default)) == []

    # One case pair handed over on its own is a pair too, and the definition
    # keeps the head it was written with.
    # (= (one-case $pair) (case 1 ($pair)))
    m += equation(S["one-case"](V.pair)).to(S.case(1, (V.pair,)))

    # !(test (one-case (1 hit)) hit)
    assert m.eval(S["one-case"]((1, S.hit))) == [S.hit]

    # Cases are checked when they arrive, because nothing after that point can
    # check them.
    # !(test (car-atom (catch (switch 1 foo))) Error)
    try:
        m.eval(S.switch(1, S.foo))
        refused = None
    except MettaOperationError as error:
        refused = error
    assert refused is not None

    # Written out, `(case 1 foo)` is not a case with bad cases, it is a program
    # using the name as data, and it still reduces to itself.
    # !(test (case 1 foo) (case 1 foo))
    assert m.eval(S.case(1, S.foo)) == [S.case(1, S.foo)]
