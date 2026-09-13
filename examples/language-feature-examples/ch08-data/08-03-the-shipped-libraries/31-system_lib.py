"""Purpose: the environment, the working directory and the platform, as data.

Names and values are `G("...")` text, because they are text and not names; a
platform key is a symbol. A variable that is not set has no answer, which `list()`
reads as the empty list.

Guarantees: the same claims as 31-system_lib.metta
[tested: python extensions/python/tools/twin_coverage.py examples/ch08-data/08-03-the-shipped-libraries/31-system_lib.metta; commit=b109f59a8095add8ecf264b011e683184274acbb].
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import G, S, lib
from metta._errors.errors import MettaError


def twin(m):
    """Read and write the environment, ask the platform, and read the directory."""
    m += lib.system
    # lib_pairs is beside it because the environment IS a relation, and lib_string
    # for the text checks over what the platform answers.
    m += lib.pairs
    m += lib.string

    def refused(call):
        """Whether evaluating a call raises, which is what if-error reads."""
        try:
            list(m.eval(call))
        except MettaError:
            return True
        return False

    get = m.fn.env_get
    set_to, unset = m.fn["env-set!"], m.fn["env-unset!"]
    info, keys = m.fn.platform_info, m.fn.platform_keys
    directory = m.fn.working_directory

    # A variable that is not set has NO answer, which is what makes unset and empty
    # different states.
    assert list(get(G("NO_SUCH_VARIABLE_HERE"))) == []
    assert (S.unset if list(get(G("NO_SUCH_VARIABLE_HERE"))) == [] else S.set) == S.unset

    # A write is visible to every later read in this process, and to every child
    # process it starts.
    assert set_to(G("METTA_SYSTEM_EXAMPLE"), G("on")) == [True]
    assert get(G("METTA_SYSTEM_EXAMPLE")) == [G("on")]
    assert set_to(G("METTA_SYSTEM_EXAMPLE"), G("")) == [True]
    # An empty value is SET, which is the state a presence test has to tell apart.
    assert get(G("METTA_SYSTEM_EXAMPLE")) == [G("")]
    assert (S.unset if list(get(G("METTA_SYSTEM_EXAMPLE"))) == [] else S.set) == S.set
    assert unset(G("METTA_SYSTEM_EXAMPLE")) == [True]
    assert list(get(G("METTA_SYSTEM_EXAMPLE"))) == []
    # Removing one that is not set is silent.
    assert unset(G("METTA_SYSTEM_EXAMPLE")) == [True]

    # The whole environment is a relation of (Name Value) pairs, so lib_pairs reads
    # it: the names are Strings, which is also what keeps the relation inert.
    assert set_to(G("METTA_SYSTEM_EXAMPLE"), G("listed")) == [True]
    assert m.fn.pairs_is(S.env_all()) == [True]
    assert list(m.fn.pairs_lookup(S.env_all(), G("METTA_SYSTEM_EXAMPLE"))) == [G("listed")]
    assert list(m.fn.pairs_lookup(S.env_all(), G("NO_SUCH_VARIABLE_HERE"))) == []
    assert unset(G("METTA_SYSTEM_EXAMPLE")) == [True]

    # The platform, one key at a time, and every key as data. The host NAME is not a
    # key: gethostname/1 is library(socket)'s, and a whole network library is too
    # much to link for one string.
    assert info(S.family) == [G("unix")]
    assert info(S.dialect) == [G("swi")]
    assert info(S.cores).one() == info(S.cores).one()
    assert len(info(S.version_numbers).one()) == 3
    assert len(keys().one()) == 10
    assert refused(S.platform_info(S.nosuch))
    # The version as text and as numbers agree.
    assert m.fn.string_starts_with(
        S.platform_info(S.version),
        S.number_to_string(S.car_atom(S.platform_info(S.version_numbers))),
    ) == [True]

    # The working directory is the process's own, absolute and without a trailing
    # separator.
    assert m.fn.string_starts_with(S.working_directory(), G("/")) == [True]
    assert m.fn.string_ends_with(S.working_directory(), G("/")) == [False]
    assert refused(S["change-directory!"](G("/no/such/directory/here")))
    # The directory is unchanged by a refused move.
    assert m.fn.string_starts_with(directory(), G("/")) == [True]

    # Every refusal names what it was given.
    assert list(m.eval(S.env_get(7))) == [
        S.Error(S.env_get(7), S.BadArgType(1, S.String, S.Number)),
    ]
    assert refused(S["env-set!"](G("A"), S.nosuch()))
    assert list(m.eval(S["change-directory!"](7))) == [
        S.Error(S["change-directory!"](7), S.BadArgType(1, S.String, S.Number)),
    ]


#: MEASURED on this branch rather than inherited: this twin is new, so there is
#: no earlier pin to move. The 29 claims cover the eight heads, the unset-against-
#: empty distinction, the ten platform keys and the refusals
#: [measured 2026-09-12: 117508 inferences against the example's 122661, minimum
#: of three serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3
#: examples/ch08-data/08-03-the-shipped-libraries/31-system_lib.metta;
#: fixture=lib_system at its functional commit, artifacts purged before the run;
#: commit=b109f59a8095add8ecf264b011e683184274acbb].
#: RE-PINNED 2026-09-13, 117508 to 118039 (+531), File exports its staged
#: publisher to Compression; the shared native builder accepts the private
#: archive provider recipe. All consumers are remeasured after those dependency
#: changes [measured 2026-09-13: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=7b42d5ee5cecb82709617b7ed08dfa2c1441f268].
#: RE-PINNED 2026-09-13, 118039 to 200522 (+82483), Combinatorics, Functional,
#: Pairs and Sets now derive collection operations through MeTTa equations,
#: segments and folds. This example imports the changed provider directly or
#: through its library dependencies [measured 2026-09-13: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=WORKTREE].
#: RE-PINNED 2026-09-13, 200522 to 201865 (+1343), The validated range
#: continuation now lives in the private support file rather than appearing as
#: a public library head. The import adds its measured loading cost without
#: changing the continuation body [measured 2026-09-13: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=WORKTREE].
BUDGET = 201865
