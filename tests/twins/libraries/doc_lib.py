"""examples/libraries/doc_lib.metta in Python: documentation is atoms in a space.

MeTTa HE's design, and the mettafied one: a `(@doc ...)` form is an ordinary
atom, so retrieval is a match and a program can reason about its own
documentation. Both halves of that land in Python without a new mechanism. A
`@m.define` docstring EMITS the `@doc` atom, so the example's two hand-written
forms are simply the docstrings of the two functions they document, and a
Google-style docstring emits all four parts.

The scoped formal `get-doc` is the receiver verb `m.doc(subject)`. This
example instead imports lib_doc and tests that library's unary raw-document
function: it returns the exact `(@doc ...)` atom and gives no answer for an
undocumented subject. The rung comments keep that semantic distinction
visible. `undocumented` remains lib_doc's own function and stays named.

Neither function is ANNOTATED, and that is the example's own program rather
than an omission: `(= (greet $who) $who)` declares no type, so each parameter's
`@type` comes back as `%Undefined%`, the marked name of the unconstrained type,
which is exactly what an undeclared parameter has. Annotating would emit
`(: greet (-> String String))` beside the doc and make `(greet 5)` a BadType
error the example never asked for.

The summaries end with a full stop where the example's prose does not, because
the `@desc` atom IS the docstring, verbatim, and a docstring that carries no
terminal punctuation is a pydocstyle finding. One character of prose is the
twin's own datum, the way its scratch file names are; what the claims are about
is the round trip.
"""

from metta import G, S

#: A PLACEHOLDER, not a measurement. The twins wave re-authored this file and
#: the integrator prices every budget in one pass on the merged tree, so a
#: figure measured here would pin a tree that does not ship
#: [assumed: this twin's inference cost is unmeasured on this branch;
#: commit=1e264c186c531e69acde5ad03ff6a79210626df4].
BUDGET = 1

#: What an undeclared parameter's type comes back as. `%Undefined%` is a marked
#: name rather than an identifier, so it takes rung 5's exact door.
UNDECLARED = S["@type"](S["%Undefined%"])

#: The two summaries, written once here and once as the docstring they are. A
#: drift between the two copies is the defect these claims exist to catch.
GREET_SUMMARY = G("Greets somebody by name.")
ADD_TWO_SUMMARY = G("Adds two numbers.")


def twin(m):
    """Document two functions from Python, then ask the space what it knows."""
    m.fn["import!"](m, S.library(S["lib_doc"]))

    @m.define
    def greet(who):
        """Greets somebody by name."""
        return who

    @m.define
    def add_two(a, b):
        """Adds two numbers.

        Args:
            a: the first
            b: the second

        Returns:
            their sum
        """
        return a + b

    # Retrieval answers the atom the docstring became.
    assert m.fn.get_doc(  # rung: lib_doc's unary raw-document query, not scoped m.doc
        S.greet
    ) == [
        S["@doc"](
            S.greet,
            S["@kind"](S.function),
            S["@desc"](GREET_SUMMARY),
            S["@params"]((S["@param"](UNDECLARED, S["@desc"](G(""))),)),
        )
    ]

    # @doc carries the kind, the summary and the parameters always, and the
    # return as well when the docstring says what comes back.
    assert m.fn.get_doc(  # rung: lib_doc's unary raw-document query, not scoped m.doc
        S.add_two
    ) == [
        S["@doc"](
            S.add_two,
            S["@kind"](S.function),
            S["@desc"](ADD_TWO_SUMMARY),
            S["@params"]((
                S["@param"](UNDECLARED, S["@desc"](G("the first"))),
                S["@param"](UNDECLARED, S["@desc"](G("the second"))),
            )),
            S["@return"](UNDECLARED, S["@desc"](G("their sum"))),
        )
    ]

    # An undocumented name answers nothing at all rather than an empty doc.
    assert list(m.fn.get_doc(  # rung: unary raw get-doc has an empty missing result
        S.greet_nobody
    )) == []
    assert list(m.fn.get_doc(  # rung: unary raw get-doc has an empty missing result
        S.missing
    )) == []

    # And a program can ask what it has NOT documented, which is the gap worth
    # closing in a real codebase. Both functions above are documented.
    assert list(m.fn.undocumented()) == []

    assert greet(G("ann")) == [G("ann")]
    assert add_two(2, 3) == [5]
