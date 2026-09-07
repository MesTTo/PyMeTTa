"""Purpose: read program text with holes into text and bindings.

The two things the engine needs are the text its own reader parses and the
name-to-value pairs the holes ride in on, and the three faces that produce
them are a 3.14 ``t"..."`` literal, a backport's template object, and a string
plus keyword values.

A hole IS a binding. ``bind(name=value)`` substitutes a symbol with a value
after the reader and before the run; a hole does the same by position, so the
door generates a symbol nothing else can name, splices it where the hole was,
and hands the pair to the mechanism that already exists. Nothing is rendered to
text: a ``str`` value stays a String atom and never has to be escaped.

The architecture is tdom's, which splices a generated placeholder per
interpolation, parses the assembled text with the real parser, and translates
positions back for its errors [source:
https://github.com/t-strings/tdom/blob/main/tdom/placeholders.py and
tdom/parser_utils.py at the repository's main branch, read 2026-09-06]. The
three format specs are psycopg 3.3's ``i``/``l``/``q`` under this library's own
names [source: https://www.psycopg.org/psycopg3/docs/basic/tstrings.html].

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
Fails when: the caller wants the template rendered to a string. It is not a
  formatter; ``format(...)`` and f-strings are Python's own answer for text.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from __future__ import annotations

import string as _string
from typing import TYPE_CHECKING, Any, NamedTuple

from ._atoms_core import Atom, Grounded, Symbol, encode
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
#: them, before the format spec. The result is a str and enters as a String.
_CONVERSIONS: dict[str, Callable[[Any], str]] = {"r": repr, "s": str, "a": ascii}

#: The three specs, each sugar for one atom constructor, which is the whole
#: marker vocabulary: there is no other.
_SPECS = ("sym", "expr", "py")

_ELLIPSIS_AT = 60


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
    unused = sorted(set(values) - assembly.used)
    if unused:
        msg = (
            f"{called} was given values the program text does not use: "
            f"{unused!r}. Every keyword names a {{field}} in the text."
        )
        raise TypeError(msg)
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


class _Assembly:
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
        "called",
        "reserved",
        "used",
    )

    def __init__(self, called: str, reserved: tuple[str, ...] = ()) -> None:
        self.called = called
        self._program: list[str] = []
        self._display: list[str] = []
        self._holes: list[_Hole] = []
        self._plen = 0
        self._dlen = 0
        self._dbase = 0
        #: The door's own keyword-only parameters, and the field names this
        #: call's text actually consumed, so a keyword nothing uses can be
        #: refused and a collision with a parameter can be named.
        self.reserved = reserved
        self.used: set[str] = set()

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
    template: TemplateLike, assembly: _Assembly, seen: tuple[int, ...]
) -> None:
    """The 3.14 literal and the backport, read structurally.

    ``seen`` carries the ids on the current nesting path, so a hand-built
    object holding itself refuses instead of recursing forever.
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
            assembly.literal(segment)
            continue
        interpolation = interpolations[index]
        shown = _written(
            interpolation.expression,
            interpolation.conversion,
            interpolation.format_spec,
        )
        label, kept = _debug_fold(segment, interpolation)
        assembly.literal(kept)
        if label is not None:
            shown = "{" + interpolation.expression + "=}"
            assembly.hole(encode(label), shown, shows=False)
            assembly.gap()
        _place(
            assembly,
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
    text: str, values: Mapping[str, Any], assembly: _Assembly
) -> None:
    """A plain string plus keyword values, split by ``string.Formatter``.

    ``{{`` and ``}}`` arrive already resolved in the literal chunks, and
    ``{a.b}`` and ``{a[0]}`` resolve exactly as ``str.format`` resolves them,
    because this IS ``str.format``'s parser.
    """
    formatter = _string.Formatter()
    for literal, field, spec, conversion in formatter.parse(text):
        assembly.literal(literal)
        if field is None:
            continue
        shown = _written(field, conversion, spec or "")
        if spec and "{" in spec:
            msg = (
                f"{assembly.called}: a nested format spec is not a hole spec: "
                f"{shown}. The specs are {', '.join(_SPECS)}."
            )
            raise ValueError(msg)
        value = _field_value(field, values, assembly)
        _place(assembly, value, conversion, spec or "", shown)


def _field_value(field: str, values: Mapping[str, Any], assembly: _Assembly) -> Any:
    """Resolve one field against the keywords, or refuse naming it."""
    called = assembly.called
    head = field.split(".", 1)[0].split("[", 1)[0]
    if head == "" or head.isdigit():
        msg = (
            f"{called}: a hole must be NAMED, and {{{field}}} is positional. "
            f"Write {{name}} and pass name=..., since a value here is a "
            f"binding and a binding has a name."
        )
        raise ValueError(msg)
    if head not in values:
        if head in assembly.reserved:
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
    assembly.used.add(head)
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
    assembly: _Assembly,
    value: Any,
    conversion: str | None,
    spec: str,
    shown: str,
    *,
    seen: tuple[int, ...] = (),
) -> None:
    """One hole's value into the assembly: spliced if text, bound otherwise.

    A NESTED template with neither a conversion nor a spec composes: its text
    becomes text and its holes become holes of this call. It is a literal the
    author wrote, so it carries no injection risk, which is the distinction
    psycopg draws between a composable statement snippet and a runtime string.
    With a conversion or a spec the author has said "treat this as a value",
    and it is one.
    """
    if conversion is None and not spec and is_template(value):
        _template_parts(value, assembly, seen)
        return
    assembly.hole(_atom(value, conversion, spec, shown), shown)


def _atom(value: Any, conversion: str | None, spec: str, shown: str) -> Atom:
    """The atom a hole's value becomes: conversion first, then the spec.

    Python's own order, and the specs are exactly the atom constructors:
    ``sym`` is ``Symbol``, ``expr`` is ``parse`` and ``py`` is ``Grounded``.
    With no spec the value takes ``encode``'s ladder, so an int is a Number, a
    str a String, an Atom itself, a Space its handle.
    """
    if conversion is not None:
        convert = _CONVERSIONS.get(conversion)
        if convert is None:
            msg = (
                f"unknown conversion {conversion!r} at {shown}: the "
                f"conversions are !r, !s and !a, as in an f-string"
            )
            raise ValueError(msg)
        value = convert(value)
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
    msg = (
        f"unknown hole spec {spec!r} at {shown}: the specs are sym (Symbol), "
        f"expr (parse) and py (Grounded). For Python formatting, format in "
        f"Python and pass the string, as in {{f'{{value:.2f}}'}}."
    )
    raise ValueError(msg)


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
