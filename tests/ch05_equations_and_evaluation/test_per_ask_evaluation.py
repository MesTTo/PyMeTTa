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
    commit=7b238053d2907cd514e3fd9a29927d43a53c5a3c]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import os
import subprocess
import sys

from metta import S, V, equation

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

    # They COMPOSE. The interpreter is handed the theory's space, so it
    # interprets the theory: head and third argument of one application, not
    # rival answers to one question.
    space.run("(: compose-eval (-> Atom Atom Atom %Undefined%))")
    space.run("(= (compose-eval $t $ty $s) (Traced (metta $t $ty $s)))")
    composed = list(
        space.answers(S.choice(), theory=laws, interpreter=S["compose-eval"])
    )
    assert composed == [S.Traced(S.left), S.Traced(S.right)]
    assert list(space.answers(S.choice(), interpreter=S["compose-eval"])) == [
        S.Traced(S.base)
    ]


def test_eval_status_selects_the_same_relations_answers_does(metta):
    """The door that REPORTS the evaluation path can select one.

    eval_status took timeout= and inferences= while eval() and answers()
    took those plus under=, theory= and interpreter=. Being unable
    to point the status door at an alternative evaluation relation was the
    sharpest form of that gap: an explicit interpreter is exactly when
    "did anything reduce this, or is it its own answer" is worth asking.
    """
    space = metta._new_space()
    space.add(equation(S.choice()).to(S.base))
    laws = (
        equation(S.choice()).to(S.left),
        equation(S.choice()).to(S.right),
    )

    assert space.eval_status(S.choice()) == [("value", S.base)]
    assert space.eval_status(S.choice(), theory=laws) == [
        ("value", S.left),
        ("value", S.right),
    ]
    # The receiver is unchanged by the ask.
    assert space.eval_status(S.choice()) == [("value", S.base)]

    interpreter = space.define(_ask_interpreter, name="status-interpreter")
    target = S.Payload(S.value)
    # Without one the term is its own answer; with one the application reduces.
    assert space.eval_status(target) == [("not-reducible", target)]
    assert space.eval_status(target, interpreter=interpreter) == [
        ("value", S.Interpreted(target, S["%Undefined%"], space))
    ]

    # And they compose here for the same reason they compose on answers().
    space.run("(: status-eval (-> Atom Atom Atom %Undefined%))")
    space.run("(= (status-eval $t $ty $s) (Traced (metta $t $ty $s)))")
    assert space.eval_status(
        S.choice(), theory=laws, interpreter=S["status-eval"]
    ) == [("value", S.Traced(S.left)), ("value", S.Traced(S.right))]


def test_an_interpreter_must_declare_its_metatypes(metta):
    """`Atom` in, `%Undefined%` out, or the engine reduces around it.

    MeTTa reduces a call's arguments before the callee sees them, so an
    interpreter declared the ordinary way is handed the ANSWER rather than the
    term it was meant to interpret, and its own answer is not reduced when the
    return metatype is `Atom`. Both halves are the declaration's job and
    neither is this door's to enforce -- MeTTa would call either function
    happily -- so the contract states them and this measures them.
    """
    space = metta._new_space()
    space.add(equation(S.choice()).to(S.base))

    @space.define(name="plain-interp")
    def plain_interp(term, _expected, _space):
        return S.Saw(term)

    # An ordinary define sees the reduced answer.
    assert list(space.answers(S.choice(), interpreter=S["plain-interp"])) == [
        S.Saw(S.base)
    ]

    # An Atom-typed first parameter sees the term.
    space.run("(: atom-interp (-> Atom Atom Atom %Undefined%))")
    space.run("(= (atom-interp $t $ty $s) (Saw $t))")
    assert list(space.answers(S.choice(), interpreter=S["atom-interp"])) == [
        S.Saw(S.choice())
    ]

    # An Atom RETURN metatype leaves the interpreter's own answer unreduced.
    space.run("(: unreduced-interp (-> Atom Atom Atom Atom))")
    space.run("(= (unreduced-interp $t $ty $s) (metta $t $ty $s))")
    assert list(space.answers(S.choice(), interpreter=S["unreduced-interp"])) == [
        S.metta(S.choice(), S["%Undefined%"], space)
    ]


def test_derivation_binds_host_values_like_the_doors_beside_it(metta):
    """A binding lands BEFORE the search, so a bound proof was unaskable."""
    space = metta._new_space()
    space.add(equation(S["p14-proof-double"](V.x)).to(S["*"](V.x, 2)))

    direct = space.derivation(S["p14-proof-double"](5))
    with space.bind({"n": 5}):
        bound = space.derivation(S["p14-proof-double"](S.n))
    # Same call and same answer. Not the whole tree: the engine names an
    # unresolved variable freshly per search, so the equations inside read
    # `$_1` and `$_2` for the same equation.
    assert [(proof.call, proof.answer) for proof in bound] == [
        (proof.call, proof.answer) for proof in direct
    ]
    assert bound

    # Without it the symbol is just a symbol, so nothing reduces and no
    # proof exists, which is the state that made the question unaskable.
    assert space.derivation(S["p14-proof-double"](S.n)) != bound


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
