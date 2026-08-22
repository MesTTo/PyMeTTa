"""The Python twin of examples/types/recursive_types.metta: types answer many.

One name may be declared more than once, so `get-type` is nondeterministic: a
blacksmith makes swords AND paperclips, and asking the type of `(blacksmith
iron)` answers both results. Applying a value to a value that is not a function
answers the pair of their types, which is the last form's subject.

Every atom here is a declaration and there is no equation to compile, so all
four are written as the atoms they are. The annotation door writes the same
atom, and `Sword | Paperclip` would even write both alternatives, but it needs
a Python class per MeTTa type and a function to hang the signature on, and
this file declares neither.
"""

from petta import S

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 4121 to 4238, +117, by P14.8's
#: m.eval fuel-scope alignment: petta_fuel_step/2 now charges every
#: reduction as it does under `!`, less the two-inference-per-runnable-form
#: saving from the deterministic b_getval/2 fuel-balance read. Prior: ADDED
#: 2026-08-22 at 4121 by 47554fc's control/types twin baseline.
BUDGET = 4238

SWORD = S["->"](S.Metal, S.Sword)
PAPERCLIP = S["->"](S.Metal, S.Paperclip)


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    # (: blacksmith (-> Metal Sword))
    m += S[":"](S.blacksmith, SWORD)
    # (: blacksmith (-> Metal Paperclip))
    m += S[":"](S.blacksmith, PAPERCLIP)
    # (: iron Metal)
    m += S[":"](S.iron, S.Metal)
    # (: gold Metal)
    m += S[":"](S.gold, S.Metal)

    kind = S["get-type"]

    # !(test (get-type iron) Metal)
    yield m.eval(S.test(kind(S.iron), S.Metal))
    # !(test (collapse (get-type blacksmith)) ((-> Metal Sword) (-> Metal Paperclip)))
    yield m.eval(
        S.test(
            S.collapse(kind(S.blacksmith)),
            (SWORD, PAPERCLIP),
        )
    )
    # !(test (collapse (get-type (blacksmith iron))) (Sword Paperclip))
    yield m.eval(
        S.test(
            S.collapse(kind(S.blacksmith(S.iron))),
            (S.Sword, S.Paperclip),
        )
    )
    # !(test (collapse (get-type (iron blacksmith)))
    #        ((Metal (-> Metal Sword)) (Metal (-> Metal Paperclip))))
    yield m.eval(
        S.test(
            S.collapse(kind(S.iron(S.blacksmith))),
            (
                (S.Metal, SWORD),
                (S.Metal, PAPERCLIP),
            ),
        )
    )
