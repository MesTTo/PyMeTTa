"""The Python twin of examples/types/dont_eval_type.metta: a user evaluation mask.

Declaring a type to be a `DontEvalType` makes every parameter of that type
arrive UNEVALUATED, with no naming rule behind it: the mask is a declaration
the program writes, not a convention the engine hard-codes. So
`(inspect-opaque (+ 1 2))` sees the expression rather than 3.

All three atoms are written at the container door. The equation's body is
`get-metatype`, and a compiled body resolves a free name EXACTLY, so a
hyphenated engine function cannot be reached from one (wave one recorded that
against P14.4 for `fibsmart`); the declaration goes with it, because the
annotation door writes its declaration AFTER the equation and that ordering is
its own residue entry, filed against P14.9 by types/outputtype.py.
"""

from petta import S, V

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 1510 to 1544, +34, by P14.8's
#: m.eval fuel-scope alignment: petta_fuel_step/2 now charges every
#: reduction as it does under `!`, less the two-inference-per-runnable-form
#: saving from the deterministic b_getval/2 fuel-balance read. Prior: ADDED
#: 2026-08-22 at 1510 by 47554fc's control/types twin baseline.
BUDGET = 1544


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    # (: OpaquePayload DontEvalType)
    m += S[":"](S.OpaquePayload, S.DontEvalType)
    # (: inspect-opaque (-> OpaquePayload Symbol))
    m += S[":"](
        S["inspect-opaque"], S["->"](S.OpaquePayload, S.Symbol)
    )
    # (= (inspect-opaque $written) (get-metatype $written))
    m += S["="](
        S["inspect-opaque"](V.written), S["get-metatype"](V.written)
    )

    # !(test (inspect-opaque (+ 1 2)) Expression)
    yield m.eval(
        S.test(
            S["inspect-opaque"](S["+"](1, 2)), S.Expression
        )
    )
