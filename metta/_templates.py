"""Purpose: read program text with holes into a program, or render it as text.

The two things the engine needs are the text its own reader parses and the
name-to-value pairs the holes ride in on, and the three faces that produce
them are a 3.14 ``t"..."`` literal, a backport's template object, and a string
plus keyword values.

A hole IS a binding. ``bind(name=value)`` substitutes a symbol with a value
after the reader and before the run; a hole does the same by position, so the
door generates a symbol nothing else can name, splices it where the hole was,
and hands the pair to the mechanism that already exists. Nothing is rendered to
text on that side: a ``str`` value stays a String atom and never has to be
escaped.

The OTHER direction is this module too. One template reads into a program and
renders into text, so a card, a reference page or a documentation section is a
template over a query rather than a program that prints. Both directions walk
the same three faces through the same code and part company at one method: a
hole's value becomes an atom at ``_Assembly`` and text at ``_Text``. The spec
vocabulary is ONE table, ``_SPECS``, whose rows carry the direction they work
in, so each door's refusal is derived from the other's rows and neither can
name a vocabulary the other has moved on from.

The architecture is tdom's, which splices a generated placeholder per
interpolation, parses the assembled text with the real parser, and translates
positions back for its errors [source:
https://github.com/t-strings/tdom/blob/main/tdom/placeholders.py and
tdom/parser_utils.py at the repository's main branch, read 2026-09-06]. The
three entry specs are psycopg 3.3's ``i``/``l``/``q`` under this library's own
names [source: https://www.psycopg.org/psycopg3/docs/basic/tstrings.html], and
rendering follows PEP 750's own loop, ``convert`` then ``format`` per
interpolation with the literal segments between [source:
https://docs.python.org/3.14/library/string.templatelib.html, ``convert``;
measured on 3.14.4 that the loop reproduces the f-string byte for byte,
``{x=}`` included].

A rendered hole is what the ENGINE puts at a ``format-args`` hole: a String's
characters, any other atom's MeTTa text [source: engine/metta/operators.pl,
metta_console_text/2, which is what upstream's formatArgsString interpolates].
``{v:sexp}`` is the other engine rendering, ``sdisplay/2``, which is what
``println!`` prints and ``repr`` answers, and which ``parse`` reads back.

Assumes:
  - ``BOUNDARY`` is the engine reader's token boundary set, Unicode
    White_Space plus ``(``, ``)`` and ``;`` [tested:
    test_the_boundary_table_matches_the_engines; commit=4481c32eb0e922047199c54cea97c24995c6959e]
  - a template's ``strings`` is one longer than its ``interpolations``, which
    PEP 750 guarantees and which a hand-built object is checked for [tested:
    test_a_malformed_template_object_is_refused; commit=4481c32eb0e922047199c54cea97c24995c6959e]
Guarantees:
  - a spliced hole name reads back as one symbol and can be substituted, since
    it is a token of no boundary character that is not a number, a string, a
    boolean or a variable [tested: test_the_reserved_hole_symbol_reads_as_itself;
    commit=4481c32eb0e922047199c54cea97c24995c6959e]
  - a hole that would not be its own token is refused with its line and column
    in the text the author wrote, separately for a string literal, a comment and
    a symbol [tested: test_a_hole_inside_a_string_literal_is_refused,
    test_a_hole_inside_a_comment_is_refused,
    test_a_hole_inside_a_symbol_is_refused; commit=4481c32eb0e922047199c54cea97c24995c6959e]
  - author text carrying the reserved prefix is refused, so a generated name
    cannot collide with one the program already uses [tested:
    test_program_text_may_not_spell_the_reserved_prefix; commit=4481c32eb0e922047199c54cea97c24995c6959e]
  - values enter through ``encode``, so an int is a Number, a str a String, an
    Atom itself and a Space its handle [tested:
    test_a_hole_enters_each_value_kind_through_encode; commit=4481c32eb0e922047199c54cea97c24995c6959e]
  - a rendered hole with no spec answers what the engine's own
    ``format-args`` puts at ``{}``, and ``{v:sexp}`` what ``repr`` answers
    [tested: test_a_rendered_hole_is_what_format_args_interpolates,
    test_the_sexp_spec_is_what_repr_answers; commit=adb831d29a48596d3068a3087115b216c18b5b38]
  - the 3.14 literal and the keyword face render the same bytes [tested:
    test_the_two_faces_render_identically; commit=adb831d29a48596d3068a3087115b216c18b5b38]
  - a spec belonging to the other direction refuses naming that direction, and
    an unknown one names this direction's specs [tested:
    test_a_render_spec_at_an_entry_hole_names_the_render_door,
    test_an_entry_spec_at_a_rendered_hole_names_the_reader,
    test_an_unknown_render_spec_names_the_render_specs; commit=adb831d29a48596d3068a3087115b216c18b5b38]
Fails when: the caller wants a loop. A template holds one level: PEP 750's
  grammar has no statement form, so ``{for row in rows}`` is a SyntaxError on
  the 3.14 face, and a literal's values are evaluated when the literal is,
  so no per-item binding could arrive later anyway. Iterate in Python and
  compose the pieces, which ``{parts:lines}`` and a nested template do.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from __future__ import annotations

import string as _string
from typing import TYPE_CHECKING, Any, NamedTuple

from ._atoms_core import Atom, Grounded, Symbol, decode, encode
from .errors import Remedy, refusing

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

    from ._api_types import InterpolationLike, TemplateLike

#: What the library splices at a hole. A program may not spell it: the doors
#: refuse author text containing this prefix and ``bind()`` refuses a key in
#: this namespace, which closes collision on both surfaces rather than making
#: it improbable. The shape follows ``metta.atoms.fresh``'s ``__metta_fresh_``,
#: the library's existing generated-name convention.
HOLE_PREFIX = "__metta_hole_"

# The engine reader's token boundary set: the Unicode White_Space property plus
# the three punctuation characters that end a token. Python's str.isspace() is a
# SUPERSET (it answers True for U+001C to U+001F, which are not White_Space), so
# the table is written out rather than derived from it
# [source: engine/parser.pl, metta_token_boundary/2].
_LAYOUT = frozenset(
    "\t\n\v\f\r \u0020\u0085\u00a0\u1680"
    "\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a"
    "\u2028\u2029\u202f\u205f\u3000"
)
BOUNDARY = _LAYOUT | frozenset("();")

#: The conversions PEP 750 records, applied here exactly as f-strings apply
#: them, before the format spec. The result is a str: it enters as a String on
#: the reading side and is the text itself on the rendering side, which is what
#: makes ``{v!r}`` in a rendered template the f-string's own bytes.
_CONVERSIONS: dict[str, Callable[[Any], str]] = {"r": repr, "s": str, "a": ascii}

#: The two directions a hole can work in: into a program, or into text.
ENTRY = "entry"
RENDER = "render"

#: THE spec table, both directions in one place. A reading spec is sugar for
#: one atom constructor and a rendering spec for one rendering the engine
#: already has; each row's gloss is what a refusal calls it, so adding a spec
#: to one direction puts it in the other's message without it being written
#: twice. There is no third vocabulary: Python's own presentation specs stay
#: Python's, applied to a RENDERED hole because a rendered hole is text.
_SPECS: dict[str, tuple[str, str]] = {
    "sym": (ENTRY, "Symbol"),
    "expr": (ENTRY, "parse"),
    "py": (ENTRY, "Grounded"),
    "sexp": (RENDER, "canonical MeTTa text"),
    "quoted": (RENDER, "a MeTTa string literal"),
    "json": (RENDER, "one line of JSON"),
    "table": (RENDER, "a Markdown table"),
    "lines": (RENDER, "one value per line"),
}

_ELLIPSIS_AT = 60


def _spec_list(direction: str) -> str:
    """One direction's specs, spelled the way a refusal names them."""
    named = [
        f"{name} ({gloss})"
        for name, (side, gloss) in _SPECS.items()
        if side == direction
    ]
    return ", ".join(named[:-1]) + " and " + named[-1]


def _spec_refusal(spec: str, shown: str, direction: str) -> ValueError:
    """Refuse a spec this direction does not know, from the one table.

    A spec of the OTHER direction is not unknown, it is misplaced, and the
    message says which door owns it. Anything else is unknown and names this
    direction's own specs.
    """
    known = _SPECS.get(spec)
    if known is not None:
        side, gloss = known
        if side == RENDER:
            wrong = (
                f"the {spec} spec renders a value as text ({gloss}), and this "
                f"hole enters a program"
            )
            # Named `door` rather than `remedy`: the refusal-remedy lane reads
            # the word `remedy` in a raise's footprint as a promise that the
            # repair is carried as DATA, and these sentences name a door rather
            # than a repair an editor could apply.
            door = (
                "metta.render() is the door that renders; render first and "
                "pass the answer as a value"
            )
        else:
            wrong = (
                f"the {spec} spec builds an atom ({gloss}), and this hole "
                f"renders text"
            )
            door = (
                "m.run() and its siblings are the doors that read a hole into "
                "a program"
            )
        msg = f"{wrong}: {shown}. The specs here are {_spec_list(direction)}. {door}."
        return ValueError(msg)
    if direction == ENTRY:
        tail = (
            "For Python formatting, format in Python and pass the string, as "
            "in {f'{value:.2f}'}."
        )
    else:
        tail = (
            "A Python format spec works here too, as in {value:.2f}, since a "
            "rendered hole is text."
        )
    msg = (
        f"unknown hole spec {spec!r} at {shown}: the specs are "
        f"{_spec_list(direction)}. {tail}"
    )
    return ValueError(msg)


def is_template(value: Any) -> bool:
    """Whether this object is program text with holes.

    Structural, never an isinstance against ``string.templatelib.Template``:
    that class does not exist below 3.14 and this library's floor is 3.12, so
    the 3.14 literal, ``tstrings-backport``'s object and a test double are one
    type here exactly because none of them is named.
    """
    if isinstance(value, (str, Atom)):
        return False
    return isinstance(getattr(value, "strings", None), tuple) and isinstance(
        getattr(value, "interpolations", None), tuple
    )


def read_source(
    source: Any,
    values: Mapping[str, Any],
    *,
    called: str,
    reserved: tuple[str, ...] = (),
) -> tuple[str, dict[str, Any] | None]:
    """One door's source text and the bindings its holes need.

    The text-only door: ``source`` must be a string or program text with
    holes, never an atom.
    """
    if isinstance(source, str) and not values:
        return source, None
    if not isinstance(source, str) and not is_template(source):
        msg = (
            f"{called} takes MeTTa source as a string, or as program text with "
            f"holes (a t-string, or a string with {{fields}} and keyword "
            f"values), got {source!r}"
        )
        raise TypeError(msg)
    targets, holes = read_targets((source,), values, called=called, reserved=reserved)
    # Both faces answer text for a text input, which the check above has
    # already established this is.
    return targets[0], holes


def read_targets(
    targets: tuple[Any, ...],
    values: Mapping[str, Any],
    *,
    called: str,
    reserved: tuple[str, ...] = (),
) -> tuple[tuple[Any, ...], dict[str, Any] | None]:
    """Every target of ONE call, rewritten, with one bindings map for the lot.

    A target that is neither a template nor a string with fields crosses
    unchanged, so an atom target and a plain string cost one isinstance. Holes
    are numbered across the whole call, which is what lets ``eval(a, b)`` and a
    nested template share one map without colliding.
    """
    if not values and not any(is_template(target) for target in targets):
        return targets, None
    assembly = _Assembly(called, reserved)
    out: list[Any] = []
    for target in targets:
        if is_template(target):
            if values:
                msg = (
                    f"{called} takes a hole's value from the template itself; "
                    f"keyword values apply to the string form, so pass one or "
                    f"the other, not {sorted(values)!r} beside a template"
                )
                raise TypeError(msg)
            start = assembly.begin()
            _template_parts(target, assembly, ())
            out.append(assembly.text_since(start))
        elif isinstance(target, str) and values:
            start = assembly.begin()
            _keyword_parts(target, values, assembly)
            out.append(assembly.text_since(start))
        else:
            out.append(target)
        assembly.separate()
    assembly.check_unused(values)
    assembly.check()
    return tuple(out), assembly.bindings()


def refuse_template(value: Any, called: str, remedy: str, fix: Remedy) -> None:
    """Refuse a template at a door that has nowhere to put its holes.

    ``remedy`` is the sentence the caller reads and ``fix`` is the same
    repair as data, which is what an editor offers.
    """
    if is_template(value):
        msg = f"{called} does not take program text with holes: {remedy}"
        raise refusing(TypeError(msg), remedy=fix)


# ------------------------------------------------------------------- assembly


class _Hole(NamedTuple):
    """A hole, placed: where it sits in both texts and how it was written.

    ``display_from`` is its own TARGET's origin in the author's text, so a
    refusal about the second target of ``eval(a, b)`` counts lines from that
    target's first line rather than from the first target's.
    """

    name: str
    atom: Atom
    shown: str
    display_from: int
    display_at: int
    program_at: int


class _Holes:
    """What both directions of one call share: the door, its keywords, its fields.

    A subclass says what a hole's value BECOMES, in ``value``, and what the
    literal text between holes becomes, in ``literal``. Everything else about
    reading the three faces is written once, above this line and below it.
    """

    __slots__ = ("called", "reserved", "used")

    #: Which half of ``_SPECS`` this sink's holes may spell. Declared without a
    #: value, so a sink that forgot to choose is an error rather than a silent
    #: direction.
    DIRECTION: str

    def __init__(self, called: str, reserved: tuple[str, ...] = ()) -> None:
        self.called = called
        #: The door's own keyword-only parameters, and the field names this
        #: call's text actually consumed, so a keyword nothing uses can be
        #: refused and a collision with a parameter can be named.
        self.reserved = reserved
        self.used: set[str] = set()

    def literal(self, text: str) -> None:
        """Author text, verbatim."""
        raise NotImplementedError

    def value(self, value: Any, conversion: str | None, spec: str, shown: str) -> None:
        """One hole's value, converted and specced, into whatever is built."""
        raise NotImplementedError

    def prefix(self, segment: str, interpolation: InterpolationLike) -> str:
        """Write the literal before a hole, answering how the hole was written.

        The base is the rendering reading: PEP 750 folds a debug form's ``x=``
        into the preceding segment, and writing the segment whole is exactly
        what makes ``render(t"{x=}")`` the f-string's own bytes. ``_Assembly``
        overrides it, because a program has atoms rather than text and the
        label has to become one of them.
        """
        self.literal(segment)
        return _written(
            interpolation.expression,
            interpolation.conversion,
            interpolation.format_spec,
        )

    def check_unused(
        self, values: Mapping[str, Any], implicit: frozenset[str] = frozenset()
    ) -> None:
        """Refuse a value the text never asked for, naming it.

        ``implicit`` is what the DOOR supplied rather than the caller, such as
        the receiver ``Rows.render`` binds: a template that does not mention it
        is an ordinary template, not a mistake.
        """
        unused = sorted(set(values) - self.used - implicit)
        if unused:
            msg = (
                f"{self.called} was given values the program text does not "
                f"use: {unused!r}. Every keyword names a {{field}} in the text."
            )
            raise TypeError(msg)


class _Assembly(_Holes):
    """The two texts under construction, the engine's and the author's.

    The engine's text carries the generated symbols and is what gets parsed;
    the author's carries ``{n}`` where each hole is and is what a refusal
    counts lines and columns in. Every hole records its offset in both, so a
    defect found in the parsed text is reported in the written one.
    """

    __slots__ = (
        "_dbase",
        "_display",
        "_dlen",
        "_holes",
        "_plen",
        "_program",
    )

    DIRECTION = ENTRY

    def __init__(self, called: str, reserved: tuple[str, ...] = ()) -> None:
        super().__init__(called, reserved)
        self._program: list[str] = []
        self._display: list[str] = []
        self._holes: list[_Hole] = []
        self._plen = 0
        self._dlen = 0
        self._dbase = 0

    def begin(self) -> int:
        """Start one target, answering its offset in the engine's text.

        It also records the target's own origin in the author's text, which is
        what a refusal counts its lines and columns from.
        """
        self._dbase = self._dlen
        return self._plen

    def text_since(self, start: int) -> str:
        """One target's own program text, taken while it is still the last."""
        return "".join(self._program)[start : self._plen]

    def separate(self) -> None:
        """End a target, so the next one's first token cannot touch this one's."""
        self._program.append("\n")
        self._plen += 1
        self._display.append("\n")
        self._dlen += 1

    def literal(self, text: str) -> None:
        """Author text, verbatim into the program and re-escaped for display."""
        if not text:
            return
        found = text.find(HOLE_PREFIX)
        if found >= 0:
            line, column = _line_column(
                "".join(self._display) + _escaped(text[:found]), self._dlen + found
            )
            msg = (
                f"{self.called}: program text may not spell the reserved hole "
                f"prefix {HOLE_PREFIX!r}, found at line {line}, column {column}. "
                f"The library splices its own symbols of that spelling at each "
                f"hole, so a program using the prefix could not be told apart "
                f"from one."
            )
            raise ValueError(msg)
        self._program.append(text)
        self._plen += len(text)
        shown = _escaped(text)
        self._display.append(shown)
        self._dlen += len(shown)

    def hole(self, atom: Atom, shown: str, *, shows: bool = True) -> None:
        """One value, as a generated symbol in the program text."""
        name = f"{HOLE_PREFIX}{len(self._holes)}"
        self._holes.append(
            _Hole(name, atom, shown, self._dbase, self._dlen, self._plen)
        )
        self._program.append(name)
        self._plen += len(name)
        if shows:
            self._display.append(shown)
            self._dlen += len(shown)

    def value(self, value: Any, conversion: str | None, spec: str, shown: str) -> None:
        """A hole's value as the atom it becomes, spliced in as a symbol."""
        self.hole(_atom(value, conversion, spec, shown), shown)

    def prefix(self, segment: str, interpolation: InterpolationLike) -> str:
        """The literal before a hole, with a folded debug label taken out of it.

        A program has atoms rather than text, so ``{x=}``'s label cannot stay
        glued to the value: it enters as its own String and the value follows,
        which is what makes ``!(log {x=})`` read ``(log "x=" "42")``.
        """
        label, kept = _debug_fold(segment, interpolation)
        self.literal(kept)
        shown = _written(
            interpolation.expression,
            interpolation.conversion,
            interpolation.format_spec,
        )
        if label is None:
            return shown
        shown = "{" + interpolation.expression + "=}"
        self.hole(encode(label), shown, shows=False)
        self.gap()
        return shown

    def gap(self) -> None:
        """A space the author did not write, between two holes of one fold."""
        self._program.append(" ")
        self._plen += 1

    def check(self) -> None:
        """Refuse every hole the engine's reader would not read as its own atom."""
        program = "".join(self._program)
        display = "".join(self._display)
        spans = _spans(program)
        starts = [span[0] for span in spans]
        for hole in self._holes:
            index = _preceding(starts, hole.program_at)
            start, end, kind = spans[index]
            before = display[hole.display_from : hole.display_at]
            line, column = _line_column(before, len(before))
            where = f"{hole.shown} at line {line}, column {column}"
            if kind == "comment":
                msg = (
                    f"{self.called}: a hole cannot sit inside a ; comment: "
                    f"{where} would be read as comment text and discarded, so "
                    f"its value would never reach the program."
                )
                raise ValueError(msg)
            if kind == "string":
                msg = (
                    f"{self.called}: a hole cannot sit inside a string "
                    f"literal: {where} is inside "
                    f"{_shown(program[start:end], self._holes)}. A string is "
                    f"one value, so bind the whole string and let it enter as "
                    f"a String atom, which is what a Python str does."
                )
                raise ValueError(msg)
            if (start, end) != (hole.program_at, hole.program_at + len(hole.name)):
                msg = (
                    f"{self.called}: a hole cannot sit inside a symbol: "
                    f"{where} is part of "
                    f"{_shown(program[start:end], self._holes)}. Separate it "
                    f"with a space, or build the whole symbol at the hole with "
                    f"{{Symbol(...)}} or {{name:sym}}."
                )
                raise ValueError(msg)

    def bindings(self) -> dict[str, Any] | None:
        """The name-to-atom map, or None when the call held no hole."""
        return {hole.name: hole.atom for hole in self._holes} or None


def _escaped(text: str) -> str:
    """Author text back in its written form, where a brace was doubled."""
    return text.replace("{", "{{").replace("}", "}}")


def _line_column(text: str, offset: int) -> tuple[int, int]:
    """The 1-based line and column of an offset."""
    head = text[:offset]
    return head.count("\n") + 1, offset - head.rfind("\n")


def _preceding(starts: list[int], offset: int) -> int:
    """The index of the last span starting at or before an offset.

    A hole's name begins with ``_``, which ends no token, so a span always
    starts at or before it and this never answers -1 for a caller obeying that
    invariant. If one ever did, ``spans[-1]`` would be some other token and the
    hole would be refused as not being its own, which fails safe rather than
    admitting a hole nobody checked.
    """
    low, high = 0, len(starts)
    while low < high:
        middle = (low + high) // 2
        if starts[middle] <= offset:
            low = middle + 1
        else:
            high = middle
    return low - 1


def _shown(fragment: str, holes: list[_Hole]) -> str:
    """A fragment of the engine's text with each hole back in written form."""
    for hole in holes:
        fragment = fragment.replace(hole.name, hole.shown)
    if len(fragment) > _ELLIPSIS_AT:
        fragment = fragment[:_ELLIPSIS_AT] + "..."
    return f"`{fragment}`"


def _spans(text: str) -> list[tuple[int, int, str]]:
    r"""Every token, string and comment in the text, as the engine reads them.

    The reader's own grammar, restated: layout is skipped, ``;`` opens a
    comment that ends at ``\n`` and at nothing else, a ``"`` AT A TOKEN START
    commits to the quoted scanner where a backslash escapes the next character,
    and any other run of non-boundary characters is one token
    [source: engine/parser.pl, metta_layout//0, reader_token_text//1 and
    token//1]. A ``"`` in the middle of a token is an ordinary symbol
    character, which is why the scan tracks token starts rather than testing
    the previous character.
    """
    out: list[tuple[int, int, str]] = []
    index, length = 0, len(text)
    while index < length:
        char = text[index]
        if char in _LAYOUT or char in "()":
            index += 1
        elif char == ";":
            newline = text.find("\n", index)
            end = length if newline < 0 else newline + 1
            out.append((index, end, "comment"))
            index = end
        elif char == '"':
            scan = index + 1
            while scan < length and text[scan] != '"':
                scan += 2 if text[scan] == "\\" else 1
            end = min(scan + 1, length)
            out.append((index, end, "string"))
            index = end
        else:
            scan = index
            while scan < length and text[scan] not in BOUNDARY:
                scan += 1
            out.append((index, scan, "token"))
            index = scan
    return out


# ---------------------------------------------------------------- the faces


def _template_parts(
    template: TemplateLike, sink: _Holes, seen: tuple[int, ...]
) -> None:
    """The 3.14 literal and the backport, read structurally.

    ``seen`` carries the ids on the current nesting path, so a hand-built
    object holding itself refuses instead of recursing forever. This is PEP
    750's own rendering loop, segment then interpolation, with the sink
    deciding what an interpolation becomes.
    """
    if id(template) in seen:
        msg = "a template cannot contain itself"
        raise ValueError(msg)
    strings, interpolations = template.strings, template.interpolations
    if len(strings) != len(interpolations) + 1:
        msg = (
            f"a template's strings must be one longer than its "
            f"interpolations, got {len(strings)} and {len(interpolations)}"
        )
        raise ValueError(msg)
    for index, segment in enumerate(strings):
        if index >= len(interpolations):
            sink.literal(segment)
            continue
        interpolation = interpolations[index]
        shown = sink.prefix(segment, interpolation)
        _place(
            sink,
            interpolation.value,
            interpolation.conversion,
            interpolation.format_spec,
            shown,
            seen=(*seen, id(template)),
        )


def _debug_fold(
    segment: str, interpolation: InterpolationLike
) -> tuple[str | None, str]:
    """Split a folded ``{x=}`` label off the segment before it, if there is one.

    PEP 750 appends the source text up to and including the ``=`` to the
    PRECEDING segment and sets the conversion to ``r``. Measured on 3.14.4:
    ``t"!(log {x=})"`` has strings ``('!(log x=', ')')`` with expression ``x``,
    and ``t"{x = }"`` keeps the author's spacing in the fold while the
    expression stays ``x``. Left alone the label would be glued to the hole and
    every debug form would be refused as inside a symbol, which is a useless
    answer to a form written on purpose.

    The discriminator is the conversion plus a whole token: the segment must
    end in the interpolation's own expression followed by ``=``, and that
    expression must itself start the token. So ``t"!(f x={v!r})"`` is not a
    fold (the expression is ``v``, the tail is ``x=``) and neither is
    ``t"!(fix={x!r})"`` (``x`` sits inside ``fix``). A hand-written
    ``t"!(f v={v!r})"`` IS indistinguishable from ``t"!(f {v=})"`` in the
    Template, by PEP 750's design, and gets the same reading.
    """
    if interpolation.conversion != "r" or interpolation.format_spec:
        return None, segment
    body = segment.rstrip()
    if not body.endswith("="):
        return None, segment
    body = body[:-1].rstrip()
    expression = interpolation.expression
    if not expression or not body.endswith(expression):
        return None, segment
    at = len(body) - len(expression)
    if at > 0 and body[at - 1] not in BOUNDARY:
        return None, segment
    return segment[at:].rstrip(), segment[:at]


def _keyword_parts(
    text: str, values: Mapping[str, Any], sink: _Holes
) -> None:
    """A plain string plus keyword values, split by ``string.Formatter``.

    ``{{`` and ``}}`` arrive already resolved in the literal chunks, and
    ``{a.b}`` and ``{a[0]}`` resolve exactly as ``str.format`` resolves them,
    because this IS ``str.format``'s parser.
    """
    formatter = _string.Formatter()
    for literal, field, spec, conversion in formatter.parse(text):
        sink.literal(literal)
        if field is None:
            continue
        shown = _written(field, conversion, spec or "")
        if spec and "{" in spec:
            msg = (
                f"{sink.called}: a nested format spec is not a hole spec: "
                f"{shown}. The specs are {_spec_list(sink.DIRECTION)}."
            )
            raise ValueError(msg)
        value = _field_value(field, values, sink)
        _place(sink, value, conversion, spec or "", shown)


def _field_value(field: str, values: Mapping[str, Any], sink: _Holes) -> Any:
    """Resolve one field against the keywords, or refuse naming it."""
    called = sink.called
    head = field.split(".", 1)[0].split("[", 1)[0]
    if head == "" or head.isdigit():
        msg = (
            f"{called}: a hole must be NAMED, and {{{field}}} is positional. "
            f"Write {{name}} and pass name=..., since a value here is a "
            f"binding and a binding has a name."
        )
        raise ValueError(msg)
    if head not in values:
        if head in sink.reserved:
            msg = (
                f"{called}: the field {{{field}}} cannot take a keyword value, "
                f"because {called} takes {head}= as its own argument. Write the "
                f"program as a t-string, where there are no keywords to collide "
                f"with, or rename the field."
            )
            raise ValueError(msg)
        msg = (
            f"{called}: no value for the field {{{field}}}; pass {head}=... "
            f"beside the program text."
        )
        raise ValueError(msg)
    try:
        value, _ = _string.Formatter().get_field(field, (), values)
    except (AttributeError, IndexError, KeyError, TypeError) as exc:
        msg = f"{called}: the field {{{field}}} does not resolve: {exc}"
        raise ValueError(msg) from exc
    sink.used.add(head)
    return value


def _written(expression: str, conversion: str | None, spec: str) -> str:
    """A hole back in the form the author wrote it, for a refusal to name."""
    return (
        "{"
        + expression
        + (f"!{conversion}" if conversion else "")
        + (f":{spec}" if spec else "")
        + "}"
    )


def _place(
    sink: _Holes,
    value: Any,
    conversion: str | None,
    spec: str,
    shown: str,
    *,
    seen: tuple[int, ...] = (),
) -> None:
    """One hole's value into whatever is being built, in either direction.

    A NESTED template with neither a conversion nor a spec composes: reading,
    its text becomes text and its holes become holes of this call; rendering,
    it renders into this text. It is a literal the author wrote, so it carries
    no injection risk, which is the distinction psycopg draws between a
    composable statement snippet and a runtime string. With a conversion or a
    spec the author has said "treat this as a value", and it is one.
    """
    if conversion is None and not spec and is_template(value):
        _template_parts(value, sink, seen)
        return
    sink.value(value, conversion, spec, shown)


def _atom(value: Any, conversion: str | None, spec: str, shown: str) -> Atom:
    """The atom a hole's value becomes: conversion first, then the spec.

    Python's own order, and the specs are exactly the atom constructors:
    ``sym`` is ``Symbol``, ``expr`` is ``parse`` and ``py`` is ``Grounded``.
    With no spec the value takes ``encode``'s ladder, so an int is a Number, a
    str a String, an Atom itself, a Space its handle.
    """
    value = _converted(value, conversion, shown)
    if not spec:
        return encode(value)
    if spec == "py":
        return Grounded(value)
    if spec in ("sym", "expr"):
        if not isinstance(value, str):
            msg = (
                f"the {spec} spec takes a str, and {shown} has "
                f"{type(value).__name__}. Drop the spec to let the value enter "
                f"through encode, or convert it first with !s."
            )
            raise TypeError(msg)
        if spec == "sym":
            return Symbol(value)
        # Deferred because metta.atoms carries this door's own face, so
        # importing it here at module scope would be an import cycle.
        from .atoms import parse  # noqa: PLC0415

        return parse(value)
    raise _spec_refusal(spec, shown, ENTRY)


def _converted(value: Any, conversion: str | None, shown: str) -> Any:
    """PEP 750's conversion, applied before the spec in both directions.

    ``string.templatelib.convert``'s own three cases, written out because the
    module they live in does not exist below 3.14 and this library's floor is
    3.12 [source: https://docs.python.org/3.14/library/string.templatelib.html].
    """
    if conversion is None:
        return value
    convert = _CONVERSIONS.get(conversion)
    if convert is None:
        msg = (
            f"unknown conversion {conversion!r} at {shown}: the "
            f"conversions are !r, !s and !a, as in an f-string"
        )
        raise ValueError(msg)
    return convert(value)


# ------------------------------------------------------------------ rendering


class _Text(_Holes):
    """The other sink: a hole's value becomes text instead of an atom."""

    __slots__ = ("_parts",)

    DIRECTION = RENDER

    def __init__(self, called: str, reserved: tuple[str, ...] = ()) -> None:
        super().__init__(called, reserved)
        self._parts: list[str] = []

    def literal(self, text: str) -> None:
        """Author text, verbatim: nothing is spliced, so nothing is reserved."""
        self._parts.append(text)

    def value(self, value: Any, conversion: str | None, spec: str, shown: str) -> None:
        """A hole's value as the text it renders to."""
        self._parts.append(_text(_converted(value, conversion, shown), spec, shown))

    def text(self) -> str:
        """Everything written so far, as one string."""
        return "".join(self._parts)


def render(source: Any, /, **values: Any) -> str:
    """Program text with holes, rendered to finished text.

    The same three faces the reading doors take, answering a ``str`` instead
    of running anything: a 3.14 ``t"..."`` literal, any object with ``strings``
    and ``interpolations``, or a string with ``{fields}`` and keyword values.

    A hole with no spec renders the way the engine's own ``format-args``
    renders one, so a String is its characters and any other atom its MeTTa
    text; ``{v:sexp}`` is what ``repr`` answers and ``parse`` reads back,
    ``{v:quoted}`` a MeTTa string literal, ``{v:json}`` one line of JSON,
    ``{rows:table}`` a Markdown table and ``{rows:lines}`` one value per line.
    Any other spec is Python's own, applied to the value, because a rendered
    hole is text: ``{n:.2f}`` and ``{name:<20}`` mean here what they mean in an
    f-string.

    The longhand is the rung below: ``str(atom)`` for one atom's text,
    ``rows.table()`` for the columns, ``metta._json.dumps`` for the JSON.
    """
    return render_with(source, values, called="render", implicit=frozenset())


def render_with(
    source: Any,
    values: Mapping[str, Any],
    *,
    called: str,
    implicit: frozenset[str],
) -> str:
    """``render``, with the values as a map and the door's own ones named.

    ``implicit`` is what the DOOR supplied rather than the caller, which is
    the receiver ``Rows.render`` binds as ``rows``: it is exempt from the
    unused-value refusal, and passing anything ELSE beside a template is
    refused here exactly as it is at ``render``.
    """
    given = sorted(set(values) - implicit)
    sink = _Text(called)
    if is_template(source):
        if given:
            msg = (
                f"{called} takes a hole's value from the template itself; "
                f"keyword values apply to the string form, so pass one or the "
                f"other, not {given!r} beside a template"
            )
            raise TypeError(msg)
        _template_parts(source, sink, ())
    elif isinstance(source, str):
        if not values:
            # The keyword face engages only with values, exactly as it does at
            # the reading doors: text holding a brace renders as itself. A
            # method face always has one, its receiver, so its text is always
            # read as fields.
            return source
        _keyword_parts(source, values, sink)
    else:
        msg = (
            f"{called} takes text, or program text with holes (a t-string, or "
            f"a string with {{fields}} and keyword values), got {source!r}. "
            f"One atom's text is str(atom) or format(atom, 'sexp')."
        )
        raise TypeError(msg)
    sink.check_unused(values, implicit)
    return sink.text()


def renders(spec: str) -> bool:
    """Whether this spec is one of the rendering table's own."""
    known = _SPECS.get(spec)
    return known is not None and known[0] == RENDER


def formatted(value: Any, spec: str, python: Any) -> str:
    """``__format__`` for a type this library owns: the table, then Python's.

    Three rules, in order. An EMPTY spec is ``str(value)``, which is Python's
    own law for ``format``. A spec from the rendering table is that rendering,
    so ``f"{rows:table}"`` needs no import and cannot drift from
    ``render(t"{rows:table}")``. Anything else is Python's presentation
    grammar, applied to ``python``: the value itself where the type has one
    Python spelling (a Grounded number), its text otherwise, which is where
    fill, alignment, width and precision act.
    """
    if not spec:
        return str(value)
    if renders(spec):
        return _text(value, spec, f"format({type(value).__name__}, {spec!r})")
    if spec in _SPECS:
        raise _spec_refusal(spec, f"format({type(value).__name__}, {spec!r})", RENDER)
    return format(python, spec)


def _text(value: Any, spec: str, shown: str) -> str:
    """The text a hole's value renders to under one spec.

    Unknown here means "not this library's", not "wrong": a rendered hole is
    text, so the spec falls through to the VALUE's own ``__format__`` and
    Python's presentation grammar works unchanged. Only a spec Python refuses
    too is refused, and it is refused naming this direction's specs.
    """
    if not spec:
        return _console(value)
    if spec == "sexp":
        return str(_atom_of(value))
    if spec == "quoted":
        return str(Grounded(_console(value)))
    if spec == "json":
        return _json_text(value)
    if spec == "table":
        return _table_text(value, shown)
    if spec == "lines":
        return _lines_text(value, shown)
    if spec in _SPECS:
        raise _spec_refusal(spec, shown, RENDER)
    try:
        return format(value, spec)
    except (TypeError, ValueError) as exc:
        raise _spec_refusal(spec, shown, RENDER) from exc


def _atom_of(value: Any) -> Atom:
    """The atom behind a rendered value, which is ``encode``'s ladder again."""
    return value if isinstance(value, Atom) else encode(value)


def _console(value: Any) -> str:
    """One value's text, which is what the engine interpolates at a ``{}``.

    ``metta_console_text/2``: a String is its own characters and any other
    atom is its MeTTa text [source: engine/metta/operators.pl, and upstream's
    formatArgsString that it follows]. A Python ``str`` is text already and is
    itself; anything else crosses through ``encode`` first, so a value with a
    MeTTa reading renders in MeTTa's spelling rather than Python's.

    This is why a bare hole differs from ``format(atom, "")``: Python's law
    makes the empty spec ``str(atom)``, the quoted literal, while a hole in a
    template is the engine's ``{}``, the characters.
    """
    if isinstance(value, str):
        return value
    atom = _atom_of(value)
    inner = getattr(atom, "value", None)
    return inner if isinstance(inner, str) else str(atom)


def _json_text(value: Any) -> str:
    """One line of JSON, through the engine's codec and nothing else.

    Atoms are not JSON values, so each one takes the reading ``to_dicts`` and
    ``table`` already take: a grounded value decodes and any other atom
    becomes its text. Containers are walked, because a dict of atoms is the
    shape a rendered payload arrives in.
    """
    from ._json import dumps  # noqa: PLC0415  -- the codec boots the engine

    return dumps(_json_value(value)).decode("utf-8")


def _json_value(value: Any) -> Any:
    """A value in JSON's own vocabulary, atoms and query results included."""
    if _is_table(value):
        return value.to_dicts()
    if isinstance(value, Atom):
        plain = decode(value)
        return str(plain) if isinstance(plain, Atom) else plain
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    return value


def _is_table(value: Any) -> bool:
    """Whether this value is a query result: named columns and plain records.

    Structural, the way a template is: ``Rows`` and ``Answers`` answer True
    here, and so would any other projection that grows the same two doors,
    without this module importing the one that has them today.
    """
    return callable(getattr(value, "to_dicts", None)) and isinstance(
        getattr(value, "columns", None), (tuple, list)
    )


def _table_text(value: Any, shown: str) -> str:
    """A query result as a GitHub-flavoured Markdown pipe table.

    The columns are the query's own variable names and each cell is the plain
    value ``to_dicts`` answers, rendered as any other hole would be. Every row
    the result holds is written: the display protocols bound themselves at
    ``config.display_rows`` because a terminal is not a document, and a
    document asked for these rows.

    A cell escapes a backslash and then a pipe, and a newline becomes ``<br>``,
    because a pipe table row is one line and a literal ``|`` would open a
    column [source: https://github.github.com/gfm, example 200: "Include a pipe
    in a cell's content by escaping it, including inside other inline spans"].
    """
    if not _is_table(value):
        msg = (
            f"the table spec renders a query result, one with named columns "
            f"and rows, and {shown} has {type(value).__name__}. m.match(...) "
            f"and m.answers(...) answer one; a list of values is {{v:lines}}."
        )
        raise TypeError(msg)
    columns = [str(name) for name in value.columns]
    records = value.to_dicts()
    lines = [
        "| " + " | ".join(_cell(name) for name in columns) + " |",
        "|" + "|".join("---" for _ in columns) + "|",
    ]
    lines += [
        "| " + " | ".join(_cell(record[name]) for name in columns) + " |"
        for record in records
    ]
    return "\n".join(lines)


def _cell(value: Any) -> str:
    """One table cell: the value's text, with the table's own syntax escaped."""
    text = _console(value)
    return (
        text.replace("\\", "\\\\").replace("|", "\\|").replace("\n", "<br>")
    )


def _lines_text(value: Any, shown: str) -> str:
    """One value per line, each rendered as a bare hole renders it.

    A nested template renders here too, which is what makes iteration a Python
    comprehension over templates rather than a loop the grammar cannot spell:
    ``render(t"{parts:lines}", ...)`` with ``parts`` a list of templates is the
    one-level composition PEP 750 leaves room for.
    """
    if isinstance(value, (str, bytes, bytearray)):
        msg = (
            f"the lines spec renders one value per line and {shown} is "
            f"{type(value).__name__}, which is ONE value. Drop the spec to "
            f"render the text itself, or pass a list of values."
        )
        raise TypeError(msg)
    try:
        items = list(value)
    except TypeError as exc:
        msg = (
            f"the lines spec renders one value per line and {shown} has "
            f"{type(value).__name__}, which is not iterable: {exc}"
        )
        raise TypeError(msg) from exc
    return "\n".join(
        render(item) if is_template(item) else _console(item) for item in items
    )


def apply(atom: Atom, holes: Mapping[str, Atom]) -> Atom:
    """Put a call's holes into a term, for the doors with no binding channel.

    ``match`` opens a cursor and ``parse`` runs nothing, so neither has a place
    to send the engine a binding pair; the value goes into the term instead.
    The values are ALREADY atoms, which is what makes this agree with the
    engine path exactly: a ``str`` here would have to choose between reading as
    MeTTa text and entering as a String, and ``encode`` has already chosen.
    """
    return atom.map(
        lambda item: (
            holes[item.name]
            if isinstance(item, Symbol) and item.name in holes
            else item
        )
    )
