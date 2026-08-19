"""Purpose: hold EXTENDING.md to the extension points the engine actually has.

The page is what a library author reads instead of the source, so a seam it
does not mention is a seam nobody finds. Four were missing when this was first
checked: metta_foreign_clear/1, which had lived in the Python shim rather than
beside the other five space hooks; py_object_extra_type/2 and
py_object_type_names/2, which are how a host value gets a type; and
prolog:error_message//1, which is how a library gives its own error term a
rendering. Nothing would have said so.
Guarantees:
  - every multifile seam declared in src/ext_points.pl is named in
    EXTENDING.md [tested test_every_declared_seam_is_documented]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import ast
import importlib.util
import re
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]


def _load_reference():
    """The generator is a tool, not a package member, so it is loaded by path
    rather than imported: putting it under petta/ would ship a build-time
    script in the wheel."""
    spec = importlib.util.spec_from_file_location(
        "petta_reference_tool", _REPO / "python" / "tools" / "reference.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_reference = _load_reference()
_ROOT = _REPO
_SEAMS = _REPO / "src" / "ext_points.pl"
_PAGE = _REPO / "EXTENDING.md"

# `:- multifile name/2.` and `:- multifile prolog:error_message//1.`
_DECLARATION = re.compile(r"^:-\s*multifile\s+([\w:]+)//?\d+\.", re.MULTILINE)


def _declared_seams() -> list[str]:
    return _DECLARATION.findall(_SEAMS.read_text(encoding="utf-8"))


def test_the_seam_list_is_not_empty():
    """A regex that stopped matching would make the check below vacuous."""
    assert len(_declared_seams()) >= 10


@pytest.mark.parametrize("seam", _declared_seams())
def test_every_declared_seam_is_documented(seam):
    page = _PAGE.read_text(encoding="utf-8")
    # The page may write prolog:error_message with or without its module
    # qualifier, so the bare name is what has to appear.
    name = seam.split(":")[-1]
    assert name in page, (
        f"{seam} is declared in src/ext_points.pl and not mentioned in "
        f"EXTENDING.md, so a library author reading the page cannot find it"
    )


# The reference pages promise "The entries below reproduce the source
# signatures and docstrings" and hand-maintenance made that false 67 times
# across nineteen pages. They are generated from the modules now; these are
# the generator's own tests, since check.sh only asks whether the checked-in
# pages match.
def test_every_reference_page_names_its_source():
    """The Source: line is what says which module a page documents."""
    for page, module_path, title in _reference.sources():
        assert (_ROOT / module_path).exists(), (
            f"{page.name} names {module_path}, which is not there"
        )
        assert title.startswith("petta"), page.name


def test_the_reference_pages_are_up_to_date():
    stale = [
        page.name
        for page, module_path, title in _reference.sources()
        if page.read_text(encoding="utf-8") != _reference.page_for(module_path, title)
    ]
    assert not stale, (
        f"{stale} no longer match their source; run "
        f"`python python/tools/reference.py --write`"
    )


def test_a_signature_too_long_for_one_line_wraps_one_argument_per_line():
    """ast.unparse writes any signature on one line, and one method's came out
    at 300 columns."""
    node = ast.parse(
        "def a_method_with_a_long_name(self, a: dict[str, int] = {}, *, "
        "keyword_one: str | None = None, keyword_two: int = 1, "
        "keyword_three: bool = False) -> list[tuple[int, str]]: ..."
    ).body[0]
    wrapped = _reference.signature(node)
    assert wrapped.startswith("def a_method_with_a_long_name(\n")
    # A default inside a subscript is not an argument boundary.
    assert "    a: dict[str, int] = {},\n" in wrapped


def test_an_overloaded_method_is_documented_once():
    """@overload declares a type, not a definition. All four gave MeTTa.run
    four identical reference entries."""
    page = _reference.page_for("python/petta/space.py", "petta.space")
    assert page.count("### `MeTTa.run`") == 1


def test_a_tag_shaped_word_in_prose_is_escaped_and_code_is_not():
    """CommonMark reads `<obj>` as a raw HTML tag and the browser renders an
    unknown element as nothing, so a docstring saying "(wrapped name <obj>)"
    lost the word it was about. markdown-it escapes code spans and indented
    code blocks itself, so escaping those too would display the escape.
    """
    assert _reference.escape_tags("a (wrapped name <obj>) b") == (
        "a (wrapped name &lt;obj>) b"
    )
    assert _reference.escape_tags("under `<engine>/../lib` and") == (
        "under `<engine>/../lib` and"
    )
    assert _reference.escape_tags("to ``<journal>.tail`` and") == (
        "to ``<journal>.tail`` and"
    )
    assert _reference.escape_tags("    # <mylib-join/3 prolog: 1 call>") == (
        "    # <mylib-join/3 prolog: 1 call>"
    )


def _load_libdoc():
    import importlib.util as _importlib_util

    specification = _importlib_util.spec_from_file_location(
        "petta_libdoc_tool", _REPO / "python" / "tools" / "libdoc.py"
    )
    module = _importlib_util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def test_the_metta_library_page_is_up_to_date():
    libdoc = _load_libdoc()
    current = libdoc._PAGE.read_text(encoding="utf-8")
    assert current == libdoc.page(), (
        "metta-libraries.md no longer matches the libraries' @doc atoms; "
        "run `python python/tools/libdoc.py --write`"
    )


def _lint_kinds() -> set[str]:
    """Every kind petta.lint can emit, read out of the analysis module.

    Derived rather than listed, because a hand-kept list is the thing that
    drifts: the kinds reach a Finding two ways, directly as its first
    argument and through a simplifier's (kind, detail, replacement) triple,
    and both shapes are matched here.
    """
    tree = ast.parse((_REPO / "python" / "petta" / "_lint_analysis.py").read_text())
    kinds: set[str] = set()
    for node in ast.walk(tree):
        first = None
        if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "Finding":
            first = node.args[0] if node.args else None
        elif isinstance(node, ast.Tuple) and len(node.elts) == 3:
            first = node.elts[0]
        if isinstance(first, ast.Constant) and isinstance(first.value, str):
            kinds.add(first.value)
    return kinds


def test_every_lint_kind_is_named_on_the_page_its_findings_link_to():
    """Every Finding carries docs_link, so the page it names is a promise.

    It was pointed at the generated reference page, which reproduces
    signatures and docstrings and named none of the seventeen kinds; a
    reader following the link from a finding learned nothing about it.
    """
    from petta import S
    from petta.lint import Finding

    link = Finding("kind", "subject", "detail", S.evidence).docs_link
    page, _, anchor = link.partition("#")
    path = _REPO / page.split("/blob/main/", 1)[1]
    assert path.is_file(), f"docs_link names {path}, which is not in the tree"
    text = path.read_text(encoding="utf-8")
    assert anchor == "lint-a-space" and "## Lint a space" in text
    missing = sorted(kind for kind in _lint_kinds() if f"`{kind}`" not in text)
    assert not missing, f"{missing} can be reported and are not documented at {link}"
