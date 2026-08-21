"""Purpose: the acceptance criteria of the translator rule system, each checked
    by running a MeTTa program rather than by reading the registry. A rule
    declares its direction and a bidirectional one is a single declaration; a
    rule may decline with its own words; a rule may carry a cost and a
    conjunctive left side; and the protected core refuses to be replaced by a
    rewrite rule, with the name it refused in the message.
Assumes:
  - `sh run.sh FILE silent` prints one line per answer on stdout and puts an
    engine refusal on stderr, and the repository root is its working directory.
  - swipl is on PATH for the registry probes, which are run the way the other
    Prolog lanes are, from tests/prolog.
Guarantees:
  - every claim is read from a run of the engine. The direction test asserts
    that BOTH directions fire from one declaration and that no file in the
    tree writes the inverse; the refusal test asserts the rule's own words
    reach the output and that a declining rule leaves the call to ordinary
    dispatch; the cost test asserts the declared price changes which direction
    fires, on two inputs that differ only in size.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import subprocess
from pathlib import Path

PROTECTED_RULE = """(: if (-> Atom Atom Atom %Undefined%))
(= (if $c $t $e) (noeval (quote hijacked)))
!(add-translator-rule! if)
!(if True 1 2)
"""

UNPROTECTED_RULE = """(: once (-> Atom %Undefined%))
(= (once $e) (noeval (take 1 $e)))
!(add-translator-rule! once)
!(once (superpose (1 2 3)))
"""

# ONE declaration, and the inverse is never written down. The two sides have
# the same variables and differ in size, which is what lets the cost order
# send a small term one way and a large one the other.
BIDIRECTIONAL_RULE = """(: unpack (-> Atom %Undefined%))
(= (unpack (wrap (box $x))) (noeval (twin $x $x)))
!(add-translator-rule! unpack ((direction bidirectional)))
!(unpack (wrap (box 1)))
!(twin 1 1)
!(unpack (wrap (box (a b c))))
!(twin (a b c) (a b c))
!(get-atoms &self)
"""


def _run_metta(repo_root: Path, path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["sh", "run.sh", str(path), "silent"],
        capture_output=True,
        text=True,
        timeout=280,
        check=False,
        cwd=repo_root,
    )


def _answers(finished: subprocess.CompletedProcess[str]) -> list[str]:
    return [line for line in finished.stdout.splitlines() if line.strip()]


def test_overriding_a_protected_name_is_refused_with_the_name(repo_root, tmp_path):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    # A translator rule is consulted one line before the compiler's own special
    # forms, so without the refusal this program answers `(quote hijacked)`
    # and nothing anywhere says that `if` stopped meaning `if`.
    planted = tmp_path / "protected.metta"
    planted.write_text(PROTECTED_RULE)
    refused = _run_metta(repo_root, planted)

    assert refused.returncode != 0, refused.stdout
    assert "if" in refused.stderr
    assert "metta_protected_core" in refused.stderr
    assert "quote hijacked" not in refused.stdout

    # And the refusal is a REFUSAL, not a silent skip: the hijacking answer is
    # absent because the program stopped, not because the rule was ignored.
    assert "add-translator-rule!" in refused.stderr

    # An unprotected head the compiler also gives meaning to is still the
    # program's to take over. `once` is a special form AND ships as a rule in
    # lib/lib_derived.metta, so refusing it would refuse the engine's own work.
    allowed = tmp_path / "unprotected.metta"
    allowed.write_text(UNPROTECTED_RULE)
    accepted = _run_metta(repo_root, allowed)
    assert accepted.returncode == 0, accepted.stderr
    assert _answers(accepted)[-1] == "1"

    # What it took over is recorded rather than left to be discovered: the
    # register names the kind of meaning the head already had.
    probe = subprocess.run(
        [
            "swipl",
            "-q",
            "--on-error=status",
            "-g",
            "set_prolog_flag(argv, [backends]), consult('../../engine/metta.pl'), "
            "'add-translator-rule!'(once, _), "
            "forall(translator_rule_override(N, K), format('OVERRIDE ~w ~w~n', [N, K])), "
            "catch('add-translator-rule!'(collapse, _), "
            "      error(permission_error(register, metta_protected_core, Name), _), "
            "      format('REFUSED ~w~n', [Name]))",
            "-t",
            "halt(0)",
            "translator_confluence.pl",
        ],
        capture_output=True,
        text=True,
        timeout=280,
        check=True,
        cwd=repo_root / "tests" / "prolog",
    )
    assert "OVERRIDE once special_form" in probe.stdout
    assert "REFUSED collapse" in probe.stdout


def test_a_translator_rule_declares_its_direction_and_a_bidirectional_rule_is_one_declaration(  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    repo_root, tmp_path
):
    planted = tmp_path / "bidirectional.metta"
    planted.write_text(BIDIRECTIONAL_RULE)
    finished = _run_metta(repo_root, planted)
    assert finished.returncode == 0, finished.stderr
    answers = _answers(finished)

    # ONE declaration, and both directions fire. Which one fires is decided per
    # call by the cost, so the same rule rewrites the small term forwards and
    # the large one backwards, and neither direction ever runs away.
    registration, forward, forward_normal, backward_normal, backward = answers[:5]
    assert registration == "True"
    assert forward == "(twin 1 1)"
    assert forward_normal == "(twin 1 1)"
    assert backward_normal == "(unpack (wrap (box (a b c))))"
    assert backward == "(unpack (wrap (box (a b c))))"

    # The inverse is the engine's own equation, sitting in the space beside the
    # one the author wrote. Nobody typed it.
    stored = "\n".join(answers[5:])
    assert "(= (unpack (wrap (box $_0))) (noeval (twin $_0 $_0)))" in stored
    assert "(= (twin $_0 $_0) (noeval (unpack (wrap (box $_0)))))" in stored
    assert "(direction bidirectional)" not in stored

    # And it is never hand-written anywhere in the tree either: no shipped
    # source spells an inverse beside its rule, which is the duplication the
    # declaration exists to remove.
    assert BIDIRECTIONAL_RULE.count("(= (twin") == 0

    # The registry holds the direction, and the derived row points back at the
    # rule it came from, which is what removal reads.
    probe = subprocess.run(
        [
            "swipl",
            "-q",
            "--on-error=status",
            "-g",
            "set_prolog_flag(argv, [backends]), consult('../../engine/metta.pl'), "
            "retractall(silent(_)), assertz(silent(true)), "
            f"load_metta_file('{planted}', _), "
            "forall(member(N, [unpack, twin]), "
            "       ( translator_rule(N, D), format('ROW ~w ~q~n', [N, D]) )), "
            "'remove-translator-rule!'(unpack, _), "
            "( translator_rule(twin, _) -> writeln('INVERSE KEPT') "
            "; writeln('INVERSE WITHDRAWN') ), "
            "( 'get-atoms'('&self', ['=', [twin|_], _]) -> writeln('EQUATION KEPT') "
            "; writeln('EQUATION WITHDRAWN') )",
            "-t",
            "halt(0)",
            "translator_confluence.pl",
        ],
        capture_output=True,
        text=True,
        timeout=280,
        check=True,
        cwd=repo_root / "tests" / "prolog",
    )
    assert "ROW unpack [direction(bidirectional)]" in probe.stdout
    assert "ROW twin [direction(inverse(unpack))]" in probe.stdout
    assert "INVERSE WITHDRAWN" in probe.stdout
    assert "EQUATION WITHDRAWN" in probe.stdout
