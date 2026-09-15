"""Purpose: distinguish constructor inputs from stored dataclass fields."""

import dataclasses
from typing import NamedTuple, NotRequired, TypedDict

import pytest

from metta._spaces.results import Rows
from metta.convert import register_type, unregister_type


def test_rows_into_uses_constructor_inputs():
    """Computed fields, defaults and keyword-only inputs follow construction."""
    @dataclasses.dataclass
    class Record:
        stored: int
        optional: int = 4
        keyword: int = dataclasses.field(default=5, kw_only=True)
        computed: int = dataclasses.field(init=False, default=9)

    assert Rows(("stored", "computed"), [(1, 999)]).into(Record) == [Record(1)]
    assert Rows(("stored", "keyword"), [(2, 7)]).into(Record) == [Record(2, keyword=7)]
    with pytest.raises(TypeError, match="stored"):
        Rows(("optional",), [(3,)]).into(Record)


def test_registered_constructor_binds_positional_only_and_keyword_only_inputs():
    """Named columns keep defaults before supplied positional-only arguments."""
    class AuditBoundRecord:
        def __init__(self, first: int = 3, second: int = 4, /, *, required: str):
            self.values = first, second, required

    register_type(AuditBoundRecord, image="handle")
    try:
        result = Rows(("second", "required"), [(8, "present")]).into(AuditBoundRecord)
        assert result[0].values == (3, 8, "present")
        with pytest.raises(TypeError, match="required"):
            Rows(("second",), [(8,)]).into(AuditBoundRecord)
        with pytest.raises(TypeError, match="not int"):
            Rows(("second", "required"), [(True, "present")]).into(AuditBoundRecord)
    finally:
        unregister_type(AuditBoundRecord)


def test_dataclass_factory_and_initvar_are_constructor_inputs():
    """Fresh default factories and transient InitVar inputs keep native behavior."""
    @dataclasses.dataclass
    class AuditConstructedRecord:
        source: dataclasses.InitVar[int]
        values: list = dataclasses.field(default_factory=list)
        stored: int = dataclasses.field(init=False)

        def __post_init__(self, source):
            self.stored = source * 2

    first, second = Rows(("source",), [(2,), (3,)]).into(AuditConstructedRecord)
    assert (first.stored, second.stored) == (4, 6)
    assert first.values == second.values == []
    assert first.values is not second.values


def test_namedtuple_constructor_defaults_are_optional_columns():
    """Omitted fields use the tuple constructor's own defaults."""
    class AuditDefaultTuple(NamedTuple):
        required: int
        optional: int = 7

    try:
        assert Rows(("required",), [(2,)]).into(AuditDefaultTuple) == [AuditDefaultTuple(2)]
    finally:
        unregister_type(AuditDefaultTuple)


def test_typed_mapping_keeps_omitted_optional_keys_absent():
    """Optionality is key presence, including keys that are not identifiers."""
    class AuditOptions(TypedDict):
        required: int
        optional: NotRequired[int]

    assert Rows(("required",), [(2,)]).into(AuditOptions) == [{"required": 2}]
    assert Rows(("required", "optional"), [(2, 4)]).into(AuditOptions) == [
        {"required": 2, "optional": 4}
    ]
    with pytest.raises(TypeError, match="required"):
        Rows(("optional",), [(2,)]).into(AuditOptions)
    UnusualKeys = TypedDict("UnusualKeys", {"field-name": int}, total=False)
    assert Rows(("field-name",), [(3,)]).into(UnusualKeys) == [{"field-name": 3}]
