"""examples/integration/python_import.metta in Python: importing a .py file.

`import!` on a Python file makes that module's functions reachable by their
dotted names, and the two claims call one of each kind: one answering text and
one answering a number.

The example asserts the text answer through `repr` because a MeTTa program
cannot look at a symbol any other way. Here the answer is an atom, so the claim
names it: a Python string comes back from `py-call` as a SYMBOL, which is
upstream's conversion and is exactly what the claim now says.

The file is a host path, so it is a `pathlib.Path`, and only its rendering
crosses: `import!` reads the path as an atom rather than as a Python object,
so a `Path` handed over whole raises at the seam (friction, P14.13). Resolving
it against the importing FILE is what a MeTTa program gets for free and a
Python-authored one does not, so the path is written from the repository root.
"""

from pathlib import Path

from metta import S, ground

#: The file the import reads. A path is a Path, and the door takes its text.
FIXTURE = Path("examples/integration/_fixtures/python_import_file.py")

#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-24: unpriced placeholder, re-pinned by the
#: integrator; commit=WORKTREE].
BUDGET = 1


def twin(m):
    """Import a Python file, then call two of its functions."""
    # Known issue: `import!` has no Python door on the handle. The perfect
    # spelling is `m.import_(target)`, or `m += lib.<name>` for a shipped
    # library (appendix stamp 1), and neither exists yet, so the directive is
    # reached by its own bang name, which performs it where it is written.
    m.fn["import!"](m, ground(str(FIXTURE)))

    py = m.fn.py_call
    greeting = py(S["python_import_file.greet"](ground("PeTTa User")))
    assert greeting.one() == S["Hello, PeTTa User from Python!"]
    assert py(S["python_import_file.add"](10, 20)).one() == 30   # [30]
