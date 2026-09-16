"""Purpose: verify class consumers of the native owned-record contract.

Owns resources: contexts release declarations and objects; concurrent controls
  release each worker even if preparation fails.
Guarantees: controls observe native rows, Python aliases, source lifetimes and
  retained dependency values through the generated class programs
  [source: extensions/python/tests/ch09_types/test_class_owned_records.py;
  commit=829c6960c1f02a4745aa60408a8e8b5feba0521e].
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from metta import Atom, Expression, Grounded, MeTTa, S, Space, V, convert
from metta._declare.classes import declaration
from metta._errors.errors import EngineError


def _schemas(plan):
    row = S["@owned-record"](S[plan.space._name], V.owner, V.storage, V.prefix)
    return Space("&metta", _runtime=plan.space._rt).eval(S.match(S["&metta"], row, row))


@pytest.mark.parametrize("base", [object, Space])
def test_record_patterns_follow_the_class_program_not_its_instances(base):
    """Borrowing and allocation preserve one pattern per actual storage prefix."""
    with MeTTa() as context:
        first, second = context.space(), context.space()

        @dataclass
        class RecordProgram(base):
            left: int
            right: int = 2

        first.define(RecordProgram, methods=False)
        plan = declaration(RecordProgram)
        rows = _schemas(plan)
        assert len(rows) == 3
        second.define(RecordProgram, methods=False)
        values = [RecordProgram(index) for index in range(5)]
        assert len(_schemas(plan)) == 3
        assert all(value.left == index for index, value in enumerate(values))
        first.drop()
        assert declaration(RecordProgram) is plan
        assert len(_schemas(plan)) == 3
        second.drop()
        assert declaration(RecordProgram) is None
        assert _schemas(plan) == []


def test_record_declaration_withdrawal_preserves_an_independent_equal_occurrence():
    """A class releases only the catalog occurrences its publication added."""
    with MeTTa() as context:
        home = context.space()

        @dataclass
        class RecordSource:
            value: int

        home.define(RecordSource, methods=False)
        plan = declaration(RecordSource)
        catalog = Space("&metta", _runtime=home._rt)
        row = _schemas(plan)[0]
        catalog.add(row)
        try:
            assert len(_schemas(plan)) == 3
            home.drop()
            assert len(_schemas(plan)) == 1
        finally:
            catalog.remove(row)


@pytest.mark.parametrize("base", [object, Space])
def test_record_declarations_roll_back_with_their_class(base):
    """Failed publication leaves neither instrumentation nor catalog ownership."""
    with MeTTa() as context:
        home = context.self

        @dataclass
        class RecordRollback(base):
            value: int

        plans = []

        def failed():
            home.define(RecordRollback, methods=False)
            plans.append(declaration(RecordRollback))
            assert len(_schemas(plans[-1])) == 2
            message = "record declaration rollback"
            raise ValueError(message)

        with pytest.raises(ValueError, match="record declaration rollback"):
            home.transaction(failed)
        assert declaration(RecordRollback) is None
        assert _schemas(plans[0]) == []
        home.define(RecordRollback, methods=False)
        assert RecordRollback(3).value == 3


@pytest.mark.parametrize("base", [object, Space])
@pytest.mark.parametrize("empty", [False, True])
@pytest.mark.parametrize("native", [False, True])
@pytest.mark.parametrize("same_value", [False, True])
def test_overlapping_field_writes_use_the_published_record_patterns(base, empty, native, same_value, overlap):
    """Both setter routes reject the second committed occurrence, including equal values."""
    with MeTTa() as context:
        home = context.self

        @dataclass
        class RecordOverlap(base):
            value: int

        home.define(RecordOverlap, methods=False)
        plan = declaration(RecordOverlap)
        if empty:
            image = plan.answer(S[f"_mint-{plan.name}"]())
            holder = convert.build(image, RecordOverlap)
        else:
            holder = RecordOverlap(0)
            image = convert.project(holder).atom
        record = plan.field_record(image, plan.storage_head("value"))
        storage = Space(record.storage, _runtime=home._rt)

        def write(value):
            if native:
                storage.remove(record.row(V.value))
                storage.add(record.row(Grounded(value)))
            else:
                holder.value = value

        first, second = overlap(home, [lambda: write(1), lambda: write(1 if same_value else 2)])
        assert first is None
        assert isinstance(second, EngineError)
        assert "retry the outer transaction" in str(second)
        assert holder.value == 1
        assert storage.eval(S.match(record.storage, record.row(V.value), V.value)) == [1]


@pytest.mark.parametrize("base", [object, Space])
@pytest.mark.parametrize("corruption", ["duplicate_value", "variable_value_key", "duplicate_owner", "variable_owner_key", "retired_owner"])
def test_generated_reads_refuse_malformed_original_native_records(base, corruption):
    """Unwrapped graph edits cannot make the getter choose a plausible row.

    A plain add or remove outside a transaction runs no commit check, so the
    corruption lands. Every read of the record then refuses and names the
    repair rather than a retry, and the repaired record reads as before.
    """
    with MeTTa() as context:
        home = context.self

        @dataclass
        class RecordMalformed(base):
            value: int

        home.define(RecordMalformed, methods=False)
        holder = RecordMalformed(1)
        plan = declaration(RecordMalformed)
        image = convert.project(holder).atom
        record = plan.field_record(image, plan.storage_head("value"))
        storage = Space(record.storage, _runtime=home._rt)
        owner_rows = S["owned-by"](S.RecordMalformed(V.identity))
        if corruption == "duplicate_value":
            storage.add(record.row(Grounded(1)))
            remedy = "remove the surplus value rows"
        elif corruption == "variable_value_key":
            # A prototype's sole key is its fixed field head.
            storage.add(Expression([V.field_head, Grounded(2)]) if base is Space
                        else S["_field-value"](S.RecordMalformed(V.identity), 2))
            remedy = "must be ground"
        elif corruption == "duplicate_owner":
            plan.space.add(record.owner_row)
            remedy = "remove the surplus owner rows"
        elif corruption == "variable_owner_key":
            plan.space.remove(record.owner_row)
            plan.space.add(owner_rows)
            remedy = "must be ground"
        else:
            plan.space.remove(record.owner_row)
            remedy = "the native owner has retired"

        def repair():
            del storage[record.row(V.value)]
            while plan.space.remove(owner_rows):
                pass
            plan.space.add(record.owner_row)
            storage.add(record.row(Grounded(1)))

        try:
            with pytest.raises(EngineError, match=remedy):
                _ = holder.value
            with pytest.raises(EngineError, match=remedy):
                plan.answer(S["RecordMalformed-value"](S.noeval(image)))
        finally:
            home.transaction(repair)
        assert holder.value == 1


@pytest.mark.parametrize("base", [object, Space])
def test_stored_error_dependency_rows_keep_their_referenced_spaces(base):
    """An Error stored as data is not a failed Scope dependency query."""
    with MeTTa() as context:
        home = context.self

        @dataclass
        class RecordErrorDependency(base):
            payload: Atom

        home.define(RecordErrorDependency, methods=False)
        plan = declaration(RecordErrorDependency)
        with home.scope():
            with home.scope() as inner:
                holder = RecordErrorDependency(S.empty_payload)
                image = convert.project(holder).atom
                payload = context.space()
                record = plan.field_record(image, plan.storage_head("payload"))
                storage = Space(record.storage, _runtime=home._rt)
                error = S.Error(S.data(S[payload.name]), S.stored)
                storage.remove(record.row(V.value))
                storage.add(record.row(error))
                inner.keep(image)
            assert not payload.dropped
            assert storage.eval(S.match(record.storage, record.row(V.value), record.row(V.value))) == [record.row(error)]
        assert payload.dropped
