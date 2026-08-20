"""Purpose: derive a whole table-backed space provider from MeTTa bridge
declarations, so the contract is rewrite rules and both directions of
the boundary fall out of matching them. The module is petta.tables
because petta.bridge is already the standing bridge RULE between two
spaces (petta.subscribe.bridge); the two are the same idea at two
boundaries, a declared correspondence the engine keeps live.

    (bridge (edge $a $b) (row edges (a $a) (b $b)))

One pattern pair relates an atom shape to a table shape. Matched
left-to-right a query becomes WHERE and an add becomes INSERT; matched
right-to-left a row becomes the atom. A provider takes a SCHEMA, any
number of declarations: a schema is a set of rewrite rules the way a
function is a set of equations, so a query answers the union of every
shape it admits, exactly as overlapping equations answer together. The
one place the equation reading is deliberately NOT copied is add: a
ground atom two shapes admit is refused naming both, because storing
it twice would invent an occurrence, and a multiset must not.

This is the bidirectional-transformations literature's third approach,
writing the consistency relation and deriving both transformations
[source: the GRACE report,
gsd.uwaterloo.ca/sites/default/files/GRACE-report-ICMT09.pdf; TRIP2 did
it with Prolog rules, Wadler's views are the in/out pair], and the lens
round-trip laws are what check_space_provider verifies against the
derived claims.

Declarations may live in &petta, ctx-scoped like every other contract
atom: `declare(m, "&crm", "(bridge (edge $a $b) (row edges ...))")`
writes `(bridge &crm (edge $a $b) (row edges ...))` there, MeTTa source
can add the same atom itself, and `TableBridge.from_context(m, "&crm",
connection)` reads every one back, so a program carries its schema as
knowledge and the attach is one line.

Guarantees:
  - the whole pattern family is filtered exactly where SQL can express
    it: ground positions become comparisons, a repeated variable becomes
    the equality it demands (column to column, or column to the declared
    head literal), and a variable head constrains nothing [tested
    test_the_kit_certifies_the_pushdown_claim]
  - a nonground compound below a column variable downgrades pushdown to
    inexact instead of overclaiming, and removal falls back to
    unification so it still means what remove-atom means everywhere
    [tested test_a_nonground_compound_downgrades_and_removal_still_unifies]
  - writes are refused unless the atom grounds every column, because a
    row of NULLs standing for variables would silently weaken removal
    [tested test_a_nonground_add_is_refused]
  - an atom every shape refuses, or two shapes admit, is refused naming
    the shapes [tested test_an_ambiguous_add_is_refused_naming_both]
Decides:
  - declarations are trusted code, not user data: table and column
    names are interpolated into SQL, so a bridge declaration belongs in
    the program the way a schema does
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator
from typing import Any, Protocol, cast

from .atoms import Atom, Expr, Var, is_ground, unify
from .foreign import SpaceProvider


class Executes(Protocol):
    """The slice of a DB-API connection the bridge stands on."""

    def execute(self, sql: str, parameters: Any = ..., /) -> Any: ...

    def commit(self) -> None: ...

    def rollback(self) -> None: ...


def _declaration_error(declaration: Any) -> ValueError:
    return ValueError(
        f"a bridge declaration is (bridge <atom-shape> <row-shape>), got {declaration}"
    )


class _Shape:
    """One declaration's derivation: shape atom, table, columns, and the
    constraint reading of any pattern against them.
    """

    def __init__(self, declaration: Atom) -> None:
        if not isinstance(declaration, Expr) or len(declaration.children) != 3:
            raise _declaration_error(declaration)
        head, atom_shape, row_shape = declaration.children
        if str(head) != "bridge" or not isinstance(atom_shape, Expr) or not isinstance(row_shape, Expr):
            raise _declaration_error(declaration)
        self.shape = atom_shape
        table, *columns = row_shape.children[1:]
        self.table = str(table)
        self.columns: dict[str, str] = {}
        for pair in columns:
            if not isinstance(pair, Expr) or len(pair.children) != 2:
                raise ValueError(f"a row column is (name $var), got {pair}")
            column, variable = pair.children
            if not isinstance(variable, Var):
                raise ValueError(f"a row column binds a variable, got {pair}")
            self.columns[str(variable)] = str(column)
        for child in atom_shape.children:
            if isinstance(child, Var) and str(child) not in self.columns:
                raise ValueError(f"the atom shape's {child} has no column in {row_shape}")

    def constraints(self, pattern: Atom) -> tuple[list[str], list[str], bool] | None:
        """WHERE fragments from matching the pattern against this shape.

        Answers (where, arguments, exact), or None when the shapes cannot
        match and no row is a candidate. A pattern variable binds the
        position it first met, a declared literal or a column, and every
        later occurrence becomes the equality the pattern itself demands;
        the kit's repeated-variable folds probe exactly this.
        """
        if not isinstance(pattern, Expr) or len(pattern.children) != len(self.shape.children):
            return None
        where: list[str] = []
        arguments: list[str] = []
        exact = True
        seen: dict[str, tuple[str, str]] = {}
        for shaped, given in zip(self.shape.children, pattern.children, strict=True):
            if not isinstance(shaped, Var):
                constant = str(shaped)
                if isinstance(given, Var):
                    name = str(given)
                    prior = seen.get(name)
                    if prior is None:
                        seen[name] = ("value", constant)
                    elif prior[0] == "value":
                        if prior[1] != constant:
                            return None
                    else:
                        where.append(f"{prior[1]} = ?")
                        arguments.append(constant)
                    continue
                if str(given) != constant:
                    return None
                continue
            column = self.columns[str(shaped)]
            if isinstance(given, Var):
                name = str(given)
                prior = seen.get(name)
                if prior is None:
                    seen[name] = ("column", column)
                elif prior[0] == "column":
                    where.append(f"{column} = {prior[1]}")
                else:
                    where.append(f"{column} = ?")
                    arguments.append(prior[1])
                continue
            if isinstance(given, Expr) and not is_ground(given):
                exact = False
                continue
            where.append(f"{column} = ?")
            arguments.append(str(given))
        return where, arguments, exact

    def column_list(self) -> str:
        return ", ".join(
            self.columns[str(child)]
            for child in self.shape.children
            if isinstance(child, Var)
        )

    def values(self, atom: Expr) -> list[str]:
        return [
            str(given)
            for shaped, given in zip(self.shape.children, atom.children, strict=True)
            if isinstance(shaped, Var)
        ]

    def atom(self, parse: Callable[[str], Atom], row: Any) -> Atom:
        values = iter(row)
        spelled = " ".join(
            str(next(values)) if isinstance(child, Var) else str(child)
            for child in self.shape.children
        )
        return parse(f"({spelled})")


class TableBridge(SpaceProvider):
    """Every provider operation derived from the declarations; nothing in
    here is specific to any table.
    """

    def __init__(
        self,
        parse: Callable[[str], Atom],
        connection: Executes,
        declarations: Atom | str | Iterable[Atom | str],
    ) -> None:
        self._parse = parse
        self.connection = connection
        self.executed: list[str] = []
        if isinstance(declarations, (str, Atom)):
            declarations = [declarations]
        self._shapes = [
            _Shape(parse(declared) if isinstance(declared, str) else declared)
            for declared in declarations
        ]
        if not self._shapes:
            raise ValueError("a table bridge needs at least one declaration")

    @classmethod
    def from_context(
        cls,
        m: Any,
        name: str,
        connection: Executes,
    ) -> TableBridge:
        """The provider for every `(bridge <name> <shape> <row>)` atom in
        &petta, so a schema declared from MeTTa source, or by declare()
        below, becomes a provider in one line.
        """
        (group,) = m.run(
            f"!(collapse (match &petta (bridge {name} $shape $row)"
            f" (bridge $shape $row)))"
        )
        declarations = list(group[0])
        if not declarations:
            raise ValueError(f"&petta declares no (bridge {name} ...) schema")
        return cls(m.parse, connection, declarations)

    # -- the provider surface, all of it derived -----------------------------

    def atoms(self) -> Iterator[Atom]:
        return (
            shape.atom(self._parse, row)
            for shape in self._shapes
            for row in self._select(shape, [], [])
        )

    def match(self, pattern: Atom, *, limit: int | None = None) -> Iterator[Atom]:
        def answers() -> Iterator[Atom]:
            for shape, (where, arguments, _exact) in self._admitting(pattern):
                for row in self._select(shape, where, arguments, limit):
                    yield shape.atom(self._parse, row)

        return answers()

    def pushdown(self, pattern: Atom) -> str:
        admitting = self._admitting(pattern)
        if not admitting:
            return "exact"  # no shape admits it, and nothing is yielded
        return "exact" if all(exact for _s, (_w, _a, exact) in admitting) else "inexact"

    def add(self, atom: Atom) -> None:
        fitting = [
            shape
            for shape, _derived in self._admitting(atom)
            if is_ground(atom)
        ]
        if not fitting:
            raise ValueError(
                f"no declared shape admits {atom} as a ground row; the schema is "
                f"{[str(shape.shape) for shape in self._shapes]}"
            )
        if len(fitting) > 1:
            raise ValueError(
                f"{atom} is ambiguous: shapes "
                f"{[str(shape.shape) for shape in fitting]} all admit it, and "
                f"storing one atom twice would invent an occurrence"
            )
        shape = fitting[0]
        holes = ", ".join("?" for _ in shape.columns)
        self.connection.execute(
            f"INSERT INTO {shape.table} ({shape.column_list()})"  # noqa: S608 - identifiers from the trusted declaration  # nosec B608
            f" VALUES ({holes})",
            shape.values(cast(Expr, atom)),
        )

    def remove(self, pattern: Atom) -> bool:
        removed = False
        for shape, (where, arguments, exact) in self._admitting(pattern):
            if exact:
                sql = f"DELETE FROM {shape.table}"  # noqa: S608 - identifiers from the trusted declaration  # nosec B608
                if where:
                    sql += " WHERE " + " AND ".join(where)
                cursor = self.connection.execute(sql, arguments)
                removed = bool(getattr(cursor, "rowcount", 0) > 0) or removed
                continue
            # The one shape SQL cannot filter: match, keep what truly
            # unifies, and delete those exact rows, so removal still means
            # what remove-atom means everywhere.
            doomed = [
                shape.values(atom)
                for row in self._select(shape, where, arguments)
                for atom in (shape.atom(self._parse, row),)
                if isinstance(atom, Expr) and unify(pattern, atom) is not None
            ]
            clause = " AND ".join(f"{column} = ?" for column in shape.columns.values())
            for values in doomed:
                self.connection.execute(
                    f"DELETE FROM {shape.table} WHERE {clause}",  # noqa: S608 - identifiers from the trusted declaration  # nosec B608
                    values,
                )
            removed = bool(doomed) or removed
        return removed

    def clear(self) -> None:
        for table in {shape.table for shape in self._shapes}:
            self.connection.execute(f"DELETE FROM {table}")  # noqa: S608 - identifier from the trusted declaration  # nosec B608

    def begin(self) -> None:
        self.connection.execute("BEGIN")

    def commit(self) -> None:
        self.connection.commit()

    def rollback(self) -> None:
        self.connection.rollback()

    # -- shared derivation helpers -------------------------------------------

    def _admitting(self, pattern: Atom) -> list[tuple[_Shape, tuple[list[str], list[str], bool]]]:
        admitting = []
        for shape in self._shapes:
            derived = shape.constraints(pattern)
            if derived is not None:
                admitting.append((shape, derived))
        return admitting

    def _select(
        self,
        shape: _Shape,
        where: list[str],
        arguments: list[str],
        limit: int | None = None,
    ) -> list[Any]:
        sql = f"SELECT {shape.column_list()} FROM {shape.table}"  # noqa: S608  # nosec B608 - identifiers from the trusted declaration
        if where:
            sql += " WHERE " + " AND ".join(where)
        if limit is not None:
            sql += f" LIMIT {int(limit)}"
        self.executed.append(sql)
        return list(self.connection.execute(sql, arguments))


def declare(m: Any, name: str, declaration: Atom | str) -> Atom:
    """Write one ctx-scoped bridge declaration into &petta, where explain
    and any program can read the schema, and from_context will.
    """
    parsed = m.parse(declaration) if isinstance(declaration, str) else declaration
    if not isinstance(parsed, Expr):
        raise _declaration_error(parsed)
    _Shape(parsed)  # validated before it is stored, the declare_* discipline
    _, atom_shape, row_shape = parsed.children
    stored = m.parse(f"(bridge {name} {atom_shape} {row_shape})")
    m.run("!(add-atom &petta decl)", using={"decl": stored})
    return stored
