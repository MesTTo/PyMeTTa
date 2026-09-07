"""examples/ch14-seeing-your-program/03-the_clock_and_the_command_line.metta in Python: the clock, its written form, and the process's arguments.

What these answer is about the RUN rather than about any data the program
holds, so the claims are properties -- monotone, four characters, nothing
past the end -- rather than values.

`argv` answers NOTHING past the end of the argument list, which is one answer
fewer than an error and exactly what a caller checking for an optional
argument wants: an empty list is that absence.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import G, S, V, equation, fn, if_, lib


def twin(m):
    """Unix time, strftime, and the argument list by index."""
    m += lib.string
    now, written = m.fn["current-time"], m.fn["format-time"]
    argument, length = m.fn.argv, m.fn["string-length"]

    # Unix time as a float, so arithmetic on it is ordinary arithmetic.
    assert now()[0].value > 1700000000.0

    # It moves forward and never backward, which is the one property a
    # program timing itself depends on.
    assert m.answers(fn.le(S.current_time(), S.current_time())) == [True]

    # Everything that is not a directive is copied through, and the answer is
    # a NAME rather than a String.
    assert written(G("abc")) == [S.abc]
    assert written(G("abc")) != [G("abc")]
    assert length(written(G("a literal"))[0]) == [9]
    assert length(written(G(""))[0]) == [0]
    # A doubled per cent is the one escape, and it writes one character.
    assert length(written(G("%%"))[0]) == [1]

    # The directives are strftime's own, so a year is four characters and an
    # ISO date is ten, whatever day this runs on.
    assert length(written(G("%Y"))[0]) == [4]
    assert length(written(G("%Y-%m-%d"))[0]) == [10]
    assert length(written(G("%H:%M:%S"))[0]) == [8]

    # Reading past the end answers nothing at all.
    assert argument(999) == []
    assert argument(-1) == []

    # The same index answers the same thing, whatever the runner passed.
    assert argument(0) == argument(0)

    # Which makes "is there an argument here" a collapse rather than a
    # length: the empty tuple is the absent argument.
    # Built as DATA rather than compiled, because the equation's own shape is
    # what the claim is about: a Python assignment inside a body compiles to
    # `let*`, and the original writes the single-binding `let`.
    @m.rules
    def optional(index, default):
        """(= (argument-or $i $d) (let $f (collapse (argv $i)) (if ...)))."""
        yield equation(S.argument_or(index, default)).to(
            S.let(  # rung: a single-binding let has no Python statement form
                V.found,
                S.collapse(S.argv(index)),  # rung: a stored collapse is a term
                if_(S["=="](V.found, ()), default, S.car_atom(V.found)),
            )
        )

    assert m.fn["argument-or"](999, S.no_such_argument) == [S.no_such_argument]
    assert m.fn["argument-or"](0, S.no_such_argument) != [S.no_such_argument]


#: MEASURED on this branch rather than inherited: this twin is new, so there is
#: no earlier pin to move
#: [measured 2026-09-07: 53516 inferences, 0.9223x the example's 58027; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3;
#: fixture=docs/every-atom-has-an-example at its example commits; commit=WORKTREE].
BUDGET = 53516
