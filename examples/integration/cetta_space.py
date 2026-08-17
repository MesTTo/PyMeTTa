"""Purpose: a space whose matching runs in CeTTa, the C MeTTa runtime,
reached as a subprocess: the same SpaceProvider seam that carries SQLite,
DuckDB, Redis and remote engines carries a sibling MeTTa implementation.

The bridge is STORAGE-level on purpose. The atoms live here as PeTTa
atoms; CeTTa is consulted per query as a matcher over their text, its
evaluator never runs, and the engine binds every answer through its own
unification. A semantic quirk in CeTTa's matcher surfaces as a missing
or extra candidate that the conformance kit's pattern family catches,
not as a silently wrong local answer.

Guarantees:
  - removal takes every stored occurrence CeTTa matches for the pattern,
    decided in ONE subprocess run by tagging each stored atom with its
    index and matching (probe $i <pattern>) [tested
    test_cetta_space.py::test_removal_is_by_unification]
  - an atom whose text spans lines is refused at add, because the
    subprocess crossing is line-shaped
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import os
import shutil
import subprocess
from collections.abc import Iterator
from typing import Any

from _common import check, done, skip

from petta.foreign import SpaceProvider

_PROBE = "petta-cetta-probe"


class CettaSpace(SpaceProvider):
    """Atoms stored beside their text, pattern queries answered by CeTTa."""

    def __init__(self, cetta: str | None = None, timeout: float = 30.0):
        self._cetta = cetta or os.environ.get("PETTA_CETTA", "cetta")
        self._timeout = timeout
        self._atoms: list[Any] = []

    # -- the provider surface -------------------------------------------------

    def add(self, atom) -> None:
        text = str(atom)
        if "\n" in text:
            raise ValueError(f"an atom's text may not span lines: {text!r}")
        self._atoms.append(atom)

    def atoms(self) -> Iterator:
        return iter(list(self._atoms))

    def match(self, pattern) -> Iterator:
        indices = self._matching_indices(pattern)
        return iter([self._atoms[i] for i in indices])

    def remove(self, pattern) -> bool:
        doomed = set(self._matching_indices(pattern))
        if not doomed:
            return False
        self._atoms = [a for i, a in enumerate(self._atoms) if i not in doomed]
        return True

    def clear(self) -> None:
        self._atoms.clear()

    # -- the CeTTa crossing ---------------------------------------------------

    def _matching_indices(self, pattern) -> list[int]:
        """Which stored atoms match, decided by CeTTa in one run.

        Every stored atom is asserted as (probe i atom), and the query
        (match &self (probe $i <pattern>) $i) answers exactly the indices
        whose atom CeTTa matches against the pattern, with the pattern's
        variables freshened per candidate by match itself.
        """
        if not self._atoms:
            return []
        program = [
            "-e",
            " ".join(f"({_PROBE} {i} {atom})" for i, atom in enumerate(self._atoms)),
            "-e",
            f"!(match &self ({_PROBE} $petta-cetta-i {pattern}) $petta-cetta-i)",
        ]
        answer, errors = self._run(program)
        if not answer:
            #CeTTa prints nothing at all for an empty answer set, not an
            #empty list, and refuses malformed input with a nonzero exit,
            #so silence here really is "no stored atom matches".
            return []
        return [int(text) for text in _bracket_items(answer, errors) if text]

    def _run(self, arguments: list[str]) -> tuple[str, str]:
        completed = subprocess.run(  # noqa: S603 - the binary is the caller's own configuration
            [self._cetta, "--quiet", *arguments],
            capture_output=True,
            text=True,
            timeout=self._timeout,
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(
                f"cetta exited {completed.returncode}: "
                f"{completed.stderr.strip() or completed.stdout.strip()}"
            )
        return completed.stdout.strip(), completed.stderr.strip()


class CettaMatch:
    """A grounded value whose matching IS CeTTa evaluation.

    Held in a MeTTa expression and unified against an operand, it yields
    one answer atom per result CeTTa produced for its query, and the
    operand's variables bind by destructuring those answers: arbitrary
    bindings from a foreign evaluator, arriving through ordinary
    unification. This is the matcher tier of the seam, where the value's
    own logic is the authority and nothing re-derives its claims; a
    space is exactly such a value whose matcher is query.

        matcher = CettaMatch("(sol 2) (sol -2)",
                             "!(match &self (sol $s) (sol $s))", m.parse)
        !(unify <matcher> (sol $x) $x none)   ; answers 2 and -2
    """

    def __init__(self, program: str, query: str, parse, cetta: str | None = None,
                 timeout: float = 30.0):
        self._program = program
        self._query = query
        self._parse = parse
        self._space = CettaSpace(cetta=cetta, timeout=timeout)

    def match_(self, other):
        answer, _errors = self._space._run(["-e", self._program, "-e", self._query])
        if not answer:
            return
        for text in _bracket_items(answer):
            if text:
                yield self._parse(text)


def _bracket_items(answer: str, errors: str = "") -> list[str]:
    """Split CeTTa's `[a, b, c]` answer line at top-level commas."""
    line = answer.splitlines()[-1].strip() if answer else ""
    if not (line.startswith("[") and line.endswith("]")):
        raise RuntimeError(
            f"cetta answered an unexpected shape: stdout {answer!r}, "
            f"stderr {errors[-500:]!r}"
        )
    inner = line[1:-1].strip()
    if not inner:
        return []
    items, depth, start = [], 0, 0
    for position, character in enumerate(inner):
        if character == "(":
            depth += 1
        elif character == ")":
            depth -= 1
        elif character == "," and depth == 0:
            items.append(inner[start:position].strip())
            start = position + 1
    items.append(inner[start:].strip())
    return items


def demo() -> None:
    """The worked run: PeTTa queries answered over atoms CeTTa matches,
    and CeTTa evaluation results binding variables inside PeTTa unify."""
    cetta = os.environ.get("PETTA_CETTA") or shutil.which("cetta")
    if cetta is None:
        skip("cetta is not on PATH and PETTA_CETTA does not name it")
    import petta
    from petta import S, V, expr
    from petta.atoms import Gnd

    m = petta.MeTTa().new_space()
    space = CettaSpace(cetta=cetta)
    m.register_space(space, "&cetta")
    m.run("!(add-atom &cetta (edge a b))")
    m.run("!(add-atom &cetta (edge a c))")
    (group,) = m.run("!(collapse (match &cetta (edge a $x) $x))")
    check("CeTTa matches, PeTTa binds", sorted(str(a) for a in group[0]),
          ["b", "c"])

    matcher = CettaMatch(
        "(sol 2) (sol -2)",
        "!(match &self (sol $s) (sol $s))",
        m.parse,
        cetta=cetta,
    )
    rows = m.eval(expr(S.unify, Gnd(matcher), expr(S.sol, V.x), V.x, S.none))
    check("CeTTa answers bind inside unify", sorted(str(a) for a in rows),
          ["-2", "2"])
    done("cetta_space")


if __name__ == "__main__":
    demo()
