"""examples/integration/import_error_surface.metta in Python: an import that fails.

A file that does not parse and a file that does not exist both surface the same
way: the import raises, `catch` turns the raise into an `(Error ...)` atom, and
the example reads that atom with `if-error`. The twin keeps `catch`, because the
error ALGEBRA is what the file is about, and reads the atom the way Python reads
any expression, by its head.

The paths stay relative and unresolvable, unlike the sibling import twins:
these two claims are that the import FAILS, and a path that resolves against
nothing fails exactly as the example's does. The space each import names is the
handle itself, which crosses into a built term as a grounded operand.
"""

from metta import S

#: The engine library the example opens first. Its underscore is real, so it
#: takes the bracket door: `S.lib_he` would name `lib-he`, which is not a
#: library the tree ships.
LIB_HE = S["lib_he"]

#: The two ways an import can fail: a file that will not parse, and one that
#: is not there.
BROKEN = S["examples/integration/_fixtures/imports/import_error_broken"]
MISSING = S["examples/integration/_fixtures/imports/definitely_missing_import"]

#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-23: unpriced placeholder, re-pinned by the
#: integrator; commit=b5991d9d4c20f3459fae529e13e0d26331b82ee2].
BUDGET = 1


def twin(m):
    """Import two files that cannot load, and read what came back."""
    # Known issue: `import!` has no Python door on the handle. The perfect
    # spelling is `m.import_(target)`, or `m += lib.<name>` for a shipped
    # library (appendix stamp 1), and neither exists yet, so the directive is
    # reached by its own bang name, which performs it where it is written.
    m.fn["import!"](m, S.library(LIB_HE))

    broken, = m.eval(S.catch(S["import!"](m, BROKEN)))
    assert broken[0] == S.Error

    missing, = m.eval(S.catch(S["import!"](m, MISSING)))
    assert missing[0] == S.Error
