"""Purpose: pin program text with holes at every door and in every face.

Every refusal is pinned by the words it uses, since a message naming the hole
and its position is most of what the feature buys.

The suite splits by what the running interpreter can PARSE, not by what it can
run: a ``t"..."`` literal is a SyntaxError below 3.14, so the literals live in
``template_literals_314.py`` and are imported inside a version guard. The
keyword face and a hand-built template object exercise the same door on every
supported version, which is the point of accepting the shape structurally.

Guarantees:
  - the reader's boundary table and this library's copy of it cannot drift
    [tested: test_the_boundary_table_matches_the_engines; commit=4481c32eb0e922047199c54cea97c24995c6959e]
  - a hole and a binding of the same value answer identically, and a binding
    reaches occurrences a hole cannot [tested: test_a_hole_and_a_binding_answer_the_same,
    test_a_binding_reaches_every_occurrence_where_a_hole_reaches_one;
    commit=4481c32eb0e922047199c54cea97c24995c6959e]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from __future__ import annotations

import sys
from typing import Any

import pytest

from metta import Grounded, S, Symbol, V
from metta._templates import BOUNDARY, HOLE_PREFIX
from metta.atoms import parse

needs_314 = pytest.mark.skipif(
    sys.version_info < (3, 14), reason="t-string literals are 3.14 syntax"
)

if sys.version_info >= (3, 14):
    from . import template_literals_314 as lit
else:  # pragma: no cover -- the module is 3.14 syntax and cannot be parsed here
    lit = None


class Interp:
    """One interpolation, as a backport or any other producer would give it."""

    def __init__(
        self,
        value: Any,
        expression: str = "value",
        conversion: str | None = None,
        format_spec: str = "",
    ) -> None:
        """PEP 750's four fields, with the two optional ones defaulted."""
        self.value = value
        self.expression = expression
        self.conversion = conversion
        self.format_spec = format_spec


class Tpl:
    """Program text with holes, built without the 3.14 compiler.

    This is what ``tstrings-backport``'s ``t("...")`` answers and what the
    doors accept: two tuples and nothing else. Nothing here is an instance of
    ``string.templatelib.Template``, which is the whole point.
    """

    def __init__(self, strings: tuple[str, ...], interpolations: tuple[Any, ...]) -> None:
        """The two tuples, which is the whole of the structural contract."""
        self.strings = strings
        self.interpolations = interpolations

    def __repr__(self) -> str:
        """A stable spelling, so converting a template with !r is testable."""
        return "<template>"


# --------------------------------------------------------------- the mechanism


def test_the_boundary_table_matches_the_engines(metta):
    """The reader says where a token ends; this library keeps a copy of it.

    A copy can drift, so it is compared against the engine's own table rather
    than trusted. Python's ``str.isspace`` is not the same set (it answers True
    for U+001C to U+001F), which is why the table is written out at all.
    """
    row = metta.runtime.must(
        "findall(_C, parser:metta_token_boundary(_C, _K), _Cs), atom_codes(Text, _Cs)"
    )
    assert set(str(row["Text"])) == set(BOUNDARY)
    assert not {"\x1c", "\x1d", "\x1e", "\x1f"} & set(BOUNDARY)


def test_the_reserved_hole_symbol_reads_as_itself(metta):
    """The spliced spelling is one symbol to the reader, and the door works.

    The reader makes a symbol of any token that holds no boundary character
    and is not a number, a string, a boolean or a variable. The spelling is
    checked against all four, and then the round trip is run: a value reaches
    the program through a spliced symbol of exactly this shape.
    """
    name = f"{HOLE_PREFIX}0"
    assert parse(f"(f {name})").children[1] == Symbol(name)
    assert not set(name) & set(BOUNDARY)
    assert not name.startswith(("$", '"'))
    assert metta.run("!(+ {n} 1)", n=41) == [[Grounded(42)]]


def test_program_text_may_not_spell_the_reserved_prefix(metta):
    """Author text carrying the prefix could not be told from a hole."""
    with pytest.raises(ValueError, match="reserved hole prefix"):
        metta.run("!(id __metta_hole_0 {n})", n=1)


def test_bind_refuses_the_reserved_hole_namespace(metta):
    """The other half of the same closure: a name, not only text."""
    with pytest.raises(ValueError, match="cannot be bound"):
        metta.bind(__metta_hole_7=1)


def test_a_malformed_template_object_is_refused(metta):
    """The two tuples must interleave.

    PEP 750 guarantees it; a hand-built object might not.
    """
    with pytest.raises(ValueError, match="one longer than its interpolations"):
        metta.run(Tpl(("a", "b", "c"), ()))


def test_a_template_cannot_contain_itself(metta):
    """A hand-built object may cycle where a literal cannot."""
    inner = Tpl(("(", ")"), ())
    inner.interpolations = (Interp(inner),)
    with pytest.raises(ValueError, match="cannot contain itself"):
        metta.run(inner)


# ------------------------------------------------------------------ the faces


def test_a_hand_built_template_object_reaches_the_same_door(metta):
    """The backport's shape is accepted structurally, on every version."""
    assert metta.run(Tpl(("!(+ ", " 1)"), (Interp(41),))) == [[Grounded(42)]]


def test_the_template_protocols_are_public_through_metta_atoms():
    """The two protocols are `metta.atoms`' surface, not the package root's.

    They name the type of the first argument of eight doors, so they have to
    be reachable; the root is held to a narrow-core count and a hole's markers
    are the atom constructors this module already exports, so `metta.atoms` is
    where they land. `_api_types` DEFINES them and publishes nothing.
    """
    import metta
    from metta import _api_types, atoms

    assert {"TemplateLike", "InterpolationLike"} <= set(atoms.__all__)
    assert atoms.TemplateLike is _api_types.TemplateLike
    assert atoms.InterpolationLike is _api_types.InterpolationLike
    assert _api_types.__all__ == []
    for name in ("TemplateLike", "InterpolationLike"):
        assert name not in metta.__all__
        with pytest.raises(AttributeError):
            getattr(metta, name)


def test_the_keyword_face_binds_by_name_on_every_version(metta):
    """The face that needs no new syntax at all."""
    assert metta.run("!(+ {n} 1)", n=41) == [[Grounded(42)]]
    assert metta.eval("(+ {n} 1)", n=41) == [Grounded(42)]


def test_the_keyword_face_keeps_doubled_braces_as_one_brace(metta):
    """The escaped braces survive as one brace each.

    ``{{`` and ``}}`` are str.format's escapes, and MeTTa reads a brace as an
    ordinary symbol character, so the escaped form has to arrive as one.
    """
    assert metta.run("!(pair {{braced}} {n})", n=1) == [[S.pair(S["{braced}"], 1)]]
    # Without values the face does not engage and the text is the program
    # verbatim, exactly as "{{x}}" is itself until str.format is called.
    assert metta.run("!(id {{braced}})") == [[S["{{braced}}"]]]


def test_the_keyword_face_resolves_attribute_and_index_fields(metta):
    """Attribute and index fields resolve as str.format resolves them.

    They have to: this IS str.format's own parser.
    """
    assert metta.eval("(+ {row[0]} {point.imag})", row=[40, 9], point=complex(0, 2)) == [
        Grounded(42.0)
    ]


@needs_314
def test_a_literal_template_binds_an_int(metta):
    """The 3.14 face, on the door the design is named for."""
    assert metta.run(lit.fib_of(41)) == [[Grounded(42)]]


@needs_314
def test_a_string_value_enters_as_one_string_atom(metta):
    """A str is a String, never re-read as text.

    Proven by MATCHING rather than by printing: a name holding a space would
    read as two symbols if the template were rendered, so a pattern whose hole
    is that name could not match the stored fact.
    """
    space = metta._new_space()
    space.add(S.person("Ada Lovelace", 36))
    rows = list(space.match(lit.person_pattern("Ada Lovelace")))
    assert [row.age for row in rows] == [Grounded(36)]
    assert space.eval(lit.term_identity_of("Ada Lovelace")) == [Grounded("Ada Lovelace")]


@needs_314
def test_a_hole_enters_each_value_kind_through_encode(metta):
    """Every rung of encode's ladder: Atom, Space, callable, int, str."""
    space = metta._new_space()

    def side() -> int:
        return 7

    assert space.eval(lit.term_identity_of(S.already_an_atom)) == [S.already_an_atom]
    assert space.eval(lit.term_identity_of(space)) == [space]
    assert space.eval(lit.term_identity_of(9)) == [Grounded(9)]
    assert space.eval(lit.term_identity_of("text")) == [Grounded("text")]
    held = space.eval(lit.term_identity_of(side))[0]
    assert isinstance(held, Grounded)
    assert held.value is side


@needs_314
def test_a_nested_template_composes_its_text_and_its_holes(metta):
    """A template inside a hole is text the author wrote, so it splices."""
    assert metta.run(lit.nested_sum(lit.inner_sum(41))) == [[Grounded(142)]]


@needs_314
def test_the_three_specs_are_the_atom_constructors(metta):
    """The spec words: sym is Symbol, expr is parse, py is Grounded."""
    answers = metta.run(lit.spec_of("a-name", "(sub term)", {"k": 1}))
    (built,) = answers[0]
    head, name, term, obj = built.children
    assert head == S.triple
    assert name == Symbol("a-name")
    assert term == parse("(sub term)")
    assert isinstance(obj, Grounded)
    assert obj.value == {"k": 1}


@needs_314
def test_an_unknown_spec_names_the_three(metta):
    """A Python format spec is not a hole spec, and says what to write."""
    with pytest.raises(ValueError, match=r"unknown hole spec '\.2f'.*sym.*expr.*py"):
        metta.run(lit.unknown_spec_of(3.14159))


@needs_314
def test_a_conversion_applies_python_first_and_enters_as_text(metta):
    """``!r`` is Python's repr, and the result enters as a String."""
    assert metta.run(lit.repr_of("hi")) == [[Grounded("'hi'")]]


@needs_314
def test_the_debug_fold_enters_its_label_and_the_repr(metta):
    """PEP 750 folds ``x=`` into the preceding segment and sets conversion r.

    Left as text the label would be glued to the hole and refused, so it is
    split off and enters as its own String atom: ``{x=}`` is two atoms, the
    label then the repr, which is the two pieces of text an f-string writes.
    """
    label_then_value = S["debug-line"](Grounded("x="), Grounded("42"))
    assert metta.run(lit.debug_of(42)) == [[label_then_value]]
    assert metta.run(lit.spaced_debug_of(42)) == [
        [S["debug-line"](Grounded("x ="), Grounded("42"))]
    ]


# -------------------------------------------------------------- the refusals


@needs_314
def test_a_hole_inside_a_string_literal_is_refused(metta):
    """A string is one value; splicing into it is what the door removes."""
    with pytest.raises(ValueError, match=r"inside a string literal.*line 1, column 9"):
        metta.run(lit.in_string_literal("x"))


@needs_314
def test_a_hole_inside_a_symbol_is_refused(metta):
    """Glued to a symbol, the hole would name something else entirely."""
    with pytest.raises(ValueError, match=r"inside a symbol.*line 1, column 6.*`foo"):
        metta.run(lit.in_symbol("x"))


@needs_314
def test_a_hole_inside_a_comment_is_refused(metta):
    """The reader would discard it, so the value would never arrive."""
    with pytest.raises(ValueError, match="inside a ; comment"):
        metta.run(lit.in_comment("x"))


@needs_314
def test_a_hole_after_a_string_literal_is_its_own_token(metta):
    """The check is the reader's grammar, not adjacency.

    ``"a"{v}`` reads as two atoms, because a quote at a token start commits to
    the quoted scanner and the next token begins after the closing quote. An
    adjacency rule would refuse text the engine accepts.
    """
    assert parse('(pair "a"__metta_hole_0)').children[1] == Grounded("a")
    assert metta.run(lit.after_a_string(5)) == [[S.pair(Grounded("a"), 5)]]


@needs_314
def test_author_text_spelling_the_prefix_is_refused_in_a_literal(metta):
    """The same closure through the template face."""
    with pytest.raises(ValueError, match="reserved hole prefix"):
        metta.run(lit.spelling_the_prefix(1))


def test_an_unbound_field_is_refused_by_name(metta):
    """A field with no keyword names itself and what to pass."""
    with pytest.raises(ValueError, match=r"no value for the field \{n\}; pass n="):
        metta.run("!(+ {n} 1)", other=1)


def test_a_keyword_no_field_uses_is_refused(metta):
    """Otherwise a mistyped bound would be swallowed by the values face."""
    with pytest.raises(TypeError, match=r"does not use: \['timout'\]"):
        metta.run("!(+ {n} 1)", n=1, timout=5)


def test_a_positional_field_is_refused(metta):
    """A value here is a binding, and a binding has a name."""
    with pytest.raises(ValueError, match="must be NAMED"):
        metta.run("!(+ {} 1)", n=1)
    with pytest.raises(ValueError, match="must be NAMED"):
        metta.run("!(+ {0} 1)", n=1)


def test_a_field_named_by_a_door_keyword_names_the_collision(metta):
    """The parameter takes the value first, so the field can never be reached."""
    with pytest.raises(ValueError, match="run takes timeout= as its own argument"):
        metta.run("!(+ {timeout} 1)", n=1)


def test_an_unknown_conversion_names_the_three(metta):
    """A producer other than the compiler can carry any conversion letter."""
    with pytest.raises(ValueError, match=r"unknown conversion 'x'.*!r, !s and !a"):
        metta.run(Tpl(("!(id ", ")"), (Interp(1, "v", "x"),)))


def test_the_ascii_conversion_is_pythons_own(metta):
    """!a is ascii(), the third conversion PEP 750 records."""
    assert metta.run(Tpl(("!(id ", ")"), (Interp("caf\u00e9", "v", "a"),))) == [
        [Grounded("'caf\\xe9'")]
    ]


def test_a_spec_that_needs_a_str_refuses_by_type(metta):
    """The sym and expr specs build from text, so they name what they got."""
    with pytest.raises(TypeError, match=r"the sym spec takes a str, and .* has int"):
        metta.run(Tpl(("!(id ", ")"), (Interp(1, "v", None, "sym"),)))
    with pytest.raises(TypeError, match="the expr spec takes a str"):
        metta.run(Tpl(("!(id ", ")"), (Interp(1, "v", None, "expr"),)))


def test_a_converted_template_enters_as_a_value_not_as_text(metta):
    """A conversion says "treat this as a value", and a template obeys it.

    Without one a nested template composes its text into the outer call; with
    one it is converted first, so it enters as the String the conversion made.
    """
    inner = Tpl(("(+ 1 2)",), ())
    assert metta.run(Tpl(("!(id ", ")"), (Interp(inner, "inner"),))) == [[Grounded(3)]]
    assert metta.run(Tpl(("!(id ", ")"), (Interp(inner, "inner", "r"),))) == [
        [Grounded("<template>")]
    ]


def test_a_template_and_keyword_values_are_not_mixed(metta):
    """One face per call: the template carries its own values."""
    with pytest.raises(TypeError, match="from the template itself"):
        metta.run(Tpl(("!(+ ", " 1)"), (Interp(41),)), n=1)


def test_load_refuses_program_text_with_holes(metta, dummy_metta_path):
    """A PATH is not program text, and a filename cannot bind a hole."""
    assert metta.load(str(dummy_metta_path)) is not None
    with pytest.raises(TypeError, match=r"takes a PATH.*Use run\(\)"):
        metta.load(Tpl(("corpus/", ".metta"), (Interp("name"),)))


def test_run_status_refuses_program_text_with_holes(metta):
    """The engine's status door carries no bindings, and the refusal says so."""
    assert metta.run_status("!(+ 1 2)") == [[("value", Grounded(3))]]
    with pytest.raises(TypeError, match="carries no bindings"):
        metta.run_status(Tpl(("!(+ ", " 1)"), (Interp(41),)))


# ------------------------------------------------------- a hole IS a binding


def test_a_hole_and_a_binding_answer_the_same(metta):
    """The same program, the same value, two ways of naming its position."""
    through_a_hole = metta.run("!(+ {n} 1)", n=41)
    with metta.bind(n=41):
        through_a_binding = metta.run("!(+ n 1)")
    assert through_a_hole == through_a_binding == [[Grounded(42)]]


def test_a_binding_reaches_every_occurrence_where_a_hole_reaches_one(metta):
    """Why the door exists.

    A binding names a SYMBOL, so it replaces the occurrence the author meant
    as a symbol too. Here `graph` is both a value the program computes with
    and the argument of an equation ABOUT it. The binding rewrites the
    equation's own call site, so `(describe 7)` matches no clause of a head
    that now has one, and the program answers nothing at all; the hole
    rewrites only its own position and the program answers.
    """
    space = metta._new_space()
    space.run('(= (describe graph) "a symbol")')

    through_a_hole = space.run("!(pair (describe graph) (id {v}))", v=7)
    with space.bind(v=7, graph=7):
        through_a_binding = space.run("!(pair (describe graph) (id v))")

    assert through_a_hole == [[S.pair(Grounded("a symbol"), 7)]]
    assert through_a_binding == [[]]


# ------------------------------------------------------------- every door


def test_every_text_door_takes_program_text_with_holes(metta):
    """One acceptance, at each door named in llms.txt."""
    space = metta._new_space()
    space.add(S.person("Ada", 36))

    assert space.run("!(+ {n} 1)", n=41) == [[Grounded(42)]]
    assert space.eval("(+ {n} 1)", n=41) == [Grounded(42)]
    assert list(space.answers("(+ {n} 1)", n=41)) == [Grounded(42)]
    assert space.eval_status("(+ {n} 1)", n=41) == [("value", Grounded(42))]
    assert space.parse("(+ {n} 1)", n=41) == S["+"](41, 1)
    assert parse("(+ {n} 1)", n=41) == S["+"](41, 1)
    assert [row.age for row in space.match("(person {who} $age)", who="Ada")] == [
        Grounded(36)
    ]
    groups, profile = space.profile("!(+ {n} 1)", n=41)
    assert groups == [[Grounded(42)]]
    assert profile.samples >= 0


def test_a_pattern_template_matches_the_value_itself(metta):
    """A pattern has no binding channel, so the hole lands in the pattern.

    The two doors must still agree about what a value MEANS, which is why the
    value is encoded before it is substituted: `_to_atom` parses a str where
    `encode` makes it a String.
    """
    space = metta._new_space()
    space.add(S.person("Ada Lovelace", 36), S.person("Ada", 30))
    rows = list(space.match("(person {who} $age)", who="Ada Lovelace"))
    assert [row.age for row in rows] == [Grounded(36)]
    assert list(space.match(S.person("Ada Lovelace", V.age))) == rows


def test_holes_are_numbered_across_one_call(metta):
    """Two targets of one eval share one map, so their holes cannot collide."""
    assert metta.eval("(id {a})", "(id {b})", a=1, b=2) == [[Grounded(1)], [Grounded(2)]]


def test_a_refusal_counts_lines_within_its_own_target(metta):
    """A refusal counts lines from its own target's first line.

    A hole in the SECOND target of a call is reported where the author sees
    it, not offset by the lines of the target before it.
    """
    with pytest.raises(ValueError, match=r"\{b\} at line 1, column 5"):
        metta.eval("(id\n{a})", "(idx{b})", a=1, b=2)


@needs_314
def test_two_literal_targets_of_one_call_keep_their_own_values(metta):
    """The same, through the literal face."""
    left, right = lit.two_terms(1, 2)
    assert metta.eval(left, right) == [[Grounded(1)], [Grounded(2)]]


def test_plain_text_is_untouched_when_no_values_are_passed(metta):
    """A program whose symbols contain braces still runs, unscanned."""
    assert metta.run("!(id {not-a-field})") == [[S["{not-a-field}"]]]
    assert metta.eval("(id {not-a-field})") == [S["{not-a-field}"]]
