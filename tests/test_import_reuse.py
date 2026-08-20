"""Purpose: regressions for complete, idempotent library imports across
pooled-space reuse, including loud errors from imported source files.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import pytest

from petta import EngineError, S, expr

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
    parked = [metta.new_space() for _ in range(free_count)]
    try:
        names = []
        for _ in range(2):
            with metta.new_space() as scratch:
                names.append(scratch.space_name)
                assert scratch.run(DATETIME_IMPORT) == [[expr()]]
                assert _format_date_clause_count(scratch) == 1
                assert scratch.run(FORMAT_DATE_CALL) == [[S.January]]

        assert names[0] == names[1]
    finally:
        for space in parked:
            space.drop()


def test_same_life_double_import_is_a_no_op(metta):
    with metta.new_space() as scratch:
        assert scratch.run(DATETIME_IMPORT) == [[expr()]]
        clauses_before = _format_date_clause_count(scratch)
        atoms_before = scratch.count()

        assert scratch.run(DATETIME_IMPORT) == [[expr()]]
        assert _format_date_clause_count(scratch) == clauses_before == 1
        assert scratch.count() == atoms_before
        assert scratch.run(FORMAT_DATE_CALL) == [[S.January]]


def test_import_translation_leaves_variable_heads_dynamic(metta):
    with metta.new_space() as scratch:
        assert scratch.run(
            "(= (apply-two $function $left $right) "
            "($function $left $right)) !(apply-two + 20 22)"
        ) == [[42]]


def test_imported_source_error_names_the_file(metta, tmp_path):
    broken = tmp_path / "broken-import.metta"
    # An error carrying no context of its own, because that is the only kind
    # the loader may name the file in: rethrow_metta_file_error/2 leaves an
    # error that already names its own operation exactly as it found it. A
    # wrong arity used to be one and is now an ANSWER, so it neither raises
    # nor rolls the source back.
    broken.write_text(
        "(= (partial-import $number) (+ $number 1))\n!(unbalanced\n"
    )

    with metta.new_space() as scratch:
        with pytest.raises(EngineError) as caught:
            scratch.run(f'!(import! (context-space) "{broken}")')

        assert str(broken) in str(caught.value)

        # And the rollback, on a file that gets far enough to compile the
        # definition before its last form raises. Two unbound arithmetic
        # operands are a HOST instantiation error; integer division by zero
        # is a contained Error answer now and cannot be a rollback sentinel.
        # The host error carries its own context, so this half is checked
        # apart from the naming above rather than through one file that
        # cannot show both.
        broken.write_text(
            "(= (partial-import $number) (+ $number 1))\n!(+ $a $b)\n"
        )
        with pytest.raises(EngineError):
            scratch.run(f'!(import! (context-space) "{broken}")')
        clauses = scratch.runtime.once(
            "space_module(Space, _M), functor(_H, 'partial-import', 2), "
            "aggregate_all(count, clause(_M:_H, _), N)",
            Space=scratch.space_name,
        )["N"]
        assert clauses == 0

        broken.write_text("(= (recovered-import) recovered)\n")
        # import! answers the unit value, the way add-atom and pragma! do.
        assert scratch.run(f'!(import! (context-space) "{broken}")') == [[expr()]]
        assert scratch.run("!(recovered-import)") == [[S.recovered]]


def test_missing_import_is_loud_and_names_the_file(metta, tmp_path):
    missing = tmp_path / "missing-import.metta"

    with metta.new_space() as scratch, pytest.raises(EngineError) as caught:
        scratch.run(f'!(import! (context-space) "{missing}")')

    assert str(missing) in str(caught.value)


def test_an_import_into_a_named_space_registers_its_equations_there(
    metta, tmp_path
):
    """An alias import admits nothing into the caller: LeaTTa's law.

    grounded/29-builtin-module-alias-import pins it byte-exactly (MEASURED:
    both alias probes stay unreduced data, and only the companion &self
    import makes the tiers callable), and its model is World.moduleReady
    testing the RUNNING CONTEXT's own space's import mark. The loader used
    to compile an import's equations into &self's module whatever space the
    atoms went to, so a top-level call reduced through a space it never
    imported; every receiving space compiles its own copy now.
    """
    module = tmp_path / "scoped-import.metta"
    module.write_text("(= (scoped-swap (Pair $a $b)) (Pair $b $a))\n")
    with metta.new_space() as importer:
        assert importer.run(f'!(import! (context-space) "{module}")') == [
            [expr()]
        ]
        assert importer.run("!(scoped-swap (Pair a b))") == [
            [expr(S.Pair, S.b, S.a)]
        ]
        # While the importer holds it, the top level still never imported
        # it, so there the name stays data, whole call handed back.
        stayed = metta.run("!(scoped-swap (Pair c d))")
        assert stayed == [[expr(S["scoped-swap"], expr(S.Pair, S.c, S.d))]]

    # The arbiter's own spelling, a built-in module under an alias.
    bound = metta.run("!(bind! &scoped-skel (new-space))")
    assert bound == [[expr()]]
    assert metta.run("!(import! &scoped-skel skel)") == [[expr()]]
    alias_probe = metta.run("!(skel-swap-pair (Pair a b))")
    assert alias_probe == [
        [expr(S["skel-swap-pair"], expr(S.Pair, S.a, S.b))]
    ]
