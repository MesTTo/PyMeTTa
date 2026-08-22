"""Purpose: prove m.eval honours the same evaluation bounds `!` honours.
Assumes: a subprocess can import petta from the repository checkout; the probe
  runs there rather than in-process because the defect this pins ABORTS the
  interpreter, and an aborted pytest worker is a worse diagnostic than a
  failed assertion.
Guarantees:
  - both doors answer the same atoms for the same source under the same
    pragma, and a runaway recursion answers (Error ... StackOverflow) rather
    than exhausting SWI's stack.
  [tested: test_the_same_source_answers_the_same_error_through_both_doors; commit=657ae9672c07b628f8a20c7fe39aa43e58b0014f]
Fails when: the bound is read as a guarantee about wall clock or memory. It is
  branch-local reduction fuel, and a branch that finishes keeps its answer.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the contract is one continuous invariant, not summary-and-body prose

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]

# The coverage lane's one DECLINED form, examples/basics/time_and_pragmas.metta
# form 15, written both ways. The two equations are non-exclusive, so the base
# case answers 120 and the runaway branch is what max-stack-depth stops.
_SETUP = (
    "!(pragma! max-stack-depth 20)\n"
    "(= (bounded-factorial 0) 1)\n"
    "(= (bounded-factorial $n) (* $n (bounded-factorial (- $n 1))))\n"
)

_PROBE = f"""
import sys
sys.path.insert(0, {str(REPO / "bindings" / "python")!r})
from petta import MeTTa, S

metta = MeTTa()
metta.run({_SETUP!r})
door = sys.argv[1]
if door == "bang":
    (answers,) = metta.run("!(bounded-factorial 5)")
else:
    answers = metta.eval(S["bounded-factorial"](5))
print("|".join(str(atom) for atom in answers))
"""


def _door(name: str) -> str:
    """Run the probe through one door in its own interpreter."""
    result = subprocess.run(
        [sys.executable, "-c", _PROBE, name],
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    assert result.returncode == 0, f"{name} door exited {result.returncode}: {result.stderr[-2000:]}"
    return result.stdout.strip().splitlines()[-1]


def test_the_same_source_answers_the_same_error_through_both_doors() -> None:
    """m.eval and the runnable form answer the same atoms under the same pragma."""
    through_bang = _door("bang")
    through_eval = _door("eval")
    assert through_bang == through_eval
    assert through_bang == "120|(Error -3 StackOverflow)"
