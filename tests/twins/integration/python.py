"""examples/integration/python.metta in Python: five names for one seam.

The example wraps `py-call` in five equations so that a MeTTa program can make
a Python object, read and write its attributes, import a module and reach
`math.pi`, without ever writing `py-call` again. The twin defines the same five
equations, because they are what the file is: a compiled body has no spelling
for `py-call` (P14.4), so they are built as the terms they are.

Calling them is Python's own: `m.fn(name)` reads an engine function as a
callable, so `attribute(obj, S.foo)` is a function call and its answer is the
value. What cannot be Python here is the SEQUENCE in the first claim, and the
reason is measured rather than stylistic: an object made inside the engine
cannot be held by a Python name and handed back, because `py-call` re-wraps a
Python value it receives as an argument in janus's `Box`, so the callee gets the
wrapper instead of the object and `setattr` raises. The chain therefore stays
one term, and the missing spelling is filed as friction.
"""

import math

from petta import S, V, equation, val

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 7591 to 6887, -704 (-9.27%), by the twin contract
#: change: three `test` wrappers left the engine for Python's own `assert`, and
#: two of the three calls became `m.fn(name)(...)`. The five equations and the
#: `let*` chain did not move, which is why this is the smallest drop in the
#: folder. Against the example's 14270 the ratio is 0.4826 [measured 2026-08-22
#: min-of-3: `twin_coverage.py --measure examples/integration/python.metta`].
#: Prior: ADDED 2026-08-22 at 7591 by the wave-3 twin baseline, which priced a
#: transliteration.
BUDGET = 6887


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

    # Make an object, give it an attribute, read the attribute back. The three
    # steps share one term because the object cannot cross out and back in.
    stored = m.eval(S["let*"](  # rung: an engine-made object arrives back at py-call wrapped in a janus Box, so the sequence cannot become three Python statements
        ((V.obj, S["make-object"]()),
         (V.written, S["set-attribute"](V.obj, S.foo, S["math.pi"]()))),
        S["get-attribute"](V.obj, S.foo),
    ))
    assert stored == [math.pi]

    # A bound method is a head like any other, and its receiver is the argument.
    py = m.fn("py-call")
    assert py(S[".upper"](val("abc"))) == S.ABC
    assert py(S[".__add__"](5, 3)) == 8
