"""Purpose: the Pygments lexer, reached the way its consumers reach it -- by
alias, by filename, and by MIME type, through the entry point pymetta declares
-- and rendered through rich and through an HTML formatter.

The lexer is generated from the TextMate grammar the site highlights with, and
whether the two AGREE is the `tokenisation` gate lane's question, over the
whole corpus. What is here is the other half: that Pygments can find the class
at all, that the entry point in pyproject.toml names something importable, and
that the three lookups a Jupyter kernel, Sphinx and rich each use land on it.

The distribution is planted rather than installed. The suite imports `metta`
off `sys.path` and nothing in the tree is pip-installed, so
`get_lexer_by_name("metta")` would find nothing; a `.dist-info` carrying the
entry point READ OUT OF pyproject.toml puts the real lookup on the real value,
which is the part that can be wrong.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import importlib
import json
import tomllib

import pytest

# Pygments is the precondition of the door rather than a dependency of it: this
# package declares the entry point and Pygments is what loads it, so a reader
# who has neither Sphinx nor rich nor IPython has no Pygments and nothing here
# to run.
pytest.importorskip("pygments")

from pygments.lexers import (
    get_lexer_by_name,
    get_lexer_for_filename,
    get_lexer_for_mimetype,
)
from pygments.token import (
    Comment,
    Keyword,
    Name,
    Number,
    Punctuation,
    String,
)

from metta._pygments import SCOPE_TOKENS, MettaLexer

PROGRAM = '; a fact\n(: Bool Type)\n!(match &self ($x "y") @doc)\n'


@pytest.fixture
def installed(repo_root, tmp_path, monkeypatch):
    """Pygments' plugin lookup, pointed at the entry point pyproject declares.

    The value is READ from pyproject.toml rather than written here, so a typo
    in the declaration is what this fails on.
    """
    manifest = tomllib.loads(
        (repo_root / "extensions" / "python" / "pyproject.toml").read_text(encoding="utf-8")
    )
    declared = manifest["project"]["entry-points"]["pygments.lexers"]
    info = tmp_path / "pymetta-0.dist-info"
    info.mkdir()
    (info / "METADATA").write_text(
        "Metadata-Version: 2.1\nName: pymetta\nVersion: 0\n", encoding="utf-8"
    )
    (info / "entry_points.txt").write_text(
        "[pygments.lexers]\n"
        + "".join(f"{name} = {value}\n" for name, value in declared.items()),
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    importlib.invalidate_caches()
    yield declared
    importlib.invalidate_caches()


@pytest.mark.usefixtures("installed")
def test_pygments_finds_the_lexer_by_name_filename_and_mimetype():
    """The three lookups a kernel, Sphinx and rich each use land on this class."""
    assert type(get_lexer_by_name("metta")) is MettaLexer
    assert type(get_lexer_for_filename("program.metta")) is MettaLexer
    # What a Jupyter kernel's language_info calls the language, so a front end
    # given the MIME type alone colours the cell.
    assert type(get_lexer_for_mimetype("text/x-metta")) is MettaLexer


@pytest.mark.usefixtures("installed")
def test_rich_renders_a_metta_fence_by_name():
    """The alias resolves for rich itself, so a fence needs no lexer object."""
    console = pytest.importorskip("rich.console")
    syntax = pytest.importorskip("rich.syntax")
    terminal = console.Console(record=True, width=60, force_terminal=True, color_system="truecolor")
    terminal.print(syntax.Syntax(PROGRAM, "metta", theme="monokai"))
    coloured = terminal.export_text(styles=True)
    # Three colours for three groups, rather than one flat block: the comment,
    # the type atom and the number each carry their own escape sequence.
    assert len({line.split("m")[0] for line in coloured.split("\x1b[38;2;")[1:]}) >= 3


@pytest.mark.usefixtures("installed")
def test_the_html_formatter_gives_each_group_its_own_class():
    """The CSS classes an exported notebook carries for a MeTTa cell."""
    pygments = pytest.importorskip("pygments")
    html = pygments.highlight(
        PROGRAM,
        get_lexer_by_name("metta"),
        pytest.importorskip("pygments.formatters").HtmlFormatter(),
    )
    # nbconvert renders a notebook's code cells exactly this way, so these
    # classes are what a MeTTa cell carries into an exported page.
    assert 'class="c1">; a fact' in html
    assert 'class="kt">Bool' in html
    assert 'class="nv">$x' in html


def test_the_lexer_scopes_each_group_of_a_short_program():
    """One token per group, read out of the lexer rather than out of a theme."""
    scoped = {
        value: token
        for _, token, value in MettaLexer().get_tokens_unprocessed(PROGRAM)
        if token is not Punctuation
    }
    assert scoped["; a fact"] is Comment.Single
    assert scoped[":"] is Keyword
    assert scoped["Bool"] is Keyword.Type
    assert scoped["&self"] is Name.Builtin.Pseudo
    assert scoped["$x"] is Name.Variable
    assert scoped["@doc"] is Name.Decorator
    assert scoped['"'] is String.Double
    lexed = list(MettaLexer().get_tokens_unprocessed("!(+ 1 2.5)"))
    assert [token for _, token, _ in lexed].count(Number.Integer) == 1
    assert [token for _, token, _ in lexed].count(Number.Float) == 1


def test_every_group_the_grammar_scopes_has_a_token(repo_root):
    """The one grammar is the source, so a group it grows needs a colour here.

    The `tokenisation` lane says the same thing from the other end, by running
    the grammar's own tokeniser; this says it without node, on every machine.
    """
    grammar = json.loads(
        (repo_root / "website" / ".vitepress" / "metta.tmLanguage.json").read_text(
            encoding="utf-8"
        )
    )
    named = set()
    def walk(node):
        if isinstance(node, dict):
            if isinstance(node.get("name"), str) and node["name"].endswith(".metta"):
                named.add(node["name"])
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(grammar["repository"])
    assert named
    assert named <= set(SCOPE_TOKENS), sorted(named - set(SCOPE_TOKENS))
