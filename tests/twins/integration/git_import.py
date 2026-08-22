"""examples/integration/git_import.metta in Python: a repository as a library.

Four acts, then one question. A fixture Prolog file answers a clone URL,
`git-import!` clones that repository into `./repos`, the clone is imported as an
ordinary named library, and the function it ships answers.

The Prolog step is Python's own door: `m.register_prolog(path=, names=)` is what
`import_prolog_functions_from_file` names in MeTTa, and it takes the file and
the predicates to export in the same order. The other three stay terms because
`import!` and `git-import!` have no Python spelling; the space they write is
therefore named as a symbol, which the residue records.
"""

from petta import S, val

#: The space every import writes.
SELF = S["&self"]  # rung: no import door hangs off the space handle

#: The directory `git-import!` clones into, marked because it is data for a
#: MeTTa call. The fixture's Prolog path is not, because it is a host path for
#: a Python door, and it sits at the call that takes it.
REPOS = val("./repos")

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 47921 to 46435, -1486 (-3.10%), by two changes with
#: separate causes. The larger is the LANE's: an inference count here moved
#: with the number of PATH entries the caller happened to have, 45 per entry,
#: because `git-import!` reaches for an executable, so the same twin read 47921
#: under `sh check.sh` and 47845 run directly and would read a third figure on
#: another machine. The lane now fixes PATH to `MEASURED_PATH` for every
#: measurement, and this figure is the same from every ambient environment
#: tested. The smaller is this file's: the fixture's Prolog path is a HOST path
#: for a Python door, so it no longer crosses as `val()` data to be unwrapped,
#: which the lane used to force and no longer does. Against the example's 50583
#: the ratio is 0.9180 [measured 2026-08-22 min-of-3]. Prior: RE-PINNED at
#: 47921 by the twin contract change, when `import_prolog_functions_from_file`
#: became `m.register_prolog`; at 48663 when the PATH difference was first
#: isolated but read as a two-valued constant rather than a per-entry one;
#: ADDED at 48286 by the wave-3 twin baseline.
BUDGET = 46435


def twin(m):
    """Build a repository, clone it, import it, ask it a question."""
    m.eval(S["import!"](SELF, S.library(S.lib_import)))

    # The URL comes from Prolog, which register_prolog installs as a MeTTa
    # function of one argument: the base directory in, the clone URL out.
    m.register_prolog(
        path="examples/integration/_fixtures/git_fixture.pl",
        names=["git_fixture_url"],
    )
    m.eval(S["git-import!"](S.git_fixture_url(REPOS)))

    # The clone is now an ordinary named library.
    m.eval(S["import!"](SELF, S.library(S.petta_fixture_lib, S.fixture)))

    assert m.fn("fixture-answer")(14) == 42
