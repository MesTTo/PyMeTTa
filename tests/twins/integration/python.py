"""examples/integration/python.metta in Python: five names for one seam.

The example wraps `py-call` in five equations so that a MeTTa program can make
a Python object, read and write its attributes, import a module and reach
`math.pi`, without ever writing `py-call` again. All five are ordinary compiled
functions here, because a body reaches `py-call` at the static function
namespace like any other engine name, and two of them take an explicit `name=`
for a head Python's grammar cannot spell: `import` is a keyword and `math.pi`
is dotted.

Calling them is Python's own, `m.fn.<name>` reading the seam's own function as
an ordinary callable through rung 4's map.

What cannot be Python here is the SEQUENCE in the first claim, and the reason
is measured rather than stylistic: an object made inside the engine cannot be
held by a Python name and handed back, because `py-call` re-wraps a Python
value it receives as an argument in janus's `Box`, so the callee gets the
wrapper instead of the object and `setattr` raises. The chain therefore stays
one term, and the missing spelling is filed as friction.
"""

import math

from metta import S, V, fn, ground

#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-24: unpriced placeholder, re-pinned by the
#: integrator; commit=e70eaeba6b6c0afc9081239041b8459eb8bb1b92].
BUDGET = 1


def twin(m):
    """Wrap the seam five ways, then use it three times."""

    @m.define
    def make_object():                       # (= (make-object)
        return fn.py_call(S["types.SimpleNamespace"]())   # (py-call (types.SimpleNamespace)))

    @m.define
    def get_attribute(obj, name):            # (= (get-attribute $obj $name)
        return fn.py_call(S.getattr(obj, name))           # (py-call (getattr $obj $name)))

    @m.define
    def set_attribute(obj, name, value):     # (= (set-attribute $obj $name $value)
        return fn.py_call(S.setattr(obj, name, value))    # (py-call (setattr $obj $name $value)))

    @m.define(name="import")
    def import_module(name):                 # (= (import $name)
        return fn.py_call(S["importlib.import_module"](name))  # (py-call (importlib.import_module $name)))

    @m.define(name="math.pi")
    def math_pi():                           # (= (math.pi)
        return get_attribute(import_module(S.math), S.pi)      # (get-attribute (import math) pi))

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
        ((V.obj, S.make_object()),
         (V.written, S.set_attribute(V.obj, S.foo, S["math.pi"]()))),
        S.get_attribute(V.obj, S.foo),
    ))
    assert stored == [math.pi]               # [3.141592653589793]

    # A bound method is a head like any other, and its receiver is the argument.
    py = m.fn.py_call
    assert py(S[".upper"](ground("abc"))).one() == S.ABC   # (py-call (.upper "abc")) is ABC
    assert py(S[".__add__"](5, 3)).one() == 8             # (py-call (.__add__ 5 3)) is 8
