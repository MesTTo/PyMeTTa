"""Purpose: the standard-library SQL instance of the bridge: MeTTa
declarations relate edge and document atoms to SQLite tables, petta.tables
derives every provider operation from them, and the contract in &petta says
how far to trust each one and how a binary column crosses.

    (bridge (edge $a $b) (row edges (a $a) (b $b)))

The declaration is the converter, both directions, the way a MeTTa
equation is: a query becomes WHERE, an add becomes INSERT, a row becomes
the atom. petta/tables.py holds the derivation and its guarantees; this
file is only the SQLite glue and the contract:

  (context <name> closed-world)          negation may consult the table
  (annotations <name> bag)               SQL bag semantics, said plainly
  (handles <name> (edge $x $y) Exact)    the derived filtering IS the
                                         answer set, licensing LIMIT
  (handles <name> (edge $x $x) Exact)    repetition derives WHERE a = b,
                                         so the diagonal is exact too
  (writes <name> transactional)          (transaction ...) delegates to
                                         BEGIN/COMMIT/ROLLBACK
  (image <name> Blob opaque)             a BLOB crosses as one handle;
                                         lazy paths project only what they read

Declared Exact is trusted: the engine hands the bound down and a whole
join can be claimed without re-derivation. The unification the engine
still performs per answer is how bindings ENTER the local program, not
a verification pass; for an Exact shape it never rejects.
[tested: bindings/python/tests/test_sqlite_space.py]
Guarantees:
  - a Blob column follows its per-context image declaration, so opaque keeps
    the row object whole and transparent projects its bytes [tested:
    test_an_opaque_blob_column_is_reached_by_a_lazy_path_without_crossing;
    commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import sqlite3
from typing import Literal

from _common import check, done

import petta
from petta.paths import path
from petta import tables
from petta.tables import TableBridge


class Blob:
    """One SQLite BLOB with a structural image available on request."""

    __slots__ = ("data",)

    def __init__(self, data: bytes) -> None:
        self.data = data

    def __metta__(self):
        """The transparent image; opaque contexts never call this method."""
        return petta.Expression(
            [petta.S.Blob, *(petta.ground(byte) for byte in self.data)]
        )


def _blob_row(_cursor, row):
    """Keep SQLite's binary values distinct from ordinary Python bytes."""
    return tuple(Blob(value) if isinstance(value, bytes) else value for value in row)


def attach_sqlite(
    m,
    name: str,
    database: str = ":memory:",
    *,
    blob_image: Literal["opaque", "transparent", "auto"] = "opaque",
) -> TableBridge:
    """Declare the schema in &petta, then read it back into a provider:
    the declaration is knowledge first, so explain and any program can
    query it, and MeTTa source that added its own (bridge ...) atoms has
    already declared a schema this attach will honour."""
    connection = sqlite3.connect(database, check_same_thread=False)
    connection.row_factory = _blob_row
    connection.execute("CREATE TABLE IF NOT EXISTS edges (a TEXT, b TEXT)")
    connection.execute(
        "CREATE TABLE IF NOT EXISTS documents (id TEXT, payload BLOB)"
    )
    tables.declare(m, name, "(bridge (edge $a $b) (row edges (a $a) (b $b)))")
    tables.declare(
        m,
        name,
        "(bridge (document $id $blob)"
        " (row documents (id $id) (payload $blob)))",
    )
    m.declare_image(name, "Blob", blob_image)
    provider = TableBridge.from_context(m, name, connection)
    m._register_space(provider, name)
    m.declare_context(name, "closed-world")
    m.declare_annotations(name, "bag")
    m.declare_handles(name, "(edge $x $y)", "Exact")
    m.declare_handles(name, "(edge $x $x)", "Exact")
    m.declare_handles(name, "(document $id $blob)", "Exact")
    m.declare_writes(name, "transactional")
    return provider


def demo() -> None:
    """Rows answer MeTTa, SQL receives the bound, and one field is reached
    inside an opaque BLOB without projecting its complete byte sequence."""
    m = petta.MeTTa().space()
    provider = attach_sqlite(m, "&crm")
    m.run("!(add-atom &crm (edge a b))")
    m.run("!(add-atom &crm (edge b b))")
    m.run("!(add-atom &crm (edge b c))")
    (group,) = m.run("!(collapse (match &crm (edge $x $y) ($x $y)))")
    check("rows answer MeTTa", sorted(str(a) for a in group[0]),
          ["(a b)", "(b b)", "(b c)"])
    (group,) = m.run("!(collapse (match &crm (edge $x $x) $x))")
    check("the diagonal derives WHERE a = b", [str(a) for a in group[0]], ["b"])
    m.run("!(collapse (take 1 (match &crm (edge $x $y) (edge $x $y))))")
    check("the bound reached the SQL",
          any("LIMIT 1" in sql for sql in provider.executed))
    payload = bytes(range(64)) * 4
    provider.connection.execute(
        "INSERT INTO documents VALUES (?, ?)",
        ("manual", sqlite3.Binary(payload)),
    )
    rows = m._at("&crm").query(
        petta.S.document(
            petta.S.manual,
            path("data", 0, to=petta.V.first_byte),
        )
    )
    check("a lazy path reads one byte from the opaque BLOB",
          rows.to_dicts(), [{"first_byte": 0}])
    done("sqlite_space")


if __name__ == "__main__":
    demo()
