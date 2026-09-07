"""Purpose: the two seats classify the SAME refusals, and the tree throws only what the table lists.

`tests/data/error-kinds.json` lists every kind the engine's own table publishes
with the class each seat raises for it, and this side reads that file against
`_EXCEPTION_TYPES`, against the engine's live rows, and against what this seat
actually raises when the listed ball is thrown. The Node seat's suite reads the
same file against its own map, so a kind added to one seat and forgotten in the
other fails here or there rather than arriving as a generic EngineError months
later.

The list is also held to the TREE from the other direction: `thrown_kinds`
reads every literal kind the sources hand to `metta_control_signal/2` or to
shim.pl's `metta_py_raise/2`, so a kind thrown somewhere and declared nowhere
is a red row here rather than a bare EngineError at a caller. Drift between
the thrower, the classifier and the exception map is silent both ways and has
happened both ways: the `restraint` signal reached callers as EngineError
until the cache-policies branch added it by hand.
Guarantees:
  - the fixture's signal rows and `_EXCEPTION_TYPES` are the same mapping,
    compared both ways [tested: test_the_signal_rows_are_the_exception_table; commit=WORKTREE]
  - the fixture lists exactly the kinds the running engine declares, with the
    same fields [tested: test_the_fixture_lists_exactly_the_engines_own_rows; commit=WORKTREE]
  - every listed ball classifies engine-side to its own kind and fields
    [tested: test_every_listed_ball_classifies_to_its_own_kind; commit=WORKTREE]
  - throwing a listed ball through this seat raises the class the fixture
    names, and the two kinds it records as unclassified here do arrive as
    EngineError [tested: test_a_thrown_ball_raises_the_class_the_fixture_names; commit=WORKTREE]
  - a class the fixture names takes the attributes it lists
    [tested: test_each_named_class_takes_the_attributes_the_fixture_lists; commit=WORKTREE]
  - the kinds the tree throws through the reserved envelope and the fixture's
    signal rows are one set, with both differences named
    [tested: test_every_thrown_kind_is_a_listed_signal_row; commit=WORKTREE]
  - the live shim admits every kind Python raises for, so no exception entry
    is unreachable, and SWI's own unenveloped resource balls stay classified
    beside them [tested: test_the_shim_classifies_every_kind_python_names,
    test_swis_own_resource_balls_are_classified_too; commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

import builtins
import inspect
import json
import re
import subprocess
from pathlib import Path

import pytest

from metta import MeTTa
from metta import errors as error_classes

# The private table IS the subject: this file exists to pin it against the
# shared list, so reading it here is the point rather than a way around a
# public door. Nothing else in the suite touches it.
from metta._engine import _EXCEPTION_TYPES

#: Read at import rather than through the repo_root fixture, because the cases
#: below are one test per kind and parametrize runs at collection time. Same
#: derivation the host-carve scan uses.
KINDS = json.loads(
    (Path(__file__).resolve().parents[4] / "tests" / "data" / "error-kinds.json").read_text()
)["kinds"]

_ADD_A_KIND = (
    "declare its row in engine/metta/registration.pl, add it to "
    "tests/data/error-kinds.json with the class each seat raises, and map it "
    "in extensions/node/src/errors.ts"
)

#: The two spellings that NAME a kind in this tree: the envelope term itself,
#: and shim.pl's metta_py_raise/2, which builds the envelope around a kind its
#: caller passes. Both are matched with a literal atom in the kind position; an
#: occurrence with a variable there is a reader or a re-thrower, not a source.
_NAMES_A_KIND = re.compile(
    r"metta_control_signal\(\s*([a-z][a-z_0-9]*)\s*,"
    r"|metta_py_raise\(\s*([a-z][a-z_0-9]*)\s*,"
)

#: Where a kind may be thrown from. Tests are excluded because a test naming a
#: kind is exercising the seam, not publishing one.
_SOURCE_ROOTS = ("engine", "lib", "extensions")
_SOURCE_SUFFIXES = (".pl", ".py", ".c")


def thrown_kinds(repo_root):
    """Every control-signal kind this tree names, read from the tree.

    TRACKED files, asked of git rather than walked, which is the rule
    ``check_component_python`` in ``check.sh`` already states for the same
    reason: a walk finds build output nothing here owns. The Node seat's
    ``npm run build:browser`` copies the whole engine into
    ``extensions/node/_runtime/``, so a walk reads every engine source twice,
    once live and once as whatever the last build left behind, and a stale copy
    would report a kind this tree no longer throws. A walk also has to know
    where the checkout SITS: an agent worktree of this repository lives under a
    directory literally named ``ai-tmp``, and pruning that by absolute path
    prunes the whole tree.
    """
    listing = subprocess.run(
        ["git", "ls-files", "--", *_SOURCE_ROOTS],
        cwd=repo_root, capture_output=True, text=True, timeout=60, check=True,
    )
    found = set()
    for name in listing.stdout.splitlines():
        path = repo_root / name
        if path.suffix not in _SOURCE_SUFFIXES or "tests" in path.parts:
            continue
        for envelope, raised in _NAMES_A_KIND.findall(
            path.read_text(encoding="utf-8", errors="replace")
        ):
            found.add(envelope or raised)
    return found


@pytest.fixture(name="tree_kinds")
def _tree_kinds(repo_root):
    """The tree's kinds, or a skip where git will not enumerate the checkout.

    The same reading its neighbour takes in test_workspace_paths.py: a CI
    checkout git declines to read, over ownership or otherwise, is a fact about
    that machine, and reporting it as a repository defect blames the wrong
    thing.
    """
    try:
        return thrown_kinds(repo_root)
    except (OSError, subprocess.SubprocessError) as unavailable:
        pytest.skip(f"git ls-files is unavailable here: {unavailable}")


@pytest.fixture(scope="module")
def engine():
    """One engine for the module: every test here only reads."""
    with MeTTa().space("&error_kinds_probe") as space:
        yield space


def test_the_signal_rows_are_the_exception_table():
    """The signal rows and `_EXCEPTION_TYPES` are one mapping, both ways."""
    listed = {
        name: row["python"]["error"]
        for name, row in KINDS.items()
        if row["origin"] == "signal"
    }
    mapped = {name: kind.__name__ for name, kind in _EXCEPTION_TYPES.items()}
    assert listed == mapped, f"the shared kind list and _EXCEPTION_TYPES disagree; {_ADD_A_KIND}"


def test_the_fixture_lists_exactly_the_engines_own_rows(engine):
    """The shared list and the running engine declare the same kinds and fields."""
    rows = engine.runtime.must(
        "findall([_Kind, _Origin, _Fields], "
        "metta_host_error_kind_row(_Kind, _Origin, _Fields), Rows)"
    )["Rows"]
    declared = {kind: [origin, list(fields)] for kind, origin, fields in rows}
    listed = {name: [row["origin"], row["fields"]] for name, row in KINDS.items()}
    assert declared == listed, f"the engine and the shared kind list disagree; {_ADD_A_KIND}"


def test_every_thrown_kind_is_a_listed_signal_row(tree_kinds):
    """The kinds the tree throws and the fixture's signal rows are one set.

    An extra on the left is a signal that reaches a caller as a bare
    EngineError; an extra on the right is a row nothing can ever produce.
    """
    listed = {name for name, row in KINDS.items() if row["origin"] == "signal"}
    assert tree_kinds, "the scrape found nothing, so it is measuring itself"
    assert tree_kinds - listed == set(), f"thrown but listed nowhere; {_ADD_A_KIND}"
    assert listed - tree_kinds == set(), "listed as a signal but never thrown"


@pytest.mark.parametrize("name", sorted(KINDS))
def test_every_listed_ball_classifies_to_its_own_kind(name, engine):
    """Each listed ball classifies to its own kind, with its fields and their values."""
    row = KINDS[name]
    answer = engine.runtime.must(
        # _-prefixed because janus converts every NAMED variable of a goal and
        # refuses a compound: the ball and the pair list are intermediates, and
        # only the kind, the field names and their values cross.
        "term_string(_Ball, BallText), "
        "metta_host_error_kind(_Ball, Kind, _Pairs), "
        "pairs_keys_values(_Pairs, Names, Values)",
        BallText=row["ball"],
    )
    assert answer["Kind"] == name
    assert list(answer["Names"]) == row["fields"]
    carried = dict(zip(answer["Names"], (str(value) for value in answer["Values"]), strict=True))
    assert carried == row["expects"]


@pytest.mark.parametrize("name", sorted(KINDS))
def test_a_thrown_ball_raises_the_class_the_fixture_names(name, engine):
    """Throwing a listed ball through this seat raises the class the list names."""
    row = KINDS[name]
    wanted = row["python"]["error"]
    with pytest.raises(Exception) as failure:
        engine.runtime.must("term_string(_Ball, BallText), throw(_Ball)", BallText=row["ball"])
    raised = type(failure.value).__name__
    if wanted is None:
        # A recorded gap rather than an oversight: the row's own note says
        # what closing it takes, and this goes red the day it closes so the
        # shared list is updated with it.
        assert raised == "EngineError", (
            f"{name} is classified by this seat now; give its row a python class"
        )
    else:
        assert raised == wanted


@pytest.mark.parametrize("name", sorted(KINDS))
def test_each_named_class_takes_the_attributes_the_fixture_lists(name):
    """A class the list names takes the attributes the list gives it."""
    row = KINDS[name]
    wanted = row["python"]["error"]
    if wanted is None:
        assert row["python"]["attributes"] == {}
        return
    held = getattr(error_classes, wanted, None) or getattr(builtins, wanted)
    parameters = inspect.signature(held.__init__).parameters
    for field, attribute in row["python"]["attributes"].items():
        assert attribute in parameters, f"{name}.{field} is not a parameter of {wanted}"


def test_the_shim_classifies_every_kind_python_names(engine):
    """The live shim admits each kind, so no Python entry is unreachable.

    Asked of the running engine rather than read out of shim.pl, because what
    matters is what metta_control_signal_info/3 DOES with a term of that kind,
    which is also what _engine._raise asks it at the moment of the failure.
    """
    for kind in sorted(_EXCEPTION_TYPES):
        row = engine.runtime.once(
            "atom_string(Kind, KindText), "
            "metta_control_signal_info("
            "  error(metta_control_signal(Kind, detail), context(metta, Kind)), "
            "  Kind, _Detail)",
            KindText=kind,
        )
        assert row, f"the shim does not classify metta_control_signal({kind}, _)"


def test_swis_own_resource_balls_are_classified_too(engine):
    """A bound spent in a NESTED query arrives unenveloped, and still lands.

    apply_once opens its query with PL_Q_CATCH_EXCEPTION, so it takes SWI's
    ball before the enclosing call_with_inference_limit/3 can wrap it. Both
    balls are classified by name, with no detail to report.
    """
    for ball, kind in (
        ("inference_limit_exceeded", "inference_limit"),
        ("time_limit_exceeded", "time_limit"),
    ):
        row = engine.runtime.once(
            "atom_string(Ball, BallText), "
            "metta_control_signal_info(Ball, Kind, _Detail)",
            BallText=ball,
        )
        assert row.get("Kind") == kind
