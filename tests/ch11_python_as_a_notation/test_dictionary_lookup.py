"""Purpose: verify native dictionary lookup with Python default semantics.

Guarantees:
  - optional defaults preserve absence, stored data, evaluation order and
    native relation edits [tested: test_dictionary_get_preserves_stored_values,
    test_dictionary_get_evaluates_key_and_default_before_lookup,
    test_dictionary_get_observes_native_relation_edits; commit=WORKTREE]
"""

from typing import Any

import pytest

from metta import Atom, Expression, MeTTa, S, V, fn


@pytest.mark.parametrize("explicit", (False, True))
@pytest.mark.parametrize("present", (False, True))
@pytest.mark.parametrize("value", (None, False, 0, "", S["+"](1, 2)))
def test_dictionary_get_preserves_stored_values(explicit, present, value):
    """The absent case alone selects a default; stored atoms remain data."""
    def implicit_lookup(key: str, value: Atom) -> Any:
        table = {"held": value}
        return table.get(key)

    def explicit_lookup(key: str, value: Atom, fallback: Atom) -> Any:
        table = {"held": value}
        return table.get(key, fallback)

    source = explicit_lookup if explicit else implicit_lookup
    key = "held" if present else "missing"
    arguments = (key, value, S["+"](7, 8)) if explicit else (key, value)
    expected = source(*arguments)
    with MeTTa() as context:
        compiled = context.self.define(source)
        assert compiled(*arguments).one() == expected
        assert "get-value" in compiled.source()


@pytest.mark.parametrize("present", (False, True))
@pytest.mark.parametrize("failure", (None, "key", "default"))
def test_dictionary_get_evaluates_key_and_default_before_lookup(present, failure):
    """Even a present key evaluates the explicit default, once and in order."""
    events = []

    def mark(label, value):
        events.append(label)
        if label == failure:
            message = f"{label} refused"
            raise ValueError(message)
        return value

    def lookup(key: str) -> int:
        table = {"held": 11}
        return table.get(mark("key", key), mark("default", 29))

    key = "held" if present else "missing"
    with MeTTa() as context:
        compiled = context.self.define(lookup)
        outcomes = []
        for native in (False, True):
            events.clear()
            try:
                answer = compiled(key).one() if native else lookup(key)
            except Exception as error:
                assert failure is not None and f"{failure} refused" in str(error)
                answer = f"{failure} refused"
            outcomes.append((answer, events.copy()))
        assert outcomes[0] == outcomes[1]


def test_dictionary_get_observes_native_relation_edits():
    """A compiled lookup reads the live space, including native multiplicity."""
    with MeTTa() as context:
        m = context.self
        editor = S["edit-lookup-dictionary"]
        m.add(S["="](editor(V.table), Expression([])))

        @m.define
        def lookup(key: str, fallback: Atom) -> Any:
            table = {}
            fn["edit-lookup-dictionary"](table)
            return table.get(key, fallback)

        fallback = S.Kwargs(S.entry(9))
        assert lookup("held", fallback).one() == fallback
        first, second = S["+"](1, 2), S["*"](3, 4)
        m.remove(S["="](editor(V.table), V.body))
        m.add(S["="](editor(V.table), S.let(
            V.written,
            S["add-atom"](V.table, Expression(["held", first])),
            S["add-atom"](V.table, Expression(["held", second])),
        )))
        assert list(lookup("held", fallback)) == [first, second]
        m.remove(S["="](editor(V.table), V.body))
        m.add(S["="](editor(V.table), Expression([])))
        assert lookup("held", fallback).one() == fallback
