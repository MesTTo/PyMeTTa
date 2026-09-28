"""Purpose: derive lib/lib_markup/DTD/HTML5.dtd from the WHATWG HTML Standard at a pinned commit.

The DTD is the one SWI-Prolog's library(sgml) reads for the html5 dialect, and
it says what the text/html syntax fixes and SGML can express. Each rule below
reads its facts out of the Standard, so a new pin changes the DTD and no fact
about HTML is written here:

  - The elements are the rows of the element index (Index, "List of
    elements") that name HTML elements. The MathML math and SVG svg rows,
    whose Children say "per MathML" and "per SVG", are foreign elements: the
    content categories list them and they stay undeclared, since SWI's
    parser admits any child and any attribute under an element no
    declaration defines (parser.c open_element, allow_for and
    process_attributes).
  - An element's declared content follows its kind (13.1.2, "Elements"): a
    void element is EMPTY and the template element ANY. The tokenizer state
    the fragment parsing algorithm switches to for an element as its context
    gives RCDATA for the RCDATA state and CDATA for the RAWTEXT and script
    data states; where that state depends on scripting (noscript) the
    scripting-disabled branch is read, since this parser runs no script. Every
    raw text element must be in a CDATA state and every escapable raw text
    element in RCDATA, or the reading is refused.
  - The omissible tags are the optional-tag rules (13.1.2.4), one sentence
    each, and a void element's end tag.
  - A normal element admits its Children in the element index, each content
    category expanded from the categories index with its exceptions, Text as
    #PCDATA, and transparent and varies read as flow content, the Standard's
    reading of a transparent element with no parent. It also admits every
    element whose Parents name it, which recovers the context-dependent models
    the Children column summarises (dt and dd in a div; link, meta and style
    in a noscript). An element whose omitted start tag its first child implies
    (tbody by tr, colgroup by col) takes that child out of the models of the
    elements that admit it, since SGML infers an omitted start tag only where
    the parent does not admit the child itself; a tr in a table then opens a
    tbody, as the HTML parser does. A Content model reading "A x element
    followed by a y element" is that sequence (html: head, body), in which an
    element whose start tag may be omitted when it is empty is optional, since
    SGML can pass over an absent element only where the model makes it
    optional (model.c find_omitted_path descends into omissible start tags and
    never opens and closes one). The sequence is written as the choice of its
    suffixes, the longest last, (body? | (head, body?)) for html: SWI's search
    marks the state an omissible start tag leads to before it follows the
    optional member's empty path to that same state, so written (head?,
    body?) no body is ever inferred, and it tries a choice's last member
    first, so a head is inferred ahead of a body for what both admit. A
    normal element whose model admits nothing admits character data, the one
    model that keeps it open until the end tag its syntax requires.
  - The attributes are the attributes index and the event handler index: a
    row for HTML elements goes on every element, the others on the elements
    they name. A Boolean attribute, and an enumerated one whose keywords
    include its own name (hidden), is declared with its keywords, so the name
    alone parses as SGML's value shorthand; every other attribute is CDATA,
    which keeps its value as written.
  - The named character references are whatwg/html-build's entities.json at
    a pinned commit, the data the Standard's table of them (13.5) is built
    from: one CDATA entity per name. A legacy name without its semicolon must
    be the same name with it, since SGML's reference close is optional.
  Each rule is held against a planted miniature of the Standard
  [tested 2026-09-28T12:17:29+10:00: tests/checks/check_html5dtd_selftest.py, RuleTests].

Assumes: a clone of each pinned repository holding its pinned commits is the
  checkout its variable names (WHATWG_HTML for whatwg/html, WHATWG_HTML_BUILD
  for whatwg/html-build), or the one of its name beside this tree or beside
  its main checkout; `--fetch` makes each there. The pins are read from the
  object store, so a checkout's working tree and later history never reach
  the DTD [tested 2026-09-28T12:17:29+10:00: tests/checks/check_html5dtd_selftest.py, PinTests].
Guarantees: the DTD is a function of the pinned inputs, the BSD 3-Clause text
  under tools/host-notices/LICENSES and this file, and a plain run exits 1
  naming the difference when the committed DTD is not what they generate
  [tested 2026-09-28T12:17:29+10:00: tests/checks/check_html5dtd_selftest.py,
  MainTests.test_write_then_check_then_drift].
Guarantees: each input is the pinned git blob, checked by its blob id, and
  the licence notice in the header is the Standard's own, refused unless
  html-build's LICENSE opens with the same notice and the notice licenses
  portions in source code under the BSD 3-Clause License
  [tested 2026-09-28T12:17:29+10:00: tests/checks/check_html5dtd_selftest.py,
  PinTests.test_a_blob_that_is_not_the_pinned_one_refuses and
  RefusalTests.test_an_entity_table_or_licence_that_disagrees_refuses].
Guarantees: every parameter entity fits SWI's 4096-character literal and every
  declaration its 10240-character expansion (sgmldefs.h MAXSTRINGLEN and
  MAXDECL), or the run refuses, since SWI reports an overflow and loads the
  DTD without the declaration
  [source 2026-09-28T11:33:58+10:00: swipl-devel packages/sgml/sgmldefs.h and parser.c, expand_pentities]
  [tested 2026-09-28T12:17:29+10:00: tests/checks/check_html5dtd_selftest.py,
  RenderTests.test_what_swi_would_truncate_refuses].
Fails when: the Standard's markup moves out from under a reader (a table, a
  section or a sentence pattern is missing, or a cell holds a word no rule
  knows), which refuses naming it rather than writing a DTD with the fact
  missing [tested 2026-09-28T12:17:29+10:00: tests/checks/check_html5dtd_selftest.py,
  RefusalTests.test_each_moved_shape_refuses]; and where HTML is not SGML: a
  custom element's name, an attribute written without a value that is neither
  Boolean nor hidden, an entity reference in an attribute value (SWI folds its
  case in the html5 dialect), an end tag of a raw or escapable raw text element
  with white space before its '>' (SWI's scanner ends such an element only at
  the bare end tag, parser.c S_ECDATA2), and the tree builder's repairs are
  outside what a DTD can say.
Decides: an absent checkout refuses, exit 1, wherever the check runs, naming
  every place it looked; WHATWG_HTML_OPTIONAL=1 turns that into a skip, 125,
  off CI only (docs/journal/2026-09-24-a-skip-is-a-verdict-about-nothing.md)
  [tested 2026-09-28T12:17:29+10:00: tests/checks/check_html5dtd_selftest.py,
  MainTests.test_an_absent_checkout_refuses_unless_skipped_off_ci].
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
import re
import subprocess
import sys
import textwrap
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path

import artifacts

ROOT = next(parent for parent in Path(__file__).resolve().parents
            if (parent / "engine").is_dir() and (parent / "lib").is_dir())
OUTPUT = "lib/lib_markup/DTD/HTML5.dtd"
#: SPDX's BSD 3-Clause text, which the notices already carry; the header
#: replaces its template copyright line with WHATWG's.
BSD = "tools/host-notices/LICENSES/BSD-3-Clause.txt"
BSD_TEMPLATE = "Copyright (c) <year> <owner>."
#: SWI-Prolog's limits on one entity literal and one declaration after its
#: parameter entities expand, in characters with the terminator
#: [source 2026-09-28T11:33:58+10:00: swipl-devel packages/sgml/sgmldefs.h,
#: MAXSTRINGLEN and MAXDECL].
MAXSTRINGLEN = 4096
MAXDECL = 10240


@dataclass(frozen=True)
class Repository:
    """A WHATWG repository the DTD is read from.

    Its remote is where it is fetched from, its checkout the directory beside this
    tree that holds it, and its variable the one naming another checkout.
    """

    remote: str
    checkout: str
    variable: str


@dataclass(frozen=True)
class Pin:
    """One file of a WHATWG repository at a commit, and the git blob it must be."""

    repository: Repository
    commit: str
    path: str
    blob: str


HTML = Repository("https://github.com/whatwg/html", "whatwg-html", "WHATWG_HTML")
HTML_BUILD = Repository("https://github.com/whatwg/html-build", "whatwg-html-build", "WHATWG_HTML_BUILD")
STANDARD = Pin(HTML, "2f441941fc523877bd9d5cd7de3b91a81a00ca2e",
               "source", "475d5243f6b7b79f34d3e24614fc1c89437a5272")
ENTITIES = Pin(HTML_BUILD, "283a3531a61106d07d9a7d9fb3e6f3b9bfd33d70",
               "entities/out/entities.json", "557170b41f47a13a46ec695561eb5fe76da73bdb")
BUILD_LICENSE = Pin(HTML_BUILD, ENTITIES.commit, "LICENSE", "f2dcda46deccefd245749202a88a7837e35c6daa")
PINS = (STANDARD, ENTITIES, BUILD_LICENSE)
REPOSITORIES = (HTML, HTML_BUILD)
OPTIONAL = "WHATWG_HTML_OPTIONAL"
FETCH = "python extensions/python/tools/html5dtd.py --fetch"


class ReadError(ValueError):
    """An input the generator cannot read its facts from.

    Either the input is not the pinned one, or the Standard's markup no longer has
    the shape a reader takes a fact from.
    """


# ---------------------------------------------------------------- the inputs


def blob_id(data: bytes) -> str:
    """The git blob id of DATA, which is what a pin names."""
    return hashlib.sha1(b"blob %d\0" % len(data) + data, usedforsecurity=False).hexdigest()


def _git(place: Path, *arguments: str) -> subprocess.CompletedProcess[bytes]:
    """Run git on one repository, capturing bytes."""
    return subprocess.run(  # noqa: S603 -- git on a path this tool derived or was named
        ["git", "-C", str(place), *arguments],  # noqa: S607 -- git from PATH, as every lane runs it
        capture_output=True, check=False)


def candidates(repository: Repository, root: Path = ROOT) -> list[Path]:
    """Where a repository's checkout is looked for, in order.

    Its variable's path alone when set, else beside this tree and then beside the
    main checkout, whose .git `git rev-parse --git-common-dir` names from any
    linked worktree.
    """
    named = os.environ.get(repository.variable)
    if named:
        return [Path(named)]
    places = [root.parent / repository.checkout]
    common = _git(root, "rev-parse", "--path-format=absolute", "--git-common-dir")
    if common.returncode == 0 and common.stdout.strip():
        places.append(Path(common.stdout.decode().strip()).parent.parent / repository.checkout)
    return list(dict.fromkeys(places))


def located(repository: Repository, places: list[Path], pins: tuple[Pin, ...] = PINS) -> Path | None:
    """The first place holding every pin of REPOSITORY; None when no place is a repository.

    A clone lacking a pin is refused by the pin's commit, since the DTD was
    generated from those commits and no other.
    """
    wanted = [pin for pin in pins if pin.repository == repository]
    clones = [place for place in places if place.is_dir() and _git(place, "rev-parse", "--git-dir").returncode == 0]
    for place in clones:
        if all(_git(place, "cat-file", "-e", f"{pin.commit}:{pin.path}").returncode == 0 for pin in wanted):
            return place
    if clones:
        message = (f"no clone of {repository.remote} holds {', '.join(sorted({pin.commit for pin in wanted}))}: "
                   f"looked in {', '.join(map(str, clones))}; run `{FETCH}`, or name one with "
                   f"{repository.variable}")
        raise ReadError(message)
    return None


def read_pin(place: Path, pin: Pin) -> bytes:
    """The pinned blob, refused unless its id is the pin's."""
    shown = _git(place, "cat-file", "blob", f"{pin.commit}:{pin.path}")
    if shown.returncode != 0:
        message = f"{place} cannot show {pin.commit}:{pin.path}: {shown.stderr.decode(errors='replace').strip()}"
        raise ReadError(message)
    if blob_id(shown.stdout) != pin.blob:
        message = (f"{pin.repository.remote} {pin.commit}:{pin.path} is blob {blob_id(shown.stdout)}, "
                   f"not the pinned {pin.blob}")
        raise ReadError(message)
    return shown.stdout


def fetch(root: Path = ROOT, pins: tuple[Pin, ...] = PINS) -> list[Path]:
    """Make each repository's checkout, holding its pinned commits and none of their history.

    The checkout is its variable's path or else beside the main checkout, and
    github.com serves a commit by id to `fetch --depth 1`.
    """
    made: list[Path] = []
    for repository in dict.fromkeys(pin.repository for pin in pins):
        place = candidates(repository, root)[-1]
        place.mkdir(parents=True, exist_ok=True)
        if _git(place, "rev-parse", "--git-dir").returncode != 0 and _git(place, "init", "-q").returncode != 0:
            message = f"git init failed in {place}"
            raise ReadError(message)
        for commit in sorted({pin.commit for pin in pins if pin.repository == repository}):
            if _git(place, "cat-file", "-e", f"{commit}^{{commit}}").returncode == 0:
                continue
            fetched = _git(place, "fetch", "-q", "--depth", "1", "--no-tags", repository.remote, commit)
            if fetched.returncode != 0:
                message = (f"fetching {repository.remote} {commit} into {place} failed: "
                           f"{fetched.stderr.decode(errors='replace').strip()}")
                raise ReadError(message)
        for pin in pins:
            if pin.repository == repository:
                read_pin(place, pin)
        made.append(place)
    return made


def prerequisite(absent: list[tuple[Repository, list[Path]]], pins: tuple[Pin, ...] = PINS) -> int:
    """The exit an absent checkout earns.

    It is 1 wherever the check runs, and 125 only when WHATWG_HTML_OPTIONAL=1 asks
    for a skip outside CI.
    """
    absence = "; ".join(f"no clone of {repository.remote} holding "
                        f"{', '.join(sorted({pin.commit for pin in pins if pin.repository == repository}))}: "
                        f"looked in {', '.join(map(str, places))}"
                        for repository, places in absent)
    remedy = (f"run `{FETCH}`, or name clones with "
              f"{' and '.join(repository.variable for repository, _ in absent)}")
    optional = os.environ.get(OPTIONAL) == "1"
    if optional and os.environ.get("CI") != "true":
        print(f"note: {absence}; {OPTIONAL}=1 skips the comparison. {remedy}.")
        return 125
    why = f"{OPTIONAL} does not apply where CI=true" if optional else f"{OPTIONAL}=1 skips it outside CI"
    print(f"error: {absence}. {remedy}; {why}.", file=sys.stderr)
    return 1


# ------------------------------------------------------ the Standard's markup


class Node:
    """An element of the Standard's markup: its tag, attributes and children."""

    __slots__ = ("attrs", "children", "parent", "tag")

    def __init__(self, tag: str, attrs: dict[str, str], parent: Node | None) -> None:
        """An element TAG with ATTRS under PARENT, with no children yet."""
        self.tag = tag
        self.attrs = attrs
        self.parent = parent
        self.children: list[Node | str] = []

    def elements(self, tag: str) -> list[Node]:
        """Every descendant element named TAG, in document order."""
        found: list[Node] = []
        stack: list[Node] = [self]
        while stack:
            node = stack.pop()
            stack.extend(child for child in reversed(node.children) if isinstance(child, Node))
            if node is not self and node.tag == tag:
                found.append(node)
        return found

    def siblings(self) -> tuple[list[Node], list[Node]]:
        """The elements before this one in its parent and those after it, in order."""
        assert self.parent is not None
        elements = [child for child in self.parent.children if isinstance(child, Node)]
        index = elements.index(self)
        return elements[:index], elements[index + 1:]


#: The elements the source's markup never closes.
VOID = frozenset({"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta",
                  "source", "track", "wbr"})
#: The start tags that close an open p, as HTML's "close a p element" does for
#: the blocks the source writes.
BLOCKS = frozenset({"address", "article", "aside", "blockquote", "details", "div", "dl", "dd", "dt",
                    "fieldset", "figcaption", "figure", "footer", "form", "h1", "h2", "h3", "h4",
                    "h5", "h6", "header", "hgroup", "hr", "li", "main", "menu", "nav", "ol", "p",
                    "pre", "search", "section", "table", "ul"})
#: Where the search for an open p stops: HTML's button scope.
P_SCOPE = frozenset({"table", "td", "th", "caption", "template", "object", "button", "#root"})
#: A start tag, the open tags it closes and the tags that bound the search.
IMPLIED = {
    "tr": (("tr",), ("table",)),
    "td": (("td", "th"), ("tr", "table")),
    "th": (("td", "th"), ("tr", "table")),
    "thead": (("thead", "tbody", "tfoot"), ("table",)),
    "tbody": (("thead", "tbody", "tfoot"), ("table",)),
    "tfoot": (("thead", "tbody", "tfoot"), ("table",)),
    "dt": (("dt", "dd"), ("dl",)),
    "dd": (("dt", "dd"), ("dl",)),
    "li": (("li",), ("ul", "ol", "menu")),
}


class Builder(HTMLParser):
    """The source as a tree, closing the elements its markup leaves open the way HTML does.

    A cell closes at the next cell or row, a row at the next row or section, a dt
    or dd at the next one, an li at the next li, and a p at a block.
    """

    def __init__(self) -> None:
        """A parser whose tree is a bare root, the one open element."""
        super().__init__(convert_charrefs=True)
        self.root = Node("#root", {}, None)
        self.open: list[Node] = [self.root]

    def _close(self, targets: tuple[str, ...] | frozenset[str], bounds: tuple[str, ...] | frozenset[str]) -> None:
        for index in range(len(self.open) - 1, 0, -1):
            tag = self.open[index].tag
            if tag in targets:
                del self.open[index:]
                return
            if tag in bounds:
                return

    def _start(self, tag: str, attrs: list[tuple[str, str | None]], *, void: bool) -> None:
        if tag in IMPLIED:
            self._close(*IMPLIED[tag])
        if tag in BLOCKS:
            self._close(("p",), P_SCOPE)
        node = Node(tag, {name: value or "" for name, value in attrs}, self.open[-1])
        self.open[-1].children.append(node)
        if not void:
            self.open.append(node)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Open TAG, closing what its start implies."""
        self._start(tag, attrs, void=tag in VOID)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Add a self-closed TAG."""
        self._start(tag, attrs, void=True)

    def handle_endtag(self, tag: str) -> None:
        """Close TAG and everything open inside it; a stray end tag is ignored."""
        for index in range(len(self.open) - 1, 0, -1):
            if self.open[index].tag == tag:
                del self.open[index:]
                return

    def handle_data(self, data: str) -> None:
        """Keep text where it is."""
        self.open[-1].children.append(data)


def parse(text: str) -> Node:
    """The Standard's source as a tree."""
    builder = Builder()
    builder.feed(text)
    builder.close()
    return builder.root


def text_of(part: Node | str) -> str:
    """Every character under PART."""
    if isinstance(part, str):
        return part
    return "".join(text_of(child) for child in part.children)


def squash(text: str) -> str:
    """TEXT with each run of white space one space."""
    return " ".join(text.split())


Run = list  # one ';'-separated entry of an index cell: its text and elements


def runs(cell: Node) -> list[Run]:
    """The cell's entries, split at each ';' in its own text.

    Blank entries and the Standard's dash for "none" are dropped.
    """
    split: list[Run] = [[]]
    for part in cell.children:
        if isinstance(part, str):
            pieces = part.split(";")
            split[-1].append(pieces[0])
            split.extend([piece] for piece in pieces[1:])
        else:
            split[-1].append(part)
    return [run for run in split if squash("".join(text_of(part) for part in run)).strip("*— ")]


def _outside(run: Run) -> list[Node]:
    """The elements of RUN outside any parenthesis, depth-first.

    A parenthesis qualifies what a run is about and names other things.
    """
    found: list[Node] = []
    depth = 0

    def walk(parts: list[Node | str]) -> None:
        nonlocal depth
        for part in parts:
            if isinstance(part, str):
                depth += part.count("(") - part.count(")")
            elif depth == 0:
                found.append(part)
                if part.tag != "code":
                    walk(part.children)

    walk(run)
    return found


def subjects(run: Run) -> list[str]:
    """The element or attribute names a run is about.

    They are its code elements outside any parenthesis, a span wrapping one
    ("MathML math") included.
    """
    return [squash(text_of(part)) for part in _outside(run) if part.tag == "code"]


def key(run: Run) -> str:
    """The term a run naming no element refers to, lower case.

    The term is its first span outside any parenthesis, by the data-x the source
    gives a reference whose text differs from its term ("flow" for Flow content)
    else its text, and else the run's own text without the Standard's '*' mark.
    """
    spans = [part for part in _outside(run) if part.tag == "span"]
    if spans:
        return squash(spans[0].attrs.get("data-x") or text_of(spans[0])).lower()
    return words(run)


def words(run: Run) -> str:
    """A run's text as it reads, lower case and without the '*' mark."""
    return squash("".join(text_of(part) for part in run)).strip("* ").lower()


def table(root: Node, caption: str) -> list[list[Node]]:
    """The body rows of the one table with CAPTION, each a list of its cells."""
    found = [node for node in root.elements("table")
             if any(isinstance(child, Node) and child.tag == "caption" and squash(text_of(child)) == caption
                    for child in node.children)]
    if len(found) != 1:
        message = f"expected one table captioned {caption!r}, found {len(found)}"
        raise ReadError(message)
    rows = [row for body in found[0].elements("tbody") for row in body.elements("tr")]
    if not rows:
        message = f"the table captioned {caption!r} has no body rows"
        raise ReadError(message)
    return [[cell for cell in row.children if isinstance(cell, Node) and cell.tag in ("th", "td")]
            for row in rows]


def pairs(dl: Node) -> list[tuple[list[Node], list[Node]]]:
    """A dl as its groups: the terms and the definitions answering them, in order."""
    groups: list[tuple[list[Node], list[Node]]] = []
    for child in dl.children:
        if not isinstance(child, Node) or child.tag not in ("dt", "dd"):
            continue
        if child.tag == "dt" and (not groups or groups[-1][1]):
            groups.append(([], []))
        if child.tag == "dt":
            groups[-1][0].append(child)
        elif groups:
            groups[-1][1].append(child)
    return groups


def one(found: list, what: str):
    """The single match of a search, refused as missing or ambiguous otherwise."""
    if len(found) != 1:
        message = f"expected one {what}, found {len(found)}"
        raise ReadError(message)
    return found[0]


def rendered(node: Node, marks: dict[str, str]) -> str:
    """NODE's text with its code elements and marked spans spelled so its shape can be matched.

    Each code element is written <name>, and each span whose data-x, else whose
    text, MARKS names is written as that mark.
    """
    out: list[str] = []
    for part in node.children:
        if isinstance(part, str):
            out.append(part)
        elif part.tag == "code":
            out.append(f"<{squash(text_of(part))}>")
        elif part.tag == "span" and (part.attrs.get("data-x") or squash(text_of(part))) in marks:
            out.append(marks[part.attrs.get("data-x") or squash(text_of(part))])
        else:
            out.append(rendered(part, marks))
    return squash("".join(out))


# --------------------------------------------------------- what the DTD says


PCDATA = "#PCDATA"
#: The words of the index that stand for character data.
TEXT = frozenset({"text content", "text"})
#: The Children words that read as flow content.
AS_FLOW = frozenset({"transparent", "varies"})
#: The Children words of an element other specifications define.
FOREIGN = frozenset({"per svg", "per mathml"})
#: The words of the index naming elements no name declares.
CUSTOM = frozenset({"autonomous custom element", "form-associated custom element"})


@dataclass(frozen=True)
class Attribute:
    """An attribute and the keywords its name alone stands for, empty for CDATA."""

    name: str
    shorthand: tuple[str, ...]

    def declaration(self) -> str:
        """The attribute definition an ATTLIST carries."""
        kind = f"({' | '.join(self.shorthand)})" if self.shorthand else "CDATA"
        return f"{self.name} {kind} #IMPLIED"


@dataclass(frozen=True)
class Element:
    """One declared element: its tag omission, its content and its own attributes."""

    name: str
    omit_start: bool
    omit_end: bool
    content: str          # EMPTY, ANY, CDATA, RCDATA or a model group
    attributes: tuple[Attribute, ...]


@dataclass(frozen=True)
class Standard:
    """What the DTD declares, read from the Standard."""

    elements: tuple[Element, ...]
    categories: tuple[tuple[str, tuple[str, ...]], ...]    # parameter entity, members
    globals: tuple[tuple[str, tuple[Attribute, ...]], ...]  # parameter entity, attributes
    entities: tuple[tuple[str, tuple[int, ...]], ...]
    notice: str


def elements_index(root: Node) -> tuple[dict[str, list[Run]], dict[str, list[Run]], set[str]]:
    """The element index: each HTML element's Children and Parents runs, and the foreign elements.

    A foreign element is one whose Children name another specification.
    """
    children: dict[str, list[Run]] = {}
    parents: dict[str, list[Run]] = {}
    foreign: set[str] = set()
    for cells in table(root, "List of elements"):
        if len(cells) != 7:
            message = f"an element index row has {len(cells)} cells, not 7: {squash(text_of(cells[0]))!r}"
            raise ReadError(message)
        names = subjects(cells[0].children)
        if not names:
            if key(cells[0].children) not in CUSTOM:
                message = f"an element index row names no element: {squash(text_of(cells[0]))!r}"
                raise ReadError(message)
            continue
        if {key(run) for run in runs(cells[4])} & FOREIGN:
            foreign.update(names)
            continue
        for name in names:
            children[name] = runs(cells[4])
            parents[name] = runs(cells[3])
    return children, parents, foreign


def categories_index(root: Node, known: set[str]) -> dict[str, frozenset[str]]:
    """Each content category's members, its Elements and its Elements with exceptions alike.

    A member is an element name, or #PCDATA for Text; the custom elements have no
    name to list and add nothing.
    """
    members: dict[str, frozenset[str]] = {}
    for cells in table(root, "List of element content categories"):
        name = squash(text_of(cells[0])).lower()
        found: set[str] = set()
        for run in (*runs(cells[1]), *runs(cells[2])):
            if names := subjects(run):
                found.update(names)
            elif key(run) in TEXT:
                found.add(PCDATA)
            elif key(run) not in CUSTOM:
                message = f"category {name!r} lists {key(run)!r}, which no rule reads"
                raise ReadError(message)
        if unknown := {member for member in found if member != PCDATA} - known:
            message = f"category {name!r} lists {sorted(unknown)}, which the element index does not"
            raise ReadError(message)
        members[name] = frozenset(found)
    return members


def attribute_rows(root: Node) -> list[tuple[str, list[str] | None, tuple[str, ...], bool]]:
    """Every row of the two attribute indices.

    A row is the attribute's name, its elements (None for every HTML element), the
    keywords its name alone stands for, and whether it is an event handler. The
    Element(s) column links each entry to the attribute's own definition, so a run
    naming no element is read by its text: "HTML elements" is every element, and
    custom elements have no name to declare.
    """
    rows: list[tuple[str, list[str] | None, tuple[str, ...], bool]] = []
    for caption, handlers in (("List of attributes (excluding event handler content attributes)", False),
                              ("List of event handler content attributes", True)):
        for cells in table(root, caption):
            name = one(subjects(cells[0].children), f"attribute name in {squash(text_of(cells[0]))!r}")
            on: list[str] = []
            everywhere = False
            for run in runs(cells[1]):
                if names := subjects(run):
                    on.extend(names)
                elif words(run) == "html elements":
                    everywhere = True
                elif not any(term in words(run) for term in CUSTOM):
                    message = f"attribute {name!r} applies to {words(run)!r}, which no rule reads"
                    raise ReadError(message)
            value = squash(text_of(cells[3]))
            if handlers:
                shorthand: tuple[str, ...] = ()
            elif "Boolean attribute" in value:
                shorthand = (name,)
            else:
                keywords = tuple(re.findall(r'"([^"]*)"', value))
                shorthand = keywords if name in keywords else ()
            if everywhere:
                rows.append((name, None, shorthand, handlers))
            if on:
                rows.append((name, list(dict.fromkeys(on)), shorthand, handlers))
    return rows


def syntax_kinds(root: Node) -> dict[str, set[str]]:
    """The kinds of element (13.1.2 Elements): each kind's lower-case name and its elements."""
    dl = one([node for node in root.elements("dl")
              if any(squash(text_of(term)) == "Void elements" for terms, _ in pairs(node) for term in terms)],
             "dl naming the void elements")
    return {squash(text_of(term)).lower(): {name for definition in definitions
                                             for name in subjects(definition.children)}
            for terms, definitions in pairs(dl) for term in terms}


#: Tokenizer states and the declared content each gives.
STATES = {"RCDATA state": "RCDATA", "RAWTEXT state": "CDATA", "script data state": "CDATA",
          "PLAINTEXT state": "CDATA", "data state": ""}


def tokenizer_states(root: Node) -> dict[str, str]:
    """The declared content the fragment parsing algorithm's tokenizer state gives each element.

    Each element is taken as the context element, and where the state depends on
    scripting the scripting-disabled branch is read, since this parser runs none.
    """
    lead = one([paragraph for paragraph in root.elements("p")
                if "tokenization stage as follows, switching on" in squash(text_of(paragraph))],
               "paragraph introducing the fragment parsing algorithm's tokenizer states")
    _, after = lead.siblings()
    if not after or after[0].tag != "dl":
        message = "the fragment parsing algorithm's tokenizer states no longer follow their paragraph as a dl"
        raise ReadError(message)
    states: dict[str, str] = {}
    marks = {state: "{" + state + "}" for state in STATES}
    for terms, definitions in pairs(after[0]):
        sentence = " ".join(rendered(definition, marks) for definition in definitions)
        branch = sentence.split("Otherwise", 1)[-1]
        state = one(sorted(set(re.findall(r"\{([^}]+)\}", branch))), f"tokenizer state in {sentence!r}")
        for term in terms:
            for name in subjects(term.children):
                states[name] = STATES[state]
    return states


def omissions(root: Node) -> tuple[set[str], set[str], dict[str, str], set[str]]:
    """The optional-tag rules, as four answers.

    They are the elements whose start tag may be omitted, those whose end tag may
    be, the child that implies each omitted start tag, and the elements whose
    start tag may be omitted when they are empty.
    """
    heading = one([node for node in root.elements("h5") if squash(text_of(node)) == "Optional tags"],
                  "Optional tags section")
    section: list[Node] = []
    for child in heading.siblings()[1]:
        if child.tag in ("h2", "h3", "h4", "h5"):
            break
        if child.tag == "p":
            section.append(child)
    marks = {"syntax-start-tag": "{start}", "syntax-end-tag": "{end}"}
    start: set[str] = set()
    end: set[str] = set()
    implied: dict[str, str] = {}
    when_empty: set[str] = set()
    for paragraph in section:
        sentence = rendered(paragraph, marks)
        if "may be omitted" not in sentence:
            continue
        rule = re.match(r"An? <([a-z0-9]+)> element's \{(start|end)\} may be omitted if ", sentence)
        if rule is None:
            message = f"an optional-tag paragraph no rule reads: {sentence[:120]!r}"
            raise ReadError(message)
        name, which = rule.groups()
        (start if which == "start" else end).add(name)
        condition = sentence[rule.end():]
        if which == "start" and condition.startswith("the element is empty"):
            when_empty.add(name)
        if which == "start" and (child := re.search(
                rf"the first thing inside the <{name}> element is an? <([a-z0-9]+)> element", condition)):
            implied[name] = child.group(1)
    return start, end, implied, when_empty


def sequences(root: Node) -> dict[str, list[str]]:
    """Each element whose Content model is a followed-by chain, read as that sequence.

    The chain reads "A x element followed by a y element".
    """
    found: dict[str, list[str]] = {}
    for dl in root.elements("dl"):
        if "element" not in dl.attrs.get("class", "").split():
            continue
        heading = next((child for child in reversed(dl.siblings()[0]) if child.tag in ("h3", "h4", "h5")), None)
        if heading is None:
            continue
        defined = [name for dfn in heading.elements("dfn") if "element" in dfn.attrs
                   for name in subjects(dfn.children)]
        for terms, definitions in pairs(dl):
            if not any(span.attrs.get("data-x") == "concept-element-content-model"
                       for term in terms for span in term.elements("span")):
                continue
            for definition in definitions:
                chain = re.fullmatch(r"(?:An?|One) <([a-z0-9]+)> element"
                                     r"((?: followed by (?:an?|one) <[a-z0-9]+> element)+)\.",
                                     rendered(definition, {}))
                if chain:
                    order = [chain.group(1), *re.findall(r"<([a-z0-9]+)>", chain.group(2))]
                    for name in defined:
                        found[name] = order
    return found


def notice_of(root: Node, build_license: str) -> str:
    """The Standard's copyright and licence notice, which html-build's LICENSE must open with too.

    The entity data comes from html-build, so its LICENSE must carry the notice.
    """
    notice = one([squash(text_of(paragraph)) for paragraph in root.elements("p")
                  if squash(text_of(paragraph)).startswith("Copyright © WHATWG")],
                 "copyright notice in the Standard")
    if "incorporated into source code" not in notice or "BSD 3-Clause License" not in notice:
        message = f"the Standard's notice no longer licenses portions in source code as BSD-3-Clause: {notice!r}"
        raise ReadError(message)
    stated = squash(" ".join(build_license.split("\n\n")[:2]))
    if stated != notice:
        message = f"html-build's LICENSE opens {stated!r}, not the Standard's notice {notice!r}"
        raise ReadError(message)
    return notice


def named_references(data: bytes) -> tuple[tuple[str, tuple[int, ...]], ...]:
    """Each named character reference and its code points.

    A legacy name without its semicolon must be a name with it, standing for the
    same code points.
    """
    rows = json.loads(data)
    named = {reference[1:-1]: tuple(row["codepoints"]) for reference, row in rows.items()
             if reference.startswith("&") and reference.endswith(";")}
    for reference, row in rows.items():
        if not reference.startswith("&"):
            message = f"entities.json names {reference!r}, which is not a reference"
            raise ReadError(message)
        if not reference.endswith(";") and named.get(reference[1:]) != tuple(row["codepoints"]):
            message = f"legacy reference {reference!r} has no {reference + ';'!r} twin standing for the same code points"
            raise ReadError(message)
    if bad := [name for name in named if not re.fullmatch(r"[A-Za-z][A-Za-z0-9]*", name)]:
        message = f"entities.json names {bad[:5]}, which are not SGML entity names"
        raise ReadError(message)
    return tuple(sorted(named.items()))


def entity_name(category: str) -> str:
    """A content category's parameter entity: its name without the last word, hyphenated.

    The last word is 'content' or 'elements'.
    """
    return "-".join(category.split()[:-1])


def read_standard(source: str, entities: bytes, build_license: str) -> Standard:
    """Everything the DTD declares, read from the pinned inputs."""
    root = parse(source)
    children, parents, foreign = elements_index(root)
    declared = set(children)
    members = categories_index(root, declared | foreign)
    kinds = syntax_kinds(root)
    states = tokenizer_states(root)
    start, end, implied, when_empty = omissions(root)
    ordered = sequences(root)
    void = kinds.get("void elements", set())
    template = kinds.get("the template element", set())
    for kind, content in (("raw text elements", "CDATA"), ("escapable raw text elements", "RCDATA")):
        if stray := {name for name in kinds.get(kind, set()) if states.get(name) != content}:
            message = f"{kind} {sorted(stray)} are not in a tokenizer state giving {content}"
            raise ReadError(message)
    for name in sorted(void | template | start | end | set(implied) | set(implied.values())
                       | set(ordered) | {name for chain in ordered.values() for name in chain}
                       | {name for name in states if name in declared or name in void}):
        if name not in declared:
            message = f"the syntax sections name {name!r}, which the element index does not"
            raise ReadError(message)
    normal = declared - void - template - {name for name in declared if states.get(name)}

    def expanded(name: str) -> set[str]:
        tokens: set[str] = set()
        for run in children[name]:
            if names := subjects(run):
                if unknown := set(names) - declared - foreign:
                    message = f"{name}'s children name {sorted(unknown)}, which the element index does not"
                    raise ReadError(message)
                tokens.update(names)
            elif (word := key(run)) in members:
                tokens |= members[word]
            elif word in TEXT:
                tokens.add(PCDATA)
            elif word in AS_FLOW:
                tokens |= members["flow content"]
            elif word != "empty":
                message = f"{name}'s children list {word!r}, which no rule reads"
                raise ReadError(message)
        tokens |= {other for other in declared if name in
                   {parent for run in parents[other] for parent in subjects(run)}}
        return tokens

    models = {name: expanded(name) for name in sorted(normal)}
    for implying, child in implied.items():
        for name, tokens in models.items():
            if name != implying and implying in tokens:
                tokens.discard(child)

    attributes: dict[str, dict[str, Attribute]] = {name: {} for name in declared}
    everywhere: dict[bool, dict[str, Attribute]] = {False: {}, True: {}}
    for name, on, shorthand, handler in attribute_rows(root):
        attribute = Attribute(name, shorthand)
        for target in ([None] if on is None else on):
            place = everywhere[handler] if target is None else attributes.get(target)
            if place is None:
                if target in foreign:
                    continue
                message = f"attribute {name!r} applies to {target!r}, which the element index does not name"
                raise ReadError(message)
            if place.get(name, attribute) != attribute:
                message = f"attribute {name!r} on {target or 'every element'} is declared two ways"
                raise ReadError(message)
            place[name] = attribute
    common = {**everywhere[False], **everywhere[True]}
    for name, own in attributes.items():
        for attribute_name, attribute in list(own.items()):
            if attribute_name in common:
                if common[attribute_name] != attribute:
                    message = f"{name}'s attribute {attribute_name!r} differs from the one every element has"
                    raise ReadError(message)
                del own[attribute_name]

    used = {word for name in normal for run in children[name]
            if (word := key(run)) in members and not subjects(run)} | {"flow content"}
    categories = tuple(sorted((entity_name(word), tuple(sorted(members[word], key=_token_order)))
                              for word in used))

    def content(name: str) -> str:
        if name in void:
            return "EMPTY"
        if name in template:
            return "ANY"
        if states.get(name):
            return states[name]
        if name in ordered:
            return sequence(ordered[name], when_empty)
        return model_group(models[name], categories)

    elements = tuple(Element(name, name in start, name in end or name in void, content(name),
                             tuple(sorted(attributes[name].values(), key=lambda row: row.name)))
                     for name in sorted(declared))
    globals_ = (("global", tuple(sorted(everywhere[False].values(), key=lambda row: row.name))),
                ("events", tuple(sorted(everywhere[True].values(), key=lambda row: row.name))))
    return Standard(elements, categories, globals_, named_references(entities), notice_of(root, build_license))


def _token_order(token: str) -> tuple[bool, str]:
    """#PCDATA first, then names in order: the form SGML writes mixed content in."""
    return (token != PCDATA, token)


def sequence(members: list[str], optional: set[str]) -> str:
    """MEMBERS in order, those in OPTIONAL optional, as a model group whose optional members open a choice.

    S(i) is (m, S(i+1)) for a required m and (S(i+1) | (m, S(i+1))) for an
    optional one, which is the same language with the longer suffix last, so SWI's
    omitted-tag search reaches every later member and tries the earlier one first.
    """
    # Time: 2^k groups for k optional members, which the MAXDECL check bounds.
    def suffix(index: int) -> str:
        if index == len(members):
            return ""
        member, rest = members[index], suffix(index + 1)
        if member not in optional:
            return f"({member}, {rest})" if rest else member
        if not rest:
            return f"{member}?"
        return f"({rest} | ({member}, {rest}))"

    model = suffix(0)
    return model if model.startswith("(") else f"({model})"


def model_group(tokens: set[str], categories: tuple[tuple[str, tuple[str, ...]], ...]) -> str:
    """TOKENS as a repeatable choice, covered by the largest category entities they still hold whole.

    The parameter entity carrying #PCDATA comes first, and an empty set admits
    character data.
    """
    if not tokens:
        return f"({PCDATA})"
    left = set(tokens)
    parts: list[str] = []
    for entity, members in sorted(categories, key=lambda row: (-len(row[1]), row[0])):
        if set(members) <= left:
            parts.append(f"%{entity};")
            left -= set(members)
    mixed = [part for part in parts if any(part == f"%{entity};" and PCDATA in members
                                           for entity, members in categories)]
    ordered = [*mixed, *(part for part in parts if part not in mixed), *sorted(left, key=_token_order)]
    return f"({' | '.join(ordered)})*"


# ------------------------------------------------------------------ the text


def comment(paragraphs: list[str]) -> str:
    """An SGML comment declaration holding PARAGRAPHS, each wrapped at 78 columns.

    SGML ends a comment at every '--', so a hyphen pair in the text is written
    '- -'.
    """
    body = "\n\n".join(textwrap.fill(paragraph.replace("--", "- -"), width=78, initial_indent="     ",
                                     subsequent_indent="     ", break_long_words=False,
                                     break_on_hyphens=False)
                       for paragraph in paragraphs)
    return "<!--\n" + body + "\n-->"


def _fits(standard: Standard, text: str) -> None:
    """Refuse a parameter entity or declaration SWI's parser would truncate."""
    entities = {name: " | ".join(members) for name, members in standard.categories}
    entities |= {name: "\n".join(attribute.declaration() for attribute in attributes)
                 for name, attributes in standard.globals}
    for name, value in entities.items():
        if len(value) >= MAXSTRINGLEN:
            message = f"parameter entity {name} is {len(value)} characters, over SWI's {MAXSTRINGLEN - 1}"
            raise ReadError(message)
    for declaration in re.findall(r"<!(?:ELEMENT|ATTLIST)[^>]*>", text):
        expanded = re.sub(r"%([A-Za-z][A-Za-z0-9-]*);", lambda match: entities[match.group(1)], declaration)
        if len(expanded) >= MAXDECL:
            message = f"{declaration[:40]!r} expands to {len(expanded)} characters, over SWI's {MAXDECL - 1}"
            raise ReadError(message)


def render(standard: Standard, bsd: str, notice: str) -> str:
    """The DTD text: header, references, categories, attributes, elements."""
    first, _, rest = bsd.partition("\n")
    if first.strip() != BSD_TEMPLATE:
        message = f"{BSD} opens {first.strip()!r}, not the template line {BSD_TEMPLATE!r}"
        raise ReadError(message)
    holder = standard.notice.split(". ", 1)[0] + "."
    header = comment([
        "HTML5.dtd: an SGML DTD for the text/html syntax of the WHATWG HTML Standard, read by "
        "SWI-Prolog's library(sgml) for the html5 dialect.",
        f"{notice} Edit the generator, never this file.",
        f"Derived from whatwg/html {STANDARD.commit}, source (blob {STANDARD.blob}), and "
        f"whatwg/html-build {ENTITIES.commit}, entities/out/entities.json (blob {ENTITIES.blob}).",
        standard.notice,
        "This file incorporates portions of the WHATWG HTML Standard into source code, so section "
        "7.1.1 of the WHATWG Intellectual Property Rights Policy (https://whatwg.org/ipr-policy) "
        "licenses it under the BSD 3-Clause License:",
        "SPDX-License-Identifier: BSD-3-Clause",
        holder, *(squash(paragraph) for paragraph in rest.strip().split("\n\n")),
    ])
    lines = [header, "", "<!-- Named character references (13.5) -->"]
    lines += [f'<!ENTITY {name} CDATA "{"".join(f"&#{point};" for point in points)}">'
              for name, points in standard.entities]
    lines += ["", "<!-- Content categories (3.2.5.2), members with exceptions included -->"]
    lines += [f'<!ENTITY % {entity} "{" | ".join(members)}">' for entity, members in standard.categories]
    for entity, attributes in standard.globals:
        lines += ["", f'<!-- Attributes of every HTML element: {entity} -->', f'<!ENTITY % {entity} "']
        lines += [f"    {attribute.declaration()}" for attribute in attributes]
        lines.append('    ">')
    lines += ["", "<!-- Elements, and the attributes each has beside those of every element -->"]
    for element in standard.elements:
        omission = f"{'O' if element.omit_start else '-'} {'O' if element.omit_end else '-'}"
        lines.append(f"<!ELEMENT {element.name} {omission} {element.content}>")
        if element.attributes:
            lines.append(f"<!ATTLIST {element.name}")
            lines += [f"    {attribute.declaration()}" for attribute in element.attributes]
            lines[-1] += ">"
    names = " | ".join(element.name for element in standard.elements)
    lines += ["", "<!-- The attributes of every HTML element, on each -->",
              f"<!ATTLIST ({names})",
              *(f"    %{entity};" for entity, _ in standard.globals)]
    lines[-1] += ">"
    text = "\n".join(lines) + "\n"
    _fits(standard, text)
    return text


def generate(clones: dict[Repository, Path]) -> str:
    """The DTD from the pins in CLONES."""
    source, entities, build_license = (read_pin(clones[pin.repository], pin) for pin in PINS)
    standard = read_standard(source.decode("utf-8"), entities, build_license.decode("utf-8"))
    return render(standard, (ROOT / BSD).read_text(encoding="utf-8"), artifacts.notice(OUTPUT))


def main(argv: list[str] | None = None) -> int:
    """Check the committed DTD against its pins, write it, or fetch the pins."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--write", action="store_true", help=f"write {OUTPUT}")
    action.add_argument("--fetch", action="store_true", help="fetch the pinned commits into their checkouts")
    arguments = parser.parse_args(argv)
    try:
        if arguments.fetch:
            print(f"html5-dtd: the pins are in {', '.join(map(str, fetch()))}")
            return 0
        places = {repository: candidates(repository) for repository in REPOSITORIES}
        clones = {repository: located(repository, found) for repository, found in places.items()}
        if absent := [(repository, places[repository]) for repository, clone in clones.items() if clone is None]:
            return prerequisite(absent)
        text = generate({repository: clone for repository, clone in clones.items() if clone is not None})
    except ReadError as error:
        print(f"html5-dtd: {error}", file=sys.stderr)
        return 1
    target = ROOT / OUTPUT
    if arguments.write:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        print(f"html5-dtd: wrote {OUTPUT} from {', '.join(str(clone) for clone in clones.values())}")
        return 0
    committed = target.read_text(encoding="utf-8") if target.exists() else ""
    if committed != text:
        drift = list(difflib.unified_diff(committed.splitlines(), text.splitlines(),
                                          f"{OUTPUT} (committed)", f"{OUTPUT} (generated)", lineterm="", n=1))
        print("\n".join(drift[:40]))
        print(f"html5-dtd: {OUTPUT} differs from what its pins generate; run html5dtd.py --write",
              file=sys.stderr)
        return 1
    print(f"html5-dtd: {OUTPUT} is what whatwg/html {STANDARD.commit[:12]} and html-build "
          f"{ENTITIES.commit[:12]} generate")
    return 0


if __name__ == "__main__":
    sys.exit(main())
