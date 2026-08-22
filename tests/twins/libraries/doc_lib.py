"""The Python twin of examples/libraries/doc_lib.metta.

Documentation through lib_doc, with MeTTa HE's vocabulary: documentation is
ATOMS IN A SPACE, so `get-doc` is a query rather than a separate mechanism and a
program can reason about its own docs.

The Python side of that design is already shipped and this twin is what it looks
like: a `@m.define` docstring EMITS the `@doc` atom, and a Google-style one emits
all four parts, so the source's hand-written `(@doc ...)` forms are the
docstrings of the two functions they document. One docstring, both worlds. The
expectations are still built as the terms they are, because a `test` compares
against an atom.
"""

from petta import S, val

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 11626 to 13448, +1822 (+15.67%), by the P14
#: twin-style rewrite: both functions are now written by @m.define, whose
#: docstring EMITS the (@doc ...) atom the source wrote by hand, so two
#: compiles replace two equation adds and two @doc adds. The net of the four
#: is +1,822 inferences. Prior: ADDED 2026-08-22 at 11626 by the wave-3
#: libraries baseline, which recorded no cause.
BUDGET = 13448

#: The description text, written once: it is both what the docstring says and
#: what the assertion expects, and a drift between the two would be the defect.
GREET_DESC = val("Greets somebody by name")


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`.
    """
    # !(import! &self (library lib_doc))
    yield m.eval(S["import!"](S["&self"], S.library(S.lib_doc)))

    @m.define
    def greet(who):
        """Greets somebody by name"""  # noqa: D415  -- the text is DATA: it is the @desc atom this file asserts, so a period or a recased first word would be a different atom
        # (@doc greet (@desc "Greets somebody by name"))
        # (= (greet $who) $who)
        return who

    @m.define(name="add-two")
    def add_two(a, b):
        """Adds two numbers

        Args:
            a: the first
            b: the second

        Returns:
            their sum
        """  # noqa: D415  -- the summary is DATA: it is the @desc atom this file asserts
        # (@doc add-two
        #       (@desc "Adds two numbers")
        #       (@params ((@param "the first") (@param "the second")))
        #       (@return "their sum"))
        # (= (add-two $a $b) (+ $a $b))
        return a + b

    # Retrieval is a match, so it answers the atom that was written.
    # !(test (get-doc greet) (@doc greet (@desc "Greets somebody by name")))
    yield m.eval(
        S.test(
            S["get-doc"](S.greet), S["@doc"](S.greet, S["@desc"](GREET_DESC))
        )
    )

    # @doc carries two, three or four parts depending on how much was written,
    # and get-doc answers whichever shape exists.
    # !(test (get-doc add-two)
    #        (@doc add-two
    #              (@desc "Adds two numbers")
    #              (@params ((@param "the first") (@param "the second")))
    #              (@return "their sum")))
    yield m.eval(
        S.test(
            S["get-doc"](S["add-two"]),
            S["@doc"](
                S["add-two"],
                S["@desc"](val("Adds two numbers")),
                S["@params"](
                    (
                        S["@param"](val("the first")),
                        S["@param"](val("the second")),
                    )
                ),
                S["@return"](val("their sum")),
            ),
        )
    )

    # An undocumented name answers nothing at all, rather than an empty doc, so
    # you test for it with a match.
    # !(test (collapse (get-doc greet-nobody)) ())
    yield m.eval(S.test(S.collapse(S["get-doc"](S["greet-nobody"])), ()))

    # Because docs are data, a program can ask what it knows about itself.
    # !(test (collapse (get-doc missing)) ())
    yield m.eval(S.test(S.collapse(S["get-doc"](S.missing)), ()))

    # And it can ask what it has NOT documented. Both functions above are
    # documented, so neither shows.
    # !(test (collapse (undocumented)) ())
    yield m.eval(S.test(S.collapse(S.undocumented()), ()))
