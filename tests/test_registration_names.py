"""Purpose: keep operation registration names reachable through MeTTa source.

Guarantees:
  - register_op refuses every spelling the engine reader would not recover as
    one symbol, identifies the conflicting character, and leaves no engine or
    reflection state behind [tested:
    test_register_op_refuses_a_name_metta_cannot_read;
    commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

import pytest


def test_register_op_refuses_a_name_metta_cannot_read(metta):
    """Every refusal happens before either registration table changes."""
    cases = {
        "": "empty",
        "has space": "character ' '",
        "has(parenthesis": "character '('",
        'has"quote': "character '\"'",
        "has;comment": "character ';'",
        "$variable": "character '$'",
        "42": "character '4'",
        "True": "character 'T'",
    }
    before = metta.builtins()

    for name, witness in cases.items():
        with pytest.raises(ValueError) as raised:
            metta.op(lambda value: value, name=name)

        message = str(raised.value)
        assert name in message
        assert witness in message
        assert metta.builtins() == before
        assert not metta.runtime.once(
            "atom_string(_Name, Name), petta_py_op_spec(_Name, _, _)", Name=name
        )
        assert not metta.runtime.once(
            "atom_string(_Name, Name), petta_contract_fact([op, _Name, _, _])",
            Name=name,
        )
