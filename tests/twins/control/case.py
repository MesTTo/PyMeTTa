"""examples/control/case.metta in Python: the first matching branch.

The key 5 misses the literal branch 4 and meets the first variable pattern, so
the answer is 44 and the third branch never runs at all.

Two branches, one a literal and one matching anything, is a two-way question
about the key, and Python's conditional expression asks it. The third branch is
unreachable in either spelling. What is NOT reachable is a `case` whose
branches are PATTERNS over structure: Python's `match` statement has no
lowering in the compiled subset yet, which the residue table records against
P14.4, and this file's `case` happens not to need one.
"""

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 1529 to 2704, +1175 (+76.8%), by the twin contract
#: change: the `case` equation ENTERED the engine as a compiled Python
#: conditional, whose fixed registration is the whole increase, while the
#: `test` wrapper LEFT for `assert`. Measured min-of-3 over fresh processes
#: with the MORK backend linked in, which the artefact-free worktree omits
#: and which moves a compiled twin by about 10 inferences per definition;
#: against the example's 3724 the ratio is 0.7261. Prior: 1529, the
#: transliterated twin this replaces.
BUDGET = 2704


def twin(m):
    """Dispatch on a key that misses the literal branch."""
    @m.define
    def casetest(x):
        # (= (casetest $x) (case $x ((4 42) ($otherpattern 44) ($otherother $45))))
        return 42 if x == 4 else 44

    # !(test (casetest 5) 44)
    assert casetest(5) == [44]
