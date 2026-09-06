"""Purpose: where a head was written, clause by clause.

A `.metta` file answers its own file and the line each equation sits on; a
Prolog-registered head answers the file and line SWI recorded for its clause;
a head defined from Python text has no source and answers None. Clause order
is source order, a head defined across two files keeps each clause with its
own file, and an edit that removes an equation costs the line rather than
inventing one.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from __future__ import annotations

import pytest

import metta
from metta import S


@pytest.fixture()
def m(metta):
    """An isolated space, so a loaded file's clauses are this test's alone."""
    with metta._new_space() as space:
        yield space


def _write(tmp_path, name, text):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def test_a_head_loaded_from_a_metta_file_names_that_file_and_line(m, tmp_path):
    """The line is the equation's own, not the file's first or last."""
    path = _write(
        tmp_path,
        "shapes.metta",
        "; two blank lines and a declaration precede it\n"
        "\n"
        "(: quad (-> Number Number))\n"
        "(= (quad $x) (* 4 $x))\n",
    )
    m.load(str(path))

    (origin,) = m.fn.quad.origin
    assert origin is not None
    assert origin.file == str(path)
    assert origin.line == 4
    assert (origin.file, origin.line) == tuple(origin), "an Origin IS the pair"


def test_a_head_defined_from_python_text_has_no_source(m):
    """`m.run` is not a file, and saying so beats naming one."""
    m.run("(= (dbl $x) (* 2 $x))")
    assert m.fn.dbl.origin == (None,)


def test_every_clause_of_a_multi_clause_head_answers_in_clause_order(m, tmp_path):
    """One row per compiled clause, in the order the file wrote them."""
    path = _write(
        tmp_path,
        "pent.metta",
        "(= (pent $x) (* 5 $x))\n"
        "(= (pent 0) 0)\n"
        "\n"
        "; a comment between the second and third equation\n"
        "(= (pent 1) 1)\n",
    )
    m.load(str(path))

    origins = m.fn.pent.origin
    assert [o.line for o in origins] == [1, 2, 5]
    assert {o.file for o in origins} == {str(path)}


def test_two_files_defining_one_head_keep_each_clause_with_its_own_file(m, tmp_path):
    """The clause-to-equation count is kept per LOAD, not per predicate."""
    first = _write(tmp_path, "first.metta", "\n(= (shared 1) one)\n")
    second = _write(tmp_path, "second.metta", "(= (shared 2) two)\n\n(= (shared 3) three)\n")
    m.load(str(first))
    m.load(str(second))

    assert [(o.file, o.line) for o in m.fn.shared.origin] == [
        (str(first), 2),
        (str(second), 1),
        (str(second), 3),
    ]


def test_a_builtin_answers_the_prolog_file_and_line_its_clauses_carry(m):
    """clause_property/2's own answer, which is the whole builtin surface."""
    origins = m.fn["car-atom"].origin
    assert len(origins) > 1, "car-atom is defined by several guarded clauses"
    assert all(o is not None for o in origins)
    assert all(o.file.endswith(".pl") for o in origins)
    lines = [o.line for o in origins]
    assert lines == sorted(lines) and lines[0] > 0


def test_a_special_form_has_no_clauses_and_answers_nothing(m):
    """Answer the empty tuple where there is no clause to locate.

    `if` is compiled by the translator rather than defined, and having no
    clauses is exactly what the empty tuple says.
    """
    assert m.fn["if"].origin == ()


def test_an_edited_file_loses_the_line_and_keeps_the_file(m, tmp_path):
    """A wrong line is worse than no line.

    The line is located in the file as it stands, so an equation deleted
    after the load has no form to sit on. The clause is still the one that
    file put there, and the answer still says so.
    """
    path = _write(tmp_path, "edited.metta", "(= (gone $x) $x)\n(= (kept $x) $x)\n")
    m.load(str(path))
    assert m.fn.gone.origin[0].line == 1

    path.write_text("(= (kept $x) $x)\n", encoding="utf-8")
    (origin,) = m.fn.gone.origin
    assert origin.file == str(path)
    assert origin.line is None


def test_a_symbol_answers_the_ambient_spaces_origins():
    """`metta.fn.car_atom.origin` and `S["car-atom"].origin` are one door.

    The generated mention reaches the live head through the ambient space,
    so a name that means nothing anywhere answers the empty tuple rather
    than refusing.
    """
    assert metta.fn.car_atom.origin == metta.engine().fn["car-atom"].origin
    assert S["car-atom"].origin == metta.fn.car_atom.origin
    assert S.no_head_is_named_this.origin == ()
