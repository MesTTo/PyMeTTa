"""The Python twin of examples/integration/git_import.metta: a repository as a library.

Four services in a row, each named as a term because each names an engine
service rather than a computation: `lib_import` is loaded, a Prolog file exports
one predicate, `git-import!` clones the fixture repository into `./repos`, and
the cloned library is imported by name. The two file paths cross as `val(...)`,
the marked-data door.
"""

from petta import S, val

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 48286 to 48663, +377 (+0.78%), and NOT by this rewrite:
#: the pre-rewrite twin measures the same figures on this tree, so the old
#: number is stale against the engine rather than moved by anything here.
#: This twin has TWO reproducible costs and the difference is the PATH the lane
#: runs under. `sh check.sh` prepends the virtualenv's `bin` to PATH before the
#: lane, and under that PATH the twin costs 48663 and the example 52069; with an
#: unmodified PATH they cost 48587 and 51993. Each figure is stable across three
#: fresh processes, the gap is exactly 76 on BOTH sides so the ratio does not
#: move, and VIRTUAL_ENV alone does not cause it, only PATH. The pin is the
#: figure the GATE produces, since `sh check.sh twins` is what judges this file
#: [measured 2026-08-22: `env PATH=<venv>/bin:$PATH twin_coverage.py --measure`
#: against the same command without it]. Prior: ADDED 2026-08-22 at 48286 by the
#: wave-3 twin baseline.
BUDGET = 48663


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    # !(import! &self (library lib_import))
    yield m.eval(S["import!"](S["&self"], S.library(S.lib_import)))

    # !(import_prolog_functions_from_file "./examples/integration/_fixtures/git_fixture.pl"
    #                                     (git_fixture_url))
    yield m.eval(
        S.import_prolog_functions_from_file(val("./examples/integration/_fixtures/git_fixture.pl"),
            S.git_fixture_url())
    )

    # !(git-import! (git_fixture_url "./repos"))
    yield m.eval(S["git-import!"](S.git_fixture_url(val("./repos"))))

    # !(import! &self (library petta_fixture_lib fixture))
    yield m.eval(
        S["import!"](S["&self"], S.library(S.petta_fixture_lib, S.fixture))
    )

    # !(test (fixture-answer 14) 42)
    yield m.eval(S.test(S["fixture-answer"](14), 42))
