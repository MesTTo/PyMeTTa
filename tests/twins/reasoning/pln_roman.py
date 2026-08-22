"""Purpose: express the PLN Roman example through the Python surface.

The twin runs its bounded proof search over the four-sentence knowledge base.

Guarantees:
  - the query derives the source truth value and the complete four-premise
    evidence stamp [measured: twin completed; command=PYTHONPATH=bindings/python python -c "import runpy; from petta import MeTTa; runpy.run_path('bindings/python/tests/twins/reasoning/pln_roman.py') ['twin'](MeTTa(petta_path='.'))"; fixture=fresh isolated process; commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from petta import S, equation

#: STV's four symbol-head clauses, the data-valued knowledge base, the scoped
#: stack pragma, and PLN.Query's dotted name require the current term doors.
RUNG = "symbol-head STV clauses, knowledge-base data, and the scoped PLN query use term doors"

#: The import target required by the current import form.
SELF = S["&self"]

#: Successful costs from two complete concurrent ten-round observations plus
#: eight subsequent complete gate-protocol observations
#: [measured: 3285491..3285661 over 28 observations; command=python bindings/python/tools/twin_coverage.py --observe --rounds 10, repeated twice, then python bindings/python/tools/twin_coverage.py, repeated eight times; fixture=full-lane/218/workers=32; commit=WORKTREE].
BUDGET = {
    "minimum": 3285491,
    "maximum": 3285661,
    "observations": 28,
    "protocol": "full-lane/218/workers=32",
}


def _sentence(left, right, strength, identifier):
    """Build one PLN sentence with its truth value and one-item evidence stamp."""
    return S.Sentence(
        (S.Inheritance(left, right), S.stv(strength, 0.9)),
        (identifier,),
    )


def twin(m):
    """Load PLN, state the Roman-diamond knowledge base, and ask for A to D."""
    m.eval(S["import!"](SELF, S.library(S.lib_pln)))

    for concept, strength in (
        (S.A, 0.5),
        (S.B, 0.25),
        (S.C, 0.25),
        (S.D, 0.5),
    ):
        m += equation(S.STV(concept)).to(S.stv(strength, 0.9))

    m += equation(S.kb()).to(
        (
            _sentence(S.A, S.B, 0.25, 1),
            _sentence(S.A, S.C, 0.25, 2),
            _sentence(S.B, S.D, 0.5, 3),
            _sentence(S.C, S.D, 0.5, 4),
        )
    )

    raised_stack = ((S["max-stack-depth"], 100_000_000),)
    answer = m.one(
        S["with-pragma!"](
            raised_stack,
            S["PLN.Query"](S.kb(), S.Inheritance(S.A, S.D)),
        )
    )
    assert answer[0] == S.stv(0.5, 0.9473684210526316) and tuple(answer[1]) == (
        1,
        2,
        3,
        4,
    )
