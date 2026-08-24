"""examples/integration/py_numpy.metta in Python: numpy through the seam.

The example is the language's own tutorial for holding Python objects in MeTTa
[source: metta-lang.dev/docs/learn/tutorials/python_use/py_atom]. Every
`!(bind! np-abs (py-atom numpy.absolute))` is a Python name binding here, which
is what a token was for: `np_abs = ground(np.absolute)` names the object itself
rather than parsing its dotted path, and applying it is an ordinary tuple whose
head IS the function.

Where Python has the concept it wins, and here that means most of the file:
`(py-iter ...)` under a `collapse` is `.tolist()`, and asking what class an
answer belongs to is `isinstance`. Two claims resist, and the reason is
measured rather than stylistic: a numpy SCALAR does not survive the crossing
back into Python, arriving as an ordinary `int`, so `np.absolute(-5)` staying
`np.int64` is a fact only the engine can be asked about. An ndarray DOES
survive, by reference, which is why the third claim is plain Python.

`__class__` and `__name__` take the bracket door, which is what rung 5 is for:
inside a class body Python's own compiler mangles a leading double underscore,
so those names have no attribute spelling at any factory.

`Kwargs` stays. It is the seam's own spelling for keyword arguments in a
MeTTa-side call and the Python surface has no other, which is the friction this
file carries beside the scalar crossing.
"""

import numpy as np

from metta import S, ground

#: The three numpy entry points the example binds, and the submodule it holds
#: once so it can reach several functions out of it.
np_abs, np_array, np_arange = ground(np.absolute), ground(np.array), ground(np.arange)
np_random = np.random

#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-24: unpriced placeholder, re-pinned by the
#: integrator; commit=e70eaeba6b6c0afc9081239041b8459eb8bb1b92].
BUDGET = 1


def twin(m):
    """Hold four numpy objects, apply them in the engine, read the answers."""
    # A numpy scalar stays a numpy object INSIDE the engine, which is the
    # tutorial's own point.
    #
    # Known issue: the perfect claim is `isinstance(np.absolute(-5), np.int64)`
    # on the answer Python holds, and a numpy SCALAR does not survive the
    # crossing back: `m.eval` hands Python an ordinary `int` [measured
    # 2026-08-24, Grounded(5) whose .value is an int]. An ndarray DOES survive,
    # by reference, which is why the array claim below is plain `isinstance`.
    # So this one question can only be asked engine-side.
    scalar = (np_abs, -5)
    class_of = S.py_dot(scalar, S["__class__"])
    assert m.fn.py_dot(class_of, S["__name__"]) == [ground("int64")]

    # An applied bound method: the HEAD is itself a term, which no name at the
    # function namespace can spell, so this one is asked as the term it is.
    assert m.eval((S.py_dot(scalar, S.item),)) == [5]

    # An array crosses by reference, so Python can ask about it directly. The
    # example's `(py-atom "[1, 2, 3]")` evaluates Python source text; a Python
    # program writes the list.
    assert isinstance(m.answers((np_array, ground([1, 2, 3]))).one(), np.ndarray)

    # arange means different things by how many arguments you give it.
    #
    # Known issue: the perfect spelling of the last two is Python's own
    # `np.arange(step=2, stop=8)`, and a keyword argument has no Python-authored
    # spelling that still crosses the seam, so `Kwargs` is the seam's own form
    # written out as a term (the design decision is filed; nothing has landed).
    assert m.answers((np_arange, 4)).one().tolist() == [0, 1, 2, 3]
    assert m.answers((np_arange, S.Kwargs(S.step(2), S.stop(8)))).one().tolist() == [0, 2, 4, 6]
    assert m.answers(
        (np_arange, S.Kwargs(S.start(2), S.stop(10), S.step(3)))
    ).one().tolist() == [2, 5, 8]

    # A submodule held once, reached into for the function wanted: randint
    # answers a Python int, not a numpy one.
    assert isinstance(m.answers((ground(np_random.randint), 25)).one(), int)
