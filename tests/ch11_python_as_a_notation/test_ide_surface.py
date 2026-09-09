"""Purpose: the surface an editor and a checker read.

`@typing.override` as a declaration the define door checks, and the `.pyi` a
space projects.

The declaration half is the other direction of the inherited-declarations
ruling: a definition that hides an inherited one is deliberate and stays
silent, and `@override` is the developer saying so, refused when there is
nothing to hide. The projection half reads the space's own rows and renders
them, so an editor completes a MeTTa program's heads and mypy refuses a call
that passes the wrong thing.

Guarantees:
  - override is accepted over an inherited definition, refused with both
    remedies when nothing is shadowed, and absent it changes nothing [tested:
    test_override_declares_a_shadow_of_an_inherited_definition,
    test_override_is_refused_when_nothing_is_shadowed,
    test_a_shadowing_definition_without_the_decorator_is_unchanged;
    commit=dd4f82100a052e2c5254a2ef9e91f6eb9d2e0c49]
  - a generated stub parses, and a consumer of it passes `mypy --strict` on
    the right argument type and fails on the wrong one [tested:
    test_a_generated_stub_checks_its_consumer; commit=dd4f82100a052e2c5254a2ef9e91f6eb9d2e0c49]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

import ast
import subprocess
import sys
from pathlib import Path
from typing import override

import pytest

from metta._catalog.declarations import declarations
from metta._declare import functions as _space_functions
from metta._declare.stubs import stubs
from metta._errors.errors import CompileError

_PACKAGE_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture()
def base(metta):
    """A space whose definition another space can inherit and hide."""
    space = metta._new_space()
    space.run("(: ide-area (-> Number Number))")
    space.run("(= (ide-area $r) (* $r $r))")
    return space


def test_override_declares_a_shadow_of_an_inherited_definition(metta, base):
    """The decorator states what the name-hiding rule already allowed."""
    child = metta._new_space(inherits=base)

    @child.define(name="ide-area")
    @override
    def ide_area(r):
        return r + r

    assert [str(atom) for atom in child.eval("(ide-area 3)")] == ["6"]
    # The space it hides is untouched: hiding is per space, not a rewrite.
    assert [str(atom) for atom in base.eval("(ide-area 3)")] == ["9"]


def test_override_is_refused_when_nothing_is_shadowed(metta):
    """Nothing to override is the one thing the decorator claims is false."""
    space = metta._new_space()

    with pytest.raises(CompileError) as refusal:
        @space.define
        @override
        def ide_unshadowed(x):
            return x

    message = str(refusal.value)
    assert "overrides nothing" in message
    # Both remedies, which is what makes a refusal a teaching one.
    assert "Drop the decorator" in message
    assert "import the space" in message
    assert not space.is_function_here("ide-unshadowed")


def test_a_shadowing_definition_without_the_decorator_is_unchanged(metta, base):
    """Shadowing is deliberate, so silence is the ruling rather than an omission."""
    child = metta._new_space(inherits=base)

    @child.define(name="ide-area")
    def ide_area(r):
        return r * 3

    assert [str(atom) for atom in child.eval("(ide-area 2)")] == ["6"]


def test_override_holds_for_every_clause_of_the_definition_it_declared(metta, base):
    """A second clause stacks onto a name this space now owns, and is not re-asked."""
    child = metta._new_space(inherits=base)

    @child.define(name="ide-area")
    @override
    # The literal default IS the head pattern, and a patterned position is not
    # a variable in the body's scope, so the name cannot be read there.
    def ide_area_zero(_r=0):
        return 0

    @child.define(name="ide-area")
    @override
    def ide_area(r):
        return r + 1

    assert [str(atom) for atom in child.eval("(ide-area 0)")] == ["0"]
    assert [str(atom) for atom in child.eval("(ide-area 5)")] == ["6"]


def test_an_engine_builtin_is_not_something_to_override(metta):
    """`fun_here_in/2` admits every builtin; the shadow question must not."""
    space = metta._new_space()
    assert not _space_functions._is_function_inherited(space, "+")
    assert not _space_functions._is_function_inherited(space, "ide-nothing-of-this-name")


def test_declarations_carry_arrows_arities_and_documentation(metta):
    """One row per head, with the space's own order kept inside it."""
    space = metta._new_space()
    space.run("(: decl-greet (-> String String))")
    space.run("(: decl-greet (-> Atom Atom))")
    space.run('(@doc decl-greet (@desc "Say hello."))')
    space.run("(= (decl-greet $n) $n)")
    space.run("(= (decl-untyped $a $b) $a)")
    space.run("(: decl-shape Type)")

    rows = {row.name: row for row in declarations(space)}
    greet = rows["decl-greet"]
    assert [str(arrow) for arrow in greet.arrows] == [
        "(-> String String)",
        "(-> Atom Atom)",
    ]
    assert greet.arities == (1,)
    assert str(greet.documentation).startswith("(@doc decl-greet")
    assert not greet.is_type
    assert rows["decl-untyped"].arities == (2,)
    assert rows["decl-untyped"].arrows == ()
    assert rows["decl-shape"].is_type


def test_stubs_read_the_space_without_evaluating_it(metta):
    """A projection describes a program; it must not run one."""
    space = metta._new_space()
    space.run("(: stub-mark (-> Number Number))")
    space.run("(= (stub-mark $x) (stub-effect))")
    space.run("(= (stub-effect) (println! ran))")
    with space.capture() as printed:
        text = stubs(space)
    assert printed.text == ""
    assert "def stub_mark(x1: int | float, /) -> int | float:" in text


def test_the_stub_projects_the_type_table(metta):
    """Each row of the annotation reader's table, read backwards."""
    space = metta._new_space()
    space.run("(: tbl-scalars (-> Number String Bool %Undefined% Atom))")
    space.run("(: tbl-atoms (-> Symbol Variable Expression Grounded Expression))")
    space.run("(: tbl-higher (-> (-> Number Bool) Number))")
    space.run("(: tbl-unit (-> String (->)))")
    space.run("(: tbl-variable (-> $t $t $t))")
    space.run("(: tbl-none (-> Number NoneType))")
    text = stubs(space)

    assert (
        "def tbl_scalars(x1: int | float, x2: str, x3: bool, x4: Any, /) -> Atom:" in text
    )
    assert (
        "def tbl_atoms(x1: Symbol, x2: Variable, x3: Expression, x4: Grounded, /)"
        " -> Expression:" in text
    )
    assert "def tbl_higher(x1: Callable[[int | float], bool], /) -> int | float:" in text
    assert "def tbl_unit(x1: str, /) -> None:" in text
    assert "def tbl_variable[T1](x1: T1, x2: T1, /) -> T1:" in text
    assert "def tbl_none(x1: int | float, /) -> None:" in text
    # Only what the annotations mention is imported.
    assert "from collections.abc import Callable" in text
    assert "from typing import Any" in text
    assert "from metta._atoms.factories import Atom, Expression, Grounded, Symbol, Variable" in text


def test_a_declared_type_becomes_a_class_with_its_constructor(metta):
    """`install_type`'s own inverse: the type row and the constructor arrow are one class."""
    space = metta._new_space()
    space.run("(: Cls-Point Type)")
    space.run("(: Cls-Point (-> Number Number Cls-Point))")
    space.run("(: cls-area (-> Cls-Point Number))")
    text = stubs(space)
    assert "class Cls_Point(Atom):" in text
    assert "def __init__(self, x1: int | float, x2: int | float, /) -> None: ..." in text
    assert "def cls_area(x1: Cls_Point, /) -> int | float:" in text
    # A class is declared before anything that can mention it.
    assert text.index("class Cls_Point") < text.index("def cls_area")


def test_an_undeclared_head_keeps_its_arity_and_an_undocumented_one_says_its_type(metta):
    """No arrow is still not no information: the equations give the arity."""
    space = metta._new_space()
    space.run("(= (bare-head $a $b) $a)")
    space.run("(: said-nothing (-> Number Number))")
    text = stubs(space)
    assert "def bare_head(x1: Any, x2: Any, /) -> Any:" in text
    assert '"""said-nothing: (-> Number Number)"""' in text


def test_a_head_python_cannot_spell_is_named_not_dropped(metta):
    """The bracket door is the remedy, and the artefact has to say so."""
    space = metta._new_space()
    space.run("(: spell-prime? (-> Number Bool))")
    space.run("(: spell-ok (-> Number Bool))")
    text = stubs(space)
    assert "def spell_ok(x1: int | float, /) -> bool:" in text
    assert "spell-prime?" not in text.split("# Heads whose")[0]
    assert 'm.fn["<name>"]' in text
    assert "#   spell-prime?" in text


def test_the_module_docstring_names_its_sources_and_the_engine(metta, metta_module):
    """A generated file says what generated it and from what."""
    space = metta._new_space()
    space.run("(: doc-head (-> Number Number))")
    text = stubs(space, sources=[Path("a.metta"), "b.metta"])
    assert text.startswith('"""MeTTa declarations from a.metta, b.metta, as Python.')
    assert f"Generated by metta {metta_module.__version__}" in text
    assert "__all__ = [\n    \"doc_head\",\n]" in text


def test_documented_heads_carry_the_text_help_prints(metta):
    """One documentation formatter, so the stub and help() cannot disagree."""
    space = metta._new_space()
    space.run("(: docd (-> String String))")
    space.run(
        '(@doc docd (@desc "Say it back.") '
        '(@params ((@param "the words"))) (@return "the same words"))'
    )
    space.run("(= (docd $w) $w)")
    text = stubs(space)
    rendered = next(
        node
        for node in ast.parse(text).body
        if isinstance(node, ast.FunctionDef) and node.name == "docd"
    )
    # Through ast rather than a substring: the stub indents the docstring into
    # its def, and `get_docstring` undoes exactly that indentation.
    assert ast.get_docstring(rendered) == space.fn.docd.__doc__


def test_a_structured_documentation_part_reads_its_description(metta):
    """A `(@param (@type X) (@desc "..."))` says the description, not the type.

    The docstring a Python definition emits carries both, and taking the first
    child printed `(@type Number)` where the prose belongs, in help() and in
    every stub built from it.
    """
    space = metta._new_space()

    @space.define
    def ide_stretch(n: int) -> int:
        """Double a number.

        Args:
            n: the number to double
        Returns:
            twice n
        """
        return n * 2

    text = space.fn["ide-stretch"].__doc__
    assert "  - the number to double" in text
    assert "Returns: twice n" in text
    assert "@type" not in text


def test_a_generated_stub_checks_its_consumer(metta, tmp_path):
    """The whole point, end to end: a checker reads a MeTTa program's types.

    Run through mypy rather than asserted here, because the claim is about
    what a checker infers. `follow_imports_for_stubs` keeps the verdict about
    the consumer: the package's own root stub is not written to `--strict`
    and its diagnostics would drown the one being tested.
    """
    if subprocess.run(
        [sys.executable, "-c", "import mypy"], capture_output=True, check=False
    ).returncode:
        pytest.skip("mypy is not importable from this interpreter")
    space = metta._new_space()
    space.run("(: Chk-Circle Type)")
    space.run("(: Chk-Circle (-> Number Chk-Circle))")
    space.run("(: chk-area (-> Chk-Circle Number))")
    space.run("(: chk-greet (-> String String))")
    text = stubs(space, sources=["chk.metta"])
    ast.parse(text)

    (tmp_path / "chk.pyi").write_text(text, encoding="utf-8")
    (tmp_path / "mypy.ini").write_text(
        "[mypy]\nstrict = True\nfollow_imports = silent\n"
        "follow_imports_for_stubs = True\n",
        encoding="utf-8",
    )
    (tmp_path / "right.py").write_text(
        "from chk import Chk_Circle, chk_area, chk_greet\n"
        "chk_greet('hello')\n"
        "chk_area(Chk_Circle(2.0))\n",
        encoding="utf-8",
    )
    (tmp_path / "wrong.py").write_text(
        "from chk import chk_greet\nchk_greet(1)\n", encoding="utf-8"
    )

    def check(name: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable, "-m", "mypy",
                "--config-file", str(tmp_path / "mypy.ini"),
                "--no-incremental", "--cache-dir", str(tmp_path / "cache"),
                str(tmp_path / name),
            ],
            cwd=_PACKAGE_ROOT,
            env={"MYPYPATH": str(tmp_path), "PATH": "/usr/bin:/bin"},
            capture_output=True,
            text=True,
            check=False,
            timeout=300,
        )

    right = check("right.py")
    assert right.returncode == 0, right.stdout + right.stderr
    wrong = check("wrong.py")
    assert wrong.returncode != 0, wrong.stdout
    assert 'Argument 1 to "chk_greet" has incompatible type "int"' in wrong.stdout


def test_the_root_door_and_the_projection_answer_the_same_text(metta_module, metta):
    """One generator behind the package door, the CLI and the module."""
    space = metta._new_space()
    space.run("(: root-head (-> Number Number))")
    assert metta_module.stubs(space) == stubs(space)
    assert "stubs" in metta_module.__all__
