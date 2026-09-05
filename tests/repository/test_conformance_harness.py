"""Purpose: the conformance harness's own contracts, which nothing checked.

tests/conformance/petta.py is the gate that says this engine agrees with the
arbiter, and tests/conformance/petta_capture.py is what freezes the oracle it
gates against. Both were unchecked: petta.py cited a
test_the_conformance_gate_tells_the_three_cases_apart that had never existed,
so the wall had never been watched failing, and the capture's normalization,
its cleanliness rule and its skip set were believed rather than tested.

Guarantees:
  - the gate tells its three cases apart on a planted pin: an entry that
    agrees, one that does not, and one whose divergence is recorded
    [tested: test_the_conformance_gate_tells_the_three_cases_apart;
    commit=819393cb9608052a198ef0b2a8c0676d9ef9e824]
  - alpha canonicalisation is syntax-aware and scoped to one printed term, so
    a `$_7` inside a string literal is data, two answers reusing an allocation
    slot are not one variable, and sharing inside one term still decides
    [tested: test_a_variable_identifier_inside_a_string_is_data,
    test_two_answers_reusing_a_slot_are_not_one_variable,
    test_sharing_inside_one_printed_term_still_decides,
    test_a_term_printed_over_several_lines_keeps_its_sharing; commit=819393cb9608052a198ef0b2a8c0676d9ef9e824]
  - an untracked corpus input cannot enter the frozen artefact
    [tested: test_an_untracked_corpus_input_is_refused; commit=819393cb9608052a198ef0b2a8c0676d9ef9e824]
  - a skip is derived from a declared capability and reported when that
    capability arrives [tested: test_a_skip_is_derived_from_a_declared_capability,
    test_a_skip_whose_capability_arrived_is_reported; commit=819393cb9608052a198ef0b2a8c0676d9ef9e824]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "tests" / "conformance"))

import petta  # noqa: E402  -- REPO/tests/conformance must be on the path first
import petta_capture  # noqa: E402  -- REPO/tests/conformance must be on the path first

# ------------------------------------------------------------ the normalizer


def test_a_variable_identifier_inside_a_string_is_data():
    """A `$_N` in a string literal is program DATA, not an identifier.

    The regex this replaced renamed it, so two engines that printed different
    text in a string compared EQUAL: a soundness hole in the only equality the
    gate consults, because `alpha_equal` is what decides a `conforms` entry.
    """
    upstream = 'is "the token $_1 was seen", should "ok". OK\n'
    ours = 'is "the token $_2 was seen", should "ok". OK\n'
    assert upstream != ours
    assert petta.alpha(upstream) != petta.alpha(ours)

    # And an identifier OUTSIDE a string is still renamed, so the fix is a
    # narrowing of where the rule applies and not its removal.
    assert petta.alpha("answer $_1\n") == petta.alpha("answer $_9\n")


def test_two_answers_reusing_a_slot_are_not_one_variable():
    """Variable identity means something inside one printed term, not across.

    Two independent answers that happen to reuse an allocation slot were
    reported as a divergence, because the renaming namespace was the whole
    file.
    """
    upstream = "is $_0, should $_0. OK\nis $_0, should $_0. OK\n"
    ours = "is $_0, should $_0. OK\nis $_4, should $_4. OK\n"
    assert petta.alpha(upstream) == petta.alpha(ours)


def test_sharing_inside_one_printed_term_still_decides():
    """`(pair $x $x)` and `(pair $x $y)` are different terms and stay different."""
    shared = "answer (pair $_0 $_0)\n"
    distinct = "answer (pair $_0 $_1)\n"
    assert petta.alpha(shared) != petta.alpha(distinct)
    # Renaming the whole term is not a difference.
    assert petta.alpha(shared) == petta.alpha("answer (pair $_7 $_7)\n")


def test_a_term_printed_over_several_lines_keeps_its_sharing():
    """A record ends where the term does, not where the line does.

    Resetting at every physical line would make a repeated variable and two
    distinct ones the same text once the term wraps.
    """
    shared = "answer (pair $_7\n              $_7)\n"
    distinct = "answer (pair $_8\n              $_9)\n"
    assert petta.alpha(shared) != petta.alpha(distinct)


def test_the_verdict_halves_are_numbered_apart():
    """`is X, should Y` prints two terms, each numbering its own from zero.

    Measured against engine/main.pl: `!(test (foo $x) (foo $y))`, whose two
    variables are distinct, prints `is (foo $_0), should (foo $_0)`. Treating
    the line as one namespace therefore invents a coreference the writer never
    expressed, which is why the halves are canonicalised apart.
    """
    # The identifier repeats ACROSS the halves in one and not in the other.
    # Under one namespace those are different texts; under two they are the
    # same, and two is what the writer produces.
    repeated = "is (-> $_0 Bool), should (-> $_0 Bool). ✅ \n"
    apart = "is (-> $_0 Bool), should (-> $_7 Bool). ✅ \n"
    assert petta.alpha(repeated) == petta.alpha(apart)
    # Sharing WITHIN one half is still sharing, so the split narrows the
    # namespace rather than abandoning it.
    assert petta.alpha("is (-> $_0 $_0), should (x). ✅ \n") != petta.alpha(
        "is (-> $_0 $_1), should (x). ✅ \n"
    )
    # The split is at the TOP-LEVEL delimiter, so one nested inside a string
    # literal is not a split point: `$_0` and `$_5` stay one namespace here.
    nested = 'is (say ", should " $_0 $_5). ✅ \n'
    assert petta.alpha(nested) != petta.alpha('is (say ", should " $_0 $_0). ✅ \n')


def test_the_canonical_form_is_stable_under_reapplication():
    """Canonicalising a canonical form changes nothing.

    A marker that collided with what the input can already spell would break
    this, because the second pass would rename its own output.
    """
    text = "is (pair $_0 $_1), should (pair $_2 $_2). ✅ \nanswer $_9\n"
    once = petta.alpha(text)
    assert petta.alpha(once) == once


# -------------------------------------------------------------- the gate


PROGRAM = "!(test (+ 1 2) 3)\n"


def _pin(root: Path, entries: dict[str, dict], outputs: dict[str, str]) -> Path:
    """A whole conformance pin, written from scratch."""
    (root / "examples").mkdir(parents=True, exist_ok=True)
    (root / "expected").mkdir(parents=True, exist_ok=True)
    for name in entries:
        (root / "examples" / name).write_text(PROGRAM)
        (root / "expected" / f"{name}.out").write_text(outputs[name])
    (root / "MANIFEST.json").write_text(
        json.dumps({"upstream": "x", "commit": "0" * 40, "captured_with": "test",
                    "engine_flag": "silent", "skips": {}, "excluded": {},
                    "entries": entries}, indent=1, sort_keys=True) + "\n"
    )
    return root


def _gate(pin: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(REPO / "tests/conformance/petta.py"),
         "--gate", "--timeout", "90", "--show", "4"],
        capture_output=True, text=True, check=False,
        env={**os.environ, "PETTA_PIN": str(pin)},
    )


def test_the_conformance_gate_tells_the_three_cases_apart(tmp_path):
    """A gate that cannot be pointed at a planted disagreement is a wall.

    PETTA_PIN exists so this one can be, and until now nothing used it: the
    citation that named this test pointed at a name no file defined.
    """
    truth = "is 3, should 3. ✅ \ntrue\n"

    agreeing = _gate(_pin(tmp_path / "agree", {"a.metta": {"rc": 0, "status": "conforms"}},
                          {"a.metta": truth}))
    assert agreeing.returncode == 0, agreeing.stdout + agreeing.stderr
    assert "agreeing        : 1/1" in agreeing.stdout
    assert "blocking        : 0" in agreeing.stdout

    differing = _gate(_pin(tmp_path / "differ", {"a.metta": {"rc": 0, "status": "conforms"}},
                           {"a.metta": "is 3, should 4. ❌ \ntrue\n"}))
    assert differing.returncode == 1, differing.stdout
    assert "blocking        : 1" in differing.stdout

    ruled = _gate(_pin(
        tmp_path / "ruled",
        {"a.metta": {"rc": 0, "status": "diverges", "ours": truth}},
        {"a.metta": "is 3, should 4. ❌ \ntrue\n"},
    ))
    assert ruled.returncode == 0, ruled.stdout
    assert "recorded rulings: 1" in ruled.stdout

    # And a recorded divergence that stops differing in the recorded way is a
    # stale ruling, which blocks: the exemption is a ruling, not a hole.
    stale = _gate(_pin(
        tmp_path / "stale",
        {"a.metta": {"rc": 0, "status": "diverges", "ours": "is 3, should 9. ❌ \n"}},
        {"a.metta": "is 3, should 4. ❌ \ntrue\n"},
    ))
    assert stale.returncode == 1, stale.stdout
    assert "blocking        : 1" in stale.stdout


# ----------------------------------------------------------- the capture


def _upstream(root: Path) -> Path:
    """A scratch checkout shaped like upstream PeTTa, with one commit."""
    (root / "examples").mkdir(parents=True)
    (root / "src").mkdir(parents=True)
    (root / "lib").mkdir(parents=True)
    (root / "examples" / "tracked.metta").write_text(PROGRAM)
    (root / "src" / "main.pl").write_text(":- initialization(main, main).\nmain :- true.\n")
    (root / "lib" / "lib_x.metta").write_text(";; support\n")
    for command in (
        ["git", "init", "-q"],
        ["git", "add", "-A"],
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "fixture"],
    ):
        subprocess.run(command, cwd=root, check=True, capture_output=True)
    return root


def test_an_untracked_corpus_input_is_refused(tmp_path):
    """A scratch file must not enter an artefact pinned to a commit.

    upstream_commit's cleanliness check deliberately ignores `??` lines,
    because an upstream checkout carries build output and editor files that
    have nothing to do with the corpus, and that same tolerance let an
    untracked example through the glob. CeTTa's generator froze 21 such files
    for exactly this reason.
    """
    upstream = _upstream(tmp_path / "upstream")
    (upstream / "examples" / "scratch.metta").write_text(PROGRAM)

    # The whole-tree check still passes, which is the point.
    assert petta_capture.upstream_commit(upstream)

    tracked = petta_capture.tracked_examples(upstream)
    assert "examples/tracked.metta" in tracked
    assert "examples/scratch.metta" not in tracked

    with pytest.raises(SystemExit) as refused:
        petta_capture.refuse_untracked(
            upstream, ["examples/tracked.metta", "examples/scratch.metta"]
        )
    assert "examples/scratch.metta" in str(refused.value)
    assert "not\ntracked" in str(refused.value).replace(" ", "\n")

    # A tracked-only corpus is admitted, so the refusal is about tracking and
    # not about refusing everything.
    petta_capture.refuse_untracked(upstream, ["examples/tracked.metta", "lib/lib_x.metta"])


def test_a_skip_is_derived_from_a_declared_capability(monkeypatch):
    """Membership follows the capability, and the reason is the capability's.

    The list this replaced named torch.metta with "needs torch installed" on a
    box where torch imports, and nothing checked it [measured 2026-09-05].
    """
    for name, wanted in petta_capture.REQUIREMENTS.items():
        assert wanted, f"{name} declares no requirement, so it would never be skipped"
        for need in wanted:
            assert need in petta_capture.CAPABILITIES, f"{name} names an undeclared {need}"

    present = dict(petta_capture.CAPABILITIES)
    monkeypatch.setattr(
        petta_capture, "CAPABILITIES",
        {name: (True, why) for name, (_, why) in present.items()},
    )
    assert petta_capture.skips() == {}, "everything present must skip nothing"

    monkeypatch.setattr(
        petta_capture, "CAPABILITIES",
        {name: (False, why) for name, (_, why) in present.items()},
    )
    absent = petta_capture.skips()
    assert set(absent) == set(petta_capture.REQUIREMENTS)
    for name, wanted in petta_capture.REQUIREMENTS.items():
        for need in wanted:
            assert present[need][1] in absent[name], (
                f"{name}'s reason does not carry {need}'s own sentence"
            )


def test_a_skip_whose_capability_arrived_is_reported(monkeypatch):
    """A stale exclusion is visible rather than believed."""
    manifest = {"skips": {"torch.metta": "needs torch installed",
                          "repl.metta": "needs an interactive terminal"}}

    monkeypatch.setattr(
        petta_capture, "CAPABILITIES",
        {name: (name == "torch", why)
         for name, (_, why) in petta_capture.CAPABILITIES.items()},
    )
    assert petta.stale_skips(manifest) == {"torch.metta": "needs torch installed"}

    monkeypatch.setattr(
        petta_capture, "CAPABILITIES",
        {name: (False, why) for name, (_, why) in petta_capture.CAPABILITIES.items()},
    )
    assert petta.stale_skips(manifest) == {}
