"""Purpose: declare two overloads for one compiled Python implementation.

Guarantees:
  - both correlated signatures are stored before their shared equation
    [tested: test_define_emits_each_overload_from_one_source; commit=9958c72363d2fbc640d2ae39ee6f0670ecfbff67]
"""

from typing import overload

from metta import S, arrow, fn, ground


def twin(m):
    """Use typing.overload as declarations and keep one executable body."""

    @overload
    def compiled_identity(value: int) -> int: ...

    @overload
    def compiled_identity(value: str) -> str: ...

    @m.define
    def compiled_identity(value):
        return value

    assert set(m.eval(fn.get_type(S.compiled_identity))) == {
        arrow(int, int), arrow(str, str)
    }
    assert compiled_identity(7) == [7]
    assert compiled_identity(ground("word")) == [ground("word")]


#: The final image includes the provisioned engine and MORK artifacts.
#: [measured: 4769, 4769, 4769 inferences; command=PYTHONPATH=extensions/python:extensions/python/tools $VENV/bin/python -c "from pathlib import Path; from twin_coverage import run_twin; print(run_twin(Path('extensions/python/examples/language-feature-examples/ch09-types/18-compiled_overloads.py').resolve()).cost)"; fixture=three independent fresh harness processes; commit=9958c72363d2fbc640d2ae39ee6f0670ecfbff67]
#: RE-PINNED 2026-09-06, 4769 to 4800 (+31), the one pricing pass at the 0.8.0
#: release cut, and trunk's own movement rather than any mechanism in this
#: twin: each pin was taken on the base its own branch had, and the September
#: merge wave has moved the engine's clause layout, the evaluation path and the
#: library's write doors since [measured 2026-09-06: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=b96e1a15260b7538a8e42be613bcc5dd0dddd136].
#: RE-PINNED 2026-09-07, 4800 to 4905 (+105), trunk's own movement since each
#: twin's pin was taken on the base its own branch had: twenty-two first-parent
#: steps between the 0.8.0 release re-pin and this tree, the prelude's move
#: into Prolog the largest of them at +39 to +115 a twin and -65,806 on the
#: error algebra, the live-views merge -45 on every twin that writes, the
#: catalog and get-type repairs +169 on the types chapter, and the rest SWI
#: clause-indexing layout as the boot image grew; this tree also stores the
#: compiled default space operand as &self rather than a (context-space) call
#: [measured 2026-09-07: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=9010a79b01c9b2a66b96a3952fa378fb3e939dc3].
#: RE-PINNED 2026-09-08, 4905 to 4944 (+39), the merges between this lane's
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
#: RE-PINNED 2026-09-08, 4944 to 4932 (-12), metta_substitute_self/3 probes the
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
#: RE-PINNED 2026-09-08, 4932 to 4925 (-7), the evaluation-fuel scope marker is
#: a trailed write (fix/every-intermittent-root-caused, f6e05ca9):
#: `$metta_fuel_scope` is written open with b_setval/2 at scope open and read
#: with b_getval/2 where nb_current/2 used to answer, so an abandoned scope
#: closes itself when an exception unwinds the trail and the cleanup is the
#: fast ordinary exit, and every runnable form pays fewer inferences per scope;
#: a twin drops by about the count of its runnables, and the engine bench reads
#: evaluate and translate 1642 lower each on the same tree. Every twin here re-
#: reads its budget on the merged tree, minimum of three fresh processes
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=3fc65f02ce807c359f1a52026f950f345da2a9af].
#: RE-PINNED 2026-09-08, 4925 to 4942 (+17), boot content moved: the refusal
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
#: RE-PINNED 2026-09-08, 4942 to 4977 (+35), The typed host door catalog is
#: published before user code. Its declarations change catalog lookup indexes;
#: generated public names bind directly to their existing bodies [measured
#: 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=WORKTREE].
BUDGET = 4977
