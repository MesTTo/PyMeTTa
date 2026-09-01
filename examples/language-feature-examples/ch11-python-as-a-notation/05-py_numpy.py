"""examples/ch11-python-as-a-notation/05-py_numpy.metta in Python: numpy through the seam.

The example is the language's own tutorial for holding Python objects in MeTTa
[source: metta-lang.dev/docs/learn/tutorials/python_use/py_atom]. Every
`!(bind! np-abs (py-atom numpy.absolute))` is a Python name binding here, which
is what a token was for: `np_abs = ground(np.absolute)` names the object itself
rather than parsing its dotted path, and applying it is an ordinary tuple whose
head IS the function.

Where Python has the concept it wins: `(py-iter ...)` under a `collapse` is
`.tolist()`, and the scalar and ndarray answers both cross by reference. The
numeric operator boundary calls Python for a held scalar, so the tutorial's
addition remains `np.int64` on the Python side too.

`__class__` and `__name__` take the bracket door, which is what rung 5 is for:
inside a class body Python's own compiler mangles a leading double underscore,
so those names have no attribute spelling at any factory.

`Kwargs` is the stored MeTTa spelling for a Python call's keyword arguments;
calling the held object with Python keywords builds that spelling directly.
"""

import numpy as np

from metta import S, ground

#: The three numpy entry points the example binds, and the submodule it holds
#: once so it can reach several functions out of it.
np_abs, np_array, np_arange = ground(np.absolute), ground(np.array), ground(np.arange)
np_random = np.random


def twin(m):
    """Hold four numpy objects, apply them in the engine, read the answers."""
    # A numpy scalar stays the same Python object through the answer seam, and
    # Python's addition keeps the library result class. The engine-side class
    # question mirrors the tutorial while the direct assertions pin the
    # Python view that used to be lost.
    scalar = (np_abs, -5)
    class_of = S.py_dot(scalar, S["__class__"])
    assert m.fn.py_dot(class_of, S["__name__"]) == [ground("int64")]
    scalar_answer = m.answers(scalar).one()
    assert type(scalar_answer) is np.int64

    # An applied bound method: the HEAD is itself a term, which no name at the
    # function namespace can spell, so this one is asked as the term it is.
    assert m.eval((S.py_dot(scalar, S.item),)) == [5]

    addition = m.answers(S["+"](scalar, 10)).one()
    assert type(addition) is np.int64
    assert addition == np.int64(15)

    # An array crosses by reference, so Python can ask about it directly. The
    # example's `(py-atom "[1, 2, 3]")` evaluates Python source text; a Python
    # program writes the list.
    assert isinstance(m.answers((np_array, ground([1, 2, 3]))).one(), np.ndarray)

    # arange means different things by how many arguments you give it, and
    # a keyword argument is Python's own concept, so Python's own syntax
    # reaches it: applying a head with keywords builds the seam's
    # `(Kwargs (name value)...)` tail, the exact form py-call splits, and
    # the names stay exact because they are Python parameter names.
    assert m.answers(np_arange(4)).one().tolist() == [0, 1, 2, 3]
    assert m.answers(np_arange(step=2, stop=8)).one().tolist() == [0, 2, 4, 6]
    assert m.answers(np_arange(start=2, stop=10, step=3)).one().tolist() == [2, 5, 8]

    # A submodule held once, reached into for the function wanted: randint
    # answers a Python int, not a numpy one.
    assert isinstance(m.answers((ground(np_random.randint), 25)).one(), int)


#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-24: unpriced placeholder, re-pinned by the
#: integrator; commit=e70eaeba6b6c0afc9081239041b8459eb8bb1b92].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 3093 to 3112, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 3112 to 3113, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 3113 to 3140, on the release tree:
#: the typed-dispatch question moved engine-side
#: (metta_typed_dispatch_applies/2, one extra frame per direct
#: call), the conformance kit gained the family, source and
#: round-trip laws, extensions gained the spaces([...]) readying
#: moment, and any boot-content change also moves counts a few
#: tens through SWI's clause-indexing shape (qlf_boot.pl's header
#: carries the A/B), so the corpus re-pins once on the exact
#: shipping tree [measured 2026-08-25 through
#: tools/twin_coverage.py --measure min-of-3 after a canonical
#: single-boot QLF regeneration].
#: RE-PINNED 2026-08-25, 3140 to 3921, for identity-preserving
#: Python numeric dispatch and concrete Number admission: the twin now reads
#: the retained scalar and exercises the tutorial addition through Python's
#: operator seam. The 3140 starting point is the integration pricing pass
#: immediately preceding this branch [measured 2026-08-25 through
#: tools/twin_coverage.py
#: examples/ch11-python-as-a-notation/05-py_numpy.metta].
#: RE-PINNED 2026-08-25, 3921 to 3932, after the numeric seam's admission
#: gate was restricted to ground host operands. The eleven-inference movement
#: is the failure-boundary check that keeps a free operand as a MeTTa term
#: instead of sending an insufficiently-instantiated call through Janus
#: [measured 2026-08-25 through tools/twin_coverage.py
#: examples/ch11-python-as-a-notation/05-py_numpy.metta; provisional on the merged tree,
#: the final release measure re-prices].
#: RE-PINNED 2026-09-01, 3932 to 4404 (+472), the compiled-language batch:
#: try/raise/dict/set/global/type-alias compilation, engine bit family
#: builtins, prelude except/error-payload ops, variadic doors, twin heals
#: [measured 2026-09-01: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=51b792423cec5787614d1488c0793b8a50eaa6fc].
#: RE-PINNED 2026-09-01, 4404 to 4439 (+35), generic Python operators now
#: dispatch through live protocols while source twins explicitly name
#: relational engine heads [measured 2026-09-01: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=e3787593132a7ece2d300397045f7415709847c9].
#: RE-PINNED 2026-09-02, 4439 to 4588 (+149), static contract discharge and
#: policy-stable recompilation [measured 2026-09-02: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=WORKTREE].
BUDGET = 4588
