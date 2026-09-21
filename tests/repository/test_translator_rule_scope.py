"""Purpose: pin what a registered translator rule does to spaces that never
asked for it.

`add-translator-rule!` takes a head over for the WHOLE PROCESS, which the
engine documents and intends: translate_expr_dl/4 consults the rules one line
before translate_special_dl/5, so a rule wins over the compiler's own clause
(engine/translator_rules.pl:147-152). `once` is deliberately outside
protected_core_head/1 because lib_derived's swap is engine work that ships
(engine/translator_rules.pl:169-173), and
examples/ch20-extending-the-engine/20-01-translator-rules/08-derived_forms.metta
runs the swap and the swap back.

What that example does not cover is a SECOND space. The takeover is global but
the equation the rule rewrites through lives in the importing space's module,
so in any other space the name is diverted away from the fused clause and finds
no rewrite: `once` stops cutting and answers its generator entire. That
contradicts lib_derived's own Guarantees line, "once under this rule answers
what once answers".

The test pins the behaviour rather than asserting the repair, in the shape the
repository already uses for a known gap
(docs/journal/2026-09-07-sequence-variables-in-the-corpus.md): the day the
diversion becomes space-aware this file goes red and names what moved.

Known issue: a rule registered in one space diverts its head in every space,
  while the rewrite only resolves where the equation is visible. The fix site
  is engine/translator/lowering.pl:1267, whose `translator_rule(HV, _, Module)`
  is home-blind where translator_rules.pl:288-290 checks the home's space is
  among the compiling node's spaces. It is a hot path -- every head crosses it
  -- so the change needs the benchmark differential this repository requires
  before it can be default.

Assumes: the engine is one process per pytest session, which is what makes the
  leak observable at all.
Guarantees:
  - the leak is reproduced, so it cannot be lost
    [measured 2026-09-21; commit=WORKTREE]
  - `remove-translator-rule!` restores the fused clause for later spaces, which
    is what the README's lib_derived entry and the shipped corpus example both
    rely on [measured 2026-09-21; commit=WORKTREE]
Open Obligations:
  To Do: make the diversion space-aware at lowering.pl:1267
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import metta as metta_module

#: The generator is three answers wide, so `once` cutting or not is visible in
#: the answer itself rather than in a count.
PROBE = "!(collapse (once (superpose (1 2 3))))"
CUT = "(1)"
UNCUT = "(1 2 3)"


def _answer(source: str, tmp_path) -> str:
    """Run `source` on a fresh space in its own directory, as the README suite does."""
    import os

    here = os.getcwd()
    os.chdir(tmp_path)
    try:
        return str(metta_module.space().run(source)[-1])
    finally:
        os.chdir(here)


def test_a_registered_rule_diverts_once_in_a_space_that_never_imported_it(tmp_path):
    """The leak, and its undo, in one test so neither half can pass alone."""
    assert CUT in _answer(PROBE, tmp_path), "the fused once must cut before any import"

    imported = _answer(
        "!(import! &self (library lib_derived))\n" + PROBE, tmp_path)
    assert CUT in imported, "the rule answers what the fused clause answers where it is visible"

    leaked = _answer(PROBE, tmp_path)
    assert UNCUT in leaked, (
        "KNOWN ISSUE reproduced: a space that never imported lib_derived sees "
        "once diverted and uncut. If this line fails the diversion became "
        "space-aware, which is the repair -- delete the known-issue block above "
        f"and assert {CUT} here instead. Got: {leaked}"
    )

    _answer("!(remove-translator-rule! once)", tmp_path)
    assert CUT in _answer(PROBE, tmp_path), (
        "remove-translator-rule! must put the compiler's own clause back in "
        "charge; the README's lib_derived entry and 08-derived_forms.metta "
        "both depend on it"
    )
