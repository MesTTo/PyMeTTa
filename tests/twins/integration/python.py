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

The first claim's SEQUENCE is three Python statements with the object held
in a Python name between them: an atom crossed back into an argument arrives
unwrapped (py_arg_norm runs the same _unwrap the apply route runs), which is
what closed the friction this file used to record.
"""

import math

from metta import G, S, fn, ground

#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-24: unpriced placeholder, re-pinned by the
#: integrator; commit=e70eaeba6b6c0afc9081239041b8459eb8bb1b92].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 24034 to 24072, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (petta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 24072 to 24078, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 24078 to 23323, on the release tree:
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
#: RE-PINNED 2026-08-25, 23323 to 25691, as the example grows its
#: three integration rows (keyword arguments on a bound callable,
#: an opaque dict read by method, type reflection), mirrored here
#: [measured 2026-08-25 through tools/twin_coverage.py on the
#: extended pair].
#: RE-PINNED 2026-08-25, 25691 to 25696, on the identity-wire merge:
#: the numeric seam declarations move the compiled layout by a few
#: inferences (the same clause-indexing effect qlf_boot.pl records)
#: [measured 2026-08-25 through tools/twin_coverage.py on the merged
#: tree; provisional, the final release measure re-prices].
BUDGET = 25696


def twin(m):
    """Wrap the seam five ways, then use it: objects, methods, keywords,
    an opaque collection, and reflection.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

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

    # Make an object, give it an attribute, read the attribute back: three
    # Python statements, the object in a Python name between them, which is
    # this file's whole point. The crossed atom re-enters as an argument and
    # arrives unwrapped (py_arg_norm runs the same _unwrap the apply route
    # runs), so the chain no longer needs a single let* term.
    obj, = m.eval(S.make_object())
    m.eval(S.set_attribute(obj, S.foo, S["math.pi"]()))
    assert m.eval(S.get_attribute(obj, S.foo)) == [math.pi]   # [3.141592653589793]

    # A bound method is a head like any other, and its receiver is the argument.
    py = m.fn.py_call
    assert py(S[".upper"](ground("abc"))) == [S.ABC]   # (py-call (.upper "abc")) is ABC
    assert py(S[".__add__"](5, 3)) == [8]   # (py-call (.__add__ 5 3)) is 8

    # Keyword arguments ride a bound callable, and Python's own keyword
    # syntax builds the seam's (Kwargs ...) form at the call: applying the
    # handle splits it into Python keywords, while py-call itself keeps
    # upstream's plain positional semantics.
    py_round, = m.eval(S.py_atom(S.round))          # (bind! py-round (py-atom round))
    assert m.eval(py_round(3.14159, ndigits=2)) == [3.14]

    # A Python collection stays ONE object on this surface: the dict is held
    # whole, and reading it is asking it, the same method-call shape as above.
    prefs, = m.eval(S.py_atom(ground("dict(colour='green', size=7)")))
    assert py(S[".get"](prefs, S.size)) == [7]

    # The object loop closes with reflection: type answers the class, and the
    # class is an object with attributes like any other.
    cls, = py(S.type(S.make_object()))
    named, = m.eval(S.py_dot(cls, S["__name__"]))
    assert named == G("SimpleNamespace")
