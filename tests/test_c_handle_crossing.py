"""Purpose: pin the native-handle carrier: an opaque C blob crosses the
seam into Python by reference, goes back as the very same object, is
unpacked through its extension's own accessors, and dies loudly after
release.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

from pathlib import Path

import pytest

import petta
from petta import Handle
from petta.errors import EngineError

_LIBRARY = (
    Path(__file__).resolve().parents[3]
    / "examples"
    / "integration"
    / "c_extension"
    / "handle.so"
)


@pytest.fixture
def vectors():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    if not _LIBRARY.is_file():
        pytest.skip("handle.so is not built; see examples/integration/c_extension/README.md")
    m = petta.MeTTa().space()
    m.register_foreign_library(
        _LIBRARY,
        entry="install_handle",
        names=["vector-new", "vector-nth", "vector-bump", "vector-length"],
    )
    try:
        yield m
    finally:
        m.drop()


def unpack_vector(m, handle: Handle) -> list[int]:
    """The Python-side unpack method: the handle stays opaque here, and the
    extension's own accessors read the native structure out element by
    element. Nothing in this function knows what a vector is inside.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    with m.bind(h=handle):
        (row,) = m.run("!(vector-length h)")
    length = int(str(row[0]))
    return [
        int(str(m.eval("(vector-nth h i)", using={"h": handle, "i": i})[0]))
        for i in range(length)
    ]


def test_a_c_object_crosses_by_identity_and_unpacks_in_python(vectors):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m = vectors
    (row,) = m.run("!(vector-new 5)")
    handle = row[0]
    assert isinstance(handle, Handle)
    assert str(handle) == "<vector 5>"

    # Identity, not a copy: a mutation made through the handle is visible
    # on the next read through the same handle.
    with m.bind(h=handle):
        m.run("!(vector-bump h 3)")
    assert unpack_vector(m, handle) == [0, 1, 2, 4, 4]


def test_a_handle_nests_inside_expressions_both_ways(vectors):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m = vectors
    (row,) = m.run("!(holds (vector-new 3) tagged)")
    expression = row[0]
    inner = expression.children[1]
    assert isinstance(inner, Handle)
    assert unpack_vector(m, inner) == [0, 1, 2]


def test_a_released_handle_raises_by_id(vectors):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m = vectors
    (row,) = m.run("!(vector-new 2)")
    handle = row[0]
    handle.release()
    handle.release()  # idempotent
    with pytest.raises(EngineError, match="petta_native_handle"), m.bind(h=handle):
        m.run("!(vector-length h)")


def test_a_handle_refuses_pickling(vectors):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    import pickle

    m = vectors
    (row,) = m.run("!(vector-new 1)")
    with pytest.raises(TypeError, match="process-local identity"):
        pickle.dumps(row[0])


def test_a_handle_is_a_context_manager(vectors):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m = vectors
    (row,) = m.run("!(vector-new 2)")
    with row[0] as handle:
        assert unpack_vector(m, handle) == [0, 1]
    with pytest.raises(EngineError, match="petta_native_handle"), m.bind(h=handle):
        m.run("!(vector-length h)")
