"""Purpose: pin the other direction of the template door, text out of holes.

Every spec is pinned by the BYTES it renders, and the two that have an engine
twin are pinned against the engine rather than against a literal: a bare hole
is what `format-args` interpolates and `{v:sexp}` is what `repr` answers, so
this suite fails if either side moves. The 3.14 literal and the keyword face
render the same template twice and the bytes are compared, which is the claim
that makes the floor 3.12 real.

The split by what the interpreter can PARSE is the sibling suite's: a
``t"..."`` literal is a SyntaxError below 3.14, so the literals live in
``template_literals_314.py`` and are imported inside a version guard.

Guarantees:
  - each rendering spec answers documented bytes, and a spec of the other
    direction or of no direction refuses naming what is there [tested:
    test_the_specs_render_documented_bytes,
    test_an_entry_spec_at_a_rendered_hole_names_the_reader,
    test_an_unknown_render_spec_names_the_render_specs; commit=adb831d29a48596d3068a3087115b216c18b5b38]
  - a rendered hole and the engine's own interpolation agree, with the
    boolean's source spelling the one recorded difference [tested:
    test_a_rendered_hole_is_what_format_args_interpolates,
    test_the_sexp_spec_is_what_repr_answers,
    test_a_boolean_renders_its_source_spelling; commit=adb831d29a48596d3068a3087115b216c18b5b38]
  - a value rendered into a sexp position and the same value entered at a hole
    reach the same atom [tested: test_a_sexp_hole_round_trips_through_the_reader;
    commit=adb831d29a48596d3068a3087115b216c18b5b38]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from __future__ import annotations

import sys
from datetime import datetime
from fractions import Fraction
from typing import Any

import pytest

from metta import Grounded, S, Symbol, V, render
from metta._atoms.factories import parse
from metta._spaces.results import Rows

needs_314 = pytest.mark.skipif(
    sys.version_info < (3, 14), reason="t-string literals are 3.14 syntax"
)

if sys.version_info >= (3, 14):
    from . import template_literals_314 as lit
else:  # pragma: no cover -- the module is 3.14 syntax and cannot be parsed here
    lit = None


@pytest.fixture
def parents() -> Rows:
    """A two-column result, built as a query answers one."""
    return Rows(("parent", "child"), [(S.Tom, S.Bob), (S.Bob, S.Ann)])


def _engine_text(answer: Any) -> str:
    """One engine answer as the text it holds, for comparing against a render."""
    value = getattr(answer, "value", None)
    return value if isinstance(value, str) else str(answer)


# --------------------------------------------------------------- the specs


@pytest.mark.parametrize(
    ("spec", "value", "expected"),
    [
        ("", "a b", "a b"),
        ("", 10, "10"),
        ("", Fraction(1, 2), "1r2"),
        ("", Symbol("foo"), "foo"),
        ("", Grounded("hi"), "hi"),
        ("", parse('(f "hi" 1)'), '(f "hi" 1)'),
        ("sexp", "a b", '"a b"'),
        ("sexp", 10, "10"),
        ("sexp", Symbol("foo"), "foo"),
        ("sexp", Grounded("hi"), '"hi"'),
        ("quoted", "a b", '"a b"'),
        ("quoted", 10, '"10"'),
        ("quoted", Grounded("hi"), '"hi"'),
        ("quoted", Symbol("foo"), '"foo"'),
        ("json", {"a": 1}, '{"a":1}'),
        ("json", [1, "two"], '[1, "two" ]'),
        ("lines", [1, "two", Symbol("three")], "1\ntwo\nthree"),
        (".2f", 3.14159, "3.14"),
        ("<6", "ab", "ab    "),
    ],
)
def test_the_specs_render_documented_bytes(spec, value, expected):
    """Each rendering spec, and the Python specs a rendered hole also takes.

    A bare hole is the engine's own interpolation, so a String is its
    characters and every other atom its MeTTa text; `sexp` is the reading that
    reads back; `quoted` is a String literal of the text; `json` is the
    engine's codec; `lines` is one value a line. Anything else is Python's own
    presentation grammar, because a rendered hole is text.
    """
    field = "{v}" if not spec else "{v:" + spec + "}"
    assert render(field, v=value) == expected


def test_a_rendered_hole_is_what_format_args_interpolates(metta):
    """The bare hole is `metta_console_text/2`, asked of the engine itself.

    `format-args` is the engine's own template renderer and its `{}` is where
    this rule comes from, so the two are compared rather than the Python side
    being pinned to a literal that could drift from it.
    """
    sources = ['"hi"', "42", "3.5", "foo", '(f "hi" 1)', "1r2", "(a (b c))", '"a|b"']
    for source in sources:
        interpolated = _engine_text(
            metta.eval(f'(format-args "{{}}" ({source}))')[0]
        )
        assert render("{v}", v=parse(source)) == interpolated, source


def test_the_sexp_spec_is_what_repr_answers(metta):
    """`sexp` is `sdisplay/2`, which is what `repr` and `println!` write."""
    sources = ['"hi"', "42", "3.5", "foo", '(f "hi" 1)', "1r2", "(a (b c))"]
    for source in sources:
        written = _engine_text(metta.eval(f"(repr {source})")[0])
        assert render("{v:sexp}", v=parse(source)) == written, source


def test_a_boolean_renders_its_source_spelling(metta):
    """The one measured difference between the two renderings, pinned.

    This library prints `True`, the source spelling its own reader accepts,
    where the engine prints the atom it holds, `true`
    [source: metta._atoms.model.Grounded.__str__, which chose the source
    spelling deliberately]. Both read back as the same atom, so the difference
    is a spelling and not a divergence; it is pinned here so that a change to
    either side is a decision rather than a surprise.
    """
    yes = Grounded(value=True)

    assert render("{v}", v=yes) == "True"
    assert _engine_text(metta.eval('(format-args "{}" (True))')[0]) == "true"
    assert metta.eval("(id True)") == metta.eval("(id true)")


def test_a_sexp_hole_round_trips_through_the_reader(metta):
    """Rendered into a program, a sexp hole reaches the atom the hole entered.

    The two directions of one door, compared: `{v:sexp}` writes text that the
    reader reads back, and a reading hole never renders at all, so the answer
    is the same atom either way. A str with a space is the case that separates
    a rendering that escapes from one that does not.
    """
    program = render("!(id {v:sexp})", v="a b")

    assert program == '!(id "a b")'
    assert metta.run(program) == metta.run("!(id {v})", v="a b")
    assert metta.run(program) == [[Grounded("a b")]]


def test_a_table_renders_the_columns_and_every_row(parents):
    """The Markdown table: the columns, the rule, one line per row.

    Every row is written. The display protocols stop at
    `config.display_rows` because a terminal is not a document, and a document
    asked for these rows.
    """
    assert parents.render("{rows:table}") == (
        "| parent | child |\n|---|---|\n| Tom | Bob |\n| Bob | Ann |"
    )


def test_a_table_cell_escapes_the_table_syntax():
    """A pipe, a backslash and a newline cannot break the row they are in.

    GFM's own rule: "Include a pipe in a cell's content by escaping it,
    including inside other inline spans" [source:
    https://github.github.com/gfm, example 200], and a pipe-table row is one
    line, so a newline becomes `<br>`.
    """
    rows = Rows(("cell",), [("a|b",), ("c\\d",), ("e\nf",)])

    assert rows.render("{rows:table}") == (
        "| cell |\n|---|\n| a\\|b |\n| c\\\\d |\n| e<br>f |"
    )


def test_an_empty_result_still_renders_its_header():
    """No rows is a table with no body, not an absence."""
    empty = Rows(("name",), [])

    assert render("{rows:table}", rows=empty) == "| name |\n|---|"


def test_lines_renders_a_nested_template_and_refuses_one_value():
    """`lines` is where a Python comprehension of templates composes.

    A template holds one level, so iteration is Python's; the pieces compose
    through this spec and through nesting. A str is ONE value, not an
    iterable of characters, and says so.
    """
    parts = [render("- {name}", name=name) for name in ("first", "second")]

    assert render("{parts:lines}", parts=parts) == "- first\n- second"
    with pytest.raises(TypeError, match="which is ONE value"):
        render("{v:lines}", v="text")


def test_json_renders_a_result_as_records(parents):
    """`{rows:json}` is `to_dicts` through the engine's codec, one line."""
    rendered = parents.render("{rows:json}")

    assert "\n" not in rendered
    assert '"parent":"Tom"' in rendered
    assert '"child":"Ann"' in rendered


# ------------------------------------------------------------- the refusals


def test_an_entry_spec_at_a_rendered_hole_names_the_reader():
    """A spec of the other direction is misplaced, not unknown.

    Checked BEFORE the value's own `__format__`, which is what makes the
    refusal a property of the table rather than of the value: `datetime`
    formats through `strftime`, and `strftime` passes text it does not
    recognise straight through, so `format(datetime(2026, 9, 7), "sym")`
    answers the four characters `sym`. A door that fell through to the value
    would render that instead of refusing.
    """
    with pytest.raises(ValueError, match=r"the sym spec builds an atom.*m\.run"):
        render("{v:sym}", v="a")
    with pytest.raises(ValueError, match="the sym spec builds an atom"):
        render("{v:sym}", v=datetime(2026, 9, 7))
    assert format(datetime(2026, 9, 7), "sym") == "sym"


def test_a_render_spec_at_an_entry_hole_names_the_render_door(metta):
    """And the same the other way, from the one table."""
    with pytest.raises(
        ValueError, match=r"the table spec renders a value as text.*metta\.render"
    ):
        metta.run("!(id {v:table})", v=1)


def test_an_unknown_render_spec_names_the_render_specs():
    """A spec neither this library nor Python knows names this direction's."""
    with pytest.raises(
        ValueError, match=r"unknown hole spec 'sexpr'.*sexp.*quoted.*json.*table.*lines"
    ):
        render("{v:sexpr}", v="a")


def test_a_table_of_something_that_is_not_a_result_refuses():
    """The table spec wants named columns, and names the doors that answer them."""
    with pytest.raises(TypeError, match="the table spec renders a query result"):
        render("{v:table}", v=[1, 2])


def test_a_table_of_term_answers_refuses_through_the_existing_face(metta):
    """Term answers have no columns, and the refusal is the one Rows already gives."""
    answers = metta.answers("(superpose (1 2))")
    with pytest.raises(TypeError, match="the table face needs caller bindings"):
        answers.render("{rows:table}")


def test_a_value_no_field_uses_is_refused_and_the_receiver_is_not(parents):
    """The unused-value refusal, and the one value the door itself supplied."""
    with pytest.raises(TypeError, match=r"does not use: \['extra'\]"):
        render("{a}", a=1, extra=2)
    assert parents.render("no fields here") == "no fields here"


def test_the_receiver_cannot_be_given_twice(parents):
    """`rows=` beside `rows.render` names two things one name, so it refuses."""
    with pytest.raises(TypeError, match=r"binds \{rows\} to the result"):
        parents.render("{rows}", rows=parents)


def test_the_method_face_always_has_a_value_so_its_fields_are_read(parents):
    """`render("{x}")` is text; `rows.render("{x}")` is a field with no value.

    The keyword face engages when there are values, and a method face always
    has one, the receiver it binds. So the two doors read a brace differently
    and each is consistent with itself: the free function leaves `{x}` alone
    with nothing to resolve against, and the method says which field is
    missing.
    """
    assert render("{x}") == "{x}"
    with pytest.raises(ValueError, match=r"no value for the field \{x\}"):
        parents.render("{x}")


def test_render_refuses_an_atom_and_names_the_doors_that_take_one():
    """An atom is not program text; its own text is one call away."""
    with pytest.raises(TypeError, match=r"str\(atom\) or format\(atom, 'sexp'\)"):
        render(S.already_an_atom)


def test_text_with_no_values_renders_as_itself():
    """The keyword face engages only with values, exactly as the reader's does.

    So a brace is a brace until a value is there to resolve, and then `{{` and
    `}}` are `str.format`'s own escapes. This is the reading door's rule,
    kept rather than smoothed over, so one text means one thing at both.
    """
    assert render("!(id {x})") == "!(id {x})"
    assert render("{{literal}} {x}", x=1) == "{literal} 1"


# ------------------------------------------------------------ the two faces


@needs_314
def test_the_two_faces_render_identically(parents):
    """The 3.14 literal and the keyword face, rendered and compared byte for byte.

    This is what makes the 3.12 floor real: the same template written both
    ways is the same text, so a program written on the floor renders what the
    literal renders.
    """
    value = parse('(f "hi")')
    pairs = [
        (lit.rendered_pair("lib_csv", 2), ("{name} has {count} names",
                                           {"name": "lib_csv", "count": 2})),
        (lit.rendered_specs(value), ("{value} | {value:sexp} | {value:quoted}",
                                     {"value": value})),
        (lit.rendered_table(parents), ("{rows:table}", {"rows": parents})),
        (lit.rendered_lines([1, 2]), ("{items:lines}", {"items": [1, 2]})),
        (lit.rendered_json({"a": 1}), ("{value:json}", {"value": {"a": 1}})),
        (lit.rendered_python_spec(3.14159), ("{value:.2f}", {"value": 3.14159})),
        (lit.rendered_conversion("hi"), ("{value!r}", {"value": "hi"})),
        (lit.rendered_sexp_program("a b"), ("!(id {value:sexp})", {"value": "a b"})),
    ]
    for template, (text, values) in pairs:
        assert render(template) == render(text, **values), text


@needs_314
def test_the_debug_fold_renders_as_the_f_string_does():
    """Rendering is the direction PEP 750's fold needs no undoing in.

    The label is folded into the preceding segment by the compiler, so writing
    the segment whole and the value after it reproduces `f"{x=}"` exactly. The
    reading direction has to split it, because a program holds atoms rather
    than text.
    """
    x = 42

    assert render(lit.rendered_debug(x)) == f"{x=}"


@needs_314
def test_a_nested_template_renders_into_the_outer_one():
    """A template at a hole composes, which is the reading door's rule too."""
    assert render(lit.rendered_nested(lit.rendered_inner("v"))) == "[<v>]"


@needs_314
def test_an_entry_spec_refuses_on_the_literal_face_too():
    """The refusal is the sink's, not the face's."""
    with pytest.raises(ValueError, match="the sym spec builds an atom"):
        render(lit.rendered_entry_spec("a"))


# ------------------------------------------------------- the format protocol


def test_the_format_protocol_reaches_the_same_table(parents):
    """`f"{value:spec}"` is the same rendering, with no import at all.

    Python dispatches a format spec on the value's own class, so the table is
    reachable from the types this library owns; the render door applies it to
    any value, which is the difference between the two faces.
    """
    atom = parse('(f "hi")')

    assert f"{atom:sexp}" == render("{v:sexp}", v=atom)
    assert format(parents, "table") == parents.render("{rows:table}")
    assert f"{Grounded('hi'):quoted}" == '"hi"'


def test_an_empty_spec_is_str_and_python_specs_still_work():
    """Python's law for `format` is untouched, and so is the padding face.

    `format(x, "")` is `str(x)`, which for a String atom is the quoted
    literal; a bare hole in a template is the engine's `{}`, which is the
    characters. The two are different doors and the difference is deliberate.
    """
    text = Grounded("hi")

    assert format(text, "") == str(text) == '"hi"'
    assert render("{v}", v=text) == "hi"
    assert f"{Symbol('ab'):>4}" == "  ab"
    assert f"{Grounded(3.14159):.2f}" == "3.14"


def test_a_spec_the_atom_face_does_not_know_refuses_by_direction():
    """`format(atom, 'sym')` is the reading vocabulary, and says so."""
    with pytest.raises(ValueError, match="the sym spec builds an atom"):
        format(Symbol("a"), "sym")


def test_a_handle_formats_without_a_value_slot(metta):
    """A space is a Grounded whose value slot is deliberately unset.

    So every face has to reach the slot through `getattr` and only when a
    spec needs it. Reading it eagerly answered `'Space' object has no
    attribute 'value'` from inside an f-string, which is how a space reaches
    any of these doors at all.
    """
    space = metta._new_space()
    name = str(space)

    assert f"{space}" == name
    assert format(space, f">{len(name) + 2}") == f"  {name}"
    assert render("{v}", v=space) == name
    assert render("{v:sexp}", v=space) == name


# ------------------------------------------------------------- over a query


def test_a_report_is_a_template_over_a_query(metta):
    """The whole claim in one call: rows in, a document out.

    The iteration is Python's, the composition is the template's, and the
    query is the engine's.
    """
    space = metta._new_space()
    space.add(S.Parent(S.Tom, S.Bob), S.Parent(S.Bob, S.Ann))
    rows = space.match(S.Parent(V.parent, V.child))

    entries = [render("- {p} -> {c}", p=row.parent, c=row.child) for row in rows]
    report = render(
        "# {title}\n\n{entries:lines}\n\n{rows:table}",
        title="Parents",
        entries=entries,
        rows=rows,
    )

    assert report == (
        "# Parents\n\n"
        "- Tom -> Bob\n- Bob -> Ann\n\n"
        "| parent | child |\n|---|---|\n| Tom | Bob |\n| Bob | Ann |"
    )


def test_the_lazy_face_binds_the_same_name(metta):
    """A report written over the lazy view renders its eager twin unchanged.

    Both faces bind the receiver as `rows`, so switching a query between
    `match`'s lazy view and a materialised result does not rewrite the
    template that reports it.
    """
    space = metta._new_space()
    space.add(S.Parent(S.Tom, S.Bob))
    lazy = space.match(S.Parent(V.parent, V.child))
    eager = Rows(lazy.columns, lazy)

    assert lazy.render("{rows:table}") == eager.render("{rows:table}")
