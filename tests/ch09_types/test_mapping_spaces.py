"""Purpose: reconstruct declared mapping values from native graph rows.

Guarantees:
  - mapping annotations admit stored spaces and reconstruct their current
    entries without evaluating them [tested:
    test_mapping_spaces_follow_annotations_and_native_edits;
    test_mapping_space_values_preserve_syntax; commit=a8e3fc42306377adf7cae0a331f3d92fbf190304]
  - malformed or duplicate entries refuse before a mapping loses data
    [tested: test_mapping_spaces_refuse_non_mapping_rows; commit=a8e3fc42306377adf7cae0a331f3d92fbf190304]
  - compiled dictionary and keyword-collector results use the same conversion
    [tested: test_compiled_methods_return_native_mapping_values; commit=a8e3fc42306377adf7cae0a331f3d92fbf190304]
Owns resources: scopes release native stores, foreign owners unregister in
finally, and the pure-import subprocess is joined before the test returns.
"""

import subprocess
import sys
from collections.abc import Callable, Mapping, MutableMapping
from dataclasses import dataclass
from typing import Annotated, Any, NotRequired, Required, TypedDict, TypeVar

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from metta import Expression, G, MeTTa, S, Space, V, convert
from metta._declare import declarations
from metta._errors.errors import EngineError, MettaError
from metta.foreign import SpaceProvider


class MappingRow(TypedDict):
    """One required mapping field, also used by compiled result annotations."""

    value: int


ANNOTATIONS = (
    dict,
    dict[str, int],
    Mapping[str, int],
    MutableMapping[str, int],
    Annotated[dict[str, int], "mapping"],
    Required[dict[str, int]],
    NotRequired[dict[str, int]],
    TypeVar("MappingBound", bound=dict[str, int]),
    TypeVar("MappingChoice", int, dict[str, int]),
    int | dict[str, int],
    MappingRow,
)


@pytest.mark.parametrize("annotation", ANNOTATIONS)
def test_mapping_spaces_follow_annotations_and_native_edits(annotation):
    """A reconstruction reads the current rows and returns an independent value."""
    with MeTTa() as context:
        native = context.self
        native.add(Expression(["value", 3]))
        first = convert.build(native, annotation)
        assert isinstance(first, dict)
        assert first == {"value": 3}
        native.remove(Expression(["value", 3]))
        native.add(Expression(["value", 7]))
        assert convert.build(native, annotation) == {"value": 7}
        assert first == {"value": 3}
    assert first == {"value": 3}


@pytest.mark.parametrize("name", (None, "mapping_store_without_prefix", S["mapping-store"]("tenant")))
def test_mapping_space_images_use_native_identity(name):
    """Handle, symbol and expression names share the native space relation."""
    with MeTTa() as context, context.self.scope():
        native = context.self._new_space() if name is None else Space(name)
        native.add(Expression(["value", 3]))
        image = name if isinstance(name, Expression) else S[native.name]
        assert convert.build(native, dict[str, int]) == {"value": 3}
        assert convert.build(image, dict[str, int]) == {"value": 3}


@pytest.mark.parametrize("rows", (
    (S.malformed,),
    (S.too("many", "parts"),),
    (Expression(["same", 1]), Expression(["same", 2])),
))
def test_mapping_spaces_refuse_non_mapping_rows(rows):
    """A relation with malformed rows or several values per key is not a dict."""
    with MeTTa() as context:
        native = context.self
        native.add(*rows)
        with pytest.raises(TypeError, match=r"key/value|duplicate"):
            convert.build(native, dict[str, int])


@pytest.mark.parametrize("entries", (
    Expression([S.entry("same", 1), S.entry("same", 2)]),
    Expression([S.entry(1, "one"), Expression([S.entry, True, "true"])]),
    Expression([S.entry("same", 1), S.entry("same", S.Buffer(2))]),
))
def test_mapping_images_refuse_keys_that_reconstruct_as_duplicates(entries):
    """The reconstructed key, including Python's True == 1 rule, is authoritative."""
    with pytest.raises(TypeError, match="duplicate"):
        convert.build(entries, dict[Any, Any])


@settings(max_examples=30, deadline=None)
@given(st.dictionaries(
    st.text(alphabet="abcd", max_size=3),
    st.one_of(st.none(), st.booleans(), st.integers(-20, 20),
              st.sampled_from((S.scalar, S["+"](1, 2), V.held))),
    max_size=6,
))
def test_mapping_space_values_preserve_syntax(values):
    """Reading entries does not run rule-bearing symbols, expressions or variables."""
    with MeTTa() as context, context.self.scope():
        native = context.self._new_space()
        context.self.add(S["="](S.scalar, 97))
        for key, value in values.items():
            native.add(Expression([key, value]))
        result = convert.build(native, dict[str, Any], space=context.self)
        assert isinstance(result, dict)
        assert result.keys() == values.keys()
        for key, expected in values.items():
            assert convert.project(result[key]).atom.alpha_eq(convert.project(expected).atom)


def test_mapping_space_conversion_preserves_nested_callable_context():
    """Annotation recursion retains callbacks and reconstructs nested spaces."""
    with MeTTa() as context, context.self.scope():
        home = context.self
        home.run("(= (mapping-callback $x) (+ $x 4))")
        inner, outer = home._new_space(), home._new_space()
        inner.add(Expression(["callback", home.parse("(|-> ($x) (mapping-callback $x))")]))
        outer.add(Expression(["nested", inner]))
        result = convert.build(outer, dict[str, dict[str, Callable[[int], int]]], space=home)
        callback = result["nested"]["callback"]
        assert callback(3) == 7
        home.remove(S["="](S["mapping-callback"](V.x), S["+"](V.x, 4)))
        home.add(S["="](S["mapping-callback"](V.x), S["+"](V.x, 10)))
        assert callback(3) == 13


def test_mapping_space_conversion_keeps_unknown_and_borrowed_values():
    """Unregistered symbols stay symbols, and borrowed mappings keep identity."""
    with MeTTa():
        unknown = S["not-a-registered-mapping-space"]
        assert convert.build(unknown, dict[str, int]) is unknown
        borrowed = {"value": 3}
        assert convert.build(G(borrowed), dict[str, int]) is borrowed


@pytest.mark.parametrize("annotation", ANNOTATIONS)
def test_compiled_methods_return_native_mapping_values(annotation):
    """Literal dictionaries and keyword collectors cross the same result boundary."""
    with MeTTa() as context:
        home = context.self

        @home.define
        @dataclass(frozen=True)
        class MappingResults:
            def literal(self, value: int) -> annotation:
                return {"value": value}

            def collected(self, **values: int) -> annotation:
                return values

        value = MappingResults()
        assert value.literal(3) == {"value": 3}
        assert value.collected(value=5) == {"value": 5}


def test_native_mapping_result_contract_composes_through_callable_types():
    """A compiled higher-order return admits the dictionary's native space."""
    with MeTTa() as context:
        home = context.self

        @home.define
        def mapping_result(value: int) -> dict[str, int]:
            return {"value": value}

        @home.define
        def mapping_invoke(function: Callable[[int], dict[str, int]]) -> dict[str, int]:
            return function(3)

        (answer,) = home.eval(S.mapping_invoke(S.mapping_result))
        assert convert.build(answer, dict[str, int]) == {"value": 3}


def test_mapping_conversion_keeps_runtime_ownership(monkeypatch):
    """Pure conversion stays pure; a supplied Space carries its own runtime."""
    result = subprocess.run(
        [sys.executable, "-c",
         "import sys; from metta import S, Expression, convert; "
         "from metta._binding.runtime import active_runtime; "
         "assert active_runtime() is None; "
         "assert convert.build(Expression([S.entry('value', 3)]), dict[str,int]) == {'value':3}; "
         "assert active_runtime() is None; assert 'janus_swi' not in sys.modules"],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    from metta._binding import runtime

    with MeTTa() as context, context.self.scope():
        native = context.self._new_space()
        native.add(Expression(["value", 3]))
        monkeypatch.setattr(runtime, "active_runtime", lambda: None)
        assert convert.build(native, dict[str, int]) == {"value": 3}
        assert convert.build(S[native.name], dict[str, int], space=context.self) == {"value": 3}


def test_mapping_conversion_never_registers_a_name():
    """A refused read cannot turn an unregistered namespace into a space value."""
    with MeTTa() as context:
        native = Space("mapping_empty_unregistered_namespace")
        image = S[native.name]
        with pytest.raises(TypeError, match="get-atoms expects a space"):
            convert.build(native, dict[str, int])
        assert convert.build(image, dict[str, int]) is image
        assert not context.self._rt.once("metta_space_registered(Name)", Name=native.name)


@pytest.mark.parametrize("annotation", (int | dict[str, int], int | MappingRow))
def test_mapping_unions_select_structural_and_borrowed_images(annotation):
    """The selected structural inverse has the same ownership as direct build."""
    value = {"value": 3}
    image = S.MappingRow(3) if annotation == int | MappingRow else Expression([S.entry("value", 3)])
    assert convert.build(image, annotation) == value
    assert convert.build(G(value), annotation) is value


@pytest.mark.parametrize("image", (Expression([S.entry("value")]), S.MappingRow(3, 4)))
def test_mapping_union_reverse_errors_are_visible(image):
    """A recognizable image cannot hide the error raised by its chosen inverse."""
    with pytest.raises(TypeError, match=r"dict of|requires 1 field"):
        convert.build(image, int | dict[str, int] | MappingRow)


@pytest.mark.parametrize("rows", (
    (),
    (Expression(["value", 3]), Expression(["extra", 7])),
    (Expression(["value", 3]), Expression(["value", 7])),
))
def test_typed_mapping_spaces_enforce_the_field_roster(rows):
    """A TypedDict image cannot lose missing, extra or repeated keys."""
    with MeTTa() as context, context.self.scope():
        native = context.self._new_space()
        native.add(*rows)
        with pytest.raises(TypeError, match=r"keys disagree|duplicate"):
            convert.build(native, MappingRow)


def test_typed_mapping_spaces_keep_the_optional_field_refusal():
    """A space representation does not invent an optional constructor encoding."""
    class OptionalRow(TypedDict, total=False):
        value: int

    with MeTTa() as context:
        with pytest.raises(TypeError, match="optional TypedDict"):
            convert.build(context.self, OptionalRow)


def test_mapping_keys_use_their_requested_python_type():
    """An unhashable reconstructed key is refused; a tuple key is retained."""
    image = Expression([S.entry(Expression([1, 2]), 3)])
    assert convert.build(image, dict[tuple[int, ...], int]) == {(1, 2): 3}
    with pytest.raises(TypeError, match="unhashable"):
        convert.build(image, dict[list[int], int])


@pytest.mark.parametrize("entry", (Expression([]), S.malformed, S.entry, S.entry(1, 2, 3)))
def test_mapping_structural_images_require_complete_entries(entry):
    """Every stored structural entry needs its head, key and value."""
    with pytest.raises(TypeError, match="dict of"):
        convert.build(Expression([entry]), dict[str, int])


def test_empty_mapping_images_reconstruct_without_inventing_fields():
    """Empty native and structural images retain the empty declared roster."""
    class EmptyRow(TypedDict):
        """The empty record has no required fields."""

    with MeTTa() as context, context.self.scope():
        native = context.self._new_space()
        assert convert.build(native, dict[str, int]) == {}
        assert convert.build(native, EmptyRow) == {}
        assert convert.build(Expression([]), dict[str, int]) == {}
        assert convert.build(S.EmptyRow(), EmptyRow) == {}


def test_mapping_conversion_preserves_foreign_owner_errors(scratch_space):
    """A selected foreign mapping keeps the provider's read refusal."""
    class RefusingRows(SpaceProvider):
        def atoms(self):
            msg = "mapping owner refuses this read"
            raise RuntimeError(msg)

    name = "&mapping-foreign-refusal"
    declarations._register_space(scratch_space, RefusingRows(), name)
    try:
        with pytest.raises(EngineError, match="mapping owner refuses this read"):
            convert.build(S[name], dict[str, int], space=scratch_space)
    finally:
        declarations._unregister_space(scratch_space, name)


def test_mapping_union_reads_a_foreign_snapshot_once(scratch_space):
    """Selecting a mapping inverse must not consume its provider twice."""
    class Rows(SpaceProvider):
        def __init__(self):
            self.reads = 0

        def atoms(self):
            self.reads += 1
            return [Expression(["value", self.reads])]

    name = "&mapping-foreign-once"
    provider = Rows()
    declarations._register_space(scratch_space, provider, name)
    try:
        assert convert.build(S[name], int | dict[str, int], space=scratch_space) == {"value": 1}
        assert provider.reads == 1
    finally:
        declarations._unregister_space(scratch_space, name)


def test_mapping_conversion_refuses_a_retired_owner():
    """A dropped handle retains its scope error at the mapping boundary."""
    with MeTTa() as context:
        with context.self.scope():
            native = context.self._new_space()
            native.add(Expression(["value", 3]))
        with pytest.raises(MettaError, match=r"dropped|released_scope_space"):
            convert.build(native, dict[str, int])
