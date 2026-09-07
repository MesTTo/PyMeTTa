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
#: fixture=docs/every-atom-has-an-example at its example commits; commit=98397cdd04679cbf40b2d515076dadc09c1b0a32].
#: RE-PINNED 2026-09-08, 53516 to 53591 (+75), the merges between this lane's
#: burn-down base (dfd5003f) and the tree that merged it, placed by a first-
#: parent ladder through the lane's own driver over ten twins at f8c4b672,
#: 4af59757, 90c08119, ad762ee7, 72f9cdf2 and 249389cb (ai-
#: tmp/integrator-849a9e/mergeTW-twin-ladder.log): the catalog-types merge
#: (1a3579fa) moves every twin by a lookup-and-layout step of about +5 for a
#: twin that makes no typed call and about +35 for one that does, plus about +6
#: per compiled definition through the argument-delivery check at the write
#: (the authoring fit re-measured 1370+1307 to 1406+1309), and +1411 for the
#: catalog twin that enumerates the 280 new rows; the two-sided-fragments merge
#: (4af59757) moves the sequence-variable twins by what their fixed rows now
#: compute (+2604 for the two-sided fragments, -217 for the fence, +19 for
#: restricted spaces); the every-atom merge (90c08119) re-authored the reading-
#: forms twin into the sread half (+3017) and added forty-six twins pinned on
#: its own base 31d54e19, which the merges since moved by the same clusters;
#: the gate-hygiene merge (ad762ee7) makes the tabling twins cheaper by the wfs
#: library no longer loading eagerly. Every twin here re-reads its budget on
#: the merged tree, minimum of three fresh processes [measured 2026-09-08: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=08f6f4df19a283bb84ba5f679c83944b42685b2e].
BUDGET = 53591
