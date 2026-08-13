"""Purpose: regressions for complete, idempotent library imports across
pooled-space reuse, including loud errors from imported source files.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import pytest
from petta import EngineError, S

DATETIME_IMPORT = "!(import! (context-space) (library lib_datetime))"
FORMAT_DATE_CALL = '!(format-date 1735689600 "%B")'


def _format_date_clause_count(metta) -> int:
    row = metta.runtime.once(
        "space_module(Space, _M), functor(_H, 'format-date', 3), "
        "aggregate_all(count, clause(_M:_H, _), N)",
        Space=metta.space_name,
    )
    return row["N"]


def test_reused_pooled_space_reimports_complete_library(metta):
    free_count = metta.runtime.once(
        "aggregate_all(count, petta_py_free_space(_), N)"
    )["N"]
    parked = [metta.fresh_space() for _ in range(free_count)]
    try:
        names = []
        for _ in range(2):
            with metta.fresh_space() as scratch:
                names.append(scratch.space_name)
                assert scratch.run(DATETIME_IMPORT) == [[True]]
                assert _format_date_clause_count(scratch) == 1
                assert scratch.run(FORMAT_DATE_CALL) == [[S.January]]

        assert names[0] == names[1]
    finally:
        for space in parked:
            space.drop()


def test_same_life_double_import_is_a_no_op(metta):
    with metta.fresh_space() as scratch:
        assert scratch.run(DATETIME_IMPORT) == [[True]]
        clauses_before = _format_date_clause_count(scratch)
        atoms_before = scratch.count()

        assert scratch.run(DATETIME_IMPORT) == [[True]]
        assert _format_date_clause_count(scratch) == clauses_before == 1
        assert scratch.count() == atoms_before
        assert scratch.run(FORMAT_DATE_CALL) == [[S.January]]


def test_import_translation_leaves_variable_heads_dynamic(metta):
    with metta.fresh_space() as scratch:
        assert scratch.run(
            "(= (apply-two $function $left $right) "
            "($function $left $right)) !(apply-two + 20 22)"
        ) == [[42]]


def test_imported_source_error_names_the_file(metta, tmp_path):
    broken = tmp_path / "broken-import.metta"
    broken.write_text(
        "(= (partial-import $number) (+ $number 1))\n!(+ 1 2 3)\n"
    )

    with metta.fresh_space() as scratch:
        with pytest.raises(EngineError) as caught:
            scratch.run(f'!(import! (context-space) "{broken}")')

        assert str(broken) in str(caught.value)
        clauses = scratch.runtime.once(
            "space_module(Space, _M), functor(_H, 'partial-import', 2), "
            "aggregate_all(count, clause(_M:_H, _), N)",
            Space=scratch.space_name,
        )["N"]
        assert clauses == 0

        broken.write_text("(= (recovered-import) recovered)\n")
        assert scratch.run(f'!(import! (context-space) "{broken}")') == [[True]]
        assert scratch.run("!(recovered-import)") == [[S.recovered]]


def test_missing_import_is_loud_and_names_the_file(metta, tmp_path):
    missing = tmp_path / "missing-import.metta"

    with metta.fresh_space() as scratch, pytest.raises(EngineError) as caught:
        scratch.run(f'!(import! (context-space) "{missing}")')

    assert str(missing) in str(caught.value)
