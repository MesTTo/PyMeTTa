"""The Python twin of examples/spaces/pre_add_hooks.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr, val

#: Inferences this twin spends, its own tripwire.
BUDGET = 10531


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # (= (guard (secret $x)) (refuse "no secrets in this pool"))
    m += expr(
        S["="],
        expr(S["guard"], expr(S["secret"], V["x"])),
        expr(S["refuse"], val("no secrets in this pool")),
    )

    # (= (guard (raw $x)) (accept (cooked $x)))
    m += expr(
        S["="],
        expr(S["guard"], expr(S["raw"], V["x"])),
        expr(S["accept"], expr(S["cooked"], V["x"])),
    )

    # (= (guard (dup $x)) (drop))
    m += expr(S["="], expr(S["guard"], expr(S["dup"], V["x"])), expr(S["drop"]))

    # (= (guard (plain $x)) (accept))
    m += expr(S["="], expr(S["guard"], expr(S["plain"], V["x"])), expr(S["accept"]))

    # !(declare-pre-add! &pool guard)
    yield m.eval(expr(S["declare-pre-add!"], S["&pool"], S["guard"]))

    # !(add-atom &pool (plain 1))
    yield m.eval(expr(S["add-atom"], S["&pool"], expr(S["plain"], 1)))

    # !(test (match &pool (plain $x) $x) 1)
    yield m.eval(expr(S["test"], expr(S["match"], S["&pool"], expr(S["plain"], V["x"]), V["x"]), 1))

    # !(add-atom &pool (raw 7))
    yield m.eval(expr(S["add-atom"], S["&pool"], expr(S["raw"], 7)))

    # !(test (match &pool (cooked $x) $x) 7)
    yield m.eval(
        expr(S["test"], expr(S["match"], S["&pool"], expr(S["cooked"], V["x"]), V["x"]), 7)
    )

    # !(add-atom &pool (dup 3))
    yield m.eval(expr(S["add-atom"], S["&pool"], expr(S["dup"], 3)))

    # !(test (collapse (match &pool (dup $x) $x)) ())
    yield m.eval(
        expr(
            S["test"],
            expr(S["collapse"], expr(S["match"], S["&pool"], expr(S["dup"], V["x"]), V["x"])),
            expr(),
        )
    )

    # !(test (repr (catch (add-atom &pool (secret 1))))
    #        "(Error (petta_add_refused &pool (secret 1) \"no secrets in this pool\") none)")
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["repr"], expr(S["catch"], expr(S["add-atom"], S["&pool"], expr(S["secret"], 1)))
            ),
            val('(Error (petta_add_refused &pool (secret 1) "no secrets in this pool") none)'),
        )
    )

    # !(test (repr (catch (add-atom &pool (uncovered 9))))
    #        "(Error (petta_hook_stuck &pool pre-add guard (uncovered 9)) none)")
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["repr"],
                expr(S["catch"], expr(S["add-atom"], S["&pool"], expr(S["uncovered"], 9))),
            ),
            val("(Error (petta_hook_stuck &pool pre-add guard (uncovered 9)) none)"),
        )
    )

    # (= (other-guard $a) (accept))
    m += expr(S["="], expr(S["other-guard"], V["a"]), expr(S["accept"]))

    # !(test (repr (catch (declare-pre-add! &pool other-guard)))
    #        "(Error (petta_hook_conflict &pool pre-add guard other-guard) none)")
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["repr"],
                expr(S["catch"], expr(S["declare-pre-add!"], S["&pool"], S["other-guard"])),
            ),
            val("(Error (petta_hook_conflict &pool pre-add guard other-guard) none)"),
        )
    )

    # !(undeclare-pre-add! &pool)
    yield m.eval(expr(S["undeclare-pre-add!"], S["&pool"]))

    # !(add-atom &pool (uncovered 10))
    yield m.eval(expr(S["add-atom"], S["&pool"], expr(S["uncovered"], 10)))

    # !(test (match &pool (uncovered $x) $x) 10)
    yield m.eval(
        expr(S["test"], expr(S["match"], S["&pool"], expr(S["uncovered"], V["x"]), V["x"]), 10)
    )

    yield from ()
