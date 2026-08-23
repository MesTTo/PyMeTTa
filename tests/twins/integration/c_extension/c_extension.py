"""examples/integration/c_extension/c_extension.metta in Python: C, called directly.

`cbump.so` holds one foreign predicate, `loader.pl` loads it, and MeTTa calls
it with nothing in between. From Python the loading step is
`m.register_prolog(path=, names=)`, which is what
`import_prolog_functions_from_file` names in MeTTa, and the call is
`m.fn.c_bump(41)`, rung 4's hyphen map applied at the function namespace.

The example splits its import and its call into two runnables because a
runnable is compiled just before it runs, so a call written beside its own
import compiles while the name is still unregistered. A Python program has no
runnables and no such ordering hazard: the registration is a statement and the
call is the next one.

The two libraries take the bracket door because their underscores are real:
`S.lib_import` would name `lib-import`, which the tree does not ship. The space
each import writes is the handle itself, a grounded operand in the built term.

The skip stays, because a C compiler is not one of the engine's requirements
and `check.sh` builds this artefact before any tier runs. What a twin cannot do
is SAY it skipped: the lane admits a string constant only as an atom's name or
as `ground()` data, so the example's `println!` has no image here.
"""

from pathlib import Path

from metta import S

#: The two engine libraries the example opens, spelled with their real
#: underscores.
LIB_IMPORT, LIB_FILE = S["lib_import"], S["lib_file"]

#: The build artefact and the Prolog file that loads it, as host paths for a
#: Python door.
CBUMP_SO = Path("examples/integration/c_extension/cbump.so")
LOADER_PL = Path("examples/integration/c_extension/loader.pl")

#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-23: unpriced placeholder, re-pinned by the
#: integrator; commit=b5991d9d4c20f3459fae529e13e0d26331b82ee2].
BUDGET = 1


def twin(m):
    """Load the C predicate, then call it."""
    # Known issue: `import!` has no Python door on the handle. The perfect
    # spelling is `m.import_(target)`, or `m += lib.<name>` for a shipped
    # library (appendix stamp 1), and neither exists yet, so the directive is
    # reached by its own bang name, which performs it where it is written.
    m.fn["import!"](m, S.library(LIB_IMPORT))
    m.fn["import!"](m, S.library(LIB_FILE))

    if not CBUMP_SO.exists():
        # The example prints its skip here. A twin has no door for prose.
        return

    m.register_prolog(path=LOADER_PL, names=["c-bump"])
    assert m.fn.c_bump(41).one() == 42
