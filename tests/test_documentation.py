"""Purpose: hold the repository's own pages to what they promise, from
EXTENDING.md's seam list through the generated reference pages to the
governance documents.

The extension page is what a library author reads instead of the source, so a
seam it does not mention is a seam nobody finds. Four were missing when this
was first checked: seam:foreign_clear/1, which had lived in the Python shim
rather than beside the other five space hooks; seam:grounded_extra_type/2 and
seam:grounded_type_names/2, which are how a host value gets a type; and
prolog:error_message//1, which is how a library gives its own error term a
rendering. Nothing would have said so.
Guarantees:
  - every multifile seam declared in engine/ext_points.pl is named in
    EXTENDING.md [tested test_every_declared_seam_is_documented]
  - the governance documents carry the policy rather than only existing: the
    private security address and its window, the gate command, the alpha
    status, and issue forms GitHub can parse
    [tested 2026-08-19: test_the_repository_ships_its_governance_documents]
  - reference generation follows the public Space handle even though its
    implementation lives in the private petta._space module, and neither
    reference generator can restore the deleted DAS or persistent module doors
    [tested: test_an_overloaded_method_is_documented_once,
    test_the_legacy_reference_generator_tracks_the_narrow_public_modules;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import ast
import importlib.util
import re
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[3]


def _load_reference():
    """The generator is a tool, not a package member, so it is loaded by path
    rather than imported: putting it under petta/ would ship a build-time
    script in the wheel.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    spec = importlib.util.spec_from_file_location(
        "petta_reference_tool", _REPO / "bindings" / "python" / "tools" / "reference.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_reference = _load_reference()


def _load_site_reference_generator():
    """Load the earlier site generator without making website a package."""
    spec = importlib.util.spec_from_file_location(
        "petta_site_reference_generator",
        _REPO / "website" / "scripts" / "generate_reference.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(spec.name, None)
    return module


_site_reference_generator = _load_site_reference_generator()
_ROOT = _REPO
_SEAMS = _REPO / "engine" / "ext_points.pl"
_PAGE = _REPO / "EXTENDING.md"

# `:- multifile name/2.` and `:- multifile prolog:error_message//1.`
_DECLARATION = re.compile(r"^:-\s*multifile\s+([\w:]+)//?\d+\.", re.MULTILINE)


def _declared_seams() -> list[str]:
    return _DECLARATION.findall(_SEAMS.read_text(encoding="utf-8"))


def test_the_seam_list_is_not_empty():
    """A regex that stopped matching would make the check below vacuous."""
    assert len(_declared_seams()) >= 10


@pytest.mark.parametrize("seam", _declared_seams())
def test_every_declared_seam_is_documented(seam):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    page = _PAGE.read_text(encoding="utf-8")
    # The page may write prolog:error_message with or without its module
    # qualifier, so the bare name is what has to appear.
    name = seam.split(":")[-1]
    assert name in page, (
        f"{seam} is declared in engine/ext_points.pl and not mentioned in "
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


def test_the_reference_pages_are_up_to_date():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    stale = [
        page.name
        for page, module_path, title in _reference.sources()
        if page.read_text(encoding="utf-8") != _reference.page_for(module_path, title)
    ]
    assert not stale, (
        f"{stale} no longer match their source; run "
        f"`python bindings/python/tools/reference.py --write`"
    )


def test_a_signature_too_long_for_one_line_wraps_one_argument_per_line():
    """ast.unparse writes any signature on one line, and one method's came out
    at 300 columns.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
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
    """@overload declares a type, not a definition. All four gave Space.run
    four identical reference entries.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    page = _reference.page_for("bindings/python/petta/_space.py", "petta.Space")
    assert page.count("### `Space.run`") == 1


def test_the_legacy_reference_generator_tracks_the_narrow_public_modules():
    """Both checked-in generators must agree on deleted and private doors."""
    modules = {spec.name: spec.source for spec in _site_reference_generator.MODULES}
    assert modules["petta.Space"] == "bindings/python/petta/_space.py"
    assert "petta.space" not in modules
    assert "petta.das" not in modules
    assert "petta.persistent" not in modules
    assert "petta.matching" not in modules
    assert "petta.measure" not in modules
    assert not (_REPO / "website" / "reference" / "petta-das.md").exists()
    assert not (_REPO / "website" / "reference" / "petta-persistent.md").exists()
    assert not (_REPO / "website" / "live" / "das.md").exists()


def test_a_tag_shaped_word_in_prose_is_escaped_and_code_is_not():
    """CommonMark reads `<obj>` as a raw HTML tag and the browser renders an
    unknown element as nothing, so a docstring saying "(wrapped name <obj>)"
    lost the word it was about. markdown-it escapes code spans and indented
    code blocks itself, so escaping those too would display the escape.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
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


def test_an_indented_prose_continuation_escapes_tags():
    """List-item continuation indentation is prose unless a blank line starts
    an indented code block.
    """  # noqa: D205 -- one generator distinction is explained continuously
    quoted = _reference.quote(
        '- a failure once used the message\n    "Python \'<Type>\': <text>"'
    )
    assert "&lt;Type>" in quoted and "&lt;text>" in quoted
    code = _reference.quote("Example:\n\n    # <mylib-join/3 prolog: 1 call>")
    assert "    # <mylib-join/3 prolog: 1 call>" in code


def _load_libdoc():
    import importlib.util as _importlib_util

    specification = _importlib_util.spec_from_file_location(
        "petta_libdoc_tool", _REPO / "bindings" / "python" / "tools" / "libdoc.py"
    )
    module = _importlib_util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def test_the_metta_library_page_is_up_to_date():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    libdoc = _load_libdoc()
    current = libdoc._PAGE.read_text(encoding="utf-8")
    assert current == libdoc.page(), (
        "metta-libraries.md no longer matches the libraries' @doc atoms; "
        "run `python bindings/python/tools/libdoc.py --write`"
    )


def _lint_kinds() -> set[str]:
    """Every kind petta.lint can emit, read out of the analysis module.

    Derived rather than listed, because a hand-kept list is the thing that
    drifts: the kinds reach a Finding two ways, directly as its first
    argument and through a simplifier's (kind, detail, replacement) triple,
    and both shapes are matched here.
    """
    tree = ast.parse((_REPO / "bindings" / "python" / "petta" / "_lint_analysis.py").read_text())
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


# The governance documents, checked for what they say rather than for being
# there. A SECURITY.md that exists and names no address routes a reporter
# nowhere, and an issue form GitHub cannot parse is a template chooser entry
# that never appears. Every string below is a clause of the decision the pages
# were written to carry, so a rewrite that drops one fails here rather than
# quietly leaving the policy with no home.
_TEMPLATES = _REPO / ".github" / "ISSUE_TEMPLATE"

# What each page has to still be saying. The security address is the whole
# routing decision; the 90-day window and the absent bounty are what a
# reporter is owed and not owed; the gate command is the one thing a
# contributor has to run.
_SECURITY_CLAUSES = (
    "a.mesto@student.unsw.edu.au",
    "git log",
    "Do not open a public issue",
    "90 days",
    "no bug bounty",
    "0.y.z",
)
_CONTRIBUTING_CLAUSES = (
    "0.y.z",
    "labelled alpha",
    "GATE_ONLY=1 sh check.sh",
    "no contributor license agreement",
    "obligation header",
    "evidence tag",
    "a tag on a gate-green tree",
    "python -m pytest bindings/python/tests/ -q --rootdir=python -c bindings/python/pyproject.toml",
    "cd tests/prolog",
)
_FORM_TYPES = {"markdown", "textarea", "input", "dropdown", "checkboxes"}


def test_the_repository_ships_its_governance_documents():
    """Pin Phase 9 item P9.5: the decision about releases, security reports and
    contributions lives in the repository rather than in a plan.

    The templates are parsed rather than pattern-matched because GitHub parses
    them: a form whose YAML is malformed, or whose non-markdown element has no
    id, is rejected wholesale and simply does not appear in the chooser, which
    looks from the outside exactly like a repository that ships no template.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    for name, clauses in (
        ("SECURITY.md", _SECURITY_CLAUSES),
        ("CONTRIBUTING.md", _CONTRIBUTING_CLAUSES),
    ):
        page = _REPO / name
        assert page.is_file(), f"{name} is not in the tree"
        text = page.read_text(encoding="utf-8")
        for clause in clauses:
            assert clause in text, f"{name} no longer states {clause!r}"

    # Both are reachable from the page a reader actually lands on. GitHub also
    # surfaces them itself, in the Security tab and beside a new pull request,
    # but that only helps somebody already on github.com.
    readme = (_REPO / "README.md").read_text(encoding="utf-8")
    for target in ("(SECURITY.md)", "(CONTRIBUTING.md)"):
        assert target in readme, f"the README no longer links {target}"

    # SECURITY.md travels with the source archive for the same reason
    # CHANGELOG.md and CITATION.cff do: it is what a consumer of the
    # DISTRIBUTION needs, and someone repackaging from an sdist would
    # otherwise ship a project with no reporting address in it. CONTRIBUTING.md
    # is about working on the repository and stays with the repository.
    manifest = (_REPO / "MANIFEST.in").read_text(encoding="utf-8").splitlines()
    assert "include SECURITY.md" in manifest

    # PyYAML reaches the gate through bandit and xenon, which both require it,
    # so `uv sync --extra checks` always has one [source 2026-08-19: bandit
    # 1.9.4 and xenon 0.9.3 each declare pyyaml in uv.lock]. The minimum
    # dependency environment the version matrix runs does not, and skips here.
    yaml = pytest.importorskip("yaml")
    forms = {
        path.name: yaml.safe_load(path.read_text(encoding="utf-8"))
        for path in sorted(_TEMPLATES.glob("*.yml"))
        if path.name != "config.yml"
    }
    assert set(forms) == {"bug.yml", "divergence.yml"}, sorted(forms)

    fields = {}
    for template, form in forms.items():
        assert {"name", "description", "body"} <= set(form), f"{template} is missing a top key"
        identified = [one for one in form["body"] if one["type"] != "markdown"]
        for element in form["body"]:
            assert element["type"] in _FORM_TYPES, f"{template}: {element['type']}"
            assert element.get("attributes"), f"{template}: an element carries no attributes"
        ids = [one["id"] for one in identified if "id" in one]
        assert len(ids) == len(identified) == len(set(ids)), (
            f"{template}: every element but a markdown one needs its own unique id"
        )
        fields[template] = {one["id"]: one for one in identified}

    # A bug report is only actionable with the program and both answers, so the
    # form has to require all three rather than merely offer them.
    bug = fields["bug.yml"]
    for asked in ("program", "expected", "got"):
        assert bug[asked]["validations"]["required"] is True, (
            f"bug.yml stopped requiring {asked}"
        )
    # Rendered rather than passed through Markdown, or a program's `*` and `_`
    # arrive eaten. bug.yml says why the value is `text`.
    for template in forms:
        assert fields[template]["program"]["attributes"]["render"] == "text", template

    # A divergence that names no reference cannot be settled, which is the one
    # thing this form exists to collect.
    divergence = fields["divergence.yml"]
    assert divergence["reference"]["type"] == "dropdown"
    assert len(divergence["reference"]["attributes"]["options"]) >= 2
    for asked in ("reference", "citation", "program"):
        assert divergence[asked]["validations"]["required"] is True, (
            f"divergence.yml stopped requiring {asked}"
        )

    # The chooser is where a security report gets caught before it is public.
    config = yaml.safe_load((_TEMPLATES / "config.yml").read_text(encoding="utf-8"))
    links = {one["name"]: one["url"] for one in config["contact_links"]}
    assert any(url.endswith("/SECURITY.md") for url in links.values()), links
