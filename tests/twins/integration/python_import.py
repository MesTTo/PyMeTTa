"""examples/integration/python_import.metta in Python: importing a .py file.

`import!` on a Python file makes that module's functions reachable by their
dotted names, and the two claims call one of each kind: one answering text and
one answering a number.

The example asserts the text answer through `repr` because a MeTTa program
cannot look at a symbol any other way. Here the answer is an atom, so the claim
names it: a Python string comes back from `py-call` as a SYMBOL, which is
upstream's conversion and is exactly what the claim now says.

The path is written from the repository root, because a Python program has no
importing file to resolve a relative import against, and `import!` names its
space as a symbol because no import door hangs off the space handle.
"""

from petta import S, val

#: The space the import writes, and the file it reads.
SELF = S["&self"]  # rung: no import door hangs off the space handle
FIXTURE = val("examples/integration/_fixtures/python_import_file.py")

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 2081 to 1480, -601 (-28.9%), by the twin contract
#: change: two `test` wrappers and a `repr` left the engine for Python's own
#: `assert` and atom equality; the import and the two crossings did not move.
#: Against the example's 4612 the ratio is 0.3209 [measured 2026-08-22
#: min-of-3: `twin_coverage.py --measure
#: examples/integration/python_import.metta`]. Prior: ADDED 2026-08-22 at 2081
#: by the wave-3 twin baseline, which priced a transliteration.
BUDGET = 1480


def twin(m):
    """Import a Python file, then call two of its functions."""
    m.eval(S["import!"](SELF, FIXTURE))

    py = m.fn("py-call")
    assert py(S["python_import_file.greet"](val("PeTTa User"))) == S[
        "Hello, PeTTa User from Python!"
    ]
    assert py(S["python_import_file.add"](10, 20)) == 30
