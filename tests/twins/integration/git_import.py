"""The Python twin of examples/integration/git_import.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, expr, val

#: Inferences this twin spends, its own tripwire.
BUDGET = 48286


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # !(import! &self (library lib_import))
    yield m.eval(expr(S["import!"], S["&self"], expr(S["library"], S["lib_import"])))

    # !(import_prolog_functions_from_file "./examples/integration/_fixtures/git_fixture.pl"
    #                                     (git_fixture_url))
    yield m.eval(
        expr(
            S["import_prolog_functions_from_file"],
            val("./examples/integration/_fixtures/git_fixture.pl"),
            expr(S["git_fixture_url"]),
        )
    )

    # !(git-import! (git_fixture_url "./repos"))
    yield m.eval(expr(S["git-import!"], expr(S["git_fixture_url"], val("./repos"))))

    # !(import! &self (library petta_fixture_lib fixture))
    yield m.eval(
        expr(S["import!"], S["&self"], expr(S["library"], S["petta_fixture_lib"], S["fixture"]))
    )

    # !(test (fixture-answer 14) 42)
    yield m.eval(expr(S["test"], expr(S["fixture-answer"], 14), 42))

    yield from ()
