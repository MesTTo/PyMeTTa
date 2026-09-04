"""Purpose: pin the upstream doc family against the arbiter's measured
answers, including a selected foreign space and its non-space boundaries.
Guarantees:
  - get-type-space reads only the selected space, while every doc helper
    builds the formal upstream shape [tested
    test_the_doc_family_answers_what_upstream_answers]
  - get-doc-params pairs every finite parameter list with the same-length
    type prefix and the final return type [tested
    test_get_doc_params_preserves_every_generated_position]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import pytest
from hypothesis import given
from hypothesis import strategies as st

from metta import MeTTa, parse


def test_the_doc_family_answers_what_upstream_answers(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with metta._new_space() as m:
        m.run(
            """
            (: scoped-atom Number)
            (@doc scoped-atom (@desc "ambient atom documentation"))
            (: scoped-function (-> Atom Number))
            (@doc scoped-function
              (@desc "ambient function documentation")
              (@params ((@param "ambient parameter")))
              (@return "ambient return"))
            !(bind! &foreign (new-space))
            !(add-atom &foreign (: scoped-atom String))
            !(add-atom &foreign
                (@doc scoped-atom (@desc "foreign atom documentation")))
            !(add-atom &foreign (: scoped-function (-> Atom String)))
            !(add-atom &foreign
                (@doc scoped-function
                  (@desc "foreign function documentation")
                  (@params ((@param "foreign parameter")))
                  (@return "foreign return")))
            """
        )

        atom_ambient = parse(
            '(@doc-formal (@item scoped-atom) (@kind atom) (@type Number) '
            '(@desc "ambient atom documentation"))'
        )
        atom_foreign = parse(
            '(@doc-formal (@item scoped-atom) (@kind atom) (@type String) '
            '(@desc "foreign atom documentation"))'
        )
        function_ambient = parse(
            '(@doc-formal (@item scoped-function) (@kind function) '
            '(@type (-> Atom Number)) (@desc "ambient function documentation") '
            '(@params ((@param (@type Atom) (@desc "ambient parameter")))) '
            '(@return (@type Number) (@desc "ambient return")))'
        )
        function_foreign = parse(
            '(@doc-formal (@item scoped-function) (@kind function) '
            '(@type (-> Atom String)) (@desc "foreign function documentation") '
            '(@params ((@param (@type Atom) (@desc "foreign parameter")))) '
            '(@return (@type String) (@desc "foreign return")))'
        )
        space_error = parse(
            '(Error (get-type-space not-a-space scoped-atom) '
            '"get-type-space expects a space as the first argument")'
        )

        cases = (
            ("!(get-type-space &self scoped-atom)", [[parse("Number")]]),
            ("!(get-type-space &foreign scoped-atom)", [[parse("String")]]),
            (
                "!(let $space &foreign (get-type-space $space scoped-atom))",
                [[parse("String")]],
            ),
            ("!(get-type-space not-a-space scoped-atom)", [[space_error]]),
            ("!(get-doc &self scoped-atom)", [[atom_ambient]]),
            ("!(get-doc &foreign scoped-atom)", [[atom_foreign]]),
            (
                "!(let $space &foreign (get-doc $space scoped-atom))",
                [[atom_foreign]],
            ),
            ("!(get-doc not-a-space scoped-atom)", [[space_error]]),
            ("!(get-doc-atom &self scoped-atom)", [[atom_ambient]]),
            ("!(get-doc-atom &foreign scoped-atom)", [[atom_foreign]]),
            (
                "!(let $space &foreign (get-doc-atom $space scoped-atom))",
                [[atom_foreign]],
            ),
            ("!(get-doc-atom not-a-space scoped-atom)", [[space_error]]),
            ("!(get-doc-single-atom &self scoped-atom)", [[atom_ambient]]),
            ("!(get-doc-single-atom &foreign scoped-atom)", [[atom_foreign]]),
            (
                "!(let $space &foreign "
                "(get-doc-single-atom $space scoped-atom))",
                [[atom_foreign]],
            ),
            (
                "!(get-doc-single-atom not-a-space scoped-atom)",
                [[space_error]],
            ),
            (
                "!(get-doc-function &self scoped-function (-> Atom Number))",
                [[function_ambient]],
            ),
            (
                "!(get-doc-function &foreign scoped-function (-> Atom String))",
                [[function_foreign]],
            ),
            (
                "!(let $space &foreign "
                "(get-doc-function $space scoped-function (-> Atom String)))",
                [[function_foreign]],
            ),
            (
                "!(get-doc-function not-a-space scoped-function "
                "(-> Atom Number))",
                [[]],
            ),
            (
                '!(get-doc-params ((@param "ambient parameter")) '
                '(@return "ambient return") (Atom Number))',
                [[
                    parse(
                        '(((@param (@type Atom) (@desc "ambient parameter"))) '
                        '(@return (@type Number) (@desc "ambient return")))'
                    )
                ]],
            ),
        )

        for source, expected in cases:
            assert m.run(source) == expected, source


@given(st.integers(min_value=0, max_value=8))
def test_get_doc_params_preserves_every_generated_position(parameter_count):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    params = " ".join(f'(@param "parameter {index}")' for index in range(parameter_count))
    types = " ".join([*(f"Type{index}" for index in range(parameter_count)), "ReturnType"])
    source = f'!(get-doc-params ({params}) (@return "result") ({types}))'

    formal_params = " ".join(
        f'(@param (@type Type{index}) (@desc "parameter {index}"))'
        for index in range(parameter_count)
    )
    expected = parse(
        f'(({formal_params}) (@return (@type ReturnType) (@desc "result")))'
    )

    assert MeTTa().self.run(source) == [[expected]]


def test_the_doc_verb_answers_the_structured_atom(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    import pytest

    import metta as package
    from metta import S
    from metta.errors import EngineError

    with metta._new_space() as m:
        m.run(
            """
            (: verbed-atom Number)
            (@doc verbed-atom (@desc "the verb reads this"))
            """
        )
        answer = m.doc(S["verbed-atom"])
        assert answer == parse(
            '(@doc-formal (@item verbed-atom) (@kind atom) (@type Number) '
            '(@desc "the verb reads this"))'
        )
        assert m.doc("verbed-atom") == answer
        with pytest.raises(EngineError, match="no documentation"):
            m.doc(S["never-documented-here"])
    # The module-level door reads the default context's self space, exactly
    # as metta.match and metta.eval do.
    package.run('(@doc ambient-doc-verb (@desc "ambient"))')
    ambient = package.doc(S["ambient-doc-verb"])
    assert '(@desc "ambient")' in str(ambient)


def test_a_function_documented_without_parameters_reaches_the_scoped_door(metta):
    """The portable `(@doc name (@desc ...))` shape on an arrow-typed name.

    `get-doc-function` builds the four-field shape and matches only
    `('@doc' Name Desc ('@params' _) _)`, so committing every arrow type to it
    left the scoped door answering nothing while the unary `get-doc` answered
    the same row from the same space. A downstream integration documents 47
    arrow-typed callables that way and every one of them raised here.
    """
    from metta import S
    from metta.errors import EngineError

    with metta._new_space() as kb:
        kb.run('(: fpc.test (-> Number Number))\n(@doc fpc.test (@desc "Portable"))')

        # The unary form always saw it; that is what made the scoped miss a bug
        # rather than a missing document.
        assert len(kb.eval("(get-doc fpc.test)")) == 1

        answer = str(kb.doc(S["fpc.test"]))
        assert "(@kind function)" in answer
        assert "(@type (-> Number Number))" in answer
        assert '(@desc "Portable")' in answer

        # A function documented WITH parameters keeps the full formal shape.
        kb.run(
            '(: full (-> Number Number))\n'
            '(@doc full (@desc "Full") (@params ((@param "x"))) (@return "y"))'
        )
        full = str(kb.doc(S.full))
        assert "(@params" in full
        assert "(@return" in full

        # A name that was never documented still raises, so the door keeps
        # saying "no documentation" rather than inventing a placeholder.
        # The name has to be one the engine does not document itself:
        # `undocumented` is engine vocabulary and resolves from the prelude
        # register, which is get-doc's documented fallback and not a miss.
        kb.run("(: fpc.never-written (-> Number Number))")
        with pytest.raises(EngineError):
            kb.doc(S["fpc.never-written"])
