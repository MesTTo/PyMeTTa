"""Purpose: the function protocol on m.fn(): introspection answering from
MeTTa's own declarations (name, qualname, doc, signature, type, equations),
the compiled-clauses dis, and the equation watcher riding subscriptions.
Guarantees:
  - help() on a function object renders the space's @doc atom [tested
    test_help_answers_from_mettas_own_documentation]
  - subscribe sees equation adds and removes, the function-watcher
    analogue [tested test_subscribe_is_the_function_watcher]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

import functools
import inspect
import pydoc

import pytest

from petta import PettaError


@pytest.fixture()
def m(metta):
    space = metta.new_space()
    space.run("(: fp-inc (-> Number Number))")
    space.run("(= (fp-inc $x) (+ $x 1))")
    space.run(
        '(@doc fp-inc (@desc "Adds one.") '
        '(@params ((@param "a number"))) (@return "the successor"))'
    )
    return space


def test_name_and_qualname_mirror_methods(m):
    f = m.fn("fp-inc")
    assert f.__name__ == "fp-inc"
    assert f.__qualname__ == f"{m.space_name}.fp-inc"
    # The class's own name is untouched by the instance attributes.
    assert type(f).__name__ == "_EngineFunction"


def test_type_is_the_declared_arrow_or_none(m):
    assert str(m.fn("fp-inc").type) == "(-> Number Number)"
    assert m.fn("fp-undeclared").type is None


def test_signature_comes_from_the_arrow(m):
    signature = inspect.signature(m.fn("fp-inc"))
    parameters = list(signature.parameters.values())
    assert len(parameters) == 1
    assert parameters[0].kind is inspect.Parameter.POSITIONAL_ONLY
    assert parameters[0].annotation == "Number"
    assert signature.return_annotation == "Number"
    # No arrow declared: an honest (*args), not a guessed arity.
    fallback = inspect.signature(m.fn("fp-undeclared"))
    assert [p.kind for p in fallback.parameters.values()] == [
        inspect.Parameter.VAR_POSITIONAL
    ]


def test_equations_are_live_from_the_space(m):
    f = m.fn("fp-inc")
    (equation,) = f.equations
    assert str(equation).startswith("(= (fp-inc ")
    m.run("(= (fp-inc 0) zero)")
    assert len(f.equations) == 2  # live, not a snapshot


def test_doc_formats_the_doc_atom(m):
    text = m.fn("fp-inc").__doc__
    assert text.startswith("fp-inc: Adds one.")
    assert "  - a number" in text
    assert "Returns: the successor" in text


def test_doc_falls_back_to_declaration_and_equations(m):
    m.run("(: fp-plain (-> Atom Atom))")
    m.run("(= (fp-plain $x) $x)")
    text = m.fn("fp-plain").__doc__
    assert text.startswith("fp-plain: (-> Atom Atom)")
    assert "Equations:" in text
    assert m.fn("fp-nothing-known").__doc__ is None


def test_builtins_answer_from_the_engine_register(m):
    assert "Casts" in m.fn("type-cast").__doc__


def test_help_answers_from_mettas_own_documentation(m):
    rendered = pydoc.render_doc(m.fn("fp-inc"))
    assert "Adds one." in rendered


def test_compiled_and_disassemble_show_the_prolog(m):
    text = m.fn("fp-inc").compiled
    assert text == m.disassemble("fp-inc")
    assert "'fp-inc'(" in text  # the translator's clause head, Prolog-quoted
    with pytest.raises(PettaError, match="no compiled clauses"):
        m.disassemble("fp-never-compiled")


def test_partial_composes_with_stdlib_machinery(m):
    m.run("(= (fp-add $x $y) (+ $x $y))")
    add_ten = functools.partial(m.fn("fp-add"), 10)
    assert add_ten(5) == 15


def test_subscribe_is_the_function_watcher(m):
    events = []
    subscription = m.subscribe(
        "(= (fp-watched $x) $body)", lambda event: events.append(event), on="both"
    )
    try:
        m.add("(= (fp-watched 1) one)")
        m.remove("(= (fp-watched 1) one)")
    finally:
        subscription.cancel()
    assert [event.action for event in events] == ["add", "remove"]
    assert str(events[0].bindings["body"]) == "one"
