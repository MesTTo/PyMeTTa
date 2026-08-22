"""examples/integration/git_import.metta in Python: a repository as a library.

Four acts, then one question. A fixture Prolog file answers a clone URL,
`git-import!` clones that repository into `./repos`, the clone is imported as an
ordinary named library, and the function it ships answers.

The Prolog step is Python's own door: `m.register_prolog(path=, names=)` is what
`import_prolog_functions_from_file` names in MeTTa, and it takes the file and
the predicates to export in the same order. The other three stay terms because
`import!` and `git-import!` have no Python spelling; the space they write is
therefore named as a symbol, which the residue records.

One wart the lane forces and the surface should not: a twin may write a string
constant only as an atom's name or as `val()` data, so a path bound for a
PYTHON door has to be carried as marked data and unwrapped at the call.
"""

from petta import S, val

#: The space every import writes.
SELF = S["&self"]  # rung: no import door hangs off the space handle

#: The fixture's Prolog file and the directory `git-import!` clones into.
#: Marked data rather than bare strings, which is the only spelling a twin has
#: for a path; `.value` is where one is handed to a Python parameter.
FIXTURE_PL = val("examples/integration/_fixtures/git_fixture.pl")
REPOS = val("./repos")

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 48663 to 47921, -742 (-1.52%), by the twin contract
#: change: the `test` wrapper left the engine for Python's own `assert`, and
#: `import_prolog_functions_from_file` left it for `m.register_prolog`, which
#: registers the same one predicate through the Python door. Against the
#: example's 52069 the ratio is 0.9203. This file still has TWO reproducible
#: costs and the variable is still PATH, re-measured today: with the
#: virtualenv's `bin` prepended, as `sh check.sh` prepends it, the twin costs
#: 47921 and the example 52069; with an unmodified PATH they cost 47845 and
#: 51993. The gap is exactly 76 on BOTH sides, so the ratio does not move. The
#: pin is the figure the GATE produces, since `sh check.sh twins` is what judges
#: this file [measured 2026-08-22 min-of-3: `env PATH=<venv>/bin:$PATH
#: twin_coverage.py --measure examples/integration/git_import.metta`, against
#: the same command without it]. Prior: RE-PINNED at 48663, +377, when the same
#: PATH difference was first isolated; ADDED 2026-08-22 at 48286 by the wave-3
#: twin baseline.
BUDGET = 47921


def twin(m):
    """Build a repository, clone it, import it, ask it a question."""
    m.eval(S["import!"](SELF, S.library(S.lib_import)))

    # The URL comes from Prolog, which register_prolog installs as a MeTTa
    # function of one argument: the base directory in, the clone URL out.
    m.register_prolog(path=FIXTURE_PL.value, names=[S.git_fixture_url.name])
    m.eval(S["git-import!"](S.git_fixture_url(REPOS)))

    # The clone is now an ordinary named library.
    m.eval(S["import!"](SELF, S.library(S.petta_fixture_lib, S.fixture)))

    assert m.fn("fixture-answer")(14) == 42
