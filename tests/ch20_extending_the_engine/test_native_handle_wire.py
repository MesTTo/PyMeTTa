"""Purpose: pin native-handle wire and table-persistence contracts.

Guarantees:
  - a native handle and an expression containing one survive the public wire
    round trip with identity and display text intact [tested:
    test_native_handles_round_trip_through_the_public_wire_codec;
    commit=WORKTREE]
  - table storage refuses process-local native identities before executing an
    insert, while portable space references remain storable [tested:
    test_table_storage_refuses_native_handles_before_writing,
    test_table_storage_preserves_portable_space_references;
    commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from metta import S, wire
from metta._atoms_core import _NativeHandle
from metta.tables import TableBridge


def _provider(parse):
    connection = sqlite3.connect(":memory:")
    connection.execute("CREATE TABLE rows (value TEXT)")
    provider = TableBridge(
        parse,
        connection,
        "(bridge (row $value) (row rows (value $value)))",
    )
    return connection, provider


def test_native_handles_round_trip_through_the_public_wire_codec():
    """The encoder preserves every field the decoder needs at any depth."""
    handle = _NativeHandle(29_001, "<fixture-native-handle>")

    encoded = json.loads(json.dumps(handle.to_wire()))
    decoded = wire.atom_from_wire(encoded)
    nested = wire.atom_from_wire(S.row(handle).to_wire())

    assert encoded == ["h", 29_001, "<fixture-native-handle>"]
    assert decoded == handle
    assert str(decoded) == "<fixture-native-handle>"
    assert nested == S.row(handle)
    assert str(nested.children[1]) == "<fixture-native-handle>"


def test_three_field_native_handle_returns_to_its_engine(metta):
    """The engine resolves the id and ignores the retained display field."""
    library = Path(
        "examples/ch19-spaces-backed-by-anything/19-03-a-builtin-in-c/handle.so"
    ).resolve()
    if not library.is_file():
        pytest.skip("handle.so is built by check.sh before the Python suite")
    metta.register_foreign_library(
        library,
        entry="install_handle",
        names=["vector-new", "vector-nth", "vector-bump", "vector-length"],
    )
    (handle,) = metta.eval(S["vector-new"](4))
    restored = wire.atom_from_wire(handle.to_wire())
    assert isinstance(restored, _NativeHandle)
    try:
        assert metta.eval(S["vector-nth"](restored, 3)) == [3]
    finally:
        restored.release()
        handle.release()


def test_table_storage_refuses_native_handles_before_writing(metta):
    """A process-local registry id is not durable database data."""
    connection, provider = _provider(metta.parse)
    handle = _NativeHandle(29_002, "<fixture-native-handle>")

    for value in (handle, S.nested(handle)):
        with pytest.raises(
            ValueError,
            match=r"native handle has process-local identity.*accessors",
        ):
            provider.add(S.row(value))

    assert connection.execute("SELECT COUNT(*) FROM rows").fetchone() == (0,)


def test_table_storage_preserves_portable_space_references(metta):
    """A named space reference keeps the stable p-tag table representation."""
    connection, provider = _provider(metta.parse)

    provider.add(S.row(metta))

    (restored,) = tuple(provider.atoms())
    assert restored == S.row(metta)
    assert connection.execute("SELECT COUNT(*) FROM rows").fetchone() == (1,)
