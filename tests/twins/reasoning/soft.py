"""Purpose: express the soft-reasoning example through the Python surface.

Weak unification and attention run in the shipped ``lib_soft`` and
``lib_measure`` libraries.

Guarantees:
  - all seventeen source claims cover symmetric symbol similarity, recursive
    soft scoring, variable binding, space matching, best-match selection, and
    normalized attention [measured: twin completed; command=PYTHONPATH=bindings/python python -c "import runpy; from petta import MeTTa; runpy.run_path('bindings/python/tests/twins/reasoning/soft.py') ['twin'](MeTTa(petta_path='.'))"; fixture=fresh isolated process; commit=b1599bdc8201a04a3689c1a88707b6f4b53b4d22]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from petta import S, V

#: Imports and the soft library's hyphenated names use the current naming
#: doors. The binding-producing score also stays a let term because a value
#: call does not expose the variable binding it found.
RUNG = "imports and soft-library calls use current naming doors, and one binding leaves through let"

#: The import target and the named zoo operand required by current term forms.
SELF = S["&self"]
ZOO = S["&zoo"]

#: Successful costs from two complete concurrent ten-round observations plus
#: eight subsequent complete gate-protocol observations
#: [measured: 186644..186685 over 28 observations; command=python bindings/python/tools/twin_coverage.py --observe --rounds 10, repeated twice, then python bindings/python/tools/twin_coverage.py, repeated eight times; fixture=full-lane/218/workers=32; commit=b1599bdc8201a04a3689c1a88707b6f4b53b4d22].
BUDGET = {
    "minimum": 186644,
    "maximum": 186685,
    "observations": 28,
    "protocol": "full-lane/218/workers=32",
}


def twin(m):
    """Load soft matching, state two similarities, then check all seventeen claims."""
    m.eval(S["import!"](SELF, S.library(S.lib_measure)))
    m.eval(S["import!"](SELF, S.library(S.lib_soft)))

    m += S.similar(S.cat, S.feline, 0.8)
    m += S.similar(S.dog, S.wolf, 0.7)

    sym_sim = m.fn("sym-sim")
    soft_score = m.fn("soft-score")

    assert sym_sim(S.cat, S.cat) == 1.0
    assert sym_sim(S.cat, S.feline) == 0.8
    assert sym_sim(S.feline, S.cat) == 0.8
    assert sym_sim(S.cat, S.dog) == 0.0

    assert soft_score(S.likes(S.cat, S.fish), S.likes(S.cat, S.fish)) == 1.0
    assert soft_score(S.likes(S.feline, S.fish), S.likes(S.cat, S.fish)) == 0.8
    assert soft_score(S.likes(S.feline, S.wolf), S.likes(S.cat, S.dog)) == 0.7
    assert soft_score(S.likes(S.cat), S.likes(S.cat, S.fish)) == 0.0
    assert soft_score(S.likes(S.cat, S.fish), S.hates(S.cat, S.fish)) == 0.0
    assert soft_score(3, 3) == 1.0
    assert soft_score(3, 4) == 0.0

    assert soft_score(V.x, S.anything) == 1.0
    probe = m.one(
        S.let(
            V.probe,
            S["soft-score"](S.likes(V.who, S.fish), S.likes(S.cat, S.fish)),
            (V.probe, V.who),
        )
    )
    assert tuple(probe) == (1.0, S.cat)

    zoo = m.space("&zoo")
    zoo += S.likes(S.cat, S.fish)
    zoo += S.likes(S.dog, S.bones)
    zoo += S.likes(S.bird, S.seeds)

    soft_match = m.fn("soft-match")
    closest = soft_match.all(ZOO, S.likes(S.feline, S.fish), 0.5)
    assert (
        len(closest) == 1
        and closest[0][0] == 0.8
        and closest[0][1] == S.likes(S.cat, S.fish)
    )
    assert m.fn("soft-best")(ZOO, S.likes(S.feline, S.fish)) == S.likes(
        S.cat, S.fish
    )
    assert len(soft_match.all(ZOO, S.likes(V.x, V.y), 0.0)) == 3

    scored = soft_match.all(ZOO, S.likes(S.feline, V.f), 0.0)
    distribution = m.fn("ws-softmax")(scored, 1.0)
    assert abs(m.fn("ws-total")(distribution) - 1.0) < 1.0e-9
