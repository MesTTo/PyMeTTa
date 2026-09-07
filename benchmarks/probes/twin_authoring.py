"""Purpose: price what AUTHORING a compiled definition costs, which is what the
twins lane's band must allow a twin whose example has no definition to author.
Assumes: run as `python extensions/python/benchmarks/probes/twin_authoring.py`
  from the repository root. The fixtures are priced through the LANE's own
  `run_twin`, so the constant this derives is the constant the band applies
  rather than one measured through a different runner; each reading is a fresh
  process because janus holds ONE Prolog VM per process and a second engine in
  the same process reads a warm image, which hides the first definition's
  premium entirely.
Guarantees: prints `definitions=<n> inferences=<m>` for n in 0..4 and the
  linear fit under them, each the minimum of three fresh processes. The fit is
  `twin_coverage.DEFINITION_WARMUP` plus `DEFINITION_COST` per definition, and
  those two constants are re-derived from this output [measured 2026-09-07: 5,
  2682, 3974, 5282, 6602, the fit 1370 once plus 1307 each, against the
  1456-plus-765 measured on 2026-08-22, which had gone stale by 71% per
  definition; commit=WORKTREE].
Fails when: run from anywhere but the repository root, which is where the
  twins lane launches its own children.
"""  # noqa: D205  -- the contract header is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import itertools
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "extensions" / "python"))
sys.path.insert(0, str(ROOT / "extensions" / "python" / "tools"))

import twin_coverage as lane  # noqa: E402

ROUNDS = 3

FIXTURE = '''\
"""One fixture holding n one-line compiled definitions."""


def twin(m):
    """Author n definitions and assert nothing about them."""
{body}
    assert True


#: The lane reads a BUDGET from every file it prices; this one is a fixture.
BUDGET = 1
'''


def fixture(directory: Path, count: int) -> Path:
    """One file holding `count` one-line decorated definitions."""
    body = (
        "".join(
            f"\n    @m.define\n    def f{index}(x):\n        return x + {index}\n"
            for index in range(count)
        )
        or "    assert m is not None"
    )
    path = directory / f"defs{count}.py"
    path.write_text(FIXTURE.format(body=body), encoding="utf-8")
    return path


def price(path: Path) -> int:
    """The fixture's cost through the lane's runner, minimum of ROUNDS."""
    samples = [lane.run_twin(path).cost for _ in range(ROUNDS)]
    if any(sample is None for sample in samples):
        msg = f"{path.name} did not run: {lane.run_twin(path).outcome.error}"
        raise RuntimeError(msg)
    return min(sample for sample in samples if sample is not None)


DOORS = """\
import sys
sys.path.insert(0, 'extensions/python')
from metta import MeTTa, S, V, equation

m = MeTTa(metta_path='.').self
with m.stats() as stored:
    if {door!r} == 'define':
        import textwrap, importlib.util, tempfile, pathlib
        source = textwrap.dedent('''
            def install(m):
                @m.define
                def h0(x):
                    return x + 1
        ''')
        path = pathlib.Path(tempfile.mkdtemp()) / 'door.py'
        path.write_text(source)
        spec = importlib.util.spec_from_file_location('door', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.install(m)
    elif {door!r} == 'write':
        m += equation(S.h0(V.x)).to(S['+'](V.x, 1))
    else:
        m.run('(= (h0 $x) (+ $x 1))')
with m.stats() as first:
    m.eval(S.h0(1))
print(f"door={door!r} store={{stored.inferences}} first-call={{first.inferences}} "
      f"total={{stored.inferences + first.inferences}}")
"""


def doors() -> None:
    """What each equation door costs to STORE and at its first call.

    The source door DEFERS translation and the two Python doors do not, so
    comparing what they cost to store alone reads one door as three times the
    other and says nothing; the sum is the comparison that means something
    [measured 2026-09-07: the FIRST definition in a process reads source 412
    plus 980 = 1392, write 868 plus 151 = 1019 and define 2682 plus 181 =
    2863; the `definitions=` rows above give the define door's MARGINAL 1307,
    which with its own first call is 87 inferences from the source door's
    1392, so the two doors are at parity once the process is warm and what the
    band has to allow is the ONE-TIME warmup].
    """
    for door in ("source", "write", "define"):
        _, text = lane.parity._run(
            [sys.executable, "-c", DOORS.format(door=door)],
            lane.REPO,
            env=lane._environment(),
        )
        for line in text.splitlines():
            if line.startswith("door="):
                print(line)


def main() -> None:
    """Print the five prices, the fit under them, and the three doors."""
    with tempfile.TemporaryDirectory(prefix="metta-twin-authoring-") as directory:
        costs = [price(fixture(Path(directory), count)) for count in range(5)]
        for count, cost in enumerate(costs):
            print(f"definitions={count} inferences={cost}")
        steps = [after - before for before, after in itertools.pairwise(costs)]
        each = sum(steps[1:]) / len(steps[1:])
        print(f"fit=warmup {costs[1] - costs[0] - each:.0f} plus {each:.0f} each")
    doors()


if __name__ == "__main__":
    main()
