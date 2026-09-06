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
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import functools
import inspect
import pydoc
import traceback

import pytest

from metta import MettaError


@pytest.fixture()
def m(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    space = metta._new_space()
    space.run("(: fp-inc (-> Number Number))")
    space.run("(= (fp-inc $x) (+ $x 1))")
    space.run("(= (fp-undeclared $x) $x)")
    space.run(
        '(@doc fp-inc (@desc "Adds one.") '
        '(@params ((@param "a number"))) (@return "the successor"))'
    )
    return space


def test_name_and_qualname_mirror_methods(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    f = m.fn.fp_inc
    assert f.__name__ == "fp-inc"
    assert f.__qualname__ == f"{m.name}.fp-inc"
    # The class's own name is untouched by the instance attributes.
    assert type(f).__name__ == "_EngineFunction"


def test_type_is_the_declared_arrow_or_none(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    assert str(m.fn.fp_inc.type) == "(-> Number Number)"
    assert m.fn.fp_undeclared.type is None


def test_signature_comes_from_the_arrow(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    signature = inspect.signature(m.fn.fp_inc)
    parameters = list(signature.parameters.values())
    assert len(parameters) == 1
    assert parameters[0].kind is inspect.Parameter.POSITIONAL_ONLY
    assert parameters[0].annotation == "Number"
    assert signature.return_annotation == "Number"
    # No arrow declared: an honest (*args), not a guessed arity.
    fallback = inspect.signature(m.fn.fp_undeclared)
    assert [p.kind for p in fallback.parameters.values()] == [
        inspect.Parameter.VAR_POSITIONAL
    ]


def test_equations_are_live_from_the_space(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    f = m.fn.fp_inc
    (equation,) = f.equations
    assert str(equation).startswith("(= (fp-inc ")
    m.run("(= (fp-inc 0) zero)")
    assert len(f.equations) == 2  # live, not a snapshot


def test_doc_formats_the_doc_atom(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    text = m.fn.fp_inc.__doc__
    assert text.startswith("fp-inc: Adds one.")
    assert "  - a number" in text
    assert "Returns: the successor" in text


def test_doc_falls_back_to_declaration_and_equations(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m.run("(: fp-plain (-> Atom Atom))")
    m.run("(= (fp-plain $x) $x)")
    text = m.fn.fp_plain.__doc__
    assert text.startswith("fp-plain: (-> Atom Atom)")
    assert "Equations:" in text
    with pytest.raises(AttributeError):
        _ = m.fn.fp_nothing_known


def test_builtins_answer_from_the_engine_register(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    assert "Casts" in m.fn.type_cast.__doc__


def test_help_answers_from_mettas_own_documentation(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    rendered = pydoc.render_doc(m.fn.fp_inc)
    assert "Adds one." in rendered


def test_compiled_and_disassemble_show_the_prolog(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    text = m.fn.fp_inc.compiled
    assert text == m._disassemble("fp-inc")
    assert "'fp-inc'(" in text  # the translator's clause head, Prolog-quoted
    with pytest.raises(MettaError, match="no compiled clauses"):
        m._disassemble("fp-never-compiled")


def test_partial_composes_with_stdlib_machinery(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m.run("(= (fp-add $x $y) (+ $x $y))")
    add_ten = functools.partial(m.fn.fp_add, 10)
    assert add_ten(5) == [15]


def test_subscribe_is_the_function_watcher(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
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


def test_a_namespace_lists_and_resolves_only_what_its_space_can_call(metta):
    """A space's function namespace is what THAT space can call.

    ``fun/1`` is process-wide by design, the translator's call-or-data
    question, so a namespace built on it advertised heads whose equations
    live in a module this space never sees, resolved them, and produced
    calls that answered themselves unreduced. Past 750 names CPython also
    stops offering a suggestion for a typo, which is how a long test process
    lost every "Did you mean" (measured 2026-09-07: 1,107 names listed
    against 306 for the same space alone).
    """
    with metta._new_space() as crowd, metta._new_space() as here:
        crowd.run("\n".join(f"(= (fp-crowd-{i} $x) $x)" for i in range(800)))
        here.run("(= (fp-dbl $x) (* 2 $x))")

        assert "fp_crowd_5" in dir(crowd.fn)
        assert "fp-crowd-5" in crowd.builtins()
        assert "fp_crowd_5" not in dir(here.fn)
        assert "fp-crowd-5" not in here.builtins()
        assert "fp-dbl" in here.builtins()
        assert here.is_function("fp-crowd-5"), "registered anywhere is the translator's question"
        assert not here.is_function_here("fp-crowd-5")
        with pytest.raises(AttributeError) as refused:
            here.fn.fp_crowd_5  # noqa: B018  -- the refusal at access IS the scenario
        assert refused.value.name == "fp_crowd_5"

        assert len(dir(here.fn)) < 750, "the suggestion pool must stay inside CPython's cap"
        with pytest.raises(AttributeError) as caught:
            here.fn.fp_dbll  # noqa: B018  -- the refusal at access IS the scenario
        rendered = "".join(traceback.format_exception(caught.value))
        assert "Did you mean: 'fp_dbl'?" in rendered

        with metta._new_space(inherits=here) as child:
            assert "fp_dbl" in dir(child.fn), "an inherited head is callable here"
            assert child.fn.fp_dbl.__name__ == "fp-dbl"
            assert "fp_crowd_5" not in dir(child.fn)
