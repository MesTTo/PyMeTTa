"""Purpose: pin the distinct one-form and whole-source reader contracts.

Guarantees:
  - parse refuses empty input and multiple top-level forms instead of choosing
    one silently [tested: test_parse_requires_exactly_one_form;
    commit=9c03403aaaca9f1a1ec52e5898dd547eb80c8e82]
  - parse preserves a source variable's name and forms returns every top-level
    atom without evaluation [tested:
    test_parse_preserves_variable_names,
    test_forms_reads_a_whole_source_without_running_it;
    commit=9c03403aaaca9f1a1ec52e5898dd547eb80c8e82]
  - each public docstring names the other reader so callers can choose by input
    shape [tested: test_the_reader_docstrings_cross_reference_each_other;
    commit=9c03403aaaca9f1a1ec52e5898dd547eb80c8e82]
"""

from __future__ import annotations

import inspect

import pytest

from metta import Expression, S, V, Variable, forms, parse
from metta.errors import EngineError


@pytest.mark.parametrize("source", ["", "(a b) (c d)"], ids=["empty", "two-forms"])
def test_parse_requires_exactly_one_form(source):
    """Refuse any source that cannot denote exactly one returned Atom."""
    with pytest.raises(EngineError, match=r"Syntax error: Parse error in form:"):
        parse(source)


def test_parse_preserves_variable_names():
    """Keep the source name rather than exposing an engine-generated name."""
    parsed = parse("(Parent $x Bob)")
    assert parsed == S.Parent(V.x, S.Bob)
    assert isinstance(parsed, Expression)
    assert parsed.children[1] == Variable("x")


def test_forms_reads_a_whole_source_without_running_it():
    """Return one Atom per top-level form, including an execution marker's term."""
    assert forms("(= (f) 1)  (a b)  !(+ 1 2)") == [
        S["="](S.f(), 1),
        S.a(S.b),
        S["+"](1, 2),
    ]


def test_the_reader_docstrings_cross_reference_each_other():
    """Make the singular and whole-source choices discoverable from either API."""
    parse_doc = inspect.getdoc(parse)
    forms_doc = inspect.getdoc(forms)
    assert parse_doc is not None and "metta.forms()" in parse_doc
    assert forms_doc is not None and "parse()" in forms_doc
