r"""Purpose: generate extensions/python/metta/_pygments.py from the TextMate
grammar the site highlights with, so one grammar colours the editor, the
website, and every Pygments consumer -- Sphinx, rich, IPython, Jupyter,
nbconvert, mkdocs -- rather than three files drifting apart.

The grammar is `website/.vitepress/metta.tmLanguage.json`. It is NOT in the
wheel (`[tool.setuptools.package-data]` ships `*.pyi`, `shim.pl` and
`py.typed`), so a lexer that read it at import would work in a checkout and
raise in an installed package. Generating a module instead puts the patterns
where the entry point can reach them, moves the Oniguruma-to-`re` translation
to a place that can REFUSE what it cannot translate, and keeps the check lane
this repository already uses for `vocabularies.py`, `aio.py` and the website
reference: regenerate and compare, and the `pygments-sync` lane fails on drift.

TextMate and Pygments agree on more than they disagree on, and the two
differences are what this file is careful about.

  ORDER. A TextMate rule list is scanned for the EARLIEST match anywhere ahead,
  ties broken by the order the patterns are listed in. A Pygments `RegexLexer`
  tries each rule ANCHORED at the cursor, in order, and takes the first that
  matches. Where any pattern matches at the cursor the two pick the same one,
  because the earliest match is then the cursor itself and the tie-break is the
  same list order; where none does, TextMate skips ahead to the next match and
  leaves the gap unscoped while Pygments needs a rule that consumes something,
  which is what the two trailing fallbacks below are. So the SCOPED spans agree
  exactly and the unscoped gaps differ only in how they are chunked, which is
  what `tests/checks/check_tokenisation_parity.py` compares character by
  character over the corpus.

  LINES. TextMate tokenises one line at a time; a Pygments lexer sees the whole
  text. `^` and `$` mean the same thing under `re.MULTILINE`, and the two
  lookarounds this grammar uses see `\n` where TextMate sees the end of the
  string, which `\s` covers either way. Anchors whose meaning does NOT survive
  that change (`\A`, `\z`, `\Z`, `\G`) are refused rather than translated.

Assumes:
  - the grammar's top-level `patterns` are `{"include": "#name"}` entries and
    each repository entry is either a list of `{"name", "match"}` rules or one
    `begin`/`end` span with `{"name", "match"}` patterns inside it; anything
    else is refused by name rather than guessed at
Guarantees:
  - the checked-in module equals what this produces, gated on every run
    [tested: tests/checks/check_tokenisation_selftest.py; commit=7ba114f280ec3b132658cacb562064d0bac23f41]
  - every pattern is compiled with the flags the generated lexer uses, so a
    construct Python's `re` does not have is a refusal here and never an
    ImportError in a consumer's process [tested:
    tests/checks/check_tokenisation_selftest.py; commit=7ba114f280ec3b132658cacb562064d0bac23f41]
  - a grammar group whose scope has no token in SCOPE_TOKENS is refused by
    name, so a new group cannot reach the lexer uncoloured [tested:
    tests/checks/check_tokenisation_selftest.py; commit=7ba114f280ec3b132658cacb562064d0bac23f41]
  - the generated lexer and the grammar tokenise the whole `.metta` corpus
    identically, character by character [tested:
    tests/checks/check_tokenisation_parity.py; commit=7ba114f280ec3b132658cacb562064d0bac23f41]
Decides: `re.MULTILINE` alone, not `re.ASCII`. Measured against the grammar's
  own tokeniser, Oniguruma's `\s` and `\d` here are Unicode-aware, and the one
  place the two still disagree is `\s`, which `translate` below spells out.
Decides: the evidence pins in HEADER below are written as the literal
  placeholder. `tests/checks/pin_provenance.py` DECLINES a placeholder in a
  Python string that is not a docstring ("this code emits or matches pins"),
  so the provenance commit rewrites the generated module and reports this file
  instead of rewriting it; edit the placeholder here to the same object ID by
  hand and rerun with --write, or the `pygments-sync` lane goes red on the
  difference.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""  # noqa: D205  -- the contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import ast
import json
import pathlib
import re
import sys
from dataclasses import dataclass

ROOT = pathlib.Path(__file__).resolve().parents[3]
GRAMMAR = ROOT / "website" / ".vitepress" / "metta.tmLanguage.json"
MODULE = ROOT / "extensions" / "python" / "metta" / "_pygments.py"

#: One TextMate scope, one Pygments token, chosen as the token Pygments' OWN
#: lexers give that lexical role rather than by translating the scope path:
#: a `;` line comment is `Comment.Single` in every Lisp lexer it ships, `$x` is
#: `Name.Variable` wherever a sigil names a variable, `&self` is the
#: `Name.Builtin.Pseudo` that `self` and `this` get, and an `@`-prefixed
#: annotation is `Name.Decorator`, which is also the purple the grammar's own
#: comment says metta-lang.dev gives `@doc`. The two paren scopes share
#: `Punctuation` because a style that distinguished them would have nothing to
#: say; they stay separate scopes, and the parity lane compares scopes.
SCOPE_TOKENS: dict[str, str] = {
    "comment.line.semicolon.metta": "Comment.Single",
    "string.quoted.double.metta": "String.Double",
    "string.quoted.single.metta": "String.Single",
    "constant.character.escape.metta": "String.Escape",
    "constant.numeric.float.metta": "Number.Float",
    "constant.numeric.integer.metta": "Number.Integer",
    "keyword.other.documentation.metta": "Name.Decorator",
    "variable.other.metta": "Name.Variable",
    "variable.language.metta": "Name.Builtin.Pseudo",
    "support.type.builtin.metta": "Keyword.Type",
    "keyword.control.metta": "Keyword",
    "keyword.operator.metta": "Operator",
    "punctuation.section.parens.begin.metta": "Punctuation",
    "punctuation.section.parens.end.metta": "Punctuation",
}

#: The two tokens that mean "the grammar scoped nothing here". The parity lane
#: reads them as the absence of a scope, so no group may map to either.
UNSCOPED = ("Text", "Whitespace")

#: Oniguruma constructs Python's `re` either lacks or spells differently. Each
#: is refused with the reason rather than translated, because every one of them
#: would otherwise become a silent difference between the site's colours and a
#: reader's: `\h`, `\R` and `\K` do not exist here at all; `\p{...}` and
#: `[[:alpha:]]` are Oniguruma's Unicode and POSIX classes; `(?<name>` and
#: `\k<name>` are the Oniguruma spellings of Python's `(?P<name>` and
#: `(?P=name)`; `\g<name>` calls a subexpression, which Python cannot do; and
#: the four anchors below mean something different to a tokeniser fed one line
#: at a time than to one given the whole file. Everything else is left to the
#: compile below, which is the check that cannot go stale.
UNTRANSLATABLE: tuple[tuple[str, str], ...] = (
    (r"\\[hHRK]", "an Oniguruma escape Python's re does not have"),
    (r"\\[AzZG]", "an anchor that means something else when the whole file is one string"),
    (r"\\p\{", "an Oniguruma Unicode property class"),
    (r"\[\[:", "a POSIX bracket expression"),
    (r"\(\?<[A-Za-z_]", "a named group in Oniguruma's spelling; Python writes (?P<name>"),
    (r"\\k<", "a named backreference in Oniguruma's spelling; Python writes (?P=name)"),
    (r"\\g<", "a subexpression call, which Python's re has no equivalent of"),
    (r"\(\?~", "Oniguruma's absent operator"),
)

FLAGS = re.MULTILINE

#: The four codepoints Python calls whitespace and Unicode does not: the ASCII
#: file, group, record and unit separators. `str.isspace()` is Unicode's
#: White_Space property PLUS these, Oniguruma's `\s` is White_Space alone, and
#: they are the whole of the difference [measured 2026-09-07: over every
#: codepoint below U+3001 that `str.isspace()` accepts, plus U+001C-U+001F,
#: U+0085, U+00A0, U+180E, U+200B, U+2060 and U+FEFF, `(f<c>1)` is scoped as a
#: number by both engines except at these four; command=the probe in
#: docs/journal/2026-09-07-one-grammar-every-highlighter.md;
#: fixture=website/scripts/tokenise.mjs against the same pattern under Python's
#: re; commit=7ba114f280ec3b132658cacb562064d0bac23f41].
NOT_UNICODE_SPACE = range(0x1C, 0x20)


class GrammarError(Exception):
    """The grammar holds something this generator refuses to guess at."""


@dataclass(frozen=True)
class Match:
    """One `{"name", "match"}` rule: a scope and the pattern that carries it."""

    scope: str
    pattern: str


@dataclass(frozen=True)
class Span:
    """One `begin`/`end` rule: a scope held across a region, and its contents."""

    scope: str
    begin: str
    end: str
    inside: tuple[Match, ...]


def _entries(group: object, name: str) -> list[dict[str, str]]:
    """The `{"name", "match"}` rules of one repository group, refusing the rest."""
    if not isinstance(group, list):
        msg = f"{name}: expected a list of patterns, found {type(group).__name__}"
        raise GrammarError(msg)
    out = []
    for entry in group:
        if not isinstance(entry, dict) or set(entry) - {"name", "match", "comment"}:
            msg = (
                f"{name}: {entry!r} is not a plain {{name, match}} rule; this "
                f"generator translates match rules and begin/end spans and "
                f"refuses anything else rather than dropping it"
            )
            raise GrammarError(msg)
        out.append({"name": entry["name"], "match": entry["match"]})
    return out


def rules(grammar: dict) -> list[Match | Span]:
    """The grammar's twelve groups, flattened into the order it lists them."""
    out: list[Match | Span] = []
    for include in grammar["patterns"]:
        if set(include) != {"include"} or not include["include"].startswith("#"):
            msg = (
                f"{include!r} is not a `#name` include into the repository; "
                f"an external grammar, $self or $base has no meaning here"
            )
            raise GrammarError(msg)
        name = include["include"][1:]
        group = grammar["repository"][name]
        known = {"name", "begin", "end", "patterns", "comment"}
        if unknown := set(group) - known:
            msg = f"{name}: {sorted(unknown)} is not translated; TextMate gives it meaning and this does not"
            raise GrammarError(msg)
        if "begin" in group or "end" in group:
            out.append(
                Span(
                    scope=group["name"],
                    begin=group["begin"],
                    end=group["end"],
                    inside=tuple(
                        Match(entry["name"], entry["match"])
                        for entry in _entries(group.get("patterns", []), name)
                    ),
                )
            )
            continue
        out.extend(
            Match(entry["name"], entry["match"])
            for entry in _entries(group["patterns"], name)
        )
    return out


def white_space() -> str:
    r"""Oniguruma's `\s`, as the body of a Python character class.

    Derived from the running Python's own Unicode tables rather than written
    out, so it follows a Python upgrade instead of rotting: every codepoint
    `str.isspace()` accepts, less the four the constant above names.
    """
    codes = [
        code
        for code in range(0x110000)
        if chr(code).isspace() and code not in NOT_UNICODE_SPACE
    ]
    out = []
    start = previous = codes[0]
    for code in [*codes[1:], -1]:
        if code == previous + 1:
            previous = code
            continue
        out.append(_escape(start) if start == previous else f"{_escape(start)}-{_escape(previous)}")
        start = previous = code
    return "".join(out)


def _escape(code: int) -> str:
    """One codepoint as a `re` escape, so no literal control character is written."""
    return f"\\x{code:02x}" if code < 0x100 else f"\\u{code:04x}"


def _class_spans(pattern: str) -> list[tuple[int, int]]:
    """The `[...]` spans of a pattern, so a substitution can tell where it is.

    A `]` immediately after the opening bracket, or after its `^`, is a literal
    `]` rather than the close; a backslash escapes the character after it.
    """
    spans = []
    at = 0
    while at < len(pattern):
        if pattern[at] == "\\":
            at += 2
            continue
        if pattern[at] != "[":
            at += 1
            continue
        start = at
        at += 1
        if at < len(pattern) and pattern[at] == "^":
            at += 1
        if at < len(pattern) and pattern[at] == "]":
            at += 1
        while at < len(pattern) and pattern[at] != "]":
            at += 2 if pattern[at] == "\\" else 1
        if at >= len(pattern):
            msg = f"{pattern!r} opens a character class at {start} and never closes it"
            raise GrammarError(msg)
        at += 1
        spans.append((start, at))
    return spans


def translate(pattern: str, where: str) -> str:
    r"""One Oniguruma pattern as the Python pattern that means the same thing.

    Only `\s` and `\S` are rewritten, and only because the two engines
    genuinely disagree about them; everything else in this grammar means the
    same to both. `\S` inside a character class is refused rather than
    approximated, since Python has no way to spell a negated set inside a
    positive one.
    """
    inside = _class_spans(pattern)
    body = white_space()
    out = []
    at = 0
    while at < len(pattern):
        pair = pattern[at : at + 2]
        if pair not in ("\\s", "\\S"):
            out.append(pattern[at])
            at += 1
            continue
        in_class = any(low < at < high for low, high in inside)
        if pair == "\\S" and in_class:
            msg = (
                f"{where}: {pattern!r} uses \\S inside a character class, and "
                f"Python's re cannot spell a negated set inside a positive one"
            )
            raise GrammarError(msg)
        out.append(body if in_class else f"[{'^' if pair == '\\S' else ''}{body}]")
        at += 2
    return "".join(out)


def check_pattern(pattern: str, where: str) -> str:
    """The translated pattern, or a refusal naming what could not be translated."""
    for probe, reason in UNTRANSLATABLE:
        if re.search(probe, pattern):
            msg = f"{where}: {pattern!r} holds {reason}"
            raise GrammarError(msg)
    translated = translate(pattern, where)
    try:
        re.compile(translated, FLAGS)
    except re.error as error:
        msg = f"{where}: {pattern!r} does not compile under Python's re: {error}"
        raise GrammarError(msg) from error
    return translated


def literal_head(pattern: str) -> str | None:
    r"""The one character a pattern must start with, when it must start with one.

    `"` answers `"` and `\\.` answers a backslash. A pattern whose first
    character is a metacharacter, or an escape that is a character CLASS rather
    than a literal, answers None: the state it belongs to then gets no run rule
    and consumes one character at a time, which is slower and never wrong.
    """
    if not pattern:
        return None
    if pattern[0] == "\\":
        second = pattern[1:2]
        return second if second and not second.isalnum() else None
    return None if pattern[0] in ".^$*+?()[]{}|\\" else pattern[0]


def _literal(pattern: str) -> str:
    """A Python source literal for one pattern, preferring the raw form.

    A raw literal is what a regex should look like in source, and it is legal
    exactly when the quote is absent from the pattern and the pattern does not
    end on an odd run of backslashes. The triple-quoted forms are tried after
    the plain ones and before `repr`, because the escape pattern inside the
    string state holds both quotes and `repr` would double every backslash in
    it. The round trip below is the check: whichever form is chosen,
    `ast.literal_eval` on it has to give the pattern back.
    """
    rendered = repr(pattern)
    if (len(pattern) - len(pattern.rstrip("\\"))) % 2 == 0:
        for quote in ("'", '"', "'''", '"""'):
            if quote in pattern or pattern.endswith(quote[0]):
                continue
            rendered = f"r{quote}{pattern}{quote}"
            break
    if ast.literal_eval(rendered) != pattern:
        msg = f"{pattern!r} did not survive rendering as {rendered}"
        raise GrammarError(msg)
    return rendered


def token(scope: str) -> str:
    """The Pygments token one scope carries, refusing a group with none."""
    name = SCOPE_TOKENS.get(scope)
    if name is None:
        msg = (
            f"the grammar scopes something {scope!r} and SCOPE_TOKENS in "
            f"{pathlib.Path(__file__).name} names no Pygments token for it; a "
            f"group nothing colours would reach every consumer as plain text"
        )
        raise GrammarError(msg)
    if name in UNSCOPED:
        msg = f"{scope!r} maps to {name}, which the parity lane reads as the absence of a scope"
        raise GrammarError(msg)
    return name


def state_lines(span: Span) -> list[str]:
    """The rules of one begin/end state, in the order TextMate resolves them.

    TextMate tries the `end` pattern before the patterns nested inside, and
    both before it gives up on the position, so the state is written the same
    way. Ordering only decides a position both could match at, and here none
    can: an end is one literal character and every nested pattern starts with a
    backslash.
    """
    held = token(span.scope)
    lines = [
        f"            ({_literal(span.end)}, {held}, '#pop'),",
        *(
            f"            ({_literal(rule.pattern)}, {token(rule.scope)}),"
            for rule in span.inside
        ),
    ]
    heads = [literal_head(span.end), *(literal_head(rule.pattern) for rule in span.inside)]
    if all(head is not None for head in heads):
        excluded = "".join(sorted({re.escape(head) for head in heads if head}))
        lines.append(
            "            # Everything up to the next character a rule above can start on."
        )
        lines.append(f"            ({_literal(f'[^{excluded}]+')}, {held}),")
    lines.append(
        "            # One character, so the state is total: a backslash the escape"
    )
    lines.append(
        "            # above does not match leaves the run rule nothing to consume."
    )
    lines.append(f"            ({_literal('[\\s\\S]')}, {held}),")
    return lines


HEADER = '''"""Purpose: colour MeTTa wherever Pygments is asked to, from the same
TextMate grammar the website and the editor use.

GENERATED by extensions/python/tools/pygmentsgen.py from
website/.vitepress/metta.tmLanguage.json; edit the grammar and rerun the
generator with --write, never this file. The `pygments-sync` gate lane fails
when the two drift, and `tokenisation` fails when this lexer and the grammar
disagree about any character of the corpus.

`pygments.lexers` finds this class through the entry point pymetta declares,
so `pip install pymetta` is the whole of the installation: Sphinx, mkdocs,
rich, IPython, nbconvert and Jupyter each ask Pygments for a lexer by name,
alias or MIME type and get this one.

    from pygments import highlight
    from pygments.formatters import HtmlFormatter
    from pygments.lexers import get_lexer_by_name

    highlight("!(+ 1 2)", get_lexer_by_name("metta"), HtmlFormatter())

Guarantees:
  - this file is what pygmentsgen.py writes from the grammar
    [tested: tests/checks/check_tokenisation_selftest.py; commit=7ba114f280ec3b132658cacb562064d0bac23f41]
  - this lexer and the grammar scope every character of every `.metta` file in
    the tree identically [tested: tests/checks/check_tokenisation_parity.py;
    commit=7ba114f280ec3b132658cacb562064d0bac23f41]
  - `metta`, `*.metta` and `text/x-metta` all reach it, which is what a
    Jupyter kernel's `language_info` names [tested:
    test_pygments_finds_the_lexer_by_name_filename_and_mimetype;
    commit=7ba114f280ec3b132658cacb562064d0bac23f41]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""  # noqa: D205  -- the contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import re

from pygments.lexer import RegexLexer
from pygments.token import (
    Comment,
    Keyword,
    Name,
    Number,
    Operator,
    Punctuation,
    String,
    Text,
    Whitespace,
    _TokenType,
)

__all__ = ["SCOPE_TOKENS", "MettaLexer"]

#: Which Pygments token each of the grammar's scopes becomes, so the parity
#: lane can carry the grammar's own vocabulary into this one and compare. Every
#: scope the grammar names is here, and `Text` and `Whitespace` are absent on
#: purpose: those two are what this lexer emits where the grammar scopes
#: nothing, which the comparison reads as the absence of a scope.
SCOPE_TOKENS: dict[str, _TokenType] = {
'''

TRAILER = '''


class MettaLexer(RegexLexer):
    """MeTTa, from the grammar at website/.vitepress/metta.tmLanguage.json."""

    name = "MeTTa"
    url = "https://mestto.github.io/MeTTa-Kernel/"
    #: What get_lexer_by_name, get_lexer_for_filename and get_lexer_for_mimetype
    #: each key on, and what get_all_lexers lists. Tuples rather than the lists
    #: Pygments' own lexers declare: all four read them by `in` or by iterating,
    #: measured, and an immutable class attribute is one neither linter here has
    #: to be told about -- a list draws ruff's RUF012 and the ClassVar that
    #: answers it draws ty's invalid-attribute-override against a base class
    #: that declares them as instance attributes.
    aliases = ("metta",)
    filenames = ("*.metta",)
    mimetypes = ("text/x-metta",)

    #: re.MULTILINE, because TextMate matches `$` against the end of a LINE
    #: and this lexer is given the whole file. Not re.ASCII: measured against
    #: the grammar's own tokeniser, Oniguruma's `\\s` and `\\d` here are
    #: Unicode-aware, so `(f<nbsp>1)` scopes its 1 as a number and re.ASCII
    #: would not.
    flags = re.MULTILINE

    #: Every `\\s` below is spelled out, and the spelling is not Python's own.
    #: `str.isspace()` is Unicode's White_Space property plus the four ASCII
    #: separators U+001C-U+001F, and Oniguruma's `\\s` is White_Space alone;
    #: pygmentsgen.py writes the set out from the running Python's Unicode
    #: tables, less those four, so a separator beside a number is scoped here
    #: exactly as the site scopes it.
    # Suppressed rather than annotated ClassVar, which ty reads as an invalid
    # override of a base class that declares this as an instance attribute:
    # RegexLexerMeta compiles this dict once per CLASS into `_tokens` and no
    # instance mutates it, so the shared mutable default RUF012 warns about
    # cannot happen here. (A comment opening with the rule's own suppression
    # word would itself be read as a blanket directive, so it opens this way.)
    tokens = {  # noqa: RUF012  -- see above
'''


def translated(rule: Match | Span) -> Match | Span:
    """One grammar rule with every pattern in it translated, or a refusal."""
    if isinstance(rule, Span):
        return Span(
            scope=rule.scope,
            begin=check_pattern(rule.begin, rule.scope),
            end=check_pattern(rule.end, rule.scope),
            inside=tuple(
                Match(nested.scope, check_pattern(nested.pattern, nested.scope))
                for nested in rule.inside
            ),
        )
    return Match(rule.scope, check_pattern(rule.pattern, rule.scope))


def module_text(grammar: dict) -> str:
    """The generated module, from the grammar's own order and nothing else."""
    flattened = [translated(rule) for rule in rules(grammar)]

    scopes = sorted({rule.scope for rule in flattened} | {
        nested.scope for rule in flattened if isinstance(rule, Span) for nested in rule.inside
    })
    mapping = "".join(f'    "{scope}": {token(scope)},\n' for scope in scopes)

    root: list[str] = []
    states: list[str] = []
    for rule in flattened:
        root.append(f"            # {rule.scope}")
        if isinstance(rule, Span):
            root.append(
                f'            ({_literal(rule.begin)}, {token(rule.scope)}, '
                f'"{rule.scope}"),'
            )
            states.append(f'        "{rule.scope}": [')
            states.extend(state_lines(rule))
            states.append("        ],")
            continue
        root.append(f"            ({_literal(rule.pattern)}, {token(rule.scope)}),")
    root.extend(
        [
            "            # Not a group in the grammar. TextMate leaves what no pattern",
            "            # matches unscoped and skips ahead; a Pygments state has to",
            "            # consume something, and these two are the least it can consume",
            "            # without reaching past a character a rule above would match.",
            r"            (r'\s+', Whitespace),",
            r"            (r'[\s\S]', Text),",
        ]
    )

    return (
        HEADER
        + mapping
        + "}"
        + TRAILER
        + '        "root": [\n'
        + "\n".join(root)
        + "\n        ],\n"
        + "\n".join(states)
        + "\n    }\n"
    )


def main(argv: list[str]) -> int:
    """Check the generated module, or rewrite it when asked."""
    try:
        wanted = module_text(json.loads(GRAMMAR.read_text(encoding="utf-8")))
    except GrammarError as error:
        print(f"{GRAMMAR.relative_to(ROOT)}: {error}", file=sys.stderr)
        return 1
    current = MODULE.read_text(encoding="utf-8") if MODULE.exists() else None
    if current == wanted:
        return 0
    if "--write" in argv:
        MODULE.write_text(wanted, encoding="utf-8")
        print(f"rewrote {MODULE.relative_to(ROOT)}")
        return 0
    print(
        f"{MODULE.relative_to(ROOT)} no longer matches "
        f"{GRAMMAR.relative_to(ROOT)}: run "
        f"`python extensions/python/tools/pygmentsgen.py --write`"
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
