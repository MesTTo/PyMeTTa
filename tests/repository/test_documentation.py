"""Purpose: hold repository documentation to its promised source contracts.

The check spans EXTENDING.md's seam list, generated reference pages, and the
governance documents. The extension page is what a library author reads instead of the source, so a
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
    implementation lives in the private metta._space module, and neither
    reference generator can restore the deleted DAS or persistent module doors
    [tested: test_an_overloaded_method_is_documented_once,
    test_the_legacy_reference_generator_tracks_the_narrow_public_modules;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - generated pages publish reader prose rather than file-local contracts or
    evidence metadata [tested: test_reference_publishes_reader_prose_only;
    commit=00afba04ff73e51bc2521371c30448898cb3c3d2]
  - EXTENDING.md's extension-cost tables carry the numbers the committed
    pins derive and name every pinned tier, so the page cannot drift from
    the gate again [tested:
    test_the_extension_cost_tables_match_the_committed_pins]
  - the site publishes the root documents by including them, and every
    include resolves, which VitePress itself does not check: its include is
    fail-open and an unresolved one publishes an empty page under a green
    build [tested: test_every_site_include_resolves; commit=a7d2f292004fe06d7671b7931cfc2ce4620b7b35]
  - every page in the site is reachable from the navigation rather than only
    from the search box [tested:
    test_every_site_page_is_reachable_from_the_navigation; commit=a7d2f292004fe06d7671b7931cfc2ce4620b7b35]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import ast
import importlib.util
import re
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[4]


def _load_reference():
    """Load the source-reference generator by path.

    The generator is a tool, not a package member. Putting it under metta/
    would ship a build-time script in the wheel.
    """
    spec = importlib.util.spec_from_file_location(
        "metta_reference_tool", _REPO / "extensions" / "python" / "tools" / "reference.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_reference = _load_reference()


def _load_site_reference_generator():
    """Load the earlier site generator without making website a package."""
    spec = importlib.util.spec_from_file_location(
        "metta_site_reference_generator",
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
def test_every_declared_seam_is_documented(seam):
    """Require each declared extension seam to appear in EXTENDING.md."""
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
        assert title.startswith("metta"), page.name


def test_the_reference_pages_are_up_to_date():
    """Require every generated reference page to match its source."""
    stale = [
        page.name
        for page, module_path, title in _reference.sources()
        if page.read_text(encoding="utf-8") != _reference.page_for(module_path, title)
    ]
    assert not stale, (
        f"{stale} no longer match their source; run "
        f"`python extensions/python/tools/reference.py --write`"
    )


def test_a_signature_too_long_for_one_line_wraps_one_argument_per_line():
    """Wrap an overlong signature one argument per line.

    ``ast.unparse`` writes any signature on one line, and one method's came out
    at 300 columns.
    """
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
    page = _reference.page_for("extensions/python/metta/_space.py", "metta.Space")
    assert page.count("### `Space.run`") == 1


def test_reference_publishes_reader_prose_only():
    """Retain public explanation while removing maintainer-only metadata."""
    fake_pin = "commit" + "=abc"
    source_tag = f"{chr(91)}source: internal.py:thing; {fake_pin}]"
    tested_tag = f"{chr(91)}tested: test_internal; {fake_pin}]"
    measured_tag = f"{chr(91)}measured: 3 calls; command=probe; {fake_pin}]"
    doc = f"""Purpose: explain the reader.

Assumes:
  - an internal condition {source_tag}
Guarantees:
  - an internal promise {tested_tag}
Open Obligations:
  To Do: None

Reader-facing detail {measured_tag}.
"""
    assert _reference.public_prose(doc) == (
        "Explain the reader.\n\nReader-facing detail."
    )


def test_the_legacy_reference_generator_tracks_the_narrow_public_modules():
    """Both checked-in generators must agree on deleted and private doors."""
    modules = {spec.name: spec.source for spec in _site_reference_generator.MODULES}
    assert modules["metta.Space"] == "extensions/python/metta/_space.py"
    assert "metta.space" not in modules
    assert "metta.das" not in modules
    assert "metta.persistent" not in modules
    assert "metta.matching" not in modules
    assert "metta.measure" not in modules
    assert not (_REPO / "website" / "reference" / "metta-das.md").exists()
    assert not (_REPO / "website" / "reference" / "metta-persistent.md").exists()
    assert not (_REPO / "website" / "live" / "das.md").exists()


_SITE = _REPO / "website"
_SITE_CONFIG = _SITE / ".vitepress" / "config.ts"
# VitePress's own directive, and its own suffixes: `#region` selects a marked
# block and `{3,10}` a line range, both stripped before the path is resolved
# [source: website/node_modules/vitepress/dist/node/chunk-D3CUZ4fa.js,
# processIncludes; commit=a7d2f292004fe06d7671b7931cfc2ce4620b7b35].
_INCLUDE = re.compile(r"<!--\s*@include:\s*(.*?)\s*-->")
_INCLUDE_SUFFIX = re.compile(r"(#[\w-]+)?(\{\d*,\d*\})?$")
_SITE_LINK = re.compile(r'link:\s*"([^"]+)"')
_REWRITE = re.compile(r'"([^"]+\.md)":\s*"([^"]+\.md)"')
# `navigation: false` in a page's opening frontmatter block: the page's own way
# to say it is unlisted on purpose. Anchored at the start of the file, because
# frontmatter is only frontmatter there.
_OPTS_OUT_OF_NAVIGATION = re.compile(
    r"\A---\r?\n(?:.*\r?\n)*?navigation:\s*false\s*\r?\n(?:.*\r?\n)*?---"
)


def _site_pages() -> list[Path]:
    """Every markdown page the site publishes, home page excluded.

    The home page is what `/` serves, so nothing links it and nothing has to.
    """
    return sorted(
        page
        for page in _SITE.rglob("*.md")
        if "node_modules" not in page.parts
        and ".vitepress" not in page.parts
        and page != _SITE / "index.md"
    )


def _site_rewrites() -> dict[str, str]:
    return dict(_REWRITE.findall(_SITE_CONFIG.read_text(encoding="utf-8")))


def test_the_site_page_list_is_not_empty():
    """A glob that stopped matching would make both checks below vacuous."""
    assert len(_site_pages()) >= 40


def test_every_site_include_resolves():
    """A page that includes a document must include a document that is there.

    VitePress's include is fail-open: `processIncludes` catches the read error,
    leaves the directive text in the page, and warns only under DEBUG, so a
    renamed source file publishes an EMPTY page and a green build. Every other
    documentation toolchain treats this as an error rather than a warning
    (Sphinx under -W, mkdocs' pymdownx.snippets under check_paths, Rust's
    include_str!), and this is that error.
    """
    resolved = 0
    for page in _site_pages():
        for directive in _INCLUDE.findall(page.read_text(encoding="utf-8")):
            path = _INCLUDE_SUFFIX.sub("", directive)
            # `@` means the site's source root; anything else is relative to
            # the including page, which is how the four engine pages reach the
            # repository's own documents one directory up.
            target = (
                _SITE / path.lstrip("@/")
                if path.startswith("@")
                else (page.parent / path)
            )
            assert target.is_file(), (
                f"{page.relative_to(_REPO)} includes {directive}, which "
                f"resolves to {target}, and no such file exists: the page would "
                f"publish empty and the build would still pass"
            )
            resolved += 1
    # Not a count of the engine section's pages, which may grow or shrink: only
    # that SOMETHING is included, since a site that includes nothing makes the
    # walk above prove nothing.
    assert resolved >= 1, (
        "no page in the site includes another file any more, so this check "
        "passes vacuously: delete it, or restore the include it was written for"
    )


def test_every_extension_has_a_site_area():
    """A seat the engine can load is a seat a reader can look up.

    A folder under extensions/ carrying an extension.pl is a seat, which is the
    same rule the engine's loader, build.sh and the metta CLI all apply, so
    adding one and forgetting its page would leave it documented nowhere.
    """
    seats = sorted(
        control.parent.name
        for control in (_REPO / "extensions").glob("*/extension.pl")
    )
    assert seats, "no extension.pl found at all, so this check proves nothing"
    # An area is a page OR a folder with an index, because a seat that has more
    # to say than one page should be able to say it: a host seat carries its
    # own tutorial beside its index, and a backend does not.
    missing = [
        seat
        for seat in seats
        if not (_SITE / "extensions" / f"{seat}.md").is_file()
        and not (_SITE / "extensions" / seat / "index.md").is_file()
    ]
    assert not missing, (
        f"these seats ship without a site area: {missing}. Add "
        f"website/extensions/<seat>.md or website/extensions/<seat>/index.md, "
        f"and a navigation entry for it"
    )


def test_every_site_page_is_reachable_from_the_navigation():
    """A page nobody links is a page nobody reads, unless it says it means to.

    Five shipped pages were reachable only through the search box when this was
    first checked: guide/contract.md, integrations/sqlite-blobs.md, and the
    generated reference pages for metta.paths, metta.events and metta.answer.

    A page that is deliberately unlisted says so in its own frontmatter, which
    is where VitePress already keeps a page's per-page settings. A draft, a
    fragment another page includes, or a page reached only from prose writes
    `navigation: false` and this passes. The exemption lives in the page rather
    than in a list here, so it is visible to whoever opens the page and it
    leaves with the page.
    """
    config = _SITE_CONFIG.read_text(encoding="utf-8")
    linked = set(_SITE_LINK.findall(config))
    rewrites = _site_rewrites()
    unreachable = []
    for page in _site_pages():
        text = page.read_text(encoding="utf-8")
        if _OPTS_OUT_OF_NAVIGATION.match(text):
            continue
        relative = page.relative_to(_SITE).as_posix()
        # A rewritten page is published under its rewritten name, so that is
        # the name the navigation has to carry.
        published = rewrites.get(relative, relative).removesuffix(".md")
        # A directory's index page is served as the directory, and only a
        # WHOLE final segment counts: an "appendix" page is not an index.
        if published == "index" or published.endswith("/index"):
            published = published[: -len("index")]
        link = "/" + published
        if link not in linked:
            unreachable.append(
                f'{page.relative_to(_REPO)}: add {{ text: "...", link: "{link}" }} '
                f"to website/.vitepress/config.ts, or put `navigation: false` in "
                f"the page's frontmatter if it is meant to be unlisted"
            )
    assert not unreachable, (
        "these pages are in the site and in no navigation entry, so only the "
        "search box finds them.\n  " + "\n  ".join(unreachable)
    )


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
        "metta_libdoc_tool", _REPO / "extensions" / "python" / "tools" / "libdoc.py"
    )
    module = _importlib_util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def test_the_metta_library_page_is_up_to_date():
    """Require the generated MeTTa library page to match its doc atoms."""
    libdoc = _load_libdoc()
    current = libdoc._PAGE.read_text(encoding="utf-8")
    assert current == libdoc.page(), (
        "metta-libraries.md no longer matches the libraries' @doc atoms; "
        "run `python extensions/python/tools/libdoc.py --write`"
    )


def _lint_kinds() -> set[str]:
    """Every kind metta.lint can emit, read out of the analysis module.

    Derived rather than listed, because a hand-kept list is the thing that
    drifts: the kinds reach a Finding two ways, directly as its first
    argument and through a simplifier's (kind, detail, replacement) triple,
    and both shapes are matched here.
    """
    tree = ast.parse((_REPO / "extensions" / "python" / "metta" / "_lint_analysis.py").read_text())
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
    from metta import S
    from metta.lint import Finding

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
    "python -m pytest extensions/python/tests/ -q --rootdir=extensions/python -c extensions/python/pyproject.toml",
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


def test_the_extension_cost_tables_match_the_committed_pins():
    """EXTENDING.md's cost tables against extension-baseline.json.

    The tables sat days stale while the gated pins moved (the ordinary row
    read 3.00 against a gated 4.00, and the C foreign row was absent from
    the gate entirely), because nothing held the page to the harness. The
    inference columns derive from the committed pins as
    (tier - driver) / operations, so this is committed text against
    committed numbers: it never measures, and the noisy microsecond
    columns stay advisory.
    """
    import json

    from benchmarks.extension_cost import _case_name

    pins = json.loads(
        (_REPO / "extensions/python/benchmarks/extension-baseline.json").read_text()
    )["benchmarks"]
    page = _PAGE.read_text()

    def rows_of(header):
        table = re.search(
            rf"^\| {re.escape(header)} \|.*\n\|[-| ]+\|\n((?:\|.*\n)+)",
            page,
            re.MULTILINE,
        )
        assert table, f"EXTENDING.md lost its '{header}' table"
        rows = {}
        for line in table.group(1).strip().splitlines():
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            rows[cells[0].replace("`", "")] = float(cells[1])
        return rows

    drivers = {
        "extension point": pins["extcost-the-driver-itself"]["inferences"],
        "write door": pins["extcost-the-add-driver-itself"]["inferences"],
    }
    documented = set()
    for header, driver in drivers.items():
        for label, shown in rows_of(header).items():
            name = _case_name(label)
            documented.add(name)
            pin = pins[name]
            expected = (pin["inferences"] - driver) / pin["operations"]
            assert shown == pytest.approx(expected, abs=0.006), (
                f"EXTENDING.md row {label!r} shows {shown:.2f} inferences/call "
                f"but the committed pins derive {expected:.2f}; regenerate the "
                f"table from `python -m benchmarks.extension_cost`"
            )

    pinned = {
        name
        for name in pins
        if name.startswith("extcost-")
        and not name.endswith("-driver-itself")
        and name != "extcost-the-driver-itself"
    }
    assert pinned == documented, (
        f"EXTENDING.md documents {sorted(documented)} but the gate pins "
        f"{sorted(pinned)}; a pinned tier missing from the page is a cost "
        f"nobody finds"
    )
