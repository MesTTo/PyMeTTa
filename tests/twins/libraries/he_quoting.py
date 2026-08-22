"""Purpose: examples/libraries/he_quoting.metta in Python: what stays unevaluated.

`quote` is an ordinary constructor and `unquote` undoes it, so both stay named:
they are the file's subject. Everything around them is Python's own.

Evaluating a term is `m.one`. Printing one is `str`, because a built atom
already prints as engine-exact swrite text, which is what MeTTa's `repr`
answers. And `noreduce-eq`, which compares two terms WITHOUT reducing them, is
Python's `==` on atoms: outside a compiled body `S["+"](1, 2) == 3` is
structural equality between an expression and a number, and it is False for
exactly the reason the example gives.
Guarantees:
  - expected printed output in this twin remains Python str text
    [tested: test_printing_text_is_not_forced_through_the_value_carrier; commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from petta import S

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 12127 to 8295, -3832 (-31.60%), by the idiomatic
#: rewrite: `repr` and `noreduce-eq` left the engine for `str()` and Python's
#: own structural `==` on atoms, and six `test` wrappers went with them.
#: Measured min-of-three with the MORK backend linked into this worktree,
#: which the earlier figure may not have been. Prior: 12127 was the last
#: figure for the generator twin that yielded `m.eval(S.test(...))` once per
#: runnable form.
BUDGET = 8295


def twin(m):
    """Quote a sum, unquote it, print it, and compare it unreduced."""
    m.eval(S["import!"](S["&self"], S.library(S.lib_he)))  # rung: import!'s target space is an ARGUMENT, and a space handle does not encode as one (the engine answers "expects a space"), so the name is written as the symbol its own door takes

    quoted = S.quote(S["+"](1, 2))
    assert m.eval(quoted) == [quoted]

    assert m.one(S["+"](1, 2)) == 3
    assert m.fn("unquote")(quoted) == 3

    # Printing an atom is what MeTTa's repr answers, character for character.
    assert str(S.unquote(42)) == "(unquote 42)"

    # Comparing without reducing is Python's own structural equality.
    assert S["+"](1, 2) == S["+"](1, 2)
    assert S["+"](1, 2) != 3
