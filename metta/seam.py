"""Purpose: this seat's one extension seam, the seat-level twin of ext_points.pl.

Every point a library can plug into is DECLARED here with its kind, its fields
and what it decides; a registrant is a row against a declared point; and both
are readable as data, so "what can I extend" is a query rather than a source
reading.

The vocabulary is the engine's, deliberately, so EXTENDING.md reads as one
document from the engine out to a satellite of a seat. Four kinds where the
engine declares five: `host_service` splits `service` by an audience internal
to the engine (host bindings against extensions) and a seat has one audience.

    declaration  a registrant writes rows; they are read as data, all of them
    ownership    a registrant writes rows; the FIRST that claims answers
    event        a registrant writes rows; every one runs, the answer discarded
    service      the SEAT writes it; a registrant CALLS it

The kinds carry the engine's own consequences. On an ownership point a row
declines by answering None and the next row is consulted, which is pluggy's
`@hookspec(firstresult=True)`; on a declaration or event point every row stays
reachable and nothing may claim, which is pluggy's default call loop
[source: https://pluggy.readthedocs.io/en/stable/, "First result only" and
"Collecting results"]. Registering against a point nobody declared is refused
by name, which is pluggy's `check_pending()` reading `unknown hook <name> in
plugin <plugin>` [source: pluggy _manager.py, PluginManager.check_pending].

Rows may live where they already live. `ext_points.pl` does not store a seam's
clauses; it declares the seam, and Prolog's database holds the clauses. A point
here may name `reader=` and `adder=`, so a registry that already exists keeps
its storage and its hot path and is still one row table from out here.

A point may also be DECLARED where its implementation lives. This module sits
under the base layer, `metta._errors.errors` reading its transport-error rows on every
refusal, so it may not import a satellite; the six points whose readers are
`metta.integrate`'s are declared there and named in `_DECLARING` here, and
`seam.at` loads that module only when a name is not already declared.

No row here is a library's. Every library the Python seat can be extended by
lives in its own distribution under `ext/`, advertising one
entry point in the `metta.extensions` group, found the way a stranger's package
is found; this package ships the four structural images and nothing else. That
is the ruling of 2026-09-07, and `tests/checks/check_hardcoded_integrations.py`
is what keeps it true.

Assumes:
  - importlib.metadata.entry_points(group=...) answers an empty sequence for a
    group nothing advertises, and a checkout advertises its members through
    the finder `extensions/python/_workspace.py` installs [source 2026-09-07:
    https://docs.python.org/3/library/importlib.metadata.html#entry-points]
Guarantees:
  - failed registration publication restores the local preimage and
    compensates completed observers; inverse failures remain retryable and
    every independent failure is reported [tested:
    test_registration_failure_restores_all_required_views,
    test_registration_inverse_retries_only_failed_actions,
    test_registration_compensates_observers_in_reverse_order,
    test_registration_retry_inside_a_caught_failure_retains_its_inverse,
    test_transaction_rollback_replays_each_seam_mutation; commit=7491c22b7db3c6a242dde38cebb597a0f179042c]
  - registered rows own a read-only copy of their field mapping and immutable
    registration metadata; field payloads retain their own ownership [tested:
    test_registered_rows_cannot_bypass_snapshot_generation; commit=23c1156bbecfa534f228853b06c9b4868ad1c645]
  - colliding entry-point names refuse before any provider loads and name
    both distribution origins in a stable order [tested:
    test_entry_point_collision_reports_both_owners; commit=4716ce2d8c4483d50fdb5146f296c019d7470dd4]
  - inverse sequences attempt both actions and retain every failure,
    including control exceptions [tested:
    test_inverse_sequence_attempts_every_action; commit=7491c22b7db3c6a242dde38cebb597a0f179042c]
  - registration listeners receive the exact point and registrant names,
    including quotes and the words " registration " [tested:
    test_registration_identity_is_not_parsed_from_prose; commit=56a8207a945675056312e206a000442b857ced03]
  - concurrent discovery waits for registration to finish, failed entries
    remain retryable, and cycles among discovery waits refuse [tested:
    test_concurrent_discovery_waits_for_complete_registration,
    test_recursive_discovery_does_not_publish_an_incomplete_group,
    test_a_discovery_wait_cycle_refuses_and_releases_its_entries,
    test_a_failed_entry_point_can_be_retried; commit=b615b5a33b43252ef9826e5387da7c9bd7f6b543]
  - a withdrawal notifies every registration listener with the inverse that
    inserts the removed row at its original position [tested:
    test_unregister_rollback_restores_each_position; commit=0be728864c734f8ac470ff5795398307984dff20]
  - frame builders and accessor door contracts are separate registrations
    [tested: test_the_row_is_registered_against_the_frame_point; commit=b615b5a33b43252ef9826e5387da7c9bd7f6b543]
  - a point is declared once with one kind, and a second declaration of the
    same name is refused naming the first [tested:
    test_a_point_is_declared_once_with_one_kind]
  - registering against an undeclared point refuses naming every declared
    point, and a row missing a declared field refuses naming the field
    [tested: test_an_undeclared_point_refuses_by_name,
    test_a_row_missing_a_declared_field_refuses]
  - dispatching a point the wrong way for its kind refuses naming the right
    way [tested: test_each_kind_refuses_the_other_kinds_dispatch]
  - an ownership point consults rows in registration order and the first
    non-None answer wins; an event point runs every row
    [tested: test_ownership_stops_at_the_first_claim,
    test_an_event_runs_every_row]
  - a row registered with fallback=True is consulted after every row that is
    not one, whatever order the two loaded in, which is pluggy's trylast and
    is what lets rows live in separate distributions: entry-point order is
    not something a package can arrange [tested:
    test_a_fallback_row_is_consulted_after_every_other_row,
    test_a_fallback_row_keeps_registration_order_among_fallbacks;
    commit=94057a0f073c0fab0a35c42beff2c324d8a0addd]
  - a point that declares an extra ends its refusal in the install command
    for the packages this repository ships against it [tested:
    test_a_refusal_names_the_extra_that_fills_the_point; commit=94057a0f073c0fab0a35c42beff2c324d8a0addd]
  - advertised() loads nothing. Discovery or dispatch loads each registration
    once; publishing the boot catalog requests every point [tested:
    test_advertised_loads_nothing,
    test_discovery_loads_an_advertised_registration_once,
    test_boot_publishes_complete_typed_door_rows; commit=b615b5a33b43252ef9826e5387da7c9bd7f6b543]
  - publish(m) writes the whole seam into a catalog under declared kind rows,
    so a MeTTa program matches the extension surface it is running on
    [tested: test_the_seam_publishes_itself_into_the_catalog]
Owns:
  - _POINTS and _ROWS hold the process-wide seam; each _Inverse retains its
    failed actions until a caller retries it successfully [tested:
    test_registration_inverse_retries_only_failed_actions; commit=7491c22b7db3c6a242dde38cebb597a0f179042c]
Guarded by:
  - _LOCK serializes declaration, registration publication, inverse actions
    and the one-shot discovery flag
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import functools
import importlib
import inspect
import re
import threading
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from importlib import metadata
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, Final, NamedTuple

from metta._lazy import lazy

if TYPE_CHECKING:
    import metta._atoms.designation
    import metta._atoms.factories
    import metta._atoms.registry
    import metta._catalog.arrow
    import metta._catalog.declarations
    import metta.doors  # noqa: F401 -- child of the deferred package namespace
if TYPE_CHECKING:
    import metta as _root
else:
    _root = lazy('metta')
if TYPE_CHECKING:
    from metta import _atoms
else:
    _atoms = lazy('metta._atoms')
if TYPE_CHECKING:
    from metta import _catalog
else:
    _catalog = lazy('metta._catalog')

__all__ = [
    "ARROW_FORMAT",
    "ARROW_KINDS",
    "ENTRY_POINT_GROUP",
    "GROUP",
    "KINDS",
    "LIBRARIES_GROUP",
    "SEAT",
    "SPACES_GROUP",
    "SQL_TEXT",
    "SQL_TYPE",
    "WRITTEN_BY",
    "Claim",
    "Point",
    "Row",
    "advertised",
    "alpha_eq",
    "array",
    "arrow",
    "arrow_batches",
    "arrow_schema",
    "arrow_stream",
    "arrow_view",
    "at",
    "batch_bounds",
    "discover",
    "door",
    "field_types",
    "frame",
    "graphql",
    "image",
    "image_of",
    "index",
    "ipc",
    "law",
    "match",
    "module",
    "on_registration",
    "optional_module",
    "point",
    "points",
    "projection",
    "publish",
    "rows",
    "service",
    "services",
    "space_of",
    "sql",
    "sql_arity",
    "sql_types",
    "transport_error",
    "typing",
    "withdraw",
]

#: The four seat kinds, in the order EXTENDING.md lists them.
KINDS: Final[tuple[str, ...]] = ("declaration", "ownership", "event", "service")

#: Who writes a kind's rows. The engine's clauses_from/2 twin, and the reason
#: the dispatch rules below are derived rather than restated: only a kind whose
#: rows a REGISTRANT writes can have a row that declines.
# closed-set: decides; policy=who writes each seat kind's rows, which is what decides whether a row may decline; reads=none, it is the engine's own clauses_from/2 split read for this seat's four kinds
WRITTEN_BY: Final[Mapping[str, str]] = {
    "declaration": "registrant",
    "ownership": "registrant",
    "event": "registrant",
    "service": "seat",
}

#: Which seat this is, written into every catalog row so one query reads the
#: whole ecosystem's extension surface when several seats' rows meet.
SEAT: Final = "python"

#: Where a package advertises rows of its own. Beside the three groups below,
#: and read the same way: names for free, loading only when a dispatch has no
#: answer without it.
GROUP: Final = "metta.extensions"

#: The three groups this seat already read, named here so the seam holds every
#: group a package may advertise under. metta.integrate re-exports them.
ENTRY_POINT_GROUP: Final = "metta.integrations"
SPACES_GROUP: Final = "metta.spaces"
LIBRARIES_GROUP: Final = "metta.libraries"

#: The modules that DECLARE points this seam does not declare itself. Their
#: readers and adders are their own, and they sit above this module in the
#: layering, so a point whose implementation lives there is declared there and
#: named here. Loaded lazily, and only when a caller asks for something this
#: table does not already hold, so the dispatch path stays free: metta._errors.errors
#: reads the transport-error rows on every refusal and must not pay 41 ms for
#: metta.integrate to do it [measured 2026-09-06, python -X importtime].
#: metta._observe.trace is here rather than declaring its service from this file: the
#: trace session reaches the execution machinery, and this module sits UNDER
#: metta._errors.errors, so an import of it from here -- even a function-local one --
#: is an edge from the base layer up into the core that import-linter counts
#: and that the layering exists to forbid.
_DECLARING: Final[tuple[str, ...]] = ("metta._spaces.handle", "metta._observe.trace", "metta.integrate")

#: A row's own attributes, which a field may therefore not be named.
_RESERVED: Final[frozenset[str]] = frozenset(
    {"point", "name", "fields", "source", "fallback"}
)

_CATALOG: Final = "&metta"
_POINT_HEAD: Final = "extension-point"
_ROW_HEAD: Final = "extension"
_FIELDS: Final = "fields"

_VAR_POSITIONAL: Final = inspect.Parameter.VAR_POSITIONAL
_EMPTY_ANNOTATION: Final = inspect.Signature.empty

#: MeTTa's types in SQL's vocabulary, for every engine that wants types.
#: `Number` is one type covering integers and floats, and DOUBLE is SQL's type
#: that holds both; cast in the query when a column wants an integer.
#: Everything else is text, because every atom has canonical MeTTa text and
#: nothing else survives a SQL column intact.
# closed-set: decides; policy=how a MeTTa type spells in SQL, for every engine that wants types; reads=none, it is the source a `sql` registrant speaks
SQL_TYPE: Final[Mapping[str, str]] = {
    "Number": "DOUBLE",
    "Bool": "BOOLEAN",
    "String": "VARCHAR",
}
SQL_TEXT: Final = "VARCHAR"

#: The five column kinds a projection carries, in the order `_arrow` unpacks
#: them, for an `arrow` or `ipc` registrant mapping each to its own library's
#: Arrow type. Here rather than beside the projection for the same reason
#: SQL_TYPE is here: it is a vocabulary a REGISTRANT has to speak, so it
#: belongs to the contract and not to the implementation. Four are native
#: Arrow types; TEXT is utf8 too and differs from UTF8 only in what a cell
#: renders as -- UTF8 carries a String atom's decoded value and TEXT carries
#: any atom's canonical MeTTa text, which is what stays faithful when one
#: column holds several kinds.
ARROW_KINDS: Final[tuple[str, str, str, str, str]] = (
    "int64",
    "float64",
    "bool",
    "utf8",
    "text",
)

#: Which kind each Arrow C format string asks for, for a producer reading a
#: requested schema back the other way [source:
#: https://arrow.apache.org/docs/format/CDataInterface.html#data-type-description-format-strings].
# closed-set: decides; policy=which Arrow kind each C format string asks for, which is Arrow's own grammar; reads=none, it is the source
ARROW_FORMAT: Final[Mapping[str, str]] = {"l": "int64", "g": "float64", "b": "bool", "u": "text"}


@dataclass(frozen=True, slots=True, eq=False)
class Row:
    """One registration: a point, who registered, and the fields they gave.

    A field is reached by its own name, `row.accessor`, because a field name is
    a NAME and `row["accessor"]` would make it text. `row.fields` is the same
    mapping for a caller that has the name as data.
    """

    point: str
    name: str
    fields: Mapping[str, Any]
    source: str
    fallback: bool

    def __init__(
        self,
        against: str,
        name: str,
        fields: Mapping[str, Any],
        source: str,
        *,
        fallback: bool = False,
    ) -> None:
        """Hold one registration against the named point, under `name`."""
        object.__setattr__(self, "point", against)
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "fields", MappingProxyType(dict(fields)))
        object.__setattr__(self, "source", source)
        object.__setattr__(self, "fallback", fallback)

    def __getattr__(self, field: str) -> Any:
        """One declared field, or a refusal naming what this row carries."""
        try:
            return self.fields[field]
        except KeyError:
            known = ", ".join(sorted(self.fields)) or "none"
            msg = (
                f"the {self.name!r} row of the {self.point!r} point has no "
                f"{field!r} field; it carries: {known}"
            )
            raise AttributeError(msg) from None

    def __repr__(self) -> str:
        """Name the point, the registrant and the fields it carries."""
        carried = ", ".join(sorted(self.fields))
        return f"Row({self.point} {self.name}: {carried})"


class Claim(NamedTuple):
    """What an ownership dispatch answers: who claimed, and with what."""

    name: str
    row: Row
    answer: Any


class Point:
    """One declared extension point: its kind, its fields, and what it decides.

    Declared through `seam.point(...)`, never constructed directly, because a
    declaration is the thing the seam has to see.
    """

    __slots__ = (
        "adder",
        "doc",
        "extra",
        "fields",
        "kind",
        "name",
        "optional",
        "reader",
        "shipped",
        "validator",
    )

    def __init__(
        self,
        name: str,
        kind: str,
        *,
        fields: tuple[str, ...],
        doc: str,
        optional: tuple[str, ...],
        shipped: str | None,
        extra: str | None,
        reader: Callable[[], Iterable[Row]] | None,
        adder: Callable[[Row], Callable[[], None] | None] | None,
        validator: Callable[[Row, tuple[Row, ...]], None] | None,
    ) -> None:
        """Record one declaration; `seam.point` validates before calling this."""
        self.name: str = name
        self.kind: str = kind
        self.fields: tuple[str, ...] = fields
        self.optional: tuple[str, ...] = optional
        self.doc: str = doc
        self.shipped: str | None = shipped
        self.extra: str | None = extra
        self.reader: Callable[[], Iterable[Row]] | None = reader
        self.adder: Callable[[Row], Callable[[], None] | None] | None = adder
        self.validator: Callable[[Row, tuple[Row, ...]], None] | None = validator

    def register(
        self,
        name: str,
        /,
        source: str = "package",
        *,
        fallback: bool = False,
        **fields: Any,
    ) -> Row:
        """Add one row to this point, answering it.

        Registering an existing name REPLACES that row in its original
        position, which is the registry's ordinary replacement and keeps
        ownership order stable across a reload.

        `fallback` says this row answers only where no other row does, which is
        pluggy's `trylast`. Registration order decides between rows of the same
        rank and nothing else, so a general row (the Array API index backend, a
        structural image) cannot shadow a specific one merely by having been
        imported first. Load order across DISTRIBUTIONS is not a thing a
        package can arrange: `importlib.metadata` promises no order over the
        entry points of a group.
        """
        return _register(self, name, source, fields, fallback=fallback)

    def unregister(self, name: str) -> bool:
        """Withdraw one row, answering whether there was one."""
        return _unregister(self, name)

    def rows(self) -> tuple[Row, ...]:
        """Every row against this point, in registration order."""
        return _rows_of(self)

    def find(self, name: str) -> Row | None:
        """One row by registrant name, or None."""
        for row in self.rows():
            if row.name == name:
                return row
        return None

    def table(self) -> dict[str, Row]:
        """This DECLARATION point's rows as data, keyed by registrant."""
        self._expect("declaration", "table()")
        return {row.name: row for row in self.rows()}

    def claim(self, *arguments: Any) -> Claim | None:
        """Consult this OWNERSHIP point: the first row whose `claims` answers.

        A row declines by answering None and the next is consulted, so a
        library that does not own this subject costs one call.
        """
        self._expect("ownership", "claim()")
        for row in self.rows():
            answer = row.claims(*arguments)
            if answer is not None:
                return Claim(row.name, row, answer)
        return None

    def each(self, *arguments: Any) -> tuple[str, ...]:
        """Run every row of this EVENT point, answering who ran.

        Every row runs, and a row that RAISES stops the ones after it and the
        exception reaches the caller. Swallowing it is the one thing an event
        seam may not do: a handler that failed silently is a handler nothing
        can find, which is the engine's own reason for keeping every clause of
        an event seam reachable.
        """
        self._expect("event", "each()")
        ran = []
        for row in self.rows():
            row.on(*arguments)
            ran.append(row.name)
        return tuple(ran)

    def call(self) -> Any:
        """This SERVICE point's callable, the one the seat publishes."""
        self._expect("service", "call()")
        return self.rows()[0].call

    def refusal(self, subject: str) -> str:
        """The sentence a caller gets when no row of this point answers.

        Names the door rather than the missing library, because the caller's
        next move is a registration and the library is only an example of one,
        and ends in the install command for the packages this repository ships
        against the point when the declaration named an extra.
        """
        registered = ", ".join(row.name for row in self.rows()) or "nothing"
        install = (
            ""
            if self.extra is None
            else f". The packages this repository ships for it install with "
            f"`pip install \'pymetta[{self.extra}]\'`"
        )
        return (
            f"no {self.name} registration handles {subject}; registered: "
            f"{registered}. A library registers with "
            f"metta.seam.at({self.name!r}).register(<name>, "
            f"{'=..., '.join(self.fields)}=...), or advertises the same call "
            f"under the {GROUP} entry-point group{install}"
        )

    def _expect(self, kind: str, spelling: str) -> None:
        if self.kind != kind:
            right = _DISPATCH[self.kind]
            msg = (
                f"{self.name!r} is a {self.kind} point, so {spelling} is not "
                f"how it is read; use {right}"
            )
            raise TypeError(msg)

    def __repr__(self) -> str:
        """Name the point, its kind and its declared fields."""
        return f"Point({self.name} {self.kind}: {', '.join(self.fields)})"


#: How each kind is read, for the refusal a wrong-kind dispatch raises.
# closed-set: decides; policy=how each seat kind is READ, for the refusal a wrong-kind dispatch raises; reads=none, it is the source
_DISPATCH: Final[Mapping[str, str]] = {
    "declaration": "table()",
    "ownership": "claim(...)",
    "event": "each(...)",
    "service": "call()",
}

_POINTS: Final[dict[str, Point]] = {}
_ROWS: Final[dict[str, list[Row]]] = {}
_LOCK: Final = threading.RLock()
_LOADED: set[str] = set()
type _RegistrationListener = Callable[[str, str, Callable[[], None]], Callable[[], None] | None]
_LISTENERS: list[_RegistrationListener] = []
_LOADED_ENTRIES: set[tuple[str, str]] = set()
_ENTRY_CHANGED = threading.Condition(_LOCK)
_LOADING_ENTRIES: dict[tuple[str, str], int] = {}
_WAITING_ENTRIES: dict[int, tuple[str, str]] = {}


def point(
    name: str,
    kind: str,
    *,
    fields: tuple[str, ...],
    doc: str,
    optional: tuple[str, ...] = (),
    shipped: str | None = None,
    extra: str | None = None,
    reader: Callable[[], Iterable[Row]] | None = None,
    adder: Callable[[Row], Callable[[], None] | None] | None = None,
    validator: Callable[[Row, tuple[Row, ...]], None] | None = None,
) -> Point:
    """Declare one extension point, answering it.

    `kind` is one of KINDS and decides how the point is read. `fields` are the
    names a row must carry and `optional` the ones it may; a row with anything
    else is refused, which is what makes a typo in a registration loud.

    `shipped` names the module holding this seat's own first registrants; it is
    imported at the first dispatch, so a point nobody uses costs nothing and
    the shipped rows arrive by the same lazy path a stranger's do.

    `extra` names THIS distribution's own extra whose requirements fill the
    point, so a refusal can end in a command rather than in a shape. It is an
    extra and never a library, which is the same split Airflow's providers keep:
    the core declares `apache-airflow[amazon]` and knows no cloud
    [source: https://airflow.apache.org/docs/apache-airflow-providers/, "Provider
    packages"]. `tests/checks/check_layering.py` refuses an extra this
    distribution does not declare.

    `reader` and `adder` are for a point whose rows already live somewhere: the
    reader answers them, and the adder performs a registration and answers the
    inverse to undo it. A point with neither keeps its rows here.

    `validator` checks a proposed declaration against the other registrants
    under the registry lock. It belongs to a point whose rows live here;
    foreign stores must validate inside their own atomic registration.
    """
    if kind not in KINDS:
        msg = f"an extension point is one of {', '.join(KINDS)}, not {kind!r}"
        raise ValueError(msg)
    if validator is not None and (adder is not None or reader is not None):
        msg_0 = "a validated point owns its rows in the seam registry"
        raise ValueError(msg_0)
    reserved = _RESERVED.intersection(fields + optional)
    if reserved:
        msg = (
            f"a row already carries {', '.join(sorted(reserved))}, so the "
            f"{name!r} point cannot declare a field of that name"
        )
        raise ValueError(msg)
    if kind == "ownership" and "claims" not in fields:
        msg = (
            f"an ownership point is consulted through a row's claims(...), so "
            f"{name!r} must declare a claims field; it declares "
            f"{', '.join(fields) or 'none'}"
        )
        raise ValueError(msg)
    if kind == "event" and "on" not in fields:
        msg = (
            f"an event point runs a row's on(...), so {name!r} must declare an "
            f"on field; it declares {', '.join(fields) or 'none'}"
        )
        raise ValueError(msg)
    with _LOCK:
        standing = _POINTS.get(name)
        if standing is not None:
            msg = (
                f"extension point {name!r} is already declared as "
                f"{standing.kind} with fields {', '.join(standing.fields)}; a "
                f"point has one kind"
            )
            raise ValueError(msg)
        declared = Point(
            name,
            kind,
            fields=fields,
            doc=doc,
            optional=optional,
            shipped=shipped,
            extra=extra,
            reader=reader,
            adder=adder,
            validator=validator,
        )
        _POINTS[name] = declared
        _ROWS.setdefault(name, [])
        return declared


def service(name: str, doc: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Publish one seat service: what a registrant may CALL.

    The other direction from the three handler kinds. A registrant that needs
    the seat's own machinery calls a published service instead of importing a
    private module, which is the surface SQLite publishes for the same reason
    and the reason the engine's own service kind exists.
    """

    def publish_one(fn: Callable[..., Any]) -> Callable[..., Any]:
        declared = point(name, "service", fields=("call",), doc=doc)
        _ROWS[name].append(Row(name, SEAT, {"call": fn}, "shipped"))
        del declared
        return fn

    return publish_one


def withdraw(name: str) -> bool:
    """Withdraw a declared point and every row against it.

    Remove-then-redeclare is how a program deliberately widens a point whose
    shipped contract does not fit it, the same move the engine's catalog
    documents for a shipped kind row. Answers whether there was a point.
    """
    with _LOCK:
        if name not in _POINTS:
            return False
        del _POINTS[name]
        _ROWS.pop(name, None)
        return True


def at(name: str) -> Point:
    """One declared point by name, or a refusal listing every declared point.

    The general spelling. A shipped point is also an attribute of this module,
    `seam.frame`, which is the sugar over this.

    A name this table does not hold loads the declaring modules once before
    refusing, so a point declared where its implementation lives is found
    without the caller having imported that module, and a point already here
    costs the dictionary lookup and nothing else.
    """
    point_of = _POINTS.get(name)
    if point_of is None:
        _load_declaring()
        point_of = _POINTS.get(name)
    if point_of is None:
        known = ", ".join(sorted(_POINTS)) or "none"
        msg = f"no extension point named {name!r}; this seat declares: {known}"
        raise KeyError(msg)
    return point_of


def points() -> dict[str, Point]:
    """Every declared point, keyed by name: the seam as data.

    Everything means everything, so this loads the declaring modules.
    """
    _load_declaring()
    with _LOCK:
        return dict(_POINTS)


def _load_declaring() -> None:
    """Import the modules that declare points of their own, once each."""
    for declaring in _DECLARING:
        with _LOCK:
            if declaring in _LOADED:
                continue
        importlib.import_module(declaring)
        with _LOCK:
            _LOADED.add(declaring)


def rows(name: str | None = None) -> tuple[Row, ...]:
    """Every row of one point, or of every point, in registration order."""
    if name is not None:
        return _rows_of(at(name))
    collected: list[Row] = []
    for declared in points().values():
        collected.extend(_rows_of(declared))
    return tuple(collected)


def services() -> dict[str, Callable[..., Any]]:
    """What this seat publishes for a registrant to call."""
    return {
        name: declared.call()
        for name, declared in points().items()
        if declared.kind == "service"
    }


def advertised(group: str = GROUP) -> dict[str, metadata.EntryPoint]:
    """The registration entry points installed packages advertise, UNLOADED.

    Asking imports nothing, so a program can list what is installed without
    paying for any of it. Loading is what `discover()` does explicitly and what
    a dispatch does on demand. A name identifies one distribution and target;
    competing declarations refuse before that identity becomes a dictionary key.
    """
    found: dict[str, metadata.EntryPoint] = {}
    for entry in metadata.entry_points(group=group):
        previous = found.get(entry.name)
        if previous is not None:
            origins = []
            for candidate in (previous, entry):
                dist = candidate.dist
                owner = (
                    (re.sub(r"[-_.]+", "-", dist.name).lower(), dist.version)
                    if dist is not None else ("<unknown distribution>", "")
                )
                origins.append((*owner, candidate.group, candidate.name, candidate.value))
            if previous.dist is not None and origins[0] == origins[1]:
                continue
            descriptions = [
                f"{owner!r} {version!r}: {target!r}"
                for owner, version, _, _, target in sorted(origins)
            ]
            raise ValueError(
                f"competing entry point {entry.name!r} in {group!r}: "
                + "; ".join(descriptions)
            )
        found[entry.name] = entry
    return found


def discover(group: str = GROUP) -> tuple[str, ...]:
    """Load every advertised registration now, answering the names loaded.

    Both target shapes are what a package already uses for the three
    integration groups, and an entry already loaded by a dispatch is not
    loaded again.
    """
    loaded = sorted(_load_entries(group))
    with _LOCK:
        if all((group, name) in _LOADED_ENTRIES for name in loaded):
            _LOADED.add(group)
    return tuple(loaded)


def publish(m: Any) -> int:
    """Write the whole seam into a space's catalog, answering the row count.

        !(match &metta (extension python frame $who $fields) $who)

    Two kind rows make the engine's own declaration checker refuse a malformed
    row at the write, the way the array layer declares (kind array-backend ...)
    for its roster. The rows carry the seat, the point and the registrant, not
    the callables: a callable is not knowledge, and what a program asks the
    catalog is who registered against what.

    Publishing is a dispatch of every point, so it LOADS what the seat ships
    and what packages advertise. Asking for the whole surface as data is
    exactly the request that cannot be answered without them.
    """
    catalog = at("catalog").call()(m)
    written = 0
    for declaration in (
        _atoms.factories._expr(_root.S.kind, _root.S[_POINT_HEAD], _root.S.symbol, _root.S.symbol, _root.S.symbol, _root.S.term),
        _atoms.factories._expr(_root.S.kind, _root.S[_ROW_HEAD], _root.S.symbol, _root.S.symbol, _root.S.symbol, _root.S.term),
    ):
        if declaration not in catalog:
            catalog.add(declaration)
    for name, declared in sorted(points().items()):
        row = _atoms.factories._expr(
            _root.S[_POINT_HEAD],
            _root.S[SEAT],
            _root.S[name],
            _root.S[declared.kind],
            _atoms.factories._expr(_root.S[_FIELDS], *(_root.S[field] for field in declared.fields)),
        )
        if row not in catalog:
            catalog.add(row)
            written += 1
        for registration in _rows_of(declared):
            registered = _atoms.factories._expr(
                _root.S[_ROW_HEAD],
                _root.S[SEAT],
                _root.S[name],
                _root.S[registration.name],
                _atoms.factories._expr(_root.S[_FIELDS], *(_root.S[field] for field in sorted(registration.fields))),
            )
            if registered not in catalog:
                catalog.add(registered)
                written += 1

    return written + _root.doors.publish(space_of(catalog)._rt)


def _register(
    declared: Point,
    name: str,
    source: str,
    fields: Mapping[str, Any],
    *,
    fallback: bool = False,
) -> Row:
    if WRITTEN_BY[declared.kind] != "registrant":
        msg = (
            f"{declared.name!r} is a {declared.kind} point, which the SEAT "
            f"writes; a registrant reads it with {_DISPATCH[declared.kind]}"
        )
        raise TypeError(msg)
    missing = [field for field in declared.fields if field not in fields]
    if missing:
        msg = (
            f"the {declared.name!r} point declares {', '.join(declared.fields)}; "
            f"the {name!r} registration is missing {', '.join(missing)}"
        )
        raise TypeError(msg)
    allowed = set(declared.fields) | set(declared.optional)
    extra = sorted(set(fields) - allowed)
    if extra:
        msg = (
            f"the {declared.name!r} point declares {', '.join(sorted(allowed))}; "
            f"the {name!r} registration also gave {', '.join(extra)}"
        )
        raise TypeError(msg)
    row = Row(declared.name, name, fields, source, fallback=fallback)
    # The row is held here whatever else happens to it, so a registration keeps
    # the NAME it was given; a point whose store is elsewhere then performs the
    # side effect through its adder and hands back the inverse. Without this a
    # name registered into a store that keeps none, the reflector list among
    # them, read back as the callable's own name.
    with _LOCK:
        held = _ROWS[declared.name]
        if declared.validator is not None:
            declared.validator(row, tuple(item for item in held if item.name != name))
        added = declared.adder(row) if declared.adder is not None else None
        for position, standing in enumerate(held):
            if standing.name == name:
                held[position] = row
                _enlist(
                    declared.name,
                    name,
                    _both(added, functools.partial(_restore, declared.name, position, standing)),
                )
                return row
        held.append(row)
        _enlist(declared.name, name, _both(added, functools.partial(held.remove, row)))
    return row


class _Inverse:
    """An ordered rollback whose successful actions are consumed under _LOCK."""

    def __init__(self, actions: Iterable[Callable[[], object]]) -> None:
        self.actions: list[Callable[[], object]] = list(actions)

    def __call__(self) -> None:
        failures: list[BaseException] = []
        with _LOCK:
            pending, self.actions = self.actions, []
            for action in pending:
                try:
                    action()
                except BaseException as error:  # noqa: BLE001 -- every inverse runs even after interruption
                    self.actions.append(action)
                    failures.append(error)
        if len(failures) == 1:
            raise failures[0]
        if failures:
            msg = "registration inverse actions failed"
            raise BaseExceptionGroup(msg, failures)


def _both(first: Callable[[], None] | None, second: Callable[[], None]) -> _Inverse:
    """Undo a foreign store's half and this table's half, in that order."""
    return _Inverse((second,) if first is None else (first, second))


def _restore(name: str, position: int, row: Row) -> None:
    with _LOCK:
        held = _ROWS[name]
        if position < len(held):
            held[position] = row


def _reinsert(name: str, position: int, row: Row) -> None:
    """Undo deletion without replacing the row that followed it."""
    with _LOCK:
        _ROWS[name].insert(position, row)


def on_registration(callback: _RegistrationListener) -> None:
    """Publish each registration, retaining its inverse when needed.

    The direction is deliberate. A registration made inside an integration's
    installer has to be undone when that installer fails, and the frame that
    records inverses lives in metta._declare.operations, which the base layer may not reach;
    a seam that imported it would drag metta._errors.errors up the stack with it. So
    the OWNER of the frame subscribes, the way metta._catalog.kinds subscribes to
    the conversion registry's own listener list.

    A stateful listener returns a callable that restores its own preimage.
    Returning None declares a projection that reconciles from the registry
    when called again after rollback. A listener that raises must leave its
    own state unchanged. Transaction journals retain each supplied inverse
    independently and return a compensator that removes that exact record.

    Publication runs under the reentrant seam lock. Listeners may read the
    seam on this thread; they must not wait for another thread to mutate it.
    """
    with _LOCK:
        _LISTENERS.append(callback)


def _registration_compensator(
    callback: _RegistrationListener, declared: str, name: str, undo: _Inverse,
) -> Callable[[], object]:
    """Publish one registration to one listener and return its compensation.

    A callable is the listener's exact compensation; None declares a projection
    that reconciles from the registry when called again after rollback, so the
    same publication call is its compensation. Anything else is a contract
    violation caught here, before the listener's receipt joins the inverse.
    """
    compensate = callback(declared, name, undo)
    if compensate is None:
        return functools.partial(callback, declared, name, undo)
    if not callable(compensate):
        msg = "a registration listener returns a compensation callable or None"
        raise TypeError(msg)
    return compensate


def _enlist(declared: str, name: str, undo: _Inverse | None) -> None:
    """Publish atomically with completed observers' rollback receipts."""
    if undo is None:
        return
    with _LOCK:
        restored = len(undo.actions)
        try:
            for callback in tuple(_LISTENERS):
                undo.actions.insert(restored, _registration_compensator(callback, declared, name, undo))
        except BaseException as error:  # rollback also covers interrupted publication
            try:
                undo()
            except BaseException as cleanup:  # noqa: BLE001 -- retain both publication and rollback failures
                msg = "registration publication and rollback failed"
                raise BaseExceptionGroup(msg, [error, cleanup]) from None
            raise


def _unregister(declared: Point, name: str) -> bool:
    with _LOCK:
        held = _ROWS[declared.name]
        for position, standing in enumerate(held):
            if standing.name == name:
                del held[position]
                break
        else:
            return False
        # Withdrawal publishes under the same lock and failure boundary as
        # insertion and replacement; its local inverse remains an insertion.
        _enlist(
            declared.name,
            name,
            _Inverse((functools.partial(_reinsert, declared.name, position, standing),)),
        )
    return True


def _rows_of(declared: Point, *, discover_first: bool = True) -> tuple[Row, ...]:
    # Discovery is for a kind a REGISTRANT writes. A service's one row is the
    # seat's, written by the decorator, and no package can add another, so
    # loading the group to read one would buy nothing and cost everything: it
    # imports every installed package, and `seam.at("module").call()` is the
    # first line of most of them [measured 2026-09-08: 124 ms and 196 modules
    # for `import metta_pandas` with fourteen packages installed, against 5 ms
    # and 38 modules once a service stopped discovering].
    if discover_first and WRITTEN_BY[declared.kind] == "registrant":
        _load_shipped(declared)
        _load_advertised()
    with _LOCK:
        held = _ranked(_ROWS[declared.name])
    if declared.reader is None:
        return held
    # A point whose rows live elsewhere still answers what was registered
    # THROUGH the older door directly, which is most of them; a row this table
    # already holds is not repeated, matched on the fields the store keeps.
    elsewhere = tuple(row for row in declared.reader() if not _holds(held, row))
    return held + elsewhere


def _ranked(held: Iterable[Row]) -> tuple[Row, ...]:
    """These rows, every non-fallback one first, each group in its own order.

    A stable partition and not a sort, so registration order still decides
    between two rows of the same rank; only the trylast rows move.
    """
    ranked = tuple(held)
    fallbacks = tuple(row for row in ranked if row.fallback)
    if not fallbacks:
        return ranked
    return tuple(row for row in ranked if not row.fallback) + fallbacks


def _holds(held: tuple[Row, ...], row: Row) -> bool:
    """Whether one of these rows is the same registration read back.

    Same NAME, or the same values under every field the two spell in common:
    a store records what IT keeps, which is rarely what the registration
    supplied, so `type` hands back `image` where the registration gave
    `to_atom`. One shared field carrying the same object is the identity that
    survives that.
    """
    for mine in held:
        if mine.name == row.name:
            return True
        shared = set(mine.fields) & set(row.fields)
        if shared and all(mine.fields[field] is row.fields[field] for field in shared):
            return True
    return False


def _load_shipped(declared: Point) -> None:
    """Import the module holding this point's first registrants, once."""
    shipped = declared.shipped
    if shipped is None:
        return
    with _LOCK:
        if shipped in _LOADED:
            return
    # Marked only after the import lands. Marking first would make a failed
    # import silent for the rest of the process: the point would answer no
    # rows forever and every refusal would name the wrong thing.
    importlib.import_module(shipped)
    with _LOCK:
        _LOADED.add(shipped)


def _load_advertised(group: str = GROUP) -> None:
    """Load the advertised group once, on the first dispatch that needs it.

    Pygments' shape: the lookup functions call find_plugin_lexers(), so an
    installed plugin is found without the importing program knowing it exists,
    while listing costs nothing.
    """
    with _LOCK:
        if group in _LOADED:
            return
    loaded = _load_entries(group)
    with _LOCK:
        if all((group, name) in _LOADED_ENTRIES for name in loaded):
            _LOADED.add(group)


def _load_entries(group: str) -> list[str]:
    """Load every entry of a group not loaded yet, answering their names.

    A target that is callable is CALLED, which is where it registers its rows;
    a module target is merely imported, its module body having registered on
    the way in. Loading is once per entry, so an explicit discover() after a
    dispatch has already loaded one is a no-op rather than a second
    registration.
    """
    names = []
    for name, entry in advertised(group).items():
        names.append(name)
        key = group, name
        thread = threading.get_ident()
        with _ENTRY_CHANGED:
            while key in _LOADING_ENTRIES and _LOADING_ENTRIES[key] != thread:
                # CPython's module lock follows the waiting-owner graph before
                # blocking. Registration imports must stay outside this lock.
                # https://github.com/python/cpython/blob/v3.14.4/Lib/importlib/_bootstrap.py
                owner: int | None = _LOADING_ENTRIES[key]
                while owner in _WAITING_ENTRIES:
                    owner = _LOADING_ENTRIES.get(_WAITING_ENTRIES[owner])
                    if owner == thread:
                        msg = f"cyclic entry-point discovery while waiting for {group}:{name}"
                        raise RuntimeError(msg)
                _WAITING_ENTRIES[thread] = key
                try:
                    _ENTRY_CHANGED.wait()
                finally:
                    del _WAITING_ENTRIES[thread]
            if key in _LOADED_ENTRIES or _LOADING_ENTRIES.get(key) == thread:
                continue
            _LOADING_ENTRIES[key] = thread
        try:
            target = entry.load()
            if callable(target):
                target()
            with _LOCK:
                _LOADED_ENTRIES.add(key)
        finally:
            with _ENTRY_CHANGED:
                del _LOADING_ENTRIES[key]
                _ENTRY_CHANGED.notify_all()
    return names


# ---------------------------------------------------------------- the points
#
# One file declares every point of this seat, for the reason ext_points.pl
# gives for declaring every engine seam in one: the kind is the load-bearing
# fact about a seam, and a kind that lives beside its implementation is a fact
# nothing can enumerate. The implementations live in their own modules and the
# rows live in their own DISTRIBUTIONS, one per library, so no library is named
# here or anywhere else in this package. `extra=` names this distribution's own
# extra that installs the packages this repository ships for the point, which is
# what a refusal ends in.

frame: Point = point(
    "frame",
    "declaration",
    fields=("module", "accessor", "build"),
    optional=("rows",),
    extra="dataframes",
    doc=(
        "A dataframe library. `accessor(module, name, door)` installs "
        "`df.<name>` the way that library spells an extension; "
        "`build(source, projection, view)` makes a frame from a typed "
        "projection, taking the Arrow view instead when the library reads one "
        "and there is a builder. `rows.to(<module>)` is the general spelling "
        "every registrant gets. Short receiver methods are separate contracts "
        "on the door point, fixing that conversion's library argument. "
        "Optional `rows(source)` returns this provider's row iterator, or "
        "None when it does not own the source."
    ),
)

sql: Point = point(
    "sql",
    "ownership",
    fields=("claims", "define"),
    optional=("undeclared",),
    extra="sql",
    doc=(
        "A SQL engine a MeTTa head can be registered into. "
        "`claims(connection)` answers the connection when this engine owns it "
        "and None otherwise; `define(connection, name, call, head, signature)` "
        "declares the function the way that engine declares one; "
        "`undeclared(name)` is the sentence for a head whose arrow this engine "
        "needs and cannot infer."
    ),
)

array: Point = point(
    "array",
    "declaration",
    fields=("module", "default"),
    optional=("missing", "scalars"),
    extra="arrays",
    doc=(
        "An array library reached through the Array API standard and DLPack. "
        "A row is what makes one available as the DEFAULT where an installer "
        "is given no default=, and what lets `Column.__array__` build an array "
        "at all; a library that only wants to be usable needs no row, because "
        "an explicit default= already takes any module the standard covers. "
        "`default` is whether this row may be the no-argument default, "
        "`missing` the sentence its absence raises, and `scalars()` a "
        "Hypothesis strategy of this library's scalar values."
    ),
)

index: Point = point(
    "index",
    "declaration",
    fields=("available", "build", "search"),
    optional=("missing",),
    extra="arrays",
    doc=(
        "A nearest-neighbour backend for an embedding store. `available()` "
        "says whether it can run here; `build(matrix)` prepares whatever the "
        "backend searches, cached until the matrix changes; "
        "`search(built, query, k)` answers (row, score) pairs best first over "
        "a normalized matrix. `backend='auto'` takes the first available row, "
        "specific rows before fallback ones, so a library installs itself into "
        "the store by registering and a general path registers as a fallback."
    ),
)

arrow: Point = point(
    "arrow",
    "ownership",
    fields=("claims", "schema", "stream", "batches"),
    optional=("missing",),
    extra="arrow",
    doc=(
        "Who builds the Arrow C structs. `claims()` answers its library when "
        "that library is importable; then `schema(projection)`, "
        "`stream(projection, requested)` and `batches(source)` are the two "
        "capsules and the reader. A CONSUMER of the PyCapsule interface needs "
        "no row at all: the capsules are the door and this is only who makes "
        "them."
    ),
)

ipc: Point = point(
    "ipc",
    "ownership",
    fields=("claims", "schema", "stream", "read", "concat"),
    optional=("missing",),
    extra="arrow",
    doc=(
        "Who writes and reads the Arrow IPC STREAMING format, the FlatBuffers "
        "envelope a gateway sends as a response body. nanoarrow builds the C "
        "structs a PyCapsule carries and does not write that envelope, so this "
        "is a second point beside `arrow`. `claims()` answers its library when "
        "importable; `schema(names, kinds, declared)` builds the one schema a "
        "cursor keeps, `stream(schema, columns)` one complete stream as bytes, "
        "`read(raw)` a stream back into a table and `concat(tables)` the "
        "drained chunks into one. A CONSUMER that reads the capsule needs no "
        "row; this is only who encodes the bytes."
    ),
)

transport_error: Point = point(
    "transport-error",
    "declaration",
    fields=("module", "classes"),
    extra="das",
    doc=(
        "Exception classes that mean the backend is ABSENT rather than wrong. "
        "`classes(module)` answers the tuple this library raises for a timeout "
        "or a closed stream, which a library whose own timeout does not "
        "subclass OSError needs to declare."
    ),
)

image: Point = point(
    "image",
    "ownership",
    fields=("claims",),
    shipped="metta._catalog.images",
    extra="models",
    doc=(
        "How a class of host types projects when nobody registered a "
        "conversion for it. `claims(cls)` answers the image for a class it "
        "recognises, built with the `image` service, or None. The four "
        "structural rows this seat ships are FALLBACKS, so a model "
        "framework's row is asked first however the two loaded: a validated "
        "model is also a class with __match_args__, and the specific reading "
        "has to win."
    ),
)

law: Point = point(
    "law",
    "declaration",
    fields=("arity", "sides"),
    optional=("same",),
    doc=(
        "One ALGEBRA LAW a declared carrier can be held to. `arity` is how "
        "many carrier values the property draws; `sides(carrier, *values)` "
        "answers the two things the law says are equal, or None where this "
        "carrier gives it nothing to compare; `same(left, right)` is the "
        "equality the law is stated under, defaulting to the seat's own. A "
        "provider whose carrier obeys a law nobody wrote down registers it "
        "here and `metta.testing.laws(...)` runs it beside the shipped ones. "
        "The NAMES are the engine's `algebra-law` vocabulary, so a law with "
        "no word there is one no declaration can ask for."
    ),
)

typing: Point = point(
    "typing",
    "declaration",
    fields=("equations", "doc"),
    doc=(
        "A TYPE-EQUATION TEMPLATE, named by the rule kind it is. A row is a "
        "shape rule over an indexed carrier -- `preserve` keeps the operand's "
        "shape, `broadcast` is NumPy's rule, `reduce-all` answers a scalar -- "
        "and none of that is about arrays: a dataframe's rows by columns and "
        "an image's height by width by channels are the same algebra. "
        "`equations` is a tuple of TEMPLATE atoms carrying `$head` where the "
        "head this rule is declared for goes and `$arg1`, `$arg2`, ... where "
        "the row's own arguments go, so a rule is DATA rather than Python that "
        "assembles expressions; a rule whose result the runtime observes "
        "rather than derives carries an empty tuple. `doc` is the sentence "
        "that says which shape the rule gives. "
        "`metta.typing.declare(space, head, kind, *arguments)` applies one and "
        "answers the inverse."
    ),
)

graphql: Point = point(
    "graphql",
    "ownership",
    fields=("claims", "schema", "execute"),
    optional=("missing",),
    extra="graphql",
    doc=(
        "Who EXECUTES a GraphQL document. The schema a served space publishes "
        "is built as SDL text by this seat and needs nobody; running a query "
        "against it needs an implementation of the language. `claims()` "
        "answers its library when importable; `schema(sdl, scalars)` builds "
        "the executable schema and attaches this engine's own serializers, "
        "given `{name: (serialize, parse_value)}`; `execute(schema, root, "
        "request)` runs one GraphQL-over-HTTP request and answers its `data` "
        "and `errors`."
    ),
)


# ------------------------------------------------------------- the services

@service(
    "projection",
    "One typed projection of rows: the columns, their Arrow kinds and their "
    "plain Python values. What a frame registrant builds a frame from.",
)
def projection(names: Iterable[str], values: Iterable[tuple[Any, ...]]) -> Any:
    """A typed projection over named columns of answer cells."""
    return _catalog.arrow.Projection.of(tuple(names), list(values))


@service(
    "arrow-view",
    "A producer wearing nothing but the Arrow PyCapsule interface, for a "
    "frame constructor that tests for a sequence before it looks for the "
    "capsule.",
)
def arrow_view(source: Any) -> Any:
    """`source` with only its Arrow capsule methods showing."""
    return _catalog.arrow.ArrowView(source)


@service(
    "space-of",
    "The space a door works in, given a context or a space. Every door in "
    "this library resolves the same way and a registrant should too.",
)
def space_of(m: Any) -> Any:
    """A context's home space, or the space itself."""
    return _atoms.designation.space_of(m)


@service(
    "module",
    "Import an optional library or raise the caller's own installation "
    "guidance, so a missing library never reads as an attribute error.",
)
def module(name: str, guidance: str) -> Any:
    """The named module, or ImportError carrying `guidance`."""
    from metta._lazy import optional as require_module  # noqa: PLC0415  -- the optional probe

    return require_module(name, guidance)


@service(
    "field-types",
    "A class's DECLARED field annotations, resolved and kept whole, for an "
    "image row whose rebuild needs a part's own class: an Enum member above "
    "all, but also an Enum inside list[Colour], which a bare-class filter "
    "would erase. Refuses naming the class when an annotation does not "
    "resolve, because that is a mistake in the declaration.",
)
def field_types(cls: type, names: tuple[str, ...]) -> tuple:
    """One class's declared annotations, in `names` order."""
    return _atoms.registry._field_types(cls, names)


@service(
    "optional-module",
    "Import a library and answer it, or answer None when that library itself "
    "is absent. The other half of `module`, for an ownership row's claims(), "
    "which DECLINES by answering None rather than raising; an ImportError "
    "raised INSIDE an installed library still propagates, because a broken "
    "install is not an absent one.",
)
def optional_module(name: str) -> Any:
    """The named module, or None when it is not installed."""
    from metta._lazy import optional_module as probe  # noqa: PLC0415  -- the optional probe

    return probe(name)


@service(
    "sql-arity",
    "A head's SQL argument count, or -1 for a head with no declared arrow, "
    "for an engine that wants the arity and no types.",
)
def sql_arity(signature: Any) -> int:
    """How many arguments a head takes, -1 when it is variadic."""
    total = 0
    for parameter in signature.parameters.values():
        if parameter.kind is _VAR_POSITIONAL:
            return -1
        total += 1
    return total


@service(
    "sql-types",
    "A head's SQL parameter and return types from its DECLARED arrow, for an "
    "engine that wants types; raises the engine's own `undeclared(name)` "
    "sentence when the head declares none.",
)
def sql_types(head: Any, name: str, signature: Any, undeclared: Any) -> tuple[list[str], str]:
    """(parameter types, return type) in SQL's vocabulary."""
    declared = getattr(head, "type", None)
    if declared is None or not _catalog.declarations.is_arrow(declared) or sql_arity(signature) < 0:
        raise TypeError(undeclared(name))
    empty = _EMPTY_ANNOTATION
    parameters = [
        SQL_TYPE.get(str(parameter.annotation), SQL_TEXT)
        for parameter in signature.parameters.values()
    ]
    returned = signature.return_annotation
    returns = SQL_TEXT if returned is empty else SQL_TYPE.get(str(returned), SQL_TEXT)
    return parameters, returns


@service(
    "batch-bounds",
    "Row windows doubling from one up to the chunk cap: the engine cursor's "
    "own policy, so a producer's record batches grow the way a cursor's "
    "chunks do and a consumer that reads one batch pays for one row.",
)
def batch_bounds(length: int) -> Any:
    """(start, stop) windows over `length` rows, doubling."""
    return _catalog.arrow.batch_bounds(length)


@service(
    "match",
    "Match a pattern against an atom, binding only the pattern's variables: "
    "the seat's directional primitive, where public unify() is symmetric. The "
    "bindings are keyed by variable NAME, which is why this is a service and "
    "not a second public spelling beside unify's variable-keyed mapping.",
)
def match(pattern: Any, atom: Any) -> Any:
    """The pattern's bindings, or None when it does not match."""
    return _atoms.factories._match(pattern, atom)


@service(
    "alpha-eq",
    "Whether two atoms are equal up to a consistent renaming of variables, "
    "which is MeTTa's =alpha. A named service and not ==, because two atoms "
    "must not compare differently for the variable names they happen to carry.",
)
def alpha_eq(left: Any, right: Any) -> bool:
    """MeTTa's =alpha over two atoms."""
    return _atoms.factories._alpha_eq(left, right)


@service(
    "arrow-schema",
    "The `arrow_schema` PyCapsule for a projection, through whichever library "
    "claimed the `arrow` point. What a producer of the PyCapsule interface "
    "answers from its own __arrow_c_schema__.",
)
def arrow_schema(projected: Any) -> Any:
    """One projection's Arrow schema capsule."""
    return _catalog.arrow.schema_capsule(projected)


@service(
    "arrow-stream",
    "The `arrow_array_stream` PyCapsule for a projection, honouring a "
    "requested schema where the claimant can. What a producer answers from "
    "its own __arrow_c_stream__.",
)
def arrow_stream(projected: Any, requested_schema: Any = None) -> Any:
    """One projection's Arrow stream capsule."""
    return _catalog.arrow.stream_capsule(projected, requested_schema)


@service(
    "arrow-batches",
    "An Arrow stream read back: its column names, and an iterator of its "
    "record batches as row tuples. The inward half of the capsule doors.",
)
def arrow_batches(source: Any) -> Any:
    """(column names, an iterator of batches) for one Arrow stream."""
    return _catalog.arrow.read_batches(source)


@service(
    "image-of",
    "Build the projection an image row answers: how a host class crosses, "
    "both ways, without the class being registered by name.",
)
def image_of(
    kind: str,
    parts: Any,
    rebuild: Any,
    name: str,
    *,
    fields: tuple[str, ...] = (),
    types: tuple[Any, ...] = (),
) -> Any:
    """One default image for a class of host types."""
    return _atoms.registry._Registration(kind, parts, rebuild, name, fields, types, explicit=False)


def _validate_door_registration(row: Row, standing: tuple[Row, ...]) -> None:

    _root.doors.validate_registration(row, standing)


door: Point = point(
    "door", "declaration", fields=("doors",),
    doc="Typed host doors contributed as namespace members or declared receiver sugars.",
    validator=_validate_door_registration,
)
