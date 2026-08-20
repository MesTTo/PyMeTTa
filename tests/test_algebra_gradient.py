"""Purpose: black-box acceptance for the P4.32 differentiable algebra rung.

Assumes:
  - the campaign's sibling ``pettorch`` checkout and PyTorch are importable.
Guarantees:
  - a grounded tensor tag retains DLPack storage and its autograd graph through
    two declared rules and one pettorch module call [tested:
    test_a_declared_gradient_algebra_propagates_derivatives_through_a_derivation;
    commit=4b2f8ea2c72fed6974470f34b3557c86574cc18d]
"""

import pytest

from petta import S, V, decode, val


def test_a_declared_gradient_algebra_propagates_derivatives_through_a_derivation(
    metta, repo_root, monkeypatch
):
    """Propagate a live tensor through two rules and back into its source."""
    sibling = repo_root.parent.parent / "pettorch"
    monkeypatch.syspath_prepend(sibling)
    import pettorch
    import torch

    pettorch.install(metta)
    leaf = torch.tensor(2.0, requires_grad=True)
    scale = torch.tensor(3.0)
    one = torch.tensor(1.0)
    metta.declare_algebra(
        "p4-gradient",
        combine="t+",
        extend="t*",
        zero=torch.tensor(0.0),
        one=one,
    )
    with metta.new_space() as program:
        program.add_tagged_fact(val(leaf), S.source(S.a))
        program.add_tagged_fact(val(scale), S.scale(S.a))
        program.add_tagged_rule(val(one), S.middle(V.x), S.source(V.x))
        program.add_tagged_rule(
            val(one),
            S.output(V.x),
            S.middle(V.x),
            S.scale(V.x),
        )
        evaluation = program.evaluate_algebra(
            S.output(S.a), algebra="p4-gradient"
        )
        assert len(evaluation.answers) == 1
        result = decode(evaluation.answers[0].tag)
        assert result.item() == pytest.approx(6.0)
        assert hasattr(result, "__dlpack__")
        assert result.grad_fn is not None
        # DLPack deliberately cannot encode autograd metadata. Export the
        # detached view to prove shared storage while retaining the live result
        # below for pettorch and backward().
        assert torch.from_dlpack(result.detach()).data_ptr() == result.data_ptr()

        program.register_op(
            lambda: result,
            name="p4-gradient-result",
            raw=False,
        )
        program.run("(= (p4-gradient-model) (p4-gradient-result))")
        model = pettorch.MettaModule(program, "p4-gradient-model")
        consumed = model()
        assert consumed is result
        consumed.backward()
        assert leaf.grad.item() == pytest.approx(3.0)
