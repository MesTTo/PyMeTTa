"""Purpose: the two seats classify the SAME refusals.

`tests/data/error-kinds.json` lists every kind the engine's own table publishes
with the class each seat raises for it, and this side reads that file against
`_EXCEPTION_TYPES`, against the engine's live rows, and against what this seat
actually raises when the listed ball is thrown. The Node seat's suite reads the
same file against its own map, so a kind added to one seat and forgotten in the
other fails here or there rather than arriving as a generic EngineError months
later.
Guarantees:
  - the fixture's signal rows and `_EXCEPTION_TYPES` are the same mapping,
    compared both ways [tested: test_the_signal_rows_are_the_exception_table]
  - the fixture lists exactly the kinds the running engine declares, with the
    same fields [tested: test_the_fixture_lists_exactly_the_engines_own_rows]
  - every listed ball classifies engine-side to its own kind and fields
    [tested: test_every_listed_ball_classifies_to_its_own_kind]
  - throwing a listed ball through this seat raises the class the fixture
    names, and the two kinds it records as unclassified here do arrive as
    EngineError [tested: test_a_thrown_ball_raises_the_class_the_fixture_names]
  - a class the fixture names takes the attributes it lists
    [tested: test_each_named_class_takes_the_attributes_the_fixture_lists]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

import builtins
import inspect
import json
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
