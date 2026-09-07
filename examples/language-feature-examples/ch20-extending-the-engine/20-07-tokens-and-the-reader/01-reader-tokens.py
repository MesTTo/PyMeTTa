"""examples/ch20-extending-the-engine/20-07-tokens-and-the-reader/01-reader-tokens.metta in Python: the reader as an extension seam.

A token pattern IS text, a regular expression, and a constructor IS a name,
so the two arguments are `G(...)` and `S...` respectively, which is the whole
of the notation.

Reading is what `parse` does, and the claims compare its answers through
`repr`, because what a registration changes is the SHAPE the reader builds
rather than any value.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import G, S

PIXELS = G("[0-9]+px")
PERCENT = G("[0-9]+%")


def twin(m):
    """Register a class, read through it, replace it, and take it back out."""
    register, unregister = m.fn["register-token!"], m.fn["unregister-token!"]

    def written(text):
        """What the reader builds from one token, as its source text.

        `(repr (parse ...))` is BUILT and evaluated once rather than called
        through `m.fn.parse`, which is a source-input door: the lane refuses
        a real call to it and permits the built term, and the built term is
        also what the original writes.
        """
        return m.answers(S.repr(S.parse(text)))  # rung: parse is a source door

    # Before registering, a token that is not a number and not a string is a
    # SYMBOL, whatever it looks like.
    assert written(G("12px")) == [G("12px")]

    # Registering is one call, and it answers True.
    assert register(PIXELS, S.Pixels) == [True]

    # Now the same text reads as an application of the constructor to the
    # token's own text, which arrives as a String.
    assert written(G("12px")) == [G('(Pixels "12px")')]

    # It is a TOKEN rule rather than a form rule, so it fires wherever a
    # token can appear and the rest of the form reads normally.
    assert written(G("(width 12px)")) == [G('(width (Pixels "12px"))')]
    assert written(G("(box 12px 4px)")) == [G('(box (Pixels "12px") (Pixels "4px"))')]

    # The pattern is anchored at both ends, so it classifies a whole token or
    # none of it.
    assert written(G("12pxy")) == [G("12pxy")]
    assert written(G("px")) == [G("px")]

    # A second pattern is a second class, and the two do not interfere.
    assert register(PERCENT, S.Percent) == [True]
    assert written(G("(size 50% 12px)")) == [
        G('(size (Percent "50%") (Pixels "12px"))')
    ]

    # Registering the same pattern again REPLACES its constructor rather than
    # adding a second class, because a token has one reading.
    assert register(PIXELS, S.Device) == [True]
    assert written(G("12px")) == [G('(Device "12px")')]

    # `unregister-token!` takes the pattern back out, and unregistering one
    # that is not there answers True rather than raising.
    assert unregister(PIXELS) == [True]
    assert written(G("12px")) == [G("12px")]
    assert unregister(PIXELS) == [True]
    assert written(G("50%")) == [G('(Percent "50%")')]
    assert unregister(PERCENT) == [True]
    assert written(G("50%")) == [G("50%")]

    # A pattern that is not text is refused by the operation's own name.
    bad_pattern = m.answers(S.repr(S.catch(S["register-token!"](12, S.Pixels))))
    assert bad_pattern == [
        G("(Error (type_error text 12) (context register-token! a token pattern is text))")
    ]

    # And a constructor that could not be written back is refused too: the
    # reader has to be able to spell what it builds.
    bad_constructor = m.answers(
        S.repr(S.catch(S["register-token!"](G("[0-9]+em"), G("not a symbol"))))
    )
    assert bad_constructor == [
        G(
            '(Error (domain_error metta_reader_constructor "not a symbol") '
            "(context (/ register-token! 3) the constructor must be a readable "
            "symbol))"
        )
    ]


#: MEASURED on this branch rather than inherited: this twin is new, so there is
#: no earlier pin to move
#: [measured 2026-09-07: 7481 inferences, 0.6017x the example's 12434; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3;
#: fixture=docs/every-atom-has-an-example at its example commits; commit=98397cdd04679cbf40b2d515076dadc09c1b0a32].
#: RE-PINNED 2026-09-08, 7481 to 7425 (-56), the evaluation-fuel scope marker
#: is a trailed write (fix/every-intermittent-root-caused, f6e05ca9):
#: `$metta_fuel_scope` is written open with b_setval/2 at scope open and read
#: with b_getval/2 where nb_current/2 used to answer, so an abandoned scope
#: closes itself when an exception unwinds the trail and the cleanup is the
#: fast ordinary exit, and every runnable form pays fewer inferences per scope;
#: a twin drops by about the count of its runnables, and the engine bench reads
#: evaluate and translate 1642 lower each on the same tree. Every twin here re-
#: reads its budget on the merged tree, minimum of three fresh processes
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=WORKTREE].
BUDGET = 7425
