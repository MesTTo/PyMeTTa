"""examples/integration/python_import.metta in Python: importing a .py file.

`import!` on a Python file makes that module's functions reachable by their
dotted names, and the two claims call one of each kind: one answering text and
one answering a number.

The example asserts the text answer through `repr` because a MeTTa program
cannot look at a symbol any other way. Here the answer is an atom, so the claim
names it: a Python string comes back from `py-call` as a SYMBOL, which is
upstream's conversion and is exactly what the claim now says.

The path is written from the repository root, because a Python program has no
importing file to resolve a relative import against: that is the residue this
file carries. The space is the handle itself, which crosses into the built term
as a grounded operand.
"""

from petta import S, ground

#: The file the import reads, a host path carried whole.
FIXTURE = ground("examples/integration/_fixtures/python_import_file.py")

#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-23: unpriced placeholder, re-pinned by the
#: integrator; commit=WORKTREE].
BUDGET = 1


def twin(m):
    """Import a Python file, then call two of its functions."""
    # Known issue, two halves. `import!` has no Python door on the handle: the
    # perfect spelling is `m.import_(target)`, or `m += lib.<name>` for a
    # shipped library (appendix stamp 1), and neither exists yet. And the
    # generic call door cannot stand in for it, because a call through the
    # function namespace answers a LAZY view: `m.fn["import!"](m, target)` as a
    # statement IMPORTS NOTHING until something pulls its answers [measured
    # 2026-08-23]. The term door evaluates eagerly, so the directive is written
    # that way.
    m.eval(S["import!"](m, FIXTURE))

    py = m.fn.py_call
    greeting = py(S["python_import_file.greet"](ground("PeTTa User")))
    assert greeting.one() == S["Hello, PeTTa User from Python!"]
    assert py(S["python_import_file.add"](10, 20)).one() == 30
