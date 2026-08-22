"""examples/spaces/spaces_removeallatoms.metta in Python: emptying a space.

`remove-all-atoms` takes everything out, equations included, and the example's
sharpest claim is what that does to the function itself: it was imported INTO
this space, so the first call removes it, and the second call has no definition
left and answers itself. `(f 42)` goes the same way.

The removal is the engine's own function rather than `del space[pattern]`,
because the two are different operations: the pattern form removes what unifies
and leaves the space standing, while this one drains the store and takes the
imported definitions with it (residue, P14.10). Reading the aftermath is the
container door, `len(space)`.

`import!` is a directive with no Python door yet, so the library arrives
through `m.fn` (residue, P14.13).
"""

from petta import S

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 25312 to 24188, -1124 (-4.4%), by the twin contract
#: change: three `(test ...)` terms became three Python `assert`s, so `test`,
#: two `repr`s and one `collapse` over `get-atoms` left the engine, replaced by
#: atom comparison and `len`. The import, the definition and both removals are
#: unchanged. Against the example's 27040 the ratio is 0.8945.
#: Prior: 25312, pinned 2026-08-22 by the P14 twin-style rewrite and
#: measured under the previous contract, where twin(m) was a generator the
#: lane consumed form by form.
BUDGET = 24188


def twin(m):
    """Fill a space, empty it, then see what is left to answer with."""
    here = S[m.space_name]
    m.fn("import!")(here, S.library(S.lib_spaces))

    m += (S.friend, S.tim, S.tom)

    @m.define
    def f(_x):
        return 42

    m.fn("remove-all-atoms")(here)

    # The function was imported into this space, so it left with everything
    # else: a second call has nothing to reduce it and answers itself.
    assert m.one(S["remove-all-atoms"](here)) == S["remove-all-atoms"](here)
    assert m.one(S.f(42)) == S.f(42)
    assert len(m) == 0
