"""The Python twin of examples/functions/specializefunctiontypes.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr

#: Inferences this twin spends, its own tripwire.
BUDGET = 3987


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # (= (g $x) $x)
    m += expr(S["="], expr(S["g"], V["x"]), V["x"])

    # (: f (-> Atom Number Atom))
    m += expr(S[":"], S["f"], expr(S["->"], S["Atom"], S["Number"], S["Atom"]))

    # (: f (-> Atom String Atom))
    m += expr(S[":"], S["f"], expr(S["->"], S["Atom"], S["String"], S["Atom"]))

    # (= (f $g $x)
    #    (repra ($g $x)))
    m += expr(S["="], expr(S["f"], V["g"], V["x"]), expr(S["repra"], expr(V["g"], V["x"])))

    # !(f g 42)
    yield m.eval(expr(S["f"], S["g"], 42))

    # !(test (match &self (: f_Spec_[g] (-> Atom Number Atom)) ok) ok)
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["match"],
                S["&self"],
                expr(S[":"], S["f_Spec_[g]"], expr(S["->"], S["Atom"], S["Number"], S["Atom"])),
                S["ok"],
            ),
            S["ok"],
        )
    )

    # !(test (match &self (: f_Spec_[g] (-> Atom String Atom)) ok) ok)
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["match"],
                S["&self"],
                expr(S[":"], S["f_Spec_[g]"], expr(S["->"], S["Atom"], S["String"], S["Atom"])),
                S["ok"],
            ),
            S["ok"],
        )
    )

    yield from ()
