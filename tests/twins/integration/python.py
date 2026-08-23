"""examples/integration/python.metta in Python: five names for one seam.

The example wraps `py-call` in five equations so that a MeTTa program can make
a Python object, read and write its attributes, import a module and reach
`math.pi`, without ever writing `py-call` again. The twin defines the same five
equations, because they are what the file is: a compiled body has no spelling
for `py-call` (P14.4), so they are built as the terms they are.

Calling them is Python's own: `m.fn.py_call` reads the seam's own function as
an ordinary callable, the attribute door applying rung 4's hyphen map.

What cannot be Python here is the SEQUENCE in the first claim, and the
reason is measured rather than stylistic: an object made inside the engine
cannot be held by a Python name and handed back, because `py-call` re-wraps a
Python value it receives as an argument in janus's `Box`, so the callee gets the
wrapper instead of the object and `setattr` raises. The chain therefore stays
one term, and the missing spelling is filed as friction.
"""

import math

from petta import S, V, equation, ground

#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-23: unpriced placeholder, re-pinned by the
#: integrator; commit=b5991d9d4c20f3459fae529e13e0d26331b82ee2].
BUDGET = 1


def twin(m):
    """Wrap the seam five ways, then use it three times."""
    m += equation(S["make-object"]()).to(S["py-call"](S["types.SimpleNamespace"]()))
    m += equation(S["get-attribute"](V.obj, V.name)).to(
        S["py-call"](S.getattr(V.obj, V.name))
    )
    m += equation(S["set-attribute"](V.obj, V.name, V.value)).to(
        S["py-call"](S.setattr(V.obj, V.name, V.value))
    )
    m += equation(S["import"](V.name)).to(S["py-call"](S["importlib.import_module"](V.name)))
    m += equation(S["math.pi"]()).to(S["get-attribute"](S["import"](S.math), S.pi))

    # Make an object, give it an attribute, read the attribute back.
    #
    # Known issue: the perfect spelling is three Python statements, an object
    # in a Python name between them. It does not work: `py-call` re-wraps a
    # Python value it receives as an ARGUMENT in janus's `Box`, so the callee
    # gets the wrapper and `setattr` raises `'Box' object has no attribute
    # 'foo'` [measured on three shapes: the engine-made namespace, a
    # Python-made types.SimpleNamespace, and a plain class instance]. The
    # chain therefore stays one term.
    stored = m.eval(S["let*"](  # rung: an engine-made object arrives back at py-call wrapped in a janus Box, so the sequence cannot become three Python statements
        ((V.obj, S["make-object"]()),
         (V.written, S["set-attribute"](V.obj, S.foo, S["math.pi"]()))),
        S["get-attribute"](V.obj, S.foo),
    ))
    assert stored == [math.pi]

    # A bound method is a head like any other, and its receiver is the argument.
    py = m.fn.py_call
    assert py(S[".upper"](ground("abc"))).one() == S.ABC
    assert py(S[".__add__"](5, 3)).one() == 8
