"""Purpose: pin the library defects exposed by the P14 twin authoring wave.

Guarantees:
  - a bound call whose resolved MeTTa name ends in ``!`` completes its effect
    before the Python call returns [tested: test_resolved_bang_call_is_eager;
    commit=WORKTREE]
"""

from pathlib import Path

from petta import S, UNIT, space


def test_resolved_bang_call_is_eager(tmp_path: Path) -> None:
    source = tmp_path / "eager-effect.metta"
    source.write_text("(= (libfix-eager-effect) eager)\n", encoding="utf-8")
    target = space()

    answers = target.fn["import!"](target, str(source))

    assert target.eval(S["libfix-eager-effect"]()) == [S.eager]
    assert list(answers) == [UNIT]
