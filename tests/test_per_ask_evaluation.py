"""Purpose: pin theory and full-interpreter selection on one answer ask.
Guarantees:
  - theory data evaluates in isolated scratch state and an interpreter head
    receives target, expected type, and receiver without either selector
    mutating the receiver [tested:
    test_answers_selects_a_theory_or_interpreter_per_ask;
    commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import pytest

from metta import S, equation


def _ask_interpreter(code, expected, context):
    return S.Interpreted(code, expected, context)


def test_answers_selects_a_theory_or_interpreter_per_ask(metta):
    """A theory replaces rules for one cursor; an interpreter wraps one call."""
    space = metta._new_space()
    space.add(equation(S.choice()).to(S.base))
    laws = (
        equation(S.choice()).to(S.left),
        equation(S.choice()).to(S.right),
    )

    selected = space.answers(S.choice(), theory=laws)
    assert list(selected) == [S.left, S.right]
    assert space.answers(S.choice()) == [S.base]

    interpreter = space.define(_ask_interpreter, name="ask-interpreter")
    target = S.Payload(S.value)
    assert space.answers(target) == [target]
    assert space.answers(target, interpreter=interpreter) == [
        S.Interpreted(target, S["%Undefined%"], space)
    ]

    with pytest.raises(TypeError, match="pass one of them per answers"):
        space.answers(target, theory=laws, interpreter=interpreter)
