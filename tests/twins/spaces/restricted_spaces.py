"""The Python twin of examples/spaces/restricted_spaces.metta: curated execution bases.

A restricted space keeps ordinary computation and its own equations, and refuses
everything it was not granted; the file operation reaches a runtime refusal that
`catch` can inspect, and the same operation answers normally in a space created
with that capability granted.

Both creations stay TERMS, and the reason is in the answers: `new-space` answers
the NAME it created, `&locked` and `&reader`, while `m.new_space(restricted=True)`
answers a handle over a name the engine picked (`&pyspace_1`). A symbol is not a
variable, so those two answers are not alpha-equal and no handle-door spelling
can carry these forms. The residue files the missing door, a NAMED restricted
space, against P14.10. Everything after the creation does use the handle:
`m.space("&locked")` names the space that was just made and `@<space>.define`
writes its equation.
"""

from petta import S, expr, val

#: The answer group the definition write contributes: `add-atom` answers the
#: unit, which is what Python's own None means at this seam (§9d).
WROTE = (expr(),)

#: The file the two capability probes ask about, named once because both forms
#: ask about the same path.
FIXTURE = val("examples/spaces/restricted_spaces.metta")

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 44917 to 46180, +1263 (+2.8%), by the P14 twin-style
#: rewrite, and one cause carries it: the equation moved from an evaluated
#: (add-atom &locked (= ...)) term to `@locked.define`, so the figure is the
#: decorator door's price for the first decorated function in a process
#: (~1,629) net of the term it replaces. The two creations are unchanged terms,
#: and the file capability probes still dominate the figure on both sides.
#: Prior: ADDED 2026-08-22 at 44917 by the wave-3 spaces baseline.
BUDGET = 46180


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    new_space, if_error = S["new-space"], S["if-error"]

    # A restricted space retains ordinary computation and its own equations.
    # !(new-space &locked (restricted))
    yield m.eval(new_space(S["&locked"], S.restricted()))
    locked = m.space("&locked")

    # !(add-atom &locked (= (double $x) (* $x 2)))
    @locked.define(name="double")
    def double(x):
        return x * 2

    yield WROTE

    # !(test (evalc (double 21) &locked) 42)
    yield m.eval(S.test(S.evalc(S.double(21), S[locked.space_name]), 42))

    # The file operation reaches a runtime refusal that catch can inspect.
    # !(test (if-error (catch (evalc (exists_file "...") &locked)) refused answered)
    #        refused)
    yield m.eval(
        S.test(
            if_error(
                S.catch(
                    S.evalc(S.exists_file(FIXTURE), S[locked.space_name])
                ),
                S.refused,
                S.answered,
            ),
            S.refused,
        )
    )

    # A capability is granted explicitly when the space is created.
    # !(new-space &reader (restricted (grants file)))
    yield m.eval(
        new_space(S["&reader"], S.restricted(S.grants(S.file)))
    )
    reader = m.space("&reader")

    # !(test (evalc (exists_file "...") &reader) true)
    yield m.eval(
        S.test(
            S.evalc(S.exists_file(FIXTURE), S[reader.space_name]),
            val(value=True),
        )
    )
