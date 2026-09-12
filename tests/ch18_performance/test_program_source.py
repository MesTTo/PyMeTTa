"""Purpose: verify portable MeTTa programs after their original spaces close.

Guarantees: reference cycles, shared spaces, lexical bindings, entity classes,
source replacement and failed writes preserve their contracts
[tested: test_program_source.py; commit=WORKTREE].
"""

import pytest

from metta import Expression, MeTTa, S, V, ground
from metta._errors.errors import EngineError, SourceNotFound
@pytest.mark.parametrize("order, answers", [((1, 0), (1, 0)), ((0, 1), (2, 0))])
def test_source_token_claims_withdraw_in_either_order(tmp_path, order, answers):
    """Source removal exposes the most recent binding whose owner still exists."""
    with MeTTa() as context:
        context.run('!(let $name (atom_concat "owned-source-token" "") (bind! $name 0))')
        paths = [tmp_path / f"claim-{index}.metta" for index in range(2)]
        for index, path in enumerate(paths):
            path.write_text(
                f'!(let $name (atom_concat "owned-source-token" "") (bind! $name {index + 1}))\n'
            )
            context.self.load(path)
        assert context.run("!(quote owned-source-token)") == [[2]]
        assert not context.runtime.once(
            "metta_engine:metta_token('owned-source-token', 1)"
        )
        for index, answer in zip(order, answers, strict=True):
            context.runtime.must(
                "filereader:withdraw_source_load(File, Space, _)",
                File=str(paths[index]), Space=context.self.name,
            )
            assert context.run("!(quote owned-source-token)") == [[answer]]


def test_a_later_explicit_token_binding_survives_source_withdrawal(tmp_path):
    """Withdrawing a file cannot erase a subsequent caller replacement."""
    path = tmp_path / "claim.metta"
    path.write_text('!(let $name (atom_concat "caller-source-token" "") (bind! $name 1))\n')
    with MeTTa() as context:
        context.self.load(path)
        context.run('!(let $name (atom_concat "caller-source-token" "") (bind! $name 2))')
        context.runtime.must(
            "filereader:withdraw_source_load(File, Space, _)",
            File=str(path), Space=context.self.name,
        )
        assert context.run("!(quote caller-source-token)") == [[2]]


def test_a_failed_source_token_binding_restores_the_previous_value(tmp_path):
    """A failed first load preserves the value it temporarily shadowed."""
    path = tmp_path / "claim-failed.metta"
    path.write_text(
        '!(let $name (atom_concat "failed-source-token" "") (bind! $name 1))\n'
        f'!(import! &self "{tmp_path / "missing.metta"}")\n'
    )
    with MeTTa() as context:
        context.run('!(let $name (atom_concat "failed-source-token" "") (bind! $name 0))')
        with pytest.raises(SourceNotFound):
            context.self.load(path)
        assert context.run("!(quote failed-source-token)") == [[0]]


@pytest.mark.parametrize("declarations", [
    "()",
    "((direction bidirectional))",
    "((left ((owned-rule $x) (seed $x))) (right (owned-result $x)))",
])
def test_a_failed_rule_registration_retires_only_its_source_artifacts(tmp_path, declarations):
    """A failed registration preserves the caller equation and removes its derivatives."""
    path = tmp_path / "failed-rule.metta"
    path.write_text(
        f"!(add-translator-rule! owned-rule {declarations})\n"
        f'!(import! &self "{tmp_path / "missing.metta"}")\n'
    )
    with MeTTa() as context:
        context.run("(= (owned-rule $x) (noeval (owned-result $x)))")
        before = context.self.source()
        with pytest.raises(SourceNotFound):
            context.self.load(path)
        assert not context.runtime.once(
            "translator_rules:translator_rule('owned-rule', _, _)"
        )
        assert not context.runtime.once(
            "translator_rules:translator_rule_derived('owned-rule', _, _)"
        )
        assert not context.runtime.once(
            "translator_rules:translator_rule('owned-result', _, _)"
        )
        assert context.self.source() == before


def test_source_withdrawal_keeps_a_later_registration_in_the_same_module(tmp_path):
    """An old source receipt cannot retire a subsequent registration of its name."""
    path = tmp_path / "replaced-rule.metta"
    path.write_text("!(add-translator-rule! later-rule)\n")
    with MeTTa() as context:
        context.run("(= (later-rule $x) (noeval (later-result $x)))")
        context.self.load(path)
        context.run("!(remove-translator-rule! later-rule)")
        context.run("!(add-translator-rule! later-rule ((cost 3)))")
        context.runtime.must(
            "filereader:withdraw_source_load(File, Space, _)",
            File=str(path), Space=context.self.name,
        )
        assert context.runtime.once(
            "translator_rules:translator_rule_declared_cost('later-rule', 3)"
        )


def test_a_released_source_module_exposes_another_modules_token(tmp_path):
    """A module release removes only its source-owned claim on a shared token."""
    path = tmp_path / "other-module-token.metta"
    path.write_text('!(let $name (atom_concat "module-owned-token" "") (bind! $name 2))\n')
    with MeTTa() as original:
        original.run('!(bind! module-owned-token 1)')
        with MeTTa() as newer:
            newer.self.load(path)
            assert original.run("!(quote module-owned-token)") == [[2]]
        assert original.run("!(quote module-owned-token)") == [[1]]
