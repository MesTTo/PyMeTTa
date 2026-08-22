"""examples/integration/import_error_surface.metta in Python: an import that fails.

A file that does not parse and a file that does not exist both surface the same
way: the import raises, `catch` turns the raise into an `(Error ...)` atom, and
the example reads that atom with `if-error`. The twin keeps `catch`, because the
error ALGEBRA is what the file is about, and reads the atom the way Python reads
any expression, by its head.

The paths stay relative and unresolvable, unlike the sibling import twins:
these two claims are that the import FAILS, and a path that resolves against
nothing fails exactly as the example's does.
"""

from petta import S

#: The space every import writes.
SELF = S["&self"]  # rung: no import door hangs off the space handle

#: The two ways an import can fail: a file that will not parse, and one that
#: is not there.
BROKEN = S["examples/integration/_fixtures/imports/import_error_broken"]
MISSING = S["examples/integration/_fixtures/imports/definitely_missing_import"]

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 9499 to 9041, -458 (-4.82%), by the twin contract
#: change: two `test` wrappers and their `if-error` guards left the engine for
#: Python's own `assert` and `e[0]`, which reads an atom's head at no engine
#: cost at all. The two failing imports are nearly the whole cost and they did
#: not move, which is why this is the smallest drop in the folder. Against the
#: example's 13223 the ratio is 0.6837 [measured 2026-08-22 min-of-3:
#: `twin_coverage.py --measure examples/integration/import_error_surface.metta`].
#: Prior: ADDED 2026-08-22 at 9499 by the wave-3 twin baseline, which priced a
#: transliteration.
BUDGET = 9041


def twin(m):
    """Import two files that cannot load, and read what came back."""
    m.eval(S["import!"](SELF, S.library(S.lib_he)))

    broken, = m.eval(S.catch(S["import!"](SELF, BROKEN)))
    assert broken[0] == S.Error

    missing, = m.eval(S.catch(S["import!"](SELF, MISSING)))
    assert missing[0] == S.Error
