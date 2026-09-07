"""examples/ch19-spaces-backed-by-anything/19-04-a-space-on-mork/01-mm2-operators.metta in Python: five operators over MORK's Rust trie.

lib_mm2's names are full-width plus and minus and an arrow, which Python's
grammar will not take, so every one of them comes through the exact subscript
door -- rung 5, and the one the ladder keeps for exactly this.

The example skips itself when the backend has not been built and so does
this, on the same artefact and with the same reason: a Rust toolchain is not
one of the engine's requirements.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from pathlib import Path

from metta import S, V, lib
from metta.errors import MettaError

_REPO = Path(__file__).resolve().parents[6]
LIBMORK = _REPO / Path("extensions/mork/mork_ffi/target/release/libmork_ffi.so")


def available(m):
    """Whether the MORK seat's artifact is built on this box.

    The lane asks this before `twin(m)` and compares the budget below only
    where it answers True: the budget was measured with the artifact present,
    and without it the twin takes the same guarded path its example takes.
    """
    del m
    return LIBMORK.exists()


def twin(m):
    """Require a seat by name, then add, remove, transform and flush."""
    # The original opens with lib_file, for the artefact check it makes in
    # MeTTa; here the check is Python's own `Path.exists`, and the import
    # stays so both spaces hold the same equations.
    m += lib.file
    # `require-extension!` is the engine's answer for the half that is
    # missing: a seat nobody ships is refused BY NAME rather than at the
    # first call into it.
    missing = None
    try:
        m.fn["require-extension!"](S.nosuchseat).one()
    except MettaError as failure:
        missing = failure
    assert "extension nosuchseat is required and not loaded" in str(missing)

    # A seat that IS loaded answers the unit, so a library can state its
    # dependency and carry on.
    assert m.fn["require-extension!"](S.python) == [()]

    if not LIBMORK.exists():
        # The example prints its skip here. A twin has no door for prose.
        return

    m += lib["lib_mm2"]
    add, add_many = m.fn["＋"], m.fn["＋*"]  # noqa: RUF001  -- the operators ARE full-width; that is what keeps them from colliding with arithmetic
    remove, transform = m.fn["－"], m.fn["~>"]  # noqa: RUF001  -- the operators ARE full-width; that is what keeps them from colliding with arithmetic
    mork = m.metta.space(S.mork)

    def edges():
        """Every (x y) an edge relates, sorted so a claim can name them."""
        return sorted(((row.x, row.y) for row in mork[S.edge(V.x, V.y)]), key=str)

    # ＋ is add-atom and － is remove-atom, both on &mork. The names are  # noqa: RUF003
    # full-width so they cannot collide with arithmetic.
    add(S.edge(S.a, S.b)).one()
    assert edges() == [(S.a, S.b)]
    remove(S.edge(S.a, S.b)).one()
    assert edges() == []

    # ＋* is the bulk add: a whole expression in one crossing, MORK parsing  # noqa: RUF003
    # the batch itself.
    add_many((S.edge(S.a, S.b), S.edge(S.b, S.c), S.edge(S.c, S.d))).one()
    assert edges() == [(S.a, S.b), (S.b, S.c), (S.c, S.d)]

    # `mork-add-atoms` is the operation under ＋*, taking the space  # noqa: RUF003
    # explicitly, and `mork-flush` makes queued additions visible.
    m.fn["mork-add-atoms"](mork, (S.tag(1), S.tag(2))).one()
    m.fn["mork-flush"](mork).one()
    assert sorted(row.n.value for row in mork[S.tag(V.n)]) == [1, 2]

    # ~> is the transform, and it is MORK's own MM2 calculus rather than a
    # MeTTa rewrite: a conjunction of patterns and an output block.
    transform(S[","](S.edge(V.x, V.y)), S.O(S["+"](S.path(V.x, V.y)))).one()
    paths = sorted(((row.x, row.y) for row in mork[S.path(V.x, V.y)]), key=str)
    assert paths == [(S.a, S.b), (S.b, S.c), (S.c, S.d)]

    # `mm2-exec` is the step ~> takes, and a transform that both removes and
    # adds is how a rule REPLACES facts rather than accumulating them.
    # `S["-"]` and not `S._`: the removal sink is the MINUS sign, and the
    # host-convention map's inverse would read `S._` as the underscore symbol,
    # which MORK answers with `unrecognized sink`.
    removes = S.O(S["-"](S.path(V.x, V.y)), S["+"](S.route(V.x, V.y)))  # rung: MM2 sinks are punctuation
    transform(S[","](S.path(V.x, V.y)), removes).one()
    m.fn["mm2-exec"](mork, 1).one()
    routes = sorted(((row.x, row.y) for row in mork[S.route(V.x, V.y)]), key=str)
    assert routes == [(S.a, S.b), (S.b, S.c), (S.c, S.d)]
    assert mork[S.path(V.x, V.y)] == []

    # Cleaning up after itself, because &mork is one store for the process.
    for x, y in edges():
        remove(S.edge(x, y)).one()
    for x, y in routes:
        remove(S.route(x, y)).one()
    for row in mork[S.tag(V.n)]:
        remove(S.tag(row.n)).one()
    assert mork[V.any] == []


#: MEASURED on this branch rather than inherited: this twin is new, so there is
#: no earlier pin to move
#: [measured 2026-09-07: 117590 inferences, 0.9534x the example's 123334; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3;
#: fixture=docs/every-atom-has-an-example at its example commits; commit=98397cdd04679cbf40b2d515076dadc09c1b0a32].
#: RE-PINNED 2026-09-08, 117590 to 117595 (+5), the merges between this lane's
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
#: extensions/python/tools/twin_coverage.py --repin; commit=WORKTREE].
BUDGET = 117595
