"""Purpose: hold the two claims the compiled body's default space operand rests
on: that `&self` and `(context-space)` name the same space wherever a program
can be, and that a compiled body naming `&self` reads the space it was
installed into rather than the engine's root.
Assumes: run as
  `python extensions/python/benchmarks/probes/running_space.py` from the
  repository root. The second half is the regression test for the door that
  was wrong: before 2026-09-07 an equation stored through `add-atom` compiled
  with `&self` UNRESOLVED, so two byte-identical equations behaved differently
  by whichever door wrote them, and the compiler could not name the running
  space at all.
Guarantees: prints `equivalence` rows for the self space, a named space and
  two instances of a parametric family, each answering the same atoms under
  both spellings; `doors` rows for the same equation installed through the
  source door and through the define door; and `cost` rows for the two
  spellings at one, five and ten calls [measured 2026-09-07: 425, 2000 and
  3997 inferences with `&self` against 1567, 3197 and 5242 with
  `(context-space)`, so the call costs 1142 on first use and 11 a call after;
  commit=9010a79b01c9b2a66b96a3952fa378fb3e939dc3].
Fails when: the engine stops resolving `&self` against the space a clause is
  compiled into, which is what `engine/spaces/foreign.pl`'s add_function_atom
  substitutes for.
"""  # noqa: D205  -- the contract header is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import metta
from metta import MeTTa, S, V, match

SPELLINGS = ("&self", "(context-space)")


def equivalence() -> None:
    """The same query under both spellings, in all three kinds of space."""
    root = MeTTa(metta_path=".").self
    named = metta.space(S.kb)
    parametric = (metta.space(S["&p-left"](100)), metta.space(S["&p-right"](10)))
    for label, space, tag in (
        ("self", root, "inroot"),
        ("named", named, "inkb"),
        ("parametric-left", parametric[0], "inleft"),
        ("parametric-right", parametric[1], "inright"),
    ):
        space.run(f"!(add-atom &self (r {tag}))")
        answers = [
            space.run(f"!(collapse (match {spelling} (r $x) $x))")
            for spelling in SPELLINGS
        ]
        agree = answers[0] == answers[1]
        print(f"equivalence {label}={answers[0]} agree={agree}")


def doors() -> None:
    """One equation naming `&self`, installed through each door that writes one."""
    space = MeTTa(metta_path=".").self
    space.run("!(add-atom &self (r 1))")
    space.run("(= (viasource) (collapse (match &self (r $x) $x)))")

    @space.define
    def viadefine():
        """The same body, through the door that compiles a Python function."""
        return collapse(match("&self", S.r(V.x), V.x))  # noqa: F821  -- `collapse` is a name a compiled body reads as MeTTa

    print(f"doors source={space.run('!(viasource)')}")
    print(f"doors define={space.run('!(viadefine)')}")
    stored = sorted(str(atom) for atom in space.atoms() if str(atom).startswith("(= ("))
    print(f"doors stored={stored}")


def cost() -> None:
    """What the call spelling costs against the symbol, at three call counts."""
    for spelling in SPELLINGS:
        for calls in (1, 5, 10):
            space = MeTTa(metta_path=".").self
            space.run(f"(= (q) (collapse (match {spelling} (r $x) $x)))")
            space.run("!(add-atom &self (r 1))")
            with space.stats() as spent:
                for _ in range(calls):
                    space.run("!(q)")
            print(f"cost spelling={spelling} calls={calls} inferences={spent.inferences}")


def main() -> None:
    """Print the equivalence, the two doors and the two prices."""
    equivalence()
    doors()
    cost()


if __name__ == "__main__":
    main()
