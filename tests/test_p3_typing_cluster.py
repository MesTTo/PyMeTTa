"""Purpose: exercise the public typing and policy contracts introduced by P3.
Guarantees:
  - type faults remain ordinary Error values that ``if-error`` can observe.
  [tested: test_an_argument_type_fault_is_a_value_a_program_can_catch; commit=WORKTREE]
  - DontEvalType declarations mask evaluation without relying on a type name.
  [tested: test_a_user_declared_lazy_type_receives_its_argument_unevaluated; commit=WORKTREE]
  - a duplicate declaration is refused with the existing row in the message.
  [tested: test_a_duplicate_declaration_names_the_first_one; commit=WORKTREE]
  - pragma! accepts only keys whose setting changes an engine mechanism.
  [tested: test_no_pragma_key_is_accepted_and_inert; commit=WORKTREE]
  - under-applied arrow heads have no type instead of a tuple fallback.
  [tested: test_an_underapplied_arrow_head_types_as_the_arbiter_does; commit=WORKTREE]
"""

import pytest

from petta import MeTTa


def _answers(metta: MeTTa, source: str) -> list[str]:
    """Return one query group's atoms in their stable textual form."""
    groups = metta.run(source)
    assert len(groups) == 1
    return [str(atom) for atom in groups[0]]


def test_an_argument_type_fault_is_a_value_a_program_can_catch():
    metta = MeTTa(verbose=False)
    metta.run("(: p32-f (-> Number Number))")
    metta.run("(= (p32-f $x) $x)")

    assert _answers(metta, '!(if-error (p32-f "wrong") caught missed)') == [
        "caught"
    ]
    assert _answers(metta, "!(if-error (p32-f 1 2) caught missed)") == [
        "caught"
    ]
    assert _answers(
        metta, '!(if-error (type-cast "wrong" Number &self) caught missed)'
    ) == ["caught"]


def test_a_user_declared_lazy_type_receives_its_argument_unevaluated():
    metta = MeTTa(verbose=False)
    metta.run("(: OpaquePayload DontEvalType)")
    metta.run("(: inspect-opaque (-> OpaquePayload Symbol))")
    metta.run("(= (inspect-opaque $written) (get-metatype $written))")

    assert _answers(metta, "!(inspect-opaque (+ 1 2))") == ["Expression"]

    metta.run("(: LooksDontEval Type)")
    metta.run("(: inspect-eager (-> LooksDontEval Symbol))")
    metta.run("(= (inspect-eager $value) (get-metatype $value))")
    eager = _answers(metta, "!(inspect-eager (+ 1 2))")
    assert eager == [
        "(Error (inspect-eager (+ 1 2)) "
        "(BadArgType 1 LooksDontEval Number))"
    ]


def test_a_duplicate_declaration_names_the_first_one():
    metta = MeTTa(verbose=False)
    first = "(: duplicate-op (-> Number Number))"
    metta.run(first)

    def duplicate_op(value: int) -> int:
        return value

    with pytest.raises(Exception) as refused:
        metta.register_op(duplicate_op, name="duplicate-op")

    message = str(refused.value)
    assert "duplicate" in message
    assert "the first declaration is (: duplicate-op (-> Number Number))" in message
    assert _answers(metta, "!(duplicate-op 5)") == ["(duplicate-op 5)"]


def test_no_pragma_key_is_accepted_and_inert():
    metta = MeTTa(verbose=False)

    assert _answers(metta, "!(pragma! max-inferences 100000)") == ["()"]
    assert _answers(metta, "!(pragma! max-inferences none)") == ["()"]

    for key, value in (
        ("type-check", "auto"),
        ("max-stack-depth", "100"),
        ("interpreter", "bare-minimal"),
        ("unknown-policy", "on"),
    ):
        with pytest.raises(Exception, match=f"metta_pragma_key.*{key}"):
            metta.run(f"!(pragma! {key} {value})")


def test_an_underapplied_arrow_head_types_as_the_arbiter_does():
    metta = MeTTa(verbose=False)
    metta.run("(: Nil (List $t))")
    metta.run("(: Cons (-> $t (List $t) (List $t)))")

    assert _answers(metta, "!(get-type (Cons 1))") == []
    assert _answers(metta, "!(get-type (Cons 1 Nil))") == ["(List Number)"]
