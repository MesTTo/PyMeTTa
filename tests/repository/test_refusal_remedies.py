"""Purpose: hold every deliberate refusal to its structured remedy.

Statically over the source, and dynamically by driving the refusals
themselves.

Guarantees:
  - every raise site whose message NAMES a remedy passes remedy= at that site,
    and the walk is proved against a planted omission rather than an empty
    scan [tested: test_every_remedy_naming_raise_site_carries_a_remedy,
    test_a_planted_site_without_a_remedy_is_reported; commit=3fc5479961fd591b1884af118528c9a64a1afbb7]
  - the refusals the prose remedies were written for carry a Remedy object
    when actually raised, across TypeError, AttributeError, ValueError,
    CompileError and DeprecationWarning [tested:
    test_a_keyword_on_a_bare_symbol_names_the_positional_form,
    test_a_wrong_keyword_on_a_known_signature_names_the_declared_order,
    test_a_handle_that_is_applied_names_the_two_ways_to_use_it,
    test_two_spaces_compared_for_order_name_the_set_doors,
    test_an_override_that_shadows_nothing_names_the_inheritance_door,
    test_a_generated_namespace_miss_names_the_live_namespace,
    test_a_column_name_given_to_index_names_the_column_door,
    test_a_cyclic_value_handed_to_the_json_codec_names_ground,
    test_an_error_answer_through_a_single_value_door_is_arbiter_grounded,
    test_a_deprecation_rows_term_remedy_decodes_to_an_edit;
    commit=3fc5479961fd591b1884af118528c9a64a1afbb7]

Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from __future__ import annotations

import ast
import re
import textwrap
import warnings
from pathlib import Path
from typing import override

import pytest

import metta as metta_module
from metta import S, V
from metta.errors import CompileError, MettaResultError, Remedy

PACKAGE = Path(metta_module.__file__).resolve().parent

#: The module that DEFINES the vocabulary. Its own refusals are about a
#: malformed Remedy, not refusals that carry one, so they name the word
#: without being sites this walk owns.
_DEFINING_MODULE = "errors.py"

#: What makes a raise site one this walk owns: the source itself calls the
#: thing in the message a remedy, either by interpolating a name spelled that
#: way or by writing the word into the text. An author who writes it has
#: declared the refusal repairable, which is exactly when the structured form
#: has to be there too.
_NAMES_A_REMEDY = "remedy"


def _scope_bodies(tree: ast.AST) -> list[ast.AST]:
    """The module and every function in it, each as one name scope."""
    return [tree, *(n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)))]


def _own_nodes(scope: ast.AST):
    """Every node of one scope, without descending into a nested function."""
    for node in ast.iter_child_nodes(scope):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        yield node
        yield from _own_nodes(node)


def _footprint(scope: ast.AST, raised: ast.expr) -> str:
    """The raise's own text plus the text of every local name it reads.

    A message is usually built into `msg` a line above the raise, so the
    word the author wrote is not in the raise expression itself. Following
    the assignments in the same scope is what puts it back.
    """
    assigned: dict[str, str] = {}
    for node in _own_nodes(scope):
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)) and node.value is not None:
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if isinstance(target, ast.Name):
                    assigned[target.id] = assigned.get(target.id, "") + ast.unparse(node)
    text = ast.unparse(raised)
    for node in ast.walk(raised):
        if isinstance(node, ast.Name) and node.id in assigned:
            text += " " + assigned[node.id]
    return text


#: A refusal is not always raised where it is built: three doors here return
#: the exception for a caller to raise, which is how one message serves
#: several call sites. Both spellings are the same site to this walk.
_BUILDERS = ("refusing", "_grounded_type_error")
_EXCEPTION_NAME = re.compile(r"[A-Z]\w*(Error|Failure|Warning|Exception)$")


def _built_exception(node: ast.AST) -> ast.expr | None:
    """The exception a statement raises or hands back, or None."""
    if isinstance(node, ast.Raise):
        return node.exc
    if not isinstance(node, ast.Return) or not isinstance(node.value, ast.Call):
        return None
    called = node.value.func
    name = called.id if isinstance(called, ast.Name) else getattr(called, "attr", "")
    if name in _BUILDERS or _EXCEPTION_NAME.match(name):
        return node.value
    return None


def remedy_naming_sites(root: Path) -> list[tuple[str, int, bool]]:
    """Every refusal whose message names a remedy, and whether it passes one.

    The static half of this lane, as a function over a root so the planted
    case below runs the same walk over a fixture rather than a copy of it.

    What it holds is one direction: a site whose PROSE calls something a
    remedy must carry the structured form. It cannot see a repairable
    refusal whose sentence never uses the word, which is why the runtime
    half below names those refusals one by one and drives them.
    """
    sites: list[tuple[str, int, bool]] = []
    for path in sorted(root.rglob("*.py")):
        if path.name == _DEFINING_MODULE:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for scope in _scope_bodies(tree):
            for node in _own_nodes(scope):
                built = _built_exception(node)
                if built is None:
                    continue
                if _NAMES_A_REMEDY not in _footprint(scope, built).lower():
                    continue
                carries = any(
                    keyword.arg == "remedy"
                    for call in ast.walk(built)
                    if isinstance(call, ast.Call)
                    for keyword in call.keywords
                )
                sites.append((str(path.relative_to(root)), node.lineno, carries))
    return sites


#: The modules that hold a remedy-naming refusal, measured 2026-09-07. Named
#: rather than counted so a module losing its last one is a red the reader can
#: place, and by file rather than by line so ordinary edits do not move it.
_REMEDY_NAMING_MODULES = frozenset(
    {
        "_atom_namespace.py",
        "_atoms_core.py",
        "_call_binding.py",
        "_define_expression.py",
        "_json.py",
        "_space_definitions.py",
        "_templates.py",
        "results.py",
        "testing.py",
    }
)


def test_every_remedy_naming_raise_site_carries_a_remedy():
    """A refusal whose prose names a repair carries that repair as data."""
    sites = remedy_naming_sites(PACKAGE)
    assert [site for site in sites if not site[2]] == []
    assert {file for file, _, _ in sites} >= _REMEDY_NAMING_MODULES


def test_a_planted_site_without_a_remedy_is_reported(tmp_path):
    """The walk is proved by a fixture that omits what the real tree has."""
    (tmp_path / "planted.py").write_text(
        textwrap.dedent(
            """
            def refuse(name):
                remedy = f"write {name}() positionally"
                msg = f"{name} takes no keywords. {remedy}."
                raise TypeError(msg)
            """
        ),
        encoding="utf-8",
    )
    assert remedy_naming_sites(tmp_path) == [("planted.py", 5, False)]
    (tmp_path / "planted.py").write_text(
        textwrap.dedent(
            """
            def refuse(name):
                remedy = f"write {name}() positionally"
                msg = f"{name} takes no keywords. {remedy}."
                raise refusing(TypeError(msg), remedy=Remedy(remedy, "quickfix", "prose", python=remedy))
            """
        ),
        encoding="utf-8",
    )
    assert remedy_naming_sites(tmp_path) == [("planted.py", 5, True)]


def _remedy_of(error: BaseException) -> Remedy:
    """The structured remedy an error carries, whatever its class."""
    remedy = getattr(error, "remedy", None)
    assert isinstance(remedy, Remedy), f"{type(error).__name__} carries no Remedy"
    return remedy


def test_a_keyword_on_a_bare_symbol_names_the_positional_form():
    """The positional-remedy site: a symbol carries no parameter names."""
    with pytest.raises(TypeError) as raised:
        S.likes(who=S.Ada)
    assert _remedy_of(raised.value).python == "S.likes(<who>)"


def test_a_wrong_keyword_on_a_known_signature_names_the_declared_order(metta):
    """The bind refusal: Signature.bind failed, so the order is the repair."""
    with metta._new_space() as space:

        @space.define
        def rr_pair(left, right):
            return S.Pair(left, right)

        with pytest.raises(TypeError) as raised:
            rr_pair(left=1, wrong=2)
    assert _remedy_of(raised.value).python == "rr-pair(<left>, <right>)"


def test_a_handle_that_is_applied_names_the_two_ways_to_use_it(metta):
    """The Handle call refusal: a handle is an operand, not an application."""
    with pytest.raises(TypeError) as raised:
        metta()
    remedy = _remedy_of(raised.value)
    assert remedy.applicability == "prose"
    assert remedy.python == "S.<head>(handle)"


def test_two_spaces_compared_for_order_name_the_set_doors(metta):
    """The space-comparison refusal: term order is not containment."""
    with metta._new_space() as one, metta._new_space() as two:
        with pytest.raises(TypeError) as raised:
            one < two  # noqa: B015  -- the comparison IS the refusal under test
    assert _remedy_of(raised.value).python == "spaces.diff(a, b)"


def test_an_override_that_shadows_nothing_names_the_inheritance_door(metta):
    """The override refusal: two remedies in prose, the reachable one as data."""
    with metta._new_space() as space, pytest.raises(CompileError) as raised:

        @space.define
        @override
        def rr_unshadowed(value):
            return value

    remedy = _remedy_of(raised.value)
    assert remedy.applicability == "prose"
    assert "m.space(" in (remedy.python or "")


def test_a_generated_namespace_miss_names_the_live_namespace():
    """Both closed-catalog doors, the attribute one and the bracket one."""
    with pytest.raises(AttributeError) as attribute:
        _ = metta_module.fn.rr_no_such_head
    with pytest.raises(AttributeError) as bracket:
        _ = metta_module.fn["rr-no-such-head"]
    for raised in (attribute, bracket):
        assert _remedy_of(raised.value).python == "space.fn.<name>"


def test_a_column_name_given_to_index_names_the_column_door(metta):
    """The answer-view collision: index is the Sequence method."""
    with metta._new_space() as space:
        space.add(S.rr_cell(S.a), S.rr_cell(S.b))
        rows = space.match(S.rr_cell(V.cell))
        with pytest.raises(ValueError, match="is a column") as raised:
            rows.index("cell")
    assert _remedy_of(raised.value).python == "answers.column('cell')"


def test_a_cyclic_value_handed_to_the_json_codec_names_ground():
    """The codec refusal: an uncrossable value is held whole instead.

    No engine fixture: the cycle walk runs BEFORE the crossing, which is the
    whole point of it, so this refusal never reaches the runtime.
    """
    from metta import _json

    cyclic: dict[str, object] = {"a": 1}
    cyclic["self"] = cyclic
    with pytest.raises(ValueError, match="contains itself") as raised:
        _json.dumps(cyclic)
    assert _remedy_of(raised.value).python == "metta.ground(value)"


def test_an_error_answer_through_a_single_value_door_is_arbiter_grounded(metta):
    """The one arbiter ground: an (Error ...) is a VALUE upstream answers."""
    with metta._new_space() as space:
        with pytest.raises(MettaResultError) as raised:
            space.answers(S["/"](1, 0)).one()
    assert raised.value.ground is not None
    assert raised.value.ground.kind == "arbiter"
    assert "tests/conformance/petta" in raised.value.ground.citation
    assert _remedy_of(raised.value).python == "m.eval(target)"


def test_a_deprecation_rows_term_remedy_decodes_to_an_edit(metta):
    """The engine's own term remedy, decoded at the crossing that reads it."""
    declaration = S.deprecated(
        S["rr-deprecated"], S["0.2.0"], S.use(S["rr-modern"])
    )
    catalog = metta_module.catalog
    with metta._new_space() as space:

        @space.define(name="rr-deprecated")
        def legacy(value):
            return S.modern(value)

        catalog.add(declaration)
        try:
            with warnings.catch_warnings(record=True) as recorded:
                warnings.simplefilter("always")
                assert list(legacy(S.value)) == [S.modern(S.value)]
        finally:
            catalog.remove(declaration)
    remedy = _remedy_of(recorded[0].message)
    assert str(remedy.edit) == "(use rr-modern)"
    assert remedy.title == "(use rr-modern)"
    assert remedy.applicability == "prose"
