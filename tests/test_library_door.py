"""Purpose: pin the library import door: `m += lib.he` performs
`!(import! <m> (library lib_he))` with the receiver as the target, the
spelling appendix stamp 1 designs and sixty-one twins were carrying as a
`fn["import!"]` workaround. The namespace's attribute map is the `lib_`
family prefix with underscores kept, never the hyphen map, because a
library is a FILE name; the bracket and call doors are the exact rungs
beneath it.
Guarantees:
  - the attribute, bracket, dotted-part, and call doors build exactly the
    module forms the engine's import! resolves
    [tested: test_the_attribute_map_is_the_family_prefix,
    test_the_exact_doors_build_the_engine_forms]
  - the write door imports into the RECEIVER, so a definition arrives in
    the space that was added to
    [tested: test_the_write_door_imports_into_the_receiver]
  - a handle refuses every atom position and every store it could hide
    in: nested in a term, mixed with stored atoms, or inside a batch
    [tested: test_a_library_handle_refuses_atom_positions]
  - a missing library refuses with the engine's own existence error
    naming the path [tested: test_a_missing_library_refuses_loudly]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import pytest

from metta import MeTTa, S, lib
from metta.errors import EngineError, MettaError


def test_the_attribute_map_is_the_family_prefix():
    """`lib.he` is `lib_he` and `lib.thread` is `lib_thread`: the prefix
    joins with underscores KEPT, because `S.lib_he` would be the atom
    `lib-he`, which no library answers.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    assert lib.he.form == S.library(S["lib_he"])
    assert lib.thread.form == S.library(S["lib_thread"])
    assert repr(lib.he) == "lib.he"
    assert "he" in dir(lib)
    assert "measure" in dir(lib)


def test_the_exact_doors_build_the_engine_forms():
    """Bracket is the exact library name, the dotted part is the
    two-argument `(library alias inner)` form, and the call is the exact
    module form a path import crosses as.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    assert lib["minimal_metta_lib"].form == S.library(S["minimal_metta_lib"])
    assert lib["metta_fixture_lib"].fixture.form == S.library(
        S["metta_fixture_lib"], S.fixture
    )
    assert lib("examples/basics/fibsmart").form == S["examples/basics/fibsmart"]
    with pytest.raises(TypeError, match="does not contain files"):
        lib["metta_fixture_lib"].fixture.deeper  # noqa: B018  -- the refusal is the behaviour under test


def test_the_write_door_imports_into_the_receiver():
    """After `m += lib.he` the library's own definitions answer here."""
    m = MeTTa().space()
    m += lib.he
    caught = m.fn.if_error(S.payload, S.caught, S.payload).one()
    assert caught == S.payload


def test_a_library_handle_refuses_atom_positions():
    """The handle names an ACT: a term position, a mixed add, and a batch
    each refuse loudly instead of storing an opaque box or hiding the
    effect inside a bulk write.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    m = MeTTa().space()
    with pytest.raises(TypeError, match="library handle, not an atom"):
        m += (S.uses, lib.he)
    with pytest.raises(TypeError, match="imports and stores cannot share"):
        m.add(lib.he, (S.edge, 1, 2))
    with pytest.raises(MettaError, match="import"):
        with m.batch():
            m += lib.he


def test_a_missing_library_refuses_loudly():
    """The engine's own existence error crosses whole, naming the path."""
    m = MeTTa().space()
    with pytest.raises(EngineError, match="nosuchlibrary"):
        m += lib.nosuchlibrary
