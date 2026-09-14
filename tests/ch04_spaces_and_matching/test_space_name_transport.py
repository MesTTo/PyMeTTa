"""Purpose: preserve native space identities across the Python transport.

Guarantees: storage, rewriting, aliases and ownership retain each name's exact
atom kinds [tested: test_parametric_names_preserve_their_native_fields,
test_parametric_aliases_share_batch_ownership,
test_parametric_names_follow_scope_release; commit=3f71a0b3af04a3ba4c88bf3906197a2a80d9080e].
Cached evaluation addresses every coexisting sibling [tested:
test_parametric_names_keep_atom_kinds_distinct; commit=WORKTREE].
"""

from contextlib import ExitStack, contextmanager

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from metta import Grounded, S, Space, V, scope, space
from metta._errors.errors import MettaError
from metta.convert import encode


@contextmanager
def _named_space(image):
    """Release each explicit name; entering a named handle only selects it."""
    home = space(image)
    try:
        with home:
            yield home
    finally:
        home.drop()


@pytest.mark.parametrize("parameter", [
    "tenant", "", 'λ \\"$value', S.tenant, 1, 1.0, 0.0, -0.0, True, None,
    (S.nested, "tenant", (False,)), Grounded({"tenant": 1}),
])
def test_parametric_names_preserve_their_native_fields(metta, parameter):
    """Read, write and rewrite through the same expression in both languages."""
    image = S["transport-space"](parameter)
    with _named_space(image) as home:
        home.add(S.entry(1))
        assert home.atoms() == [S.entry(1)]
        assert metta.eval(S["get-atoms"](image)) == [S.entry(1)]
        assert home.match(S.entry(V.value)).one().value == 1
        home.run("(= (transport-answer) 1)")
        assert "transport-answer" in home.builtins()
        assert home.fn.transport_answer().one() == 1
        assert home.remove(S["="](S["transport-answer"](), 1))
        home.add(S["="](S["transport-answer"](), 2))
        assert home.fn.transport_answer().one() == 2
        assert home.to_wire() == image.to_wire()


def test_parametric_name_carriers_reopen_and_encode_the_original_expression():
    """A returned name remains a usable value without exposing native records."""
    image = S["transport-reopen"]("tenant")
    with _named_space(image) as home:
        alias = Space(home.name)
        same = Space(image)
        copied = Space(home)
        assert home == alias == same == copied
        assert len({home, alias, same, copied}) == 1
        assert len({home.name, alias.name, same.name, copied.name}) == 1
        assert encode(home.name) == image
        assert alias.to_wire() == image.to_wire()
        alias.add(S.entry(7))
        assert home.atoms() == [S.entry(7)]
    assert home.dropped


def test_parametric_aliases_share_batch_ownership():
    """An alias contributes to the active batch and cannot create a nested one."""
    with _named_space(S["transport-batch"]("tenant")) as home:
        alias = Space(S["transport-batch"]("tenant"))
        with home.batch():
            alias.add(S.entry(1))
            assert home.atoms() == []
            with pytest.raises(MettaError, match="batches do not nest"):
                with alias.batch():
                    pass
        assert home.atoms() == [S.entry(1)]


def test_parametric_names_keep_atom_kinds_distinct(metta):
    """String, symbol, boolean, numeric kind and signed zero stay separate."""
    parameters = ["tenant", S.tenant, True, 1, 1.0, 0.0, -0.0]
    with ExitStack() as stack:
        homes = [stack.enter_context(_named_space(S["transport-distinct"](value)))
                 for value in parameters]
        assert len(set(homes)) == len(homes)
        assert len({home.name for home in homes}) == len(homes)
        for index, home in enumerate(homes):
            home.add(S.entry(index))
        for index, home in enumerate(homes):
            assert home.atoms() == [S.entry(index)]
            assert metta.eval(S["get-atoms"](home)) == [S.entry(index)]


@pytest.mark.parametrize("mutation", [
    lambda name: name.append(S.other),
    lambda name: name.clear(),
    lambda name: name.__setitem__(0, S.other),
    lambda name: name.__delitem__(0),
    lambda name: name.__iadd__([S.other]),
    lambda name: name.__imul__(2),
    lambda name: name.extend([S.other]),
    lambda name: name.insert(0, S.other),
    lambda name: name.pop(),
    lambda name: name.remove(name[0]),
    lambda name: name.reverse(),
    lambda name: name.sort(),
])
def test_parametric_name_carriers_are_immutable(mutation):
    """A name cannot change while per-space registries use its hash."""
    with _named_space(S["transport-immutable"]("tenant")) as home:
        with pytest.raises(TypeError, match="space name is immutable"):
            mutation(home.name)
        assert home.atoms() == []


def test_parametric_names_follow_scope_release():
    """Scope teardown revokes every handle naming the released graph node."""
    with scope():
        home = space(S["transport-scoped"]("tenant"))
        alias = Space(home.name)
        home.add(S.entry(1))
        assert alias.atoms() == [S.entry(1)]
    assert home.dropped
    assert alias.dropped
    with pytest.raises(MettaError, match=r"dropped|released_scope_space"):
        alias.atoms()


@given(st.text())
@settings(max_examples=30, deadline=None)
def test_arbitrary_strings_remain_native_name_parameters(metta, parameter):
    """String contents cannot turn an identity field into executable syntax."""
    image = S["transport-string"](parameter)
    with _named_space(image) as home:
        home.add(S.entry(parameter))
        assert home.atoms() == [S.entry(parameter)]
        assert metta.eval(S["get-atoms"](image)) == [S.entry(parameter)]
