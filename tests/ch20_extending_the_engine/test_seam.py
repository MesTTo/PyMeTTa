"""Purpose: the seat seam itself, kind by kind.

A point is declared once with one kind, a row is checked against that
declaration, each kind is dispatched its own way and refuses the others,
discovery is lazy and free, and the whole thing reads back as data both in
Python and in the catalog.

Guarantees:
  - every shipped coupling this package moved is a ROW, so the audit's
    "nothing is named but the first registrant" is a query rather than a
    reading [tested: test_every_shipped_library_is_a_row]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import pytest

from metta import seam
from metta.errors import EngineError
from metta.results import Rows


@pytest.fixture
def scratch():
    """A point name nobody else uses, withdrawn however the test leaves."""
    name = "test-point"
    seam.withdraw(name)
    yield name
    seam.withdraw(name)


def test_a_point_is_declared_once_with_one_kind(scratch):
    """A second declaration is refused naming the standing one.

    The engine checks the same thing for seam:kind/2, and for the same reason:
    a seam with two kinds has two cut rules and neither is true.
    """
    seam.point(scratch, "declaration", fields=("value",), doc="a value")
    with pytest.raises(ValueError, match=r"already declared as declaration"):
        seam.point(scratch, "event", fields=("on",), doc="the other kind")
    assert seam.at(scratch).kind == "declaration"


def test_an_undeclared_point_refuses_by_name():
    """Reading a point nobody declared lists every point that is."""
    with pytest.raises(KeyError, match=r"no extension point named 'nope'") as raised:
        seam.at("nope")
    assert "frame" in str(raised.value)


def test_a_row_missing_a_declared_field_refuses(scratch):
    """A registration is checked against the point's declaration, both ways."""
    point = seam.point(scratch, "declaration", fields=("module", "build"), doc="two")
    with pytest.raises(TypeError, match=r"missing build"):
        point.register("solars", module="solars")
    with pytest.raises(TypeError, match=r"also gave colour"):
        point.register("solars", module="solars", build=list, colour="red")
    assert point.table() == {}


def test_each_kind_refuses_the_other_kinds_dispatch(scratch):
    """A point is read the way its kind says, and says so when it is not."""
    point = seam.point(scratch, "declaration", fields=("value",), doc="a value")
    with pytest.raises(TypeError, match=r"declaration point.*use table\(\)"):
        point.claim(1)
    with pytest.raises(TypeError, match=r"declaration point.*use table\(\)"):
        point.each(1)
    with pytest.raises(TypeError, match=r"declaration point.*use table\(\)"):
        point.call()


def test_an_ownership_point_needs_a_claims_field_and_an_event_needs_on(scratch):
    """The dispatch a kind gets is the field a row of it has to carry."""
    with pytest.raises(ValueError, match=r"must declare a claims field"):
        seam.point(scratch, "ownership", fields=("define",), doc="no claims")
    with pytest.raises(ValueError, match=r"must declare an on field"):
        seam.point(scratch, "event", fields=("run",), doc="no on")


def test_ownership_stops_at_the_first_claim(scratch):
    """The first row that answers claims, and a later row is never consulted.

    pluggy's `@hookspec(firstresult=True)`, and the engine's ownership seams:
    a row declines by answering nothing, which costs one call.
    """
    consulted = []

    def declines(_subject):
        consulted.append("declines")

    def claims(subject):
        consulted.append("claims")
        return subject * 2

    def never(subject):
        consulted.append("never")
        return subject

    point = seam.point(scratch, "ownership", fields=("claims",), doc="first wins")
    point.register("declines", claims=declines)
    point.register("claims", claims=claims)
    point.register("never", claims=never)

    claimed = point.claim(21)
    assert claimed is not None
    assert (claimed.name, claimed.answer) == ("claims", 42)
    assert consulted == ["declines", "claims"]


def test_an_ownership_point_nobody_claims_answers_nothing_and_names_the_door(scratch):
    """No claim is None, and the refusal a caller builds names the rows."""
    point = seam.point(scratch, "ownership", fields=("claims",), doc="none claim")
    point.register("declines", claims=lambda _subject: None)
    assert point.claim(1) is None
    refusal = point.refusal("a str")
    assert "declines" in refusal
    assert "claims=..." in refusal
    assert seam.GROUP in refusal


def test_an_event_runs_every_row(scratch):
    """Every row of an event point runs, in registration order."""
    ran = []
    point = seam.point(scratch, "event", fields=("on",), doc="all run")
    point.register("first", on=lambda value: ran.append(("first", value)))
    point.register("second", on=lambda value: ran.append(("second", value)))
    assert point.each(7) == ("first", "second")
    assert ran == [("first", 7), ("second", 7)]


def test_a_second_registration_replaces_in_place(scratch):
    """Re-registering a name keeps its position, so order stays stable."""
    point = seam.point(scratch, "declaration", fields=("value",), doc="values")
    point.register("a", value=1)
    point.register("b", value=2)
    point.register("a", value=3)
    assert [(row.name, row.value) for row in point.rows()] == [("a", 3), ("b", 2)]
    assert point.unregister("a") is True
    assert point.unregister("a") is False
    assert list(point.table()) == ["b"]


def test_a_row_names_the_fields_it_carries(scratch):
    """An undeclared field read off a row is refused naming what is there."""
    point = seam.point(scratch, "declaration", fields=("value",), doc="values")
    row = point.register("a", value=1)
    assert row.value == 1
    assert row.source == "package"
    with pytest.raises(AttributeError, match=r"has no 'colour' field; it carries: value"):
        _ = row.colour


def test_a_field_may_not_take_a_rows_own_attribute_name(scratch):
    """`point`, `name`, `fields` and `source` are the row's; a field is not."""
    with pytest.raises(ValueError, match=r"a row already carries name"):
        seam.point(scratch, "declaration", fields=("name",), doc="collides")


def test_a_service_is_the_other_direction():
    """A service is the SEAT's, so a registrant calls it rather than writing it."""
    projection = seam.at("projection")
    assert projection.kind == "service"
    assert projection.call() is seam.projection
    with pytest.raises(TypeError, match=r"which the SEAT writes"):
        projection.register("solars", call=list)
    assert set(seam.services()) >= {"projection", "arrow-view", "space-of", "module"}


def test_advertised_loads_nothing(monkeypatch):
    """Listing what packages advertise imports none of it.

    Pygments' property, and the reason it is worth keeping: a program can say
    what is installed without paying for any of it.
    """
    loaded = []

    class Entry:
        name = "solars"
        group = seam.GROUP

        def load(self):
            loaded.append(self.name)
            message = "advertised() must not load"
            raise AssertionError(message)

    monkeypatch.setattr(seam.metadata, "entry_points", lambda *, group: (Entry(),) if group else ())
    assert list(seam.advertised()) == ["solars"]
    assert loaded == []


def test_discovery_loads_an_advertised_registration_once(monkeypatch, scratch):
    """An entry point registers when it is loaded, and is loaded once.

    The stranger's whole installation step: a package advertises a callable
    under `metta.extensions`, and the seat calls it.
    """
    point = seam.point(scratch, "declaration", fields=("value",), doc="values")
    calls = []

    def register_solars():
        calls.append("loaded")
        point.register("solars", source="solars", value="a star")

    class Entry:
        name = "solars"
        group = seam.GROUP

        def load(self):
            return register_solars

    monkeypatch.setattr(seam.metadata, "entry_points", lambda *, group: (Entry(),) if group else ())
    assert seam.discover() == ("solars",)
    assert seam.discover() == ("solars",)
    assert calls == ["loaded"]
    assert point.table()["solars"].value == "a star"
    assert point.table()["solars"].source == "solars"


def test_every_shipped_library_is_a_row():
    """The audit's claim, as a query: each moved coupling is a registration."""
    registered = {(row.point, row.name) for row in seam.rows()}
    assert {
        ("frame", "pandas"),
        ("frame", "polars"),
        ("sql", "sqlite3"),
        ("sql", "duckdb"),
        ("array", "numpy"),
        ("index", "faiss"),
        ("index", "argsort"),
        ("arrow", "nanoarrow"),
        ("transport-error", "websocket"),
        ("image", "pydantic"),
    } <= registered
    assert all(row.source == "shipped" for row in seam.rows() if row.point == "frame")


def test_a_shipped_sugar_is_a_declared_row_and_not_a_privilege():
    """Every `to_*` on Rows is some frame row's declared sugar, and back.

    This is what stops a third library being added as a third method: the
    method exists because a row asked for it, so `rows.to(<module>)` is what a
    registrant gets and the two shipped names are that door under a name.
    """
    sugars = {
        row.fields["sugar"]
        for row in seam.frame.table().values()
        if "sugar" in row.fields
    }
    methods = {
        name
        for name in vars(Rows)
        if name.startswith("to_") and callable(getattr(Rows, name))
    }
    assert sugars == methods - {"to_dicts"}
    for sugar in sugars:
        assert callable(getattr(Rows, sugar))


def test_a_registration_inside_a_failed_integration_is_undone_with_it(metta, scratch):
    """A row registered by an installer that then fails is not left standing.

    Installation is one unit of work, and a seam registration is process-wide
    state exactly as an operation registration is, so it enlists in the same
    transaction frame rather than in one of its own.
    """
    from metta import integrate

    point = seam.point(scratch, "declaration", fields=("value",), doc="values")

    class Doomed:
        name = "seam_rollback_probe"

        def install(self, m):
            del m
            point.register("solars", value="a star")
            message = "this installer fails after registering"
            raise RuntimeError(message)

    with pytest.raises(RuntimeError, match="fails after registering"):
        integrate.integrate(metta, Doomed())
    assert point.table() == {}


def test_the_seam_publishes_itself_into_the_catalog(metta):
    """A MeTTa program matches the extension surface it is running on."""
    seam.publish(metta)
    frames = metta.run("!(match &metta (extension python frame $who $fields) $who)")
    assert {str(atom) for group in frames for atom in group} == {"pandas", "polars"}
    kinds = metta.run("!(match &metta (extension-point python frame $kind $fields) $kind)")
    assert {str(atom) for group in kinds for atom in group} == {"declaration"}
    # Idempotent for a row already there: publishing again leaves ONE row per
    # registrant, so a program may call it whenever it wants the rows without
    # accumulating duplicates. (The count publish() answers is not stable
    # across a whole session, because points whose rows live elsewhere gain
    # rows as other tests register types.)
    seam.publish(metta)
    again = metta.run("!(match &metta (extension python frame $who $fields) $who)")
    assert sorted(str(atom) for group in again for atom in group) == ["pandas", "polars"]


def test_publishing_declares_the_kind_rows_the_engine_checks(metta):
    """The rows land under kind rows, so a malformed one is refused at the write.

    The point of publishing under a declared kind rather than as loose atoms:
    the engine's own generic checker reads the kind row and refuses a row of
    the wrong shape at the write, where a loose atom would sit there silently
    and never match.
    """
    seam.publish(metta)
    declared = metta.run("!(match &metta (kind extension-point $a $b $c $d) ($a $b $c $d))")
    assert [str(atom) for group in declared for atom in group] == [
        "(symbol symbol symbol term)"
    ]
    with pytest.raises(EngineError, match=r"does not fit its declared kind"):
        metta.run("!(add-atom &metta (extension-point python))")
