"""Purpose: pin theory and full-interpreter selection on one answer ask.
Guarantees:
  - theory data evaluates in isolated scratch state and an interpreter head
    receives target, expected type, and receiver without either selector
    mutating the receiver [tested:
    test_answers_selects_a_theory_or_interpreter_per_ask;
    commit=7c4ddf46d4e23de8390a9f2baddbf96f7575da46]
  - a theory-local or receiver-local definition hides an inherited typed
    declaration for dispatch while get-type still reports it, including when
    a nested typed call makes its argument statically settled [tested:
    test_an_inherited_arrow_does_not_veto_a_local_definition;
    commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import os
import subprocess
import sys

import pytest

from metta import S, equation

_TYPED_SHADOWING_PROBE = r"""
from metta import MeTTa, S, equation, lib

session = MeTTa().space("&self")
before = session._new_space()
print("before", list(before.answers(S["get-type"](S.choice))))

session += lib.strategy
session.run(
    "(: p14-shadow-outer (-> Number Result))\n"
    "(: p14-shadow-inner (-> Number Number))\n"
    "(= (p14-shadow-inner $x) $x)"
)
inherited = session._new_space()
print("inherited-type", list(inherited.answers(S["get-type"](S.choice))))
print("inherited-call", list(inherited.answers(S.choice())))

local = session._new_space()
local_choice = equation(S.choice()).to(S.base)
local.add(local_choice)
local.add(equation(S["p14-run-choice"]()).to(S.choice()))
laws = (
    equation(S.choice()).to(S.left),
    equation(S.choice()).to(S.right),
)
print("local-type", list(local.answers(S["get-type"](S.choice))))
print("local-call", list(local.answers(S.choice())))
print("theory-call", list(local.answers(S.choice(), theory=laws)))
print("wrapper-before-remove", list(local.answers(S["p14-run-choice"]())))
print("removed", local.remove(local_choice))
print("local-after-remove", list(local.answers(S.choice())))
print("wrapper-after-remove", list(local.answers(S["p14-run-choice"]())))

declared = session._new_space()
declared.run("(: choice (-> Result))\n(= (choice) local)")
print("declared-call", list(declared.answers(S.choice())))

nested = session._new_space()
nested.run("(: p14-shadow-outer (-> String Result))")
print("local-literal", list(nested.answers(S["p14-shadow-outer"](1))))
print(
    "local-nested",
    list(nested.answers(S["p14-shadow-outer"](S["p14-shadow-inner"](1)))),
)
"""


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


def test_an_inherited_arrow_does_not_veto_a_local_definition():
    """Lexical lookup and reporting answer different declaration questions."""
    environment = os.environ | {"PYTHONPATH": os.pathsep.join(sys.path)}
    completed = subprocess.run(
        [sys.executable, "-c", _TYPED_SHADOWING_PROBE],
        capture_output=True,
        text=True,
        env=environment,
        timeout=120,
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.splitlines() == [
        "before [%Undefined%]",
        "inherited-type [(-> Atom Atom Atom %Undefined%)]",
        "inherited-call [(Error (choice) IncorrectNumberOfArguments)]",
        "local-type [(-> Atom Atom Atom %Undefined%)]",
        "local-call [base]",
        "theory-call [left, right]",
        "wrapper-before-remove [base]",
        "removed True",
        "local-after-remove [(Error (choice) IncorrectNumberOfArguments)]",
        "wrapper-after-remove [(Error (choice) IncorrectNumberOfArguments)]",
        "declared-call [local]",
        "local-literal [(Error (p14-shadow-outer 1) (BadArgType 1 String Number))]",
        "local-nested [(Error (p14-shadow-outer (p14-shadow-inner 1)) (BadArgType 1 String Number))]",
    ]
