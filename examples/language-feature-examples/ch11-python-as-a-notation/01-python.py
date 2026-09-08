"""examples/ch11-python-as-a-notation/01-python.metta in Python: five names for one seam.

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
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
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
#: RE-PINNED 2026-08-26, 25696 to 26095 (+399), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-08-26, 26095 to 26117 (+22), on the composed
#: async-scheduler tree: a live operation call pays the six-inference
#: admission probe the baseline's p14_async_scheduler_comment prices,
#: and the scheduler, context-callback and exact-memo lifecycle clauses
#: move compiled-image layout by tens, the class this file's chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=merged p14-audit-async composed tree with engine/reader.so; commit=5059173b1767600ce4df0f6b7841d88116ee62d3].
#: RE-PINNED 2026-09-01, 26117 to 15598 (-10519), the compiled-language batch:
#: try/raise/dict/set/global/type-alias compilation, engine bit family
#: builtins, prelude except/error-payload ops, variadic doors, twin heals
#: [measured 2026-09-01: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=51b792423cec5787614d1488c0793b8a50eaa6fc].
#: RE-PINNED 2026-09-01, 15598 to 15555 (-43), the subtract-atom primitive and
#: Counter's grain for -=: a new engine head shifts every twin's load
#: structure, the removal doors changed meaning where a twin spells one, and
#: the quad twin stopped being a different program [measured 2026-09-01: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c6a40460b1db341198a6150e3600f502831a6e83].
#: RE-PINNED 2026-09-01, 15555 to 15592 (+37), generic Python operators now
#: dispatch through live protocols while source twins explicitly name
#: relational engine heads [measured 2026-09-01: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=e3787593132a7ece2d300397045f7415709847c9].
#: RE-PINNED 2026-09-02, 15592 to 15827 (+235), static contract discharge and
#: policy-stable recompilation [measured 2026-09-02: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=c00341f0ff9d83d1b9338ca86ad51708eaf07ebd].
#: RE-PINNED 2026-09-02, 15827 to 15847 (+20), static contract discharge with
#: policy checks confined to invalidated contracts [measured 2026-09-02: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c00341f0ff9d83d1b9338ca86ad51708eaf07ebd].
#: RE-PINNED 2026-09-02, 15847 to 15857 (+10), P43 protects both generated
#: policy-check fallbacks from space-local capture [measured 2026-09-02: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c00341f0ff9d83d1b9338ca86ad51708eaf07ebd].
#: RE-PINNED 2026-09-07, 15857 to 15269 (-588), the twin re-authored its
#: markers as expressions, (then-ran) and (else-ran), after c144fcdb gave the
#: MeTTa spelling add-atom upstream PeTTa's own domain (an atom with a head),
#: under which a bare symbol has no answer; the twins lane was a REPORT lane
#: and the failing claim went unreported until 2026-09-07 [measured 2026-09-07:
#: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=6cfa4d2afbfd867f91ee8eec5400a811aa365086].
#: RE-PINNED 2026-09-07, 15269 to 15430 (+161), trunk's own movement since each
#: twin's pin was taken on the base its own branch had: twenty-two first-parent
#: steps between the 0.8.0 release re-pin and this tree, the prelude's move
#: into Prolog the largest of them at +39 to +115 a twin and -65,806 on the
#: error algebra, the live-views merge -45 on every twin that writes, the
#: catalog and get-type repairs +169 on the types chapter, and the rest SWI
#: clause-indexing layout as the boot image grew; this tree also stores the
#: compiled default space operand as &self rather than a (context-space) call
#: [measured 2026-09-07: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=9010a79b01c9b2a66b96a3952fa378fb3e939dc3].
#: RE-PINNED 2026-09-08, 15430 to 15483 (+53), the merges between this lane's
#: burn-down base (dfd5003f) and the tree that merged it, placed by a first-
#: parent ladder through the lane's own driver over ten twins at f8c4b672,
#: 4af59757, 90c08119, ad762ee7, 72f9cdf2 and 249389cb (ai-
#: tmp/integrator-849a9e/mergeTW-twin-ladder.log): the catalog-types merge
#: (1a3579fa) moves every twin by a lookup-and-layout step of about +5 for a
#: twin that makes no typed call and about +35 for one that does, plus about +6
#: per compiled definition through the argument-delivery check at the write
#: (the authoring fit re-measured 1370+1307 to 1406+1309), and +1411 for the
#: catalog twin that enumerates the 280 new rows; the two-sided-fragments merge
#: (4af59757) moves the sequence-variable twins by what their fixed rows now
#: compute (+2604 for the two-sided fragments, -217 for the fence, +19 for
#: restricted spaces); the every-atom merge (90c08119) re-authored the reading-
#: forms twin into the sread half (+3017) and added forty-six twins pinned on
#: its own base 31d54e19, which the merges since moved by the same clusters;
#: the gate-hygiene merge (ad762ee7) makes the tabling twins cheaper by the wfs
#: library no longer loading eagerly. Every twin here re-reads its budget on
#: the merged tree, minimum of three fresh processes [measured 2026-09-08: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=08f6f4df19a283bb84ba5f679c83944b42685b2e].
#: RE-PINNED 2026-09-08, 15483 to 15345 (-138), metta_substitute_self/3 probes
#: the term for the text &self before walking it, one C write and one C
#: substring probe, where the twins-lane merge's one-equation door (08f6f4df)
#: walked every natively added equation in a named space unconditionally, so
#: every twin that adds or defines an equation in a named space drops by about
#: that equation's size in inferences; the same probe now guards the reader's
#: per-form door (record_translated_from/4), the deferred door's fallback
#: (stored_equation_source/4), a batch's arriving equations
#: (mark_or_translate_equation/5) and the removal probe (remove_equation/6),
#: where the walk is new and skipped for a term that never says &self, and a
#: twin that only removes or re-adds such equations pays the two-inference
#: probe per door crossing instead. Every twin here re-reads its budget on this
#: tree, minimum of three fresh processes [measured 2026-09-08: min-of-3 serial
#: fresh processes; command=python extensions/python/tools/twin_coverage.py
#: --repin; commit=856434d7c1d381b3f3d7cbbd008f46c0d41b61aa].
#: RE-PINNED 2026-09-08, 15345 to 15332 (-13), the evaluation-fuel scope marker
#: is a trailed write (fix/every-intermittent-root-caused, f6e05ca9):
#: `$metta_fuel_scope` is written open with b_setval/2 at scope open and read
#: with b_getval/2 where nb_current/2 used to answer, so an abandoned scope
#: closes itself when an exception unwinds the trail and the cleanup is the
#: fast ordinary exit, and every runnable form pays fewer inferences per scope;
#: a twin drops by about the count of its runnables, and the engine bench reads
#: evaluate and translate 1642 lower each on the same tree. Every twin here re-
#: reads its budget on the merged tree, minimum of three fresh processes
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=3fc65f02ce807c359f1a52026f950f345da2a9af].
#: RE-PINNED 2026-09-08, 15332 to 15592 (+260), The engine and library
#: predicates now resolve through their owning modules and the explicit engine
#: facade; compiled program lookup crosses the added metta_engine tier
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=WORKTREE].
#: RE-PINNED 2026-09-08, 15592 to 15445 (-147), The engine and library module
#: boundaries retain explicit lookup owners, including host registration and
#: returned callback goals [measured 2026-09-08: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=WORKTREE].
BUDGET = 15445
