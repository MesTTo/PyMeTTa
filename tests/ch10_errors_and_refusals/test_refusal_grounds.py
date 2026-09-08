"""Purpose: pin structured grounds and remedies on semantic refusals.

Guarantees:
  - atom/plain ordering refuses in both operand directions with Python's rich
    comparison ground, while atom/atom and grounded/plain ordering remain
    lawful [tested: extensions/python/tests/ch10_errors_and_refusals/test_refusal_grounds.py; commit=acb40f1912f131ae088083d1af29b4b283019bea]
  - comparison-term truthiness names Python 6.10 and the explicit conjunction
    remedy required by GG5-019 [tested:
    test_comparison_truthiness_names_python_6_10_and_the_conjunction_remedy;
    commit=acb40f1912f131ae088083d1af29b4b283019bea]
  - compiler refusals carry their Python-reference ground as data without
    rewriting the sibling-owned unknown-callee message [tested:
    test_compile_refusals_derive_a_python_reference_ground; commit=acb40f1912f131ae088083d1af29b4b283019bea]
  - the CONSTRUCT list is the compiler's own: every construct its sites name
    reaches a citation or is named as one the expression section governs, and
    every term in the citation table governs a construct that exists
    [tested: test_every_construct_the_compiler_refuses_has_a_citation,
    test_no_citation_term_governs_a_construct_that_does_not_exist;
    commit=WORKTREE]
"""

from __future__ import annotations

import pytest

from metta import G, S, V
from metta.errors import CompileError


@pytest.fixture()
def m(metta):
    """Give compiler-refusal scenarios an isolated destination."""
    with metta._new_space() as space:
        yield space


def _assert_python_ground(error: BaseException, section: str) -> None:
    ground = error.ground
    assert ground.kind == "host-reference"
    assert f"Python Language Reference section {section}" in ground.citation


@pytest.mark.parametrize(
    "comparison",
    (
        lambda: S.atom < 1,
        lambda: 1 < S.atom,
    ),
)
def test_atom_plain_order_refuses_in_both_directions_with_its_python_ground(
    comparison,
):
    """P11 and P12 refuse at Python's unsupported-rich-comparison boundary."""
    with pytest.raises(TypeError) as caught:
        comparison()

    _assert_python_ground(caught.value, "3.3.1")
    assert "unwrap a grounded primitive with .value" in str(caught.value)


def test_atom_and_grounded_order_controls_remain_allowed():
    """The ground does not broaden the refusal beyond unlike representations."""
    assert isinstance(S.a < S.b, bool)
    assert G(1) < 2


def test_comparison_truthiness_names_python_6_10_and_the_conjunction_remedy():
    """GG5-019's reference, failure mechanism, and exact remedy stay visible."""
    with pytest.raises(TypeError) as caught:
        bool(S.le(1, V.x))

    message = str(caught.value)
    assert "Python Language Reference section 6.10" in message
    assert "a chained comparison uses truthiness between its terms" in message
    assert "S.le(1, V.x) & S.le(V.x, 10)" in message
    assert "or use a named predicate" in message
    _assert_python_ground(caught.value, "6.10")


def test_an_ordinary_expression_remains_truthy():
    """Only comparison and Boolean terms own the truthiness refusal."""
    assert bool(S.Record(S.value)) is True


def test_a_refusal_renders_the_file_line_function_and_exact_caret(m):
    """CompileError renders path, function, line and a caret over the construct.

    This is errors.py's rendering guarantee, witnessed through a wall that
    still stands (the bare `raise`), since the unknown-call refusal that
    used to carry it compiles as an island now. The caret's columns are
    checked against the source line itself, so "exact span" is measured
    rather than asserted.
    """
    with pytest.raises(CompileError) as caught:
        @m.define(name="refusal-caret-span")
        def caret_scene(value):  # noqa: ARG001  -- the refused scenario needs a parameter and never runs
            raise  # noqa: PLE0704  -- Python's own rule is the scenario under test

    rendered = str(caught.value)
    lines = rendered.splitlines()
    place = next(line for line in lines if line.startswith("  --> "))
    assert "test_refusal_grounds.py" in place
    assert " in caret_scene " in place
    source_row = next(line for line in lines if line.lstrip().startswith(tuple("0123456789")))
    caret_row = lines[lines.index(source_row) + 1]
    prefix = source_row.index("| ") + 2
    body = source_row[prefix:]
    span = caret_row[prefix:]
    assert body[body.index("raise") :].startswith("raise")
    assert span[body.index("raise") : body.index("raise") + len("raise")] == "^" * len("raise")


def test_compile_refusals_derive_a_python_reference_ground(m):
    """Surviving refusals cite Python's own statements as their ground.

    The unknown-call and floor-division arms this test carried are
    compiled forms now (the island fallback and the engine's floor-div),
    so the grounds live where genuine walls remain: a bare `raise` with no
    active exception, and `nonlocal`, whose enclosing frame no stored
    equation outlives.
    """
    with pytest.raises(CompileError) as bare:
        @m.define(name="refusal-ground-bare-raise")
        def bare_raise(value):  # noqa: ARG001  -- the refused scenario needs a parameter and never runs
            raise  # noqa: PLE0704  -- Python's own rule is the scenario under test

    def enclosing():
        cell = 0
        with pytest.raises(CompileError) as caught:
            @m.define(name="refusal-ground-nonlocal")
            def nonlocal_write(value):
                nonlocal cell
                cell = value
                return value
        del cell
        return caught

    frame = enclosing()

    _assert_python_ground(bare.value, "7.8")
    _assert_python_ground(frame.value, "7.12-7.13")
    assert "no active exception" in str(bare.value)
    assert "enclosing function frame" in str(frame.value)


def test_a_space_door_on_the_context_names_the_self_spelling():
    """A context asked for a Space door says where the door is.

    An installer written as `install(m)` reached for `m.is_function` and got
    Python's bare `'MeTTa' object has no attribute 'is_function'`, which says
    nothing about `m.self.is_function` one attribute away. The roster is
    Space's own surface, so this covers every storage and introspection door
    rather than the seven that were reported.
    """
    import metta

    doors = sorted(
        name
        for name in dir(metta.Space)
        if not name.startswith("_") and not hasattr(metta.MeTTa, name)
    )
    assert {"atoms", "digest", "is_function", "type"} <= set(doors)

    with metta.MeTTa() as context:
        for name in doors:
            with pytest.raises(AttributeError) as refused:
                getattr(context, name)
            assert f"m.self.{name}" in str(refused.value)
            # The refusal stays an ordinary missing attribute, so a caller
            # probing the surface reads False rather than catching a message.
            assert not hasattr(context, name)
            assert getattr(context, name, "absent") == "absent"

        # A name that is nobody's door keeps Python's own wording, because
        # inventing a remedy for a typo would point at a space that has none.
        with pytest.raises(AttributeError) as unknown:
            getattr(context, "no_such_door_anywhere")  # noqa: B009  -- the attribute read IS the scenario
        assert "no attribute 'no_such_door_anywhere'" in str(unknown.value)
        assert "m.self." not in str(unknown.value)


def _refused_constructs() -> set[str]:
    """Every construct the compiler's own CompileError sites can name.

    The literal `construct=` values, plus the `ast` node class names the sites
    that pass `type(node).__name__` produce. This is what makes the citation
    table's CONSTRUCT list derived: a construct the compiler stops refusing
    leaves it by itself, and a new one arrives with no citation and is a
    finding here rather than a silent fall through to section 6.
    """
    import ast
    from pathlib import Path

    import metta

    package = Path(metta.__file__).resolve().parent
    found: set[str] = set()
    computed = False
    for path in sorted(package.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for call in (node for node in ast.walk(tree) if isinstance(node, ast.Call)):
            function = call.func
            name = getattr(function, "id", None) or getattr(function, "attr", None)
            if name != "CompileError":
                continue
            for keyword in call.keywords:
                if keyword.arg != "construct":
                    continue
                if isinstance(keyword.value, ast.Constant):
                    found.add(str(keyword.value.value))
                elif "__name__" in ast.unparse(keyword.value):
                    computed = True
    assert found, "the walk found no CompileError construct at all"
    assert computed, (
        "no site passes type(node).__name__ any more; the ast half of the "
        "construct universe is stale and this walk should drop it"
    )
    return found


def test_every_construct_the_compiler_refuses_has_a_citation():
    """A construct with no row, and no exemption, is a finding."""
    from metta.errors import _COMPILE_REFERENCE_BY_CONSTRUCT, _EXPRESSION_CONSTRUCTS

    terms = [term for group, _ in _COMPILE_REFERENCE_BY_CONSTRUCT for term in group]
    uncited = sorted(
        construct
        for construct in _refused_constructs()
        if construct not in _EXPRESSION_CONSTRUCTS
        and not any(term in construct.lower() for term in terms)
    )
    assert not uncited, (
        f"these constructs fall through to the expressions section with no "
        f"row and no exemption: {uncited}"
    )


def test_no_citation_term_governs_a_construct_that_does_not_exist():
    """A term matching nothing the compiler names is a stale row."""
    import ast

    from metta.errors import _COMPILE_REFERENCE_BY_CONSTRUCT

    universe = {construct.lower() for construct in _refused_constructs()}
    universe |= {name.lower() for name in dir(ast)}
    dead = sorted(
        term
        for group, _ in _COMPILE_REFERENCE_BY_CONSTRUCT
        for term in group
        if not any(term in construct for construct in universe)
    )
    assert not dead, f"these citation terms govern no construct that exists: {dead}"
