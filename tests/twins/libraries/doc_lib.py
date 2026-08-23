"""examples/libraries/doc_lib.metta in Python: documentation is atoms in a space.

MeTTa HE's design, and the mettafied one: a `(@doc ...)` form is an ordinary
atom, so retrieval is a match and a program can reason about its own
documentation. Both halves of that land in Python without a new mechanism. A
`@m.define` docstring EMITS the `@doc` atom, and a Google-style one emits all
four parts, so the example's hand-written forms are simply the docstrings of
the two functions they document; and `get-doc` is the subscript door, because
matching the space for the atom IS what the library function does.

An undocumented name therefore answers no rows, not an empty doc, which is the
distinction the example makes twice. A row projects by attribute, `row.desc`,
which is the naming convention re-applied.
"""

from petta import G, S, V

#: A PLACEHOLDER, not a measurement. The twins wave re-authored this file and
#: the integrator prices every budget in one pass on the merged tree, so a
#: figure measured here would pin a tree that does not ship
#: [assumed: this twin's inference cost is unmeasured on this branch;
#: commit=bf25e468a4b2ec6fb0c4666e4f841fbd8e2a5ccf].
BUDGET = 1

#: The description text, written once: it is both what the docstring says and
#: what the claim expects, and a drift between them would be the defect.
GREET_DESC = G("Greets somebody by name")


def twin(m):
    """Document two functions from Python, then ask the space what it knows."""
    m.eval(S["import!"](m, S.library(S["lib_doc"])))

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
    assert [row.desc for row in m[S["@doc"](S.greet, V.desc)]] == [S["@desc"](GREET_DESC)]

    # @doc carries two, three or four parts depending on how much was written.
    [documented] = m[S["@doc"](S["add-two"], V.desc, V.params, V.ret)]
    assert (documented.desc, documented.params, documented.ret) == (
        S["@desc"](G("Adds two numbers")),
        S["@params"]((S["@param"](G("the first")), S["@param"](G("the second")))),
        S["@return"](G("their sum")),
    )

    # An undocumented name answers nothing at all rather than an empty doc.
    assert list(m[S["@doc"](S["greet-nobody"], V.rest)]) == []
    assert list(m[S["@doc"](S.missing, V.rest)]) == []

    # And a program can ask what it has NOT documented, which is the gap worth
    # closing in a real codebase. Both functions above are documented.
    assert list(m.fn.undocumented()) == []
