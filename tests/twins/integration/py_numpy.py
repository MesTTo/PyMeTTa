"""examples/integration/py_numpy.metta in Python: numpy through the seam.

The example is the language's own tutorial for holding Python objects in MeTTa
[source: metta-lang.dev/docs/learn/tutorials/python_use/py_atom]. Every
`!(bind! np-abs (py-atom numpy.absolute))` is a Python name binding here, which
is what a token was for: `np_abs = val(np.absolute)` names the object itself
rather than parsing its dotted path, and applying it is an ordinary tuple, the
head being the function.

Where Python has the concept it wins, and here that means most of the file:
`(py-iter ...)` under a `collapse` is `.tolist()`, and asking what class an
answer belongs to is `isinstance`. Two claims resist, and the reason is
measured rather than stylistic: a numpy SCALAR does not survive the crossing
back into Python, arriving as an ordinary `int`, so `np.absolute(-5)` staying
`np.int64` is a fact only the engine can be asked about. An ndarray DOES
survive, by reference, which is why the third claim is plain Python. The two
that stay are also where `__class__` and `__name__` need `sym(...)`: the S
factory refuses every name beginning with `__` (residue, P14.5).

`Kwargs` stays too. It is the seam's own spelling for keyword arguments in a
MeTTa-side call and the Python surface has no other, which is the second
residue entry here.
"""

import numpy as np

from petta import S, sym, val

#: The three numpy entry points the example binds, and the submodule it holds
#: once so it can reach several functions out of it.
np_abs, np_array, np_arange = val(np.absolute), val(np.array), val(np.arange)
np_random = np.random

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 6803 to 2652, -4151 (-61.0%), by the twin contract
#: change: seven `test` wrappers, three `collapse`/`py-iter` pairs and four
#: `py-dot` reaches left the engine for `assert`, `.tolist()` and `isinstance`,
#: which on a value already in Python are native operations with no crossing at
#: all. The two `py-dot` claims that remain are the two the crossing cannot
#: answer. Against the example's 18790 the ratio is 0.1411, the cheapest twin in
#: this folder [measured 2026-08-22 min-of-3: `twin_coverage.py --measure
#: examples/integration/py_numpy.metta`]. Prior: RE-PINNED at 6803, +2, by the
#: NumPy crossing floor rather than a semantic path (twelve fresh processes on
#: three trees all read 6803); ADDED 2026-08-22 at 6801 by the wave-3 twin
#: baseline, which priced a transliteration.
BUDGET = 2652


def twin(m):
    """Hold four numpy objects, apply them in the engine, read the answers."""
    # A numpy scalar stays a numpy object INSIDE the engine, which is the
    # tutorial's own point; it is an ordinary int by the time Python sees it,
    # so this is the one question only the engine can be asked.
    scalar = (np_abs, -5)
    assert m.eval(S["py-dot"](S["py-dot"](scalar, sym("__class__")), sym("__name__"))) == [
        val("int64")
    ]
    assert m.eval((S["py-dot"](scalar, S.item),)) == [5]

    # An array crosses by reference, so Python can ask about it directly. The
    # example's `(py-atom "[1, 2, 3]")` evaluates Python source text; a Python
    # program writes the list.
    assert isinstance(m.one((np_array, val([1, 2, 3]))), np.ndarray)

    # arange means different things by how many arguments you give it, and
    # Kwargs is how a MeTTa-side call skips the ones it does not care about.
    assert m.one((np_arange, 4)).tolist() == [0, 1, 2, 3]
    assert m.one((np_arange, S.Kwargs(S.step(2), S.stop(8)))).tolist() == [0, 2, 4, 6]
    assert m.one((np_arange, S.Kwargs(S.start(2), S.stop(10), S.step(3)))).tolist() == [2, 5, 8]

    # A submodule held once, reached into for the function wanted: randint
    # answers a Python int, not a numpy one.
    assert isinstance(m.one((val(np_random.randint), 25)), int)
