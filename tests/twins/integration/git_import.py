"""examples/integration/git_import.metta in Python: a repository as a library.

Four acts, then one question. A fixture Prolog file answers a clone URL,
`git-import!` clones that repository into `./repos`, the clone is imported as an
ordinary named library, and the function it ships answers.

The Prolog step is Python's own door: `m.register_prolog(path=, names=)` is what
`import_prolog_functions_from_file` names in MeTTa, and it takes the file and
the predicates to export in the same order. The other three stay terms because
`import!` and `git-import!` have no Python spelling; the space they write is the
HANDLE itself, which crosses into a built term as a grounded operand, so nothing
here names a space as a symbol.

Three names take the bracket door rather than the attribute one, because their
underscores are real: `lib_import`, `git_fixture_url` and `petta_fixture_lib`
are spelled with underscores in MeTTa too, and the attribute map would turn
each one into hyphens and reach a library that does not exist.
"""

from petta import S, ground

#: The directory `git-import!` clones into, marked because it is data for a
#: MeTTa call. The fixture's Prolog path is not, because it is a host path for
#: a Python door, and it sits at the call that takes it.
REPOS = ground("./repos")

#: The library shipped with the engine, the Prolog predicate the fixture
#: exports, and the library the clone provides. Every one of these carries a
#: genuine underscore, so every one takes rung 5.
LIB_IMPORT = S["lib_import"]
FIXTURE_URL = S["git_fixture_url"]
FIXTURE_LIB = S["petta_fixture_lib"]

#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-23: unpriced placeholder, re-pinned by the
#: integrator; commit=b5991d9d4c20f3459fae529e13e0d26331b82ee2].
BUDGET = 1


def twin(m):
    """Build a repository, clone it, import it, ask it a question."""
    # Known issue, two halves. `import!` has no Python door on the handle: the
    # perfect spelling is `m.import_(target)`, or `m += lib.<name>` for a
    # shipped library (appendix stamp 1), and neither exists yet. And the
    # generic call door cannot stand in for it, because a call through the
    # function namespace answers a LAZY view: `m.fn["import!"](m, target)` as a
    # statement IMPORTS NOTHING until something pulls its answers [measured
    # 2026-08-23]. The term door evaluates eagerly, so the directive is written
    # that way.
    m.eval(S["import!"](m, S.library(LIB_IMPORT)))

    # The URL comes from Prolog, which register_prolog installs as a MeTTa
    # function of one argument: the base directory in, the clone URL out.
    m.register_prolog(
        path="examples/integration/_fixtures/git_fixture.pl",
        names=["git_fixture_url"],
    )
    m.eval(S["git-import!"](FIXTURE_URL(REPOS)))

    # The clone is now an ordinary named library.
    m.eval(S["import!"](m, S.library(FIXTURE_LIB, S.fixture)))

    assert m.fn.fixture_answer(14).one() == 42
