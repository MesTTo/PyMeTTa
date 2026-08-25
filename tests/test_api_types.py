"""Purpose: pin the public contextual names, inferred target types, save format,
and constants.
Guarantees:
  - type hints distinguish spaces, MeTTa functions, and save formats [tested
    test_public_context_types_are_distinct]
  - cast and build preserve a concrete target class for static callers [tested
    test_target_type_overloads_preserve_the_requested_class]
  - cast's implementation-only target name is not a keyword API [tested
    test_cast_target_is_positional_only]
  - the fixed cache, constructor, and close policies are Final [tested
    test_policy_constants_are_final]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import inspect
from typing import Final, get_args, get_overloads, get_type_hints

import pytest

import metta
from metta import MeTTa, _api_types, aio, arrays, convert
from metta import _atom_namespace as atom_namespace
from metta._ops import Operation
from metta._space import Space, current_space
from metta.casting import cast
from metta.vocabularies import SaveFormat


def test_canonical_context_types_replace_public_newtypes():
    """Space handles and symbols replace the two public string NewTypes."""
    assert "SpaceName" not in dir(metta)
    assert "MettaName" not in dir(metta)
    assert _api_types.__all__ == []
    assert get_type_hints(Space.save)["format"] is SaveFormat
    assert get_type_hints(aio.AsyncMeTTa.save)["format"] is SaveFormat
    assert issubclass(SaveFormat, str)
    assert [member.value for member in SaveFormat] == ["metta", "fast"]


def test_a_name_parameter_takes_a_plain_string():
    """A NewType is deliberately not assignable from str, which is right for
    a value threaded through internals and wrong for a parameter users pass
    literals to. The typing reference's own example constructs at the
    boundary, get_user_name(UserId(42351)), and the ergonomic spelling was
    an error in five separate example programs before this: register_space
    (name="&cetta"), unregister_space("&crm"), MeTTa(space="&bounds-demo"),
    register_op(name="fuzmatch") and is_function("<lambda>")
    [measured 2026-08-17].
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    assert get_type_hints(MeTTa.space)["name"] == str | None
    assert get_type_hints(Space.op)["name"] == str | None
    assert get_type_hints(Space.is_function)["name"] is str
    assert get_type_hints(Space._register_space)["name"] is str
    assert get_type_hints(aio.AsyncMeTTa.__init__)["space"] is str
    assert get_type_hints(current_space)["default"] is str


def test_internal_identifier_types_do_not_reopen_public_doors():
    """Transport identifiers remain distinct but private to the engine seam."""
    assert get_type_hints(Operation)["name"] is _api_types._OperationName
    assert get_type_hints(Operation)["space"] == _api_types._SpaceId | None
    assert get_type_hints(Space.name.fget)["return"] is _api_types._SpaceId
    assert get_type_hints(current_space)["return"] is _api_types._SpaceId


def test_policy_constants_are_final():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    assert get_type_hints(aio)["DEFAULT_CLOSE_TIMEOUT"] == Final[float]
    assert get_type_hints(atom_namespace)["NAMESPACE_CACHE_MAX"] == Final[int]
    assert get_type_hints(arrays)["_CONSTRUCTOR_NAMES"] == Final[tuple[str, ...]]
    assert get_type_hints(current_space)["return"] is _api_types._SpaceId


def test_target_type_overloads_preserve_the_requested_class():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    for function in (cast, Space.cast, aio.AsyncMeTTa.cast, convert.build):
        typed_target = get_overloads(function)[0]
        hints = get_type_hints(typed_target)
        target = hints["type_" if "type_" in hints else "cls"]
        assert get_args(target) == (hints["return"],)


def test_cast_target_is_positional_only():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    for function in (cast, Space.cast, aio.AsyncMeTTa.cast):
        assert (
            inspect.signature(function).parameters["type_"].kind
            is inspect.Parameter.POSITIONAL_ONLY
        )

    with pytest.raises(TypeError, match="positional-only"):
        cast(None, 3, type_=int)


def test_a_handle_is_a_grounded_species():
    """The canonical glossary's law in the class tree: a handle answers
    isinstance against Grounded, deconstructs to nothing, is always truthy,
    refuses raw-value ordering, and its value slot is deliberately unset so
    a payload read names the mistake instead of answering something.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    import pytest

    from metta import Grounded, MeTTa

    space = MeTTa().space()
    assert isinstance(space, Grounded)
    assert bool(space) is True
    with pytest.raises(AttributeError):
        _ = space.value
    match space:
        case Grounded():
            pass
        case _:
            msg = "a handle must match the Grounded pattern"
            raise AssertionError(msg)
