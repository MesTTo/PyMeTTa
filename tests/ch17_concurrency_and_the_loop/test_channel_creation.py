"""Purpose: validate channel factory answers before opening a space identity.

Guarantees:
  - unreduced or nonspace answers raise without declaring a new space
    [tested: test_channel_creation_refuses_nonspace_answers; commit=WORKTREE]
  - a returned registered space retains its identity, including expression
    names [tested: test_channel_creation_preserves_registered_space_identity;
    commit=WORKTREE]
Owns resources: each fixture drops its spaces and restores the factory call
through pytest's monkeypatch fixture [tested: test_channel_creation.py; commit=WORKTREE].
"""

import pytest

import metta
from metta import Expression, G, S, V, parallel
from metta._errors.errors import MettaError


@pytest.mark.parametrize("capacity", [None, 3])
@pytest.mark.parametrize("result", [
    S.channel(3), S["channel_new"](3), S.not_a_channel_space,
    G(0), Expression([]), S.unbound_channel(V.name),
])
def test_channel_creation_refuses_nonspace_answers(monkeypatch, capacity, result):
    """A bad native answer cannot manufacture a store from its call syntax."""
    def native_answer(owner, _head, *_arguments):
        return owner.answers(Expression([S.noeval, result]))

    monkeypatch.setattr(parallel, "_call", native_answer)
    with metta.MeTTa() as context, context.self, context.scope():
        before = context.self.space_names()
        with pytest.raises(MettaError, match=r"channel.*space"):
            metta.channel(max=capacity)
        assert context.self.space_names() == before


@pytest.mark.parametrize("parametric", [False, True])
def test_channel_creation_preserves_registered_space_identity(monkeypatch, parametric):
    """The declared result species preserves the engine's existing identity."""
    def native_answer(owner, _head, *_arguments):
        return owner.answers(Expression([S.noeval, result]))

    monkeypatch.setattr(parallel, "_call", native_answer)
    with metta.MeTTa() as context, context.self, context.scope():
        name = S.registered_channel_image("named", 3) if parametric else None
        with metta.space(name) if parametric else metta.space() as original:
            original.add(S.queued(8))
            result = original.name if parametric else original
            with metta.channel() as opened:
                assert opened.name == original.name
                assert opened.atoms() == [S.queued(8)]
