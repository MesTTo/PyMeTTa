"""Purpose: pin the library defects exposed by the P14 twin authoring wave.

Guarantees:
  - a bound call whose resolved MeTTa name ends in ``!`` completes its effect
    before the Python call returns [tested: test_resolved_bang_call_is_eager;
    commit=WORKTREE]
  - bound calls expose evaluation values through iteration and scalar doors,
    with caller bindings retained on their row and projection faces both in
    and out of a stats scope [tested: test_calls_keep_values_and_binding_rows;
    commit=WORKTREE]
"""

from pathlib import Path

from petta import TRUE, UNIT, G, S, V, space


def test_resolved_bang_call_is_eager(tmp_path: Path) -> None:
    """A statement-like import is complete without observing its answers."""
    source = tmp_path / "eager-effect.metta"
    source.write_text("(= (libfix-eager-effect) eager)\n", encoding="utf-8")
    target = space()

    answers = target.fn["import!"](target, str(source))

    assert target.eval(S["libfix-eager-effect"]()) == [S.eager]
    assert list(answers) == [UNIT]


def test_calls_keep_values_and_binding_rows() -> None:
    """Values and bindings stay available through distinct answer faces."""
    target = space()
    target.run(
        "(libfix-answer-fact 41)\n"
        "(= (libfix-answer-pick $x) "
        "(match &self (libfix-answer-fact $x) True))"
    )

    answers = target.fn["libfix-answer-pick"](V.x)

    assert list(answers) == [TRUE]
    assert list(answers.x) == [G(41)]
    assert answers.rows[0].x == G(41)
    assert answers.one() is True

    @target.define(name="libfix-defined-truth")
    def defined_truth(_value):
        return True

    outside = defined_truth(V.value)
    with target.stats():
        inside = defined_truth(V.value)

    assert outside.one() is True
    assert inside.one() is True
