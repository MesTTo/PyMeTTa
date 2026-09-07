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

Assumes:
  - importlib.metadata.entry_points(group=...) answers an empty sequence for a
    group nothing advertises [source 2026-09-07:
    https://docs.python.org/3/library/importlib.metadata.html#entry-points]
Guarantees:
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
  - discovery is lazy and free: advertised() loads nothing, and the
    `metta.extensions` group is loaded once, at the first dispatch that has no
    answer among the rows already present, which is how Pygments finds a
    plugin lexer [source: https://pygments.org/docs/plugins; pygments/plugin.py
    find_plugin_lexers] [tested: test_advertised_loads_nothing,
    test_a_dispatch_loads_the_advertised_group_once]
  - publish(m) writes the whole seam into a catalog under declared kind rows,
    so a MeTTa program matches the extension surface it is running on
    [tested: test_the_seam_publishes_itself_into_the_catalog]
Owns:
  - _POINTS and _ROWS hold the process-wide seam; a registration made inside an
    integration's transaction frame is undone with it, through the same
    registry-undo the operation registry uses [tested:
    test_a_failed_integration_unwinds_a_seam_registration]
Guarded by:
  - _LOCK serializes declaration, registration and the one-shot discovery flag
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import functools
import importlib
import inspect
import threading
from collections.abc import Callable, Iterable, Mapping
from importlib import metadata
from typing import Any, Final, NamedTuple

__all__ = [
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
    "array",
    "arrow",
    "arrow_view",
    "at",
    "discover",
    "frame",
    "image",
    "image_of",
    "index",
    "integration",
    "library",
    "module",
    "point",
    "points",
    "projection",
    "provider",
    "publish",
    "reflector",
    "repr_",
    "rows",
    "service",
    "services",
    "space_of",
    "sql",
    "sql_arity",
    "sql_types",
    "transport_error",
    "type_",
    "withdraw",
]

#: The four seat kinds, in the order EXTENDING.md lists them.
KINDS: Final[tuple[str, ...]] = ("declaration", "ownership", "event", "service")

#: Who writes a kind's rows. The engine's clauses_from/2 twin, and the reason
#: the dispatch rules below are derived rather than restated: only a kind whose
#: rows a REGISTRANT writes can have a row that declines.
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

#: A row's own attributes, which a field may therefore not be named.
_RESERVED: Final[frozenset[str]] = frozenset({"point", "name", "fields", "source"})

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
SQL_TYPE: Final[Mapping[str, str]] = {
    "Number": "DOUBLE",
    "Bool": "BOOLEAN",
    "String": "VARCHAR",
}
SQL_TEXT: Final = "VARCHAR"


class Row:
    """One registration: a point, who registered, and the fields they gave.

    A field is reached by its own name, `row.accessor`, because a field name is
    a NAME and `row["accessor"]` would make it text. `row.fields` is the same
    mapping for a caller that has the name as data.
    """

    __slots__ = ("fields", "name", "point", "source")

    def __init__(self, point: str, name: str, fields: Mapping[str, Any], source: str) -> None:
        """Hold one registration against `point` under `name`."""
        self.point = point
        self.name = name
        self.fields = dict(fields)
        self.source = source

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

    __slots__ = ("adder", "doc", "fields", "kind", "name", "optional", "reader", "shipped")

    def __init__(
        self,
        name: str,
        kind: str,
        *,
        fields: tuple[str, ...],
        doc: str,
        optional: tuple[str, ...],
        shipped: str | None,
        reader: Callable[[], Iterable[Row]] | None,
        adder: Callable[[Row], Callable[[], None] | None] | None,
    ) -> None:
        """Record one declaration; `seam.point` validates before calling this."""
        self.name = name
        self.kind = kind
        self.fields = fields
        self.optional = optional
        self.doc = doc
        self.shipped = shipped
        self.reader = reader
        self.adder = adder

    def register(self, name: str, /, source: str = "package", **fields: Any) -> Row:
        """Add one row to this point, answering it.

        Registering an existing name REPLACES that row in its original
        position, which is the registry's ordinary replacement and keeps
        ownership order stable across a reload.
        """
        return _register(self, name, source, fields)

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

        Every row runs: an exception from one is the caller's, and stops the
        rest, which is the one thing an event seam may not swallow.
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
        next move is a registration and the library is only an example of one.
        """
        registered = ", ".join(row.name for row in self.rows()) or "nothing"
        return (
            f"no {self.name} registration handles {subject}; registered: "
            f"{registered}. A library registers with "
            f"metta.seam.at({self.name!r}).register(<name>, "
            f"{'=..., '.join(self.fields)}=...), or advertises the same call "
            f"under the {GROUP} entry-point group"
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
_LOADED_ENTRIES: set[tuple[str, str]] = set()


def point(
    name: str,
    kind: str,
    *,
    fields: tuple[str, ...],
    doc: str,
    optional: tuple[str, ...] = (),
    shipped: str | None = None,
    reader: Callable[[], Iterable[Row]] | None = None,
    adder: Callable[[Row], Callable[[], None] | None] | None = None,
) -> Point:
    """Declare one extension point, answering it.

    `kind` is one of KINDS and decides how the point is read. `fields` are the
    names a row must carry and `optional` the ones it may; a row with anything
    else is refused, which is what makes a typo in a registration loud.

    `shipped` names the module holding this seat's own first registrants; it is
    imported at the first dispatch, so a point nobody uses costs nothing and
    the shipped rows arrive by the same lazy path a stranger's do.

    `reader` and `adder` are for a point whose rows already live somewhere: the
    reader answers them, and the adder performs a registration and answers the
    inverse to undo it. A point with neither keeps its rows here.
    """
    if kind not in KINDS:
        msg = f"an extension point is one of {', '.join(KINDS)}, not {kind!r}"
        raise ValueError(msg)
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
            reader=reader,
            adder=adder,
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
    """
    try:
        return _POINTS[name]
    except KeyError:
        known = ", ".join(sorted(_POINTS)) or "none"
        msg = f"no extension point named {name!r}; this seat declares: {known}"
        raise KeyError(msg) from None


def points() -> dict[str, Point]:
    """Every declared point, keyed by name: the seam as data."""
    with _LOCK:
        return dict(_POINTS)


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
    a dispatch does on demand.
    """
    return {entry.name: entry for entry in metadata.entry_points(group=group)}


def discover(group: str = GROUP) -> tuple[str, ...]:
    """Load every advertised registration now, answering the names loaded.

    Both target shapes are what a package already uses for the three
    integration groups, and an entry already loaded by a dispatch is not
    loaded again.
    """
    loaded = sorted(_load_entries(group))
    with _LOCK:
        _LOADED.add(group)
    return tuple(loaded)


def publish(m: Any) -> int:
    """Write the whole seam into a space's catalog, answering the row count.

        !(match &metta (extension python frame $who $fields) $who)

    Two kind rows make the engine's own declaration checker refuse a malformed
    row at the write, the way metta.arrays declares (kind array-backend ...)
    for its roster. The rows carry the seat, the point and the registrant, not
    the callables: a callable is not knowledge, and what a program asks the
    catalog is who registered against what.

    Publishing is a dispatch of every point, so it LOADS what the seat ships
    and what packages advertise. Asking for the whole surface as data is
    exactly the request that cannot be answered without them.
    """
    from ._api_types import space_of  # noqa: PLC0415  -- a context or a space, resolved at the door
    from ._space import Space  # noqa: PLC0415  -- the catalog is a space of this runtime
    from .atoms import S, _expr  # noqa: PLC0415  -- atoms are the base layer

    catalog = Space(_CATALOG, _runtime=space_of(m).runtime)
    written = 0
    for declaration in (
        _expr(S.kind, S[_POINT_HEAD], S.symbol, S.symbol, S.symbol, S.term),
        _expr(S.kind, S[_ROW_HEAD], S.symbol, S.symbol, S.symbol, S.term),
    ):
        if declaration not in catalog:
            catalog.add(declaration)
    for name, declared in sorted(points().items()):
        row = _expr(
            S[_POINT_HEAD],
            S[SEAT],
            S[name],
            S[declared.kind],
            _expr(S[_FIELDS], *(S[field] for field in declared.fields)),
        )
        if row not in catalog:
            catalog.add(row)
            written += 1
        for registration in _rows_of(declared):
            registered = _expr(
                S[_ROW_HEAD],
                S[SEAT],
                S[name],
                S[registration.name],
                _expr(S[_FIELDS], *(S[field] for field in sorted(registration.fields))),
            )
            if registered not in catalog:
                catalog.add(registered)
                written += 1
    return written


def _register(declared: Point, name: str, source: str, fields: Mapping[str, Any]) -> Row:
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
    row = Row(declared.name, name, fields, source)
    # The row is held here whatever else happens to it, so a registration keeps
    # the NAME it was given; a point whose store is elsewhere then performs the
    # side effect through its adder and hands back the inverse. Without this a
    # name registered into a store that keeps none, the reflector list among
    # them, read back as the callable's own name.
    added = declared.adder(row) if declared.adder is not None else None
    with _LOCK:
        held = _ROWS[declared.name]
        for index, standing in enumerate(held):
            if standing.name == name:
                held[index] = row
                _enlist(
                    _both(added, functools.partial(_restore, declared.name, index, standing)),
                    f"{declared.name} registration {name!r}",
                )
                return row
        held.append(row)

    def withdraw_row() -> None:
        _unregister(declared, name)

    _enlist(_both(added, withdraw_row), f"{declared.name} registration {name!r}")
    return row


def _both(first: Callable[[], None] | None, second: Callable[[], None]) -> Callable[[], None]:
    """Undo a foreign store's half and this table's half, in that order."""
    if first is None:
        return second

    def undo() -> None:
        first()
        second()

    return undo


def _restore(name: str, index: int, row: Row) -> None:
    with _LOCK:
        held = _ROWS[name]
        if index < len(held):
            held[index] = row


def _enlist(undo: Callable[[], None] | None, description: str) -> None:
    """Undo this registration if the installing transaction rolls back."""
    if undo is None:
        return
    from .ops import _record_registry_undo  # noqa: PLC0415  -- ops is above errors in the layering

    _record_registry_undo(undo, description=description)


def _unregister(declared: Point, name: str) -> bool:
    with _LOCK:
        held = _ROWS[declared.name]
        for index, standing in enumerate(held):
            if standing.name == name:
                del held[index]
                return True
    return False


def _rows_of(declared: Point, *, discover_first: bool = True) -> tuple[Row, ...]:
    if discover_first:
        _load_shipped(declared)
        _load_advertised()
    with _LOCK:
        held = tuple(_ROWS[declared.name])
    if declared.reader is None:
        return held
    # A point whose rows live elsewhere still answers what was registered
    # THROUGH the older door directly, which is most of them; a row this table
    # already holds is not repeated, matched on the fields the store keeps.
    elsewhere = tuple(row for row in declared.reader() if not _holds(held, row))
    return held + elsewhere


def _holds(held: tuple[Row, ...], row: Row) -> bool:
    """Whether one of these rows is the same registration read back."""
    return any(
        all(mine.fields.get(field) is value for field, value in row.fields.items())
        for mine in held
    )


def _load_shipped(declared: Point) -> None:
    """Import the module holding this point's first registrants, once."""
    module = declared.shipped
    if module is None:
        return
    with _LOCK:
        if module in _LOADED:
            return
    # Marked only after the import lands. Marking first would make a failed
    # import silent for the rest of the process: the point would answer no
    # rows forever and every refusal would name the wrong thing.
    importlib.import_module(module)
    with _LOCK:
        _LOADED.add(module)


def _load_advertised(group: str = GROUP) -> None:
    """Load the advertised group once, on the first dispatch that needs it.

    Pygments' shape: the lookup functions call find_plugin_lexers(), so an
    installed plugin is found without the importing program knowing it exists,
    while listing costs nothing.
    """
    with _LOCK:
        if group in _LOADED:
            return
    _load_entries(group)
    with _LOCK:
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
        with _LOCK:
            if (group, name) in _LOADED_ENTRIES:
                continue
            _LOADED_ENTRIES.add((group, name))
        target = entry.load()
        if callable(target):
            target()
    return names


# ---------------------------------------------------------------- the points
#
# One file declares every point of this seat, for the reason ext_points.pl
# gives for declaring every engine seam in one: the kind is the load-bearing
# fact about a seam, and a kind that lives beside its implementation is a fact
# nothing can enumerate. The implementations live in their own modules and the
# first registrants live in metta._registrants, so no library is named here.

frame = point(
    "frame",
    "declaration",
    fields=("module", "accessor", "build"),
    optional=("sugar",),
    shipped="metta._registrants",
    doc=(
        "A dataframe library. `accessor(module, name, door)` installs "
        "`df.<name>` the way that library spells an extension; "
        "`build(source, projection, view)` makes a frame from a typed "
        "projection, taking the Arrow view instead when the library reads one "
        "and there is a builder. `sugar` names the Rows method that answers "
        "this library's frame, so `to_df` and `to_pl` are rows rather than "
        "privileges; `rows.to(<module>)` is the general spelling every "
        "registrant gets."
    ),
)

sql = point(
    "sql",
    "ownership",
    fields=("claims", "define"),
    optional=("undeclared",),
    shipped="metta._registrants",
    doc=(
        "A SQL engine a MeTTa head can be registered into. "
        "`claims(connection)` answers the connection when this engine owns it "
        "and None otherwise; `define(connection, name, call, head, signature)` "
        "declares the function the way that engine declares one; "
        "`undeclared(name)` is the sentence for a head whose arrow this engine "
        "needs and cannot infer."
    ),
)

array = point(
    "array",
    "declaration",
    fields=("module", "default"),
    optional=("missing", "scalars"),
    shipped="metta._registrants",
    doc=(
        "An array library reached through the Array API standard and DLPack. "
        "A row is what makes one available as the DEFAULT for "
        "`arrays.install(m)` with no default= given, and what lets "
        "`Column.__array__` build an array at all; a library that only wants "
        "to be usable needs no row, because `install(m, default=<module>)` "
        "already takes any module the standard covers. `default` is whether "
        "this row may be the no-argument default, `missing` the sentence its "
        "absence raises, and `scalars()` a Hypothesis strategy of this "
        "library's scalar values."
    ),
)

index = point(
    "index",
    "declaration",
    fields=("available", "build", "search"),
    optional=("missing",),
    shipped="metta._registrants",
    doc=(
        "A nearest-neighbour backend for metta.arrays.EmbeddingStore. "
        "`available()` says whether it can run here; `build(matrix)` prepares "
        "whatever the backend searches, cached until the matrix changes; "
        "`search(built, query, k)` answers (row, score) pairs best first over "
        "a normalized matrix. `backend='auto'` takes the first available row "
        "in registration order, so a library installs itself into the store "
        "by registering."
    ),
)

arrow = point(
    "arrow",
    "ownership",
    fields=("claims", "schema", "stream", "batches"),
    optional=("missing",),
    shipped="metta._registrants",
    doc=(
        "Who builds the Arrow C structs. `claims()` answers its library when "
        "that library is importable; then `schema(projection)`, "
        "`stream(projection, requested)` and `batches(source)` are the two "
        "capsules and the reader. A CONSUMER of the PyCapsule interface needs "
        "no row at all: the capsules are the door and this is only who makes "
        "them."
    ),
)

transport_error = point(
    "transport-error",
    "declaration",
    fields=("module", "classes"),
    shipped="metta._registrants",
    doc=(
        "Exception classes that mean the backend is ABSENT rather than wrong. "
        "`classes(module)` answers the tuple this library raises for a timeout "
        "or a closed stream, which a library whose own timeout does not "
        "subclass OSError needs to declare."
    ),
)

image = point(
    "image",
    "ownership",
    fields=("claims",),
    shipped="metta._registrants",
    doc=(
        "How a class of host types projects when nobody registered a "
        "conversion for it. `claims(cls)` answers the image for a class it "
        "recognises, built with the `image` service, or None. Rows are "
        "consulted in registration order, so a model framework's row is asked "
        "before the structural ones."
    ),
)


# The four points below are the doors this seat already had. Their rows live
# where they always lived, so nothing about a hot lookup or a transactional
# rollback changes; what the seam adds is that they are DECLARED, so "what can
# I extend here" is one query, and that one door registers against any of
# them. This is exactly what ext_points.pl does for a Prolog seam whose
# clauses Prolog's own database holds.


def _type_rows() -> Iterable[Row]:
    from ._convert_registry import _REGISTRY  # noqa: PLC0415  -- it imports this

    return [
        Row(
            "type",
            registration.type_name,
            {"type": cls, "image": registration.image, "parts": registration.fields},
            "package",
        )
        for cls, registration in _REGISTRY.items()
        if registration.explicit
    ]


def _add_type(row: Row) -> Callable[[], None]:
    from .integrate import register_type, unregister_type  # noqa: PLC0415  -- the seat's own door

    given = dict(row.fields)
    cls = given.pop("type")
    parts = given.pop("parts", ())
    register_type(cls, name=row.name, fields=parts, **given)
    return lambda: unregister_type(cls)


def _repr_rows() -> Iterable[Row]:
    from ._atoms_core import _PROTOCOL_REPRS  # noqa: PLC0415  -- the repr registry's own store

    return [
        Row("repr", _named(text), {"claims": predicate, "text": text}, "package")
        for predicate, text in _PROTOCOL_REPRS
    ]


def _add_repr(row: Row) -> Callable[[], None]:
    from .integrate import register_repr, unregister_repr  # noqa: PLC0415  -- the seat's own door

    register_repr(row.claims, row.text)
    return lambda: unregister_repr(row.claims, row.text)


def _reflector_rows() -> Iterable[Row]:
    from .integrate import _REFLECTORS  # noqa: PLC0415  -- the reflector registry's own store

    return [
        Row("reflector", _named(lower), {"claims": claims, "lower": lower}, "package")
        for claims, lower in _REFLECTORS
    ]


def _add_reflector(row: Row) -> Callable[[], None]:
    from .integrate import (  # noqa: PLC0415  -- the seat's own door
        register_reflector,
        unregister_reflector,
    )

    register_reflector(row.claims, row.lower)
    return lambda: unregister_reflector(row.claims, row.lower)


def _named(fn: Any) -> str:
    """A callable's own name, for a registry that stored no name with it."""
    return str(getattr(fn, "__qualname__", None) or getattr(fn, "__name__", fn))


def _advertised_rows(point_name: str, group: str) -> Callable[[], Iterable[Row]]:
    """Rows for one entry-point group, read without loading any of it."""

    def read() -> Iterable[Row]:
        return [
            Row(point_name, name, {"entry": entry, "group": group}, name)
            for name, entry in advertised(group).items()
        ]

    return read


type_ = point(
    "type",
    "declaration",
    fields=("type",),
    optional=("to_atom", "from_atom", "image", "parts"),
    reader=_type_rows,
    adder=_add_type,
    doc=(
        "How a host class crosses, both ways, declared rather than derived. "
        "The ROW's name is the MeTTa type name, so nothing is said twice; "
        "`type` is the class, `to_atom`, `from_atom` and `image` are what "
        "metta.integrate.register_type takes, and `parts` is its `fields`, "
        "renamed because a row already carries its own fields. The rows are "
        "metta.convert's own registrations, read where they live."
    ),
)

repr_ = point(
    "repr",
    "ownership",
    fields=("claims", "text"),
    reader=_repr_rows,
    adder=_add_repr,
    doc=(
        "How a host value PRINTS in MeTTa. `claims(value)` recognises the "
        "values this row formats and `text(value)` renders one. "
        "`metta.integrate.register_repr` is the same door."
    ),
)

reflector = point(
    "reflector",
    "ownership",
    fields=("claims", "lower"),
    reader=_reflector_rows,
    adder=_add_reflector,
    doc=(
        "How a host object's structure becomes facts. `claims(value)` "
        "recognises what this row can lower and `lower(value, head, space)` "
        "writes the facts. `metta.integrate.register_reflector` is the same "
        "door."
    ),
)

provider = point(
    "provider",
    "declaration",
    fields=("entry", "group"),
    reader=_advertised_rows("provider", SPACES_GROUP),
    doc=(
        f"A space backed by a library's own storage, advertised under the "
        f"{SPACES_GROUP} entry-point group. The rows are what installed "
        f"packages advertise, UNLOADED; `metta.integrate.load_entry_point` "
        f"loads one by name."
    ),
)

library = point(
    "library",
    "declaration",
    fields=("entry", "group"),
    reader=_advertised_rows("library", LIBRARIES_GROUP),
    doc=(
        f"A directory of MeTTa or Prolog sources a package ships, advertised "
        f"under the {LIBRARIES_GROUP} entry-point group and importable as "
        f"`(library <name>)` once its path is registered."
    ),
)

integration = point(
    "integration",
    "declaration",
    fields=("entry", "group"),
    reader=_advertised_rows("integration", ENTRY_POINT_GROUP),
    doc=(
        f"A whole library wired into a space, advertised under the "
        f"{ENTRY_POINT_GROUP} entry-point group. `metta.integrate.discover` "
        f"installs them in dependency order."
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
    from ._arrow import Projection  # noqa: PLC0415  -- the one projection

    return Projection.of(tuple(names), list(values))


@service(
    "arrow-view",
    "A producer wearing nothing but the Arrow PyCapsule interface, for a "
    "frame constructor that tests for a sequence before it looks for the "
    "capsule.",
)
def arrow_view(source: Any) -> Any:
    """`source` with only its Arrow capsule methods showing."""
    from ._arrow import ArrowView  # noqa: PLC0415  -- the optional Arrow extra

    return ArrowView(source)


@service(
    "space-of",
    "The space a door works in, given a context or a space. Every door in "
    "this library resolves the same way and a registrant should too.",
)
def space_of(m: Any) -> Any:
    """A context's home space, or the space itself."""
    from ._api_types import space_of as resolve  # noqa: PLC0415  -- the shared resolver

    return resolve(m)


@service(
    "module",
    "Import an optional library or raise the caller's own installation "
    "guidance, so a missing library never reads as an attribute error.",
)
def module(name: str, guidance: str) -> Any:
    """The named module, or ImportError carrying `guidance`."""
    from ._optional import require_module  # noqa: PLC0415  -- the optional probe

    return require_module(name, guidance)


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
    from ._declarations import is_arrow  # noqa: PLC0415  -- the declared-arrow test

    declared = getattr(head, "type", None)
    if declared is None or not is_arrow(declared) or sql_arity(signature) < 0:
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
    from ._convert_registry import _Registration  # noqa: PLC0415  -- it imports this

    return _Registration(kind, parts, rebuild, name, fields, types, explicit=False)
