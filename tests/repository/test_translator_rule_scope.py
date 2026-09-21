"""Purpose: a translator rule answers the same thing in every space.

Not only in the space that registered it.

`add-translator-rule!` takes a head over for the WHOLE PROCESS, which the
engine documents and intends: translate_expr_dl/4 consults the rules one line
before translate_special_dl/5, so a rule wins over the compiler's own clause
(engine/translator_rules.pl:147-152), and `once` sits outside
protected_core_head/1 on purpose because lib_derived's swap is engine work that
ships (engine/translator_rules.pl:169-173).

The registration is global; the `(: once (-> Atom %Undefined%))` beside the
equation is an ordinary atom in the registering space. Until
translator_rule_type_chain/3 existed, a space that never imported the library
found no declaration, took apply_translator_rule_dl's untyped branch, and
EVALUATED the argument before the expansion could place it. `once`'s Atom
parameter exists precisely to keep the generator unrun, so `(take 1 ...)` never
received a generator and every answer passed through: `once` stopped cutting in
every space but the importing one, silently
[measured 2026-09-21: (1 2) against (1), fixed by reading the declaration from
the rule's home when the calling space has none].

Assumes: one engine process per pytest session, which is what makes a rule
  registered by one space observable from another at all.
Guarantees:
  - a rule registered in one space answers the same in a later unrelated space
    [tested: this file; commit=WORKTREE]
  - the importing space is unaffected, so the fix is additive
    [tested: this file; commit=WORKTREE]
  - `remove-translator-rule!` puts the compiler's own clause back, which the
    README's lib_derived entry and 08-derived_forms.metta both rely on
    [tested: this file; commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import contextlib

import metta as metta_module

#: Three answers wide, so a cut that stops happening shows in the answer itself
#: rather than in a count.
PROBE = "!(collapse (once (superpose (1 2 3))))"
CUT = "(1)"


def _answer(source: str, tmp_path) -> str:
    """Run `source` on a fresh space in its own directory, as the README suite does."""
    with contextlib.chdir(tmp_path):
        return str(metta_module.space().run(source)[-1])


def test_a_registered_rule_answers_the_same_in_a_space_that_never_imported_it(tmp_path):
    """Register in one space, ask in another, and give it back."""
    assert CUT in _answer(PROBE, tmp_path), "the fused once cuts before any import"

    imported = _answer("!(import! &self (library lib_derived))\n" + PROBE, tmp_path)
    assert CUT in imported, "the rule answers what the fused clause answers where it is visible"

    elsewhere = _answer(PROBE, tmp_path)
    assert CUT in elsewhere, (
        "a space that never imported lib_derived must still see once cut. Before "
        "translator_rule_type_chain/3 this answered (1 2 3), because the rule is "
        "registered for every space while the (: once ...) it needs is an atom in "
        f"the registering space. Got: {elsewhere}"
    )

    _answer("!(remove-translator-rule! once)", tmp_path)
    assert CUT in _answer(PROBE, tmp_path), (
        "remove-translator-rule! must put the compiler's own clause back in charge"
    )
