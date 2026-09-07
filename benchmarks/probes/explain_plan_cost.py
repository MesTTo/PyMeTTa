"""Purpose: price the two halves of the conjunctive admission gate against the
plan and the query, so `explain` of a cyclic conjunction is shown to cost the
query's shape and one scan of each conjunct, and none of the sort, the tries or
the traversal the join itself pays.
Assumes: `metta` imports (PYTHONPATH=extensions/python) and the engine boots;
  run as `python extensions/python/benchmarks/probes/explain_plan_cost.py`
  from the repository root.
Guarantees: prints one row per ring size, 128, 512 and 2,048 stored edges, with
  the inferences of the pure shape, the shape plus the row admission, the
  whole plan (which builds the tries), `explain` of the triangle query and the
  query itself, all measured through `stats()` in one process after a warm-up
  [measured 2026-09-07: explain 7,350 against the query's 237,473 at 2,048
  rows, 10.1%, 4.6% and 3.1% at 128, 512 and 2,048; the citation in
  extensions/python/metta/_space.py's explain docstring reads this probe; commit=WORKTREE].
Fails when: `plan-cyclic-joins` is off, which the probe switches on itself.
"""  # noqa: D205  -- the contract header is one continuous invariant, not summary-and-body prose

from metta import MeTTa, parse

CONJ = "[',',[edge,_X,_Y],[edge,_Y,_Z],[edge,_Z,_X]]"  # the whole pattern, comma head first
FORM = "(match &self (, (edge $x $y) (edge $y $z) (edge $z $x)) ($x $y $z))"


def build(m, n):
    """Store a two-out-degree ring of n nodes in the context's home space."""
    m.self.run("\n".join(
        f"!(add-atom &self (edge {i} {(i + k) % n}))" for i in range(n) for k in (1, 2)))


def inferences(m, goal):
    """Inferences one engine goal retires, read through stats()."""
    with m.self.stats() as s:
        m.self.runtime.once(goal)
    return int(s.inferences)


def main() -> None:
    """Print the five prices per ring size."""
    print(f"{'rows':>6} {'shape':>7} {'admits':>8} {'plan':>9} {'explain':>9} {'query':>10}")
    for n in (64, 256, 1024):
        with MeTTa() as m:
            m.self.run("!(pragma! plan-cyclic-joins True)")
            build(m, n)
            pre = f"_S = '{m.self.name}', spaces:native_storage_module_cache(_S,_M), "
            shape = pre + f"( spaces:native_conjunction_shape(_M,_S,{CONJ},_Sh) -> Ok=1 ; Ok=0 )"
            admits = pre + (f"( spaces:native_conjunction_shape(_M,_S,{CONJ},_Sh), "
                            "spaces:native_conjunction_rows_admit(_Sh,_M,_S) -> Ok=1 ; Ok=0 )")
            plan = pre + (f"( spaces:native_conjunction_shape(_M,_S,{CONJ},_Sh), "
                          "spaces:native_conjunction_relations(_Sh,_M,_S,_P) -> Ok=1 ; Ok=0 )")
            for goal in (shape, admits, plan):  # warm up
                m.self.runtime.once(goal)
            query = parse(FORM)
            m.self.explain(query)
            m.self.eval(query)
            with m.self.stats() as s:
                m.self.explain(query)
            explain_cost = int(s.inferences)
            with m.self.stats() as s2:
                m.self.eval(query)
            print(f"{2*n:6d} {inferences(m, shape):7d} {inferences(m, admits):8d} "
                  f"{inferences(m, plan):9d} {explain_cost:9d} {int(s2.inferences):10d}")
            m.self.run("!(pragma! plan-cyclic-joins False)")


if __name__ == "__main__":
    main()
