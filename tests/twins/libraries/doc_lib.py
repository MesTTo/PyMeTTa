"""examples/libraries/doc_lib.metta in Python: documentation is atoms in a space.

MeTTa HE's design, and the mettafied one: a `(@doc ...)` form is an ordinary
atom, so retrieval is a match and a program can reason about its own
documentation. Both halves of that land in Python without a new mechanism. A
`@m.define` docstring EMITS the `@doc` atom, and a Google-style one emits all
four parts, so the example's hand-written forms are simply the docstrings of
the two functions they document; and `get-doc` is the subscript door, because
matching the space for the atom IS what the library function does.

An undocumented name therefore answers no rows, not an empty doc, which is the
distinction the example makes twice.
"""

from petta import S, V, val

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 13448 to 9338, -4110 (-30.56%), by the idiomatic
#: rewrite: `get-doc` and its `collapse`s left the engine for the subscript
#: door, so four of the five claims are now matches the space answers
#: directly rather than library calls inside `test`. Measured min-of-three
#: with the MORK backend linked into this worktree, which the earlier figure
#: may not have been. Prior: 13448 was the last figure for the generator twin
#: that yielded `m.eval(S.test(...))` once per runnable form.
BUDGET = 9338

#: The description text, written once: it is both what the docstring says and
#: what the claim expects, and a drift between them would be the defect.
GREET_DESC = val("Greets somebody by name")


def twin(m):
    """Document two functions from Python, then ask the space what it knows."""
    m.eval(S["import!"](S["&self"], S.library(S.lib_doc)))  # rung: import!'s target space is an ARGUMENT, and a space handle does not encode as one (the engine answers "expects a space"), so the name is written as the symbol its own door takes

    @m.define
    def greet(who):
        """Greets somebody by name"""  # noqa: D415  -- the text is DATA: it is the @desc atom this file claims, so a period or a recased first word would be a different atom
        return who

    @m.define(name="add-two")
    def add_two(a, b):
        """Adds two numbers

        Args:
            a: the first
            b: the second

        Returns:
            their sum
        """  # noqa: D415  -- the summary is DATA: it is the @desc atom this file claims
        return a + b

    # Retrieval is a match, so it answers the atom that was written.
    assert m[S["@doc"](S.greet, V.desc)]["desc"] == [S["@desc"](GREET_DESC)]

    # @doc carries two, three or four parts depending on how much was written.
    [documented] = m[S["@doc"](S["add-two"], V.desc, V.params, V.ret)]
    assert (documented.desc, documented.params, documented.ret) == (
        S["@desc"](val("Adds two numbers")),
        S["@params"]((S["@param"](val("the first")), S["@param"](val("the second")))),
        S["@return"](val("their sum")),
    )

    # An undocumented name answers nothing at all rather than an empty doc.
    assert m[S["@doc"](S["greet-nobody"], V.rest)]["rest"] == []
    assert m[S["@doc"](S.missing, V.rest)]["rest"] == []

    # And a program can ask what it has NOT documented, which is the gap worth
    # closing in a real codebase. Both functions above are documented.
    assert m.fn("undocumented").all() == []
