"""examples/integration/c_extension/c_extension.metta in Python: C, called directly.

`cbump.so` holds one foreign predicate, `loader.pl` loads it, and MeTTa calls
it with nothing in between. From Python the loading step is
`m.register_prolog(path=, names=)`, which is what
`import_prolog_functions_from_file` names in MeTTa, and the call is
`m.fn("c-bump")(41)`.

The example splits its import and its call into two runnables because a
runnable is compiled just before it runs, so a call written beside its own
import compiles while the name is still unregistered. A Python program has no
runnables and no such ordering hazard: the registration is a statement and the
call is the next one.

The skip stays, because a C compiler is not one of the engine's requirements
and `check.sh` builds this artefact before any tier runs. What a twin cannot do
is SAY it skipped: the lane admits a string constant only as an atom's name or
as `val()` data, so the example's `println!` has no image here.
"""

from pathlib import Path

from petta import S, val

#: The space the imports write.
SELF = S["&self"]  # rung: no import door hangs off the space handle

#: The build artefact and the Prolog file that loads it. Marked data because a
#: twin may not write a bare string; `.value` is the path a Python door takes.
CBUMP_SO = Path(val("examples/integration/c_extension/cbump.so").value)
LOADER_PL = Path(val("examples/integration/c_extension/loader.pl").value)

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 99523 to 98204, -1319 (-1.33%), by the twin contract
#: change: two `if`/`file-exists` guards and a `test` wrapper left the engine
#: for Python's own `if`, `Path.exists()` and `assert`, and
#: `import_prolog_functions_from_file` left it for `m.register_prolog`. The two
#: library imports are most of the cost and the C call itself did not move,
#: which is why the drop is small. Against the example's 105081 the ratio is
#: 0.9346 [measured 2026-08-22 min-of-3: `twin_coverage.py --measure
#: examples/integration/c_extension/c_extension.metta`, with cbump.so built by
#: check.sh's own `swipl-ld` line]. Prior: ADDED 2026-08-22 at 99523 by the
#: wave-3 twin baseline, which priced a transliteration.
BUDGET = 98204


def twin(m):
    """Load the C predicate, then call it."""
    m.eval(S["import!"](SELF, S.library(S.lib_import)))
    m.eval(S["import!"](SELF, S.library(S.lib_file)))

    if not CBUMP_SO.exists():
        # The example prints its skip here. A twin has no door for prose.
        return

    m.register_prolog(path=LOADER_PL, names=[S["c-bump"].name])
    assert m.fn("c-bump")(41) == 42
