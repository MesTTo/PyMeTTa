"""examples/ch08-data/08-03-the-shipped-libraries/10-documentation_as_data.metta in Python: what a space has documented.

Documentation here is atoms, so reading it is matching and the answers are
whole `@doc` and `@doc-formal` atoms rather than rendered text.

This twin imports NOTHING, for the reason the original gives: every operation
reports on the space it is asked about, and an import would put another
library's names in the answers.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import G, S, arrow, typed

DOC = S["@doc"](
    S.twice,
    S["@desc"](G("Doubles a number")),
    S["@params"]((S["@param"](G("the number")),)),
    S["@return"](G("twice it")),
)


def formal(kind, params, result):
    """The `@doc-formal` shape the three reading doors answer with."""
    return S["@doc-formal"](
        S["@item"](S.twice),
        S["@kind"](S.function),
        S["@type"](kind),
        S["@desc"](G("Doubles a number")),
        S["@params"]((S["@param"](S["@type"](params), S["@desc"](G("the number"))),)),
        S["@return"](S["@type"](result), S["@desc"](G("twice it"))),
    )


def twin(m):
    """Which heads are documented, which are not, and the three shapes."""
    m += DOC
    m += typed(S.twice, arrow(S.Number, S.Number))

    @m.define
    def twice(x: int) -> int:
        # (= (twice $x) (* 2 $x))
        return 2 * x

    @m.define
    def undocumented_here(x):
        # (= (undocumented-here $x) $x)
        return x

    defined, documented = m.fn["defined-name"], m.fn["documented"]
    in_space, missing = m.fn["documented-space"], m.fn["undocumented-space"]

    # Every head this space holds an equation for, once each. Builtins are
    # not in it: they are not equations.
    assert sorted(defined(), key=str) == [S.twice, S.undocumented_here]

    # And the split on whether a `@doc` atom names the head.
    assert documented() == [S.twice]
    assert missing(m) == [S.undocumented_here]
    assert in_space(m) == [S.twice]

    # Each takes the space explicitly, for asking about one you are not
    # running in.
    empty = m.metta.space(S.empty)
    empty += S["="](S.f(S.x), S.x)
    assert in_space(empty) == []
    assert missing(empty) == [S.f]

    # `get-doc-space` answers the `@doc` atom AS WRITTEN, which is the shape
    # a program editing documentation wants.
    assert m.fn["get-doc-space"](m, S.twice) == [DOC]

    # `get-doc-atom` answers the FORMAL shape and fills its types from the
    # atom alone, so every slot is the gradual default.
    undefined = S["%Undefined%"]
    assert m.fn["get-doc-atom"](m, S.twice) == [formal(undefined, undefined, undefined)]

    # `get-doc-single-atom` reads the DECLARED type out of the space and
    # spreads it across the parameters.
    typed_doc = formal(arrow(S.Number, S.Number), S.Number, S.Number)
    assert m.fn["get-doc-single-atom"](m, S.twice) == [typed_doc]

    # `get-doc-function` takes the arrow as an argument rather than looking
    # it up, for a computed type or a name documented at two arities.
    by_arrow = m.fn["get-doc-function"]
    assert by_arrow(m, S.twice, arrow(S.Number, S.Number)) == [typed_doc]
    assert by_arrow(m, S.twice, arrow(S.String, S.String)) == [
        formal(arrow(S.String, S.String), S.String, S.String)
    ]

    # The step those three share, callable on its own.
    params = m.fn["get-doc-params"]
    assert params(
        (S["@param"](G("the number")),), S["@return"](G("twice it")), (S.Number, S.Number)
    ) == [
        (
            (S["@param"](S["@type"](S.Number), S["@desc"](G("the number"))),),
            S["@return"](S["@type"](S.Number), S["@desc"](G("twice it"))),
        )
    ]
    assert params((), S["@return"](G("nothing to say")), (S.Bool,)) == [
        ((), S["@return"](S["@type"](S.Bool), S["@desc"](G("nothing to say"))))
    ]

    # `help!` prints rather than answering, which is what a person at a
    # console wants and what a program never does.
    assert m.fn["help!"](S.twice) == [()]
    assert m.fn["help!"](S.undocumented_here) == [()]


#: MEASURED on this branch rather than inherited: this twin is new, so there is
#: no earlier pin to move
#: [measured 2026-09-07: 49054 inferences, 0.9401x the example's 52179; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3;
#: fixture=docs/every-atom-has-an-example at its example commits; commit=WORKTREE].
BUDGET = 49054
