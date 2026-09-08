"""Purpose: examples/ch08-data/08-02-sequence-variables/05-the-fence.metta in Python: the refusal, and what it says.

A refusal arrives as an EngineError, and its message is what Python can read:
the pattern it refused, the rule it broke, and the classifier that decides.
The MeTTa side takes the same refusal apart with `index-atom`, because there it
is an ordinary error atom carrying five children; the exception exposes no
attribute for that payload, so each claim below is made against the message.

The refusing `case` arm is the one line here that cannot be Python. A pattern
binding one name twice is a SyntaxError in `match/case`, and one name in both
the gap and the ordinary role is exactly that shape, so the arm tower is built
as a term and evaluated.
"""

from metta import S, V, equation, seg, solve
from metta.errors import EngineError


def twin(m):
    """Meet the fence, read what it says, and take the remedy."""
    seven = S.Order(7, S.x, S.y)
    m += seven

    # One name may not be both a gap and an ordinary variable: that mix has no
    # finite reading outside an equation head.
    refusal = None
    try:
        list(m[(S.Order, seg(V.mm), V.mm)])
    except EngineError as error:
        refusal = error
    message = str(refusal)

    # What the message carries: the pattern, the open other side a space match
    # has not read yet, the rule, and the classifier that decides it.
    assert "outside the proved finitary fragment" in message
    assert "against any atom" in message
    assert "mixed_roles" in message
    assert "metta_seq_classify/3" in message
    assert "Theorem 62" in message
    assert "Kutsia Section 6.2" in message
    assert "Kutsia Section 6.3" in message

    # The refusal is carried, not raised while the program loads: it travels
    # with the compiled pattern and throws at the ask, so an arm nothing
    # reaches cannot stop a program from running.
    arms = (
        (S.Order(8), S.plain),
        ((S.Order, seg(V.mm), V.mm), S.never),
        (V.otherwise, S.other),
    )
    assert m.eval(S.case(S.Order(8), arms)) == [S.plain]  # rung: match/case cannot bind one name twice

    # The remedy is to ask for the run and for the term under different names,
    # and to compare them where comparison belongs.
    answered = [S.pair(row.run, row.last) for row in m[(S.Order, seg(V.run), V.last)]]
    assert answered == [S.pair(seven[1:3], S.y)]
    pair = S.Order(S.x(S.y), S.x(S.y))
    agreeing = solve((S.Order, seg(V.run), V.last), pair).one()
    assert list(agreeing.run) == [agreeing.last]

    # An equation head is the one place the mix is admitted, because a head is
    # always the pattern side of a one-sided match.
    m += equation(S.echoes((seg(V.xs), S.tag, V.xs))).to(S.yes)  # rung: *args is refused at a compiled parameter
    assert m.fn.echoes((S.a, S.b, S.tag, S.a(S.b))) == [S.yes]

    # The classifier's second refusal, `no_certificate`, is for a pair with
    # gaps on BOTH sides that fits no fragment, so it names the certificate it
    # could not produce rather than a rule the program broke. `unify` is the
    # door that reaches it, being the one form whose two operands are syntax.
    nested = None
    try:
        list(m.fn.unify(
            S.f(S.g(seg(V.u), S.b)), S.f(S.g(S.a, seg(V.v))), S.yes, S.no
        ))
    except EngineError as error:
        nested = str(error)
    assert "no_certificate" in nested
    assert "outside the proved finitary fragment" in nested

    # That pair fails both two-sided fragments at once: its gaps sit below the
    # root, which the shallow fragment forbids, and neither is the last child
    # of its own expression, which the last-position fragment requires.
    # Kutsia's own infinitary witness fails for the other reason: its gaps ARE
    # at the root, but one name carries both, so the pair is not linear.
    commuting = None
    try:
        list(m.fn.unify(
            (S.f, seg(V.x), S.a), S.f(S.a, seg(V.x)), S.yes, S.no
        ))
    except EngineError as error:
        commuting = str(error)
    assert "no_certificate" in commuting

    # The two refusals carry the same message and differ in what they name: no
    # name is caught in both roles here, so the mixed list is empty where the
    # mixed-role refusal above named one.
    assert "mixed-roles: none" in commuting


#: What this twin spends, its own tripwire, taken on the tree that
#: introduced it with the engine's .qlf set built, which is what the
#: gate leaves behind and what ships.
#: [measured: 6248, 6248, 6248 inferences; command=PYTHONPATH=extensions/python:extensions/python/tools $VENV/bin/python -c "from pathlib import Path; from twin_coverage import run_twin; print(run_twin(Path('extensions/python/examples/language-feature-examples/ch08-data/08-02-sequence-variables/05-the-fence.py').resolve()).cost)"; fixture=three independent fresh harness processes at loadavg 46; commit=a403e56b4f33828834823338eb1fc316e3fea2a4]
#: RE-PINNED 2026-09-07, 6248 to 6199 (-49), the twin itself changed: its
#: no_certificate block now catches a refusal where it used to collect an
#: answer, because that shape reaches the classifier's second refusal now that
#: the door parses both operands [measured 2026-09-07: min-of-3 serial fresh
#: processes, this branch against the same twin on its base 5a85f5602;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=f4ae837efd23791200846ba72556c2ce96a7d05a].
#: RE-PINNED 2026-09-07, 6248 to 6449 (+201), trunk's own movement since each
#: twin's pin was taken on the base its own branch had: twenty-two first-parent
#: steps between the 0.8.0 release re-pin and this tree, the prelude's move
#: into Prolog the largest of them at +39 to +115 a twin and -65,806 on the
#: error algebra, the live-views merge -45 on every twin that writes, the
#: catalog and get-type repairs +169 on the types chapter, and the rest SWI
#: clause-indexing layout as the boot image grew; this tree also stores the
#: compiled default space operand as &self rather than a (context-space) call
#: [measured 2026-09-07: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=9010a79b01c9b2a66b96a3952fa378fb3e939dc3].
#: RE-PINNED 2026-09-08, 6449 to 6233 (-216), the merges between this lane's
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
#: RE-PINNED 2026-09-08, 6233 to 6207 (-26), metta_substitute_self/3 probes the
#: term for the text &self before walking it, one C write and one C substring
#: probe, where the twins-lane merge's one-equation door (08f6f4df) walked
#: every natively added equation in a named space unconditionally, so every
#: twin that adds or defines an equation in a named space drops by about that
#: equation's size in inferences; the same probe now guards the reader's per-
#: form door (record_translated_from/4), the deferred door's fallback
#: (stored_equation_source/4), a batch's arriving equations
#: (mark_or_translate_equation/5) and the removal probe (remove_equation/6),
#: where the walk is new and skipped for a term that never says &self, and a
#: twin that only removes or re-adds such equations pays the two-inference
#: probe per door crossing instead. Every twin here re-reads its budget on this
#: tree, minimum of three fresh processes [measured 2026-09-08: min-of-3 serial
#: fresh processes; command=python extensions/python/tools/twin_coverage.py
#: --repin; commit=856434d7c1d381b3f3d7cbbd008f46c0d41b61aa].
#: RE-PINNED 2026-09-08, 6207 to 6219 (+12), boot content moved: the refusal
#: table and the typing point are modules this package did not have, three
#: convert doors became one, per-library faces are projections, and the engine
#: gained a catalog watch point, and SWI clause-indexing shape shifts a twin
#: count by tens whenever boot content moves, the mechanism every earlier entry
#: in these chains names. The watch point itself is one inference per &metta
#: write, which a twin that defines a function pays three of (2239 against 2236
#: on ch03 01-comments with the two announcement clauses taken out), and the
#: (limit ...) rows it exists for cost nothing at all: 2239 either way with
#: every row-backed bound removed, because boot seeds the mirror those bounds
#: are read from [measured 2026-09-08: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=c26b6a4d28ef8fb50742440feed2c0578ebb0f58].
#: RE-PINNED 2026-09-08, 6219 to 6279 (+60), the module boundary merged with
#: trunk's later packages (refactor/engine-and-libraries-as-modules at
#: b64291369): every space now resolves through one more chain link, prelude ->
#: metta_engine -> user, the engine's measured export list is imported into the
#: host tier at boot, the closed-sets watch point costs one inference per
#: &metta write, and a cursor opened by a host pays one transaction check at
#: its door; the branch pinned its budgets on its cut, trunk re-pinned the same
#: twins for the packages that landed after that cut, and only the merged tree
#: carries both, so this entry is where the two chains meet [measured
#: 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=f1038acdcaf5230b6431c112f38a719d3dc9ef19].
#: RE-PINNED 2026-09-08, 6279 to 6381 (+102), Trailing occurrence arguments,
#: token allocation in native writes, exact source withdrawal and transaction-
#: safe shared-table guards change the engine work priced by this twin; answer
#: bags retain the upstream law [measured 2026-09-08: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=WORKTREE].
BUDGET = 6381
