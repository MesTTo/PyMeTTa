"""Purpose: examples/ch17-concurrency-and-the-loop/08-class_grains.metta in Python.

A frozen dataclass is a value. A mutable dataclass shares its class population.
A Space subclass owns private facts and rules. Both notations query those rows.
[tested: examples/ch17-concurrency-and-the-loop/08-class_grains.metta and its
Python twin; commit=518e67bc11d72ed28dfda7dd0646d1f48d14ac24]
Guarantees: the returned native value retains its current stored Space field
  [tested: examples/ch17-concurrency-and-the-loop/08-class_grains.metta and its
  Python twin; commit=bc30fbd0bbcbf535de217d5a9efad2910002f343].
Owns resources:
  - the scope releases the declaring space, classes and their instances.
"""

from dataclasses import dataclass

from metta import S, Space, Symbol, V, convert, equation, lib


def twin(m):
    """Inspect a real projection, replace facts and call two private rules."""
    m += lib.thread
    with m.scope():
        home = m.metta.space()

        @home.define
        @dataclass(frozen=True)
        class GrainPoint:
            x: int
            y: int

        @home.define
        @dataclass
        class GrainAccount:
            owner: str
            balance: int

        @home.define
        @dataclass
        class GrainAgent(Space):
            label: Symbol

        @home.define
        def discard(account: GrainAccount) -> bool:
            del account
            return True

        points = m.metta.space(S.GrainPoint)
        accounts = m.metta.space(S.GrainAccount)
        # Inspect the generated equation, including its constructor pattern.
        projection = points.eval(S.match(
            points,
            equation(S["GrainPoint-x"](S.GrainPoint(V.x, V.y))).to(V.x),
            True,  # noqa: FBT003 -- the query's answer template is the boolean atom
        )) == [True]
        point_x = home.fn["GrainPoint-x"](GrainPoint(3, 4)).one()
        alice = GrainAccount(owner="alice", balance=40)
        bob = GrainAccount(owner="bob", balance=80)
        alice.balance = 50
        population = tuple(sorted(row.n.value for row in accounts[
            S["_field-balance"](V.account, V.n)
        ]))

        def rejected():
            alice.balance = 0
            raise ValueError

        try:
            home.transaction(rejected)
        except ValueError:
            pass
        restored = alice.balance
        discard(bob).one()
        remaining = len(accounts[S["owned-by"](V.account)])

        left, right = GrainAgent(S.left), GrainAgent(S.right)
        private = equation(S.private_rule(V.receiver)).to(
            S["GrainAgent-label"](V.receiver)
        )
        # rung: these per-instance equations expose the prototype grain itself.
        for agent in (left, right):
            agent += S.internal(S.private_rule)
            agent += private
        private_values = (left.fn.private_rule(left).one(), right.fn.private_rule(right).one())
        receiver = convert.project(left).atom
        outside = home.eval(S.private_rule(receiver)) == [S.private_rule(receiver)]
        assert (projection, point_x, population, restored, remaining, private_values, outside) == (
            True, 3, (50, 80), 50, 1, (S.left, S.right), True,
        )

    rows = m.metta.space()
    with m.scope():
        rows += S.owned(S.item)
        # rung: the native cleanup expression and library spellings are the subject.
        m.fn["scope_defer"](S.item, S.remove_atom(rows, S.owned(S.item))).one()
        during = S.owned(S.item) in rows
    after = list(rows[S.owned(V.x)])
    released = m.fn["drop-space"](rows).one()
    other = m.metta.space()
    released_longhand = m.fn["space_drop"](other).one()
    assert (during, after, released, released_longhand) == (True, [], True, True)

    with m.scope():
        store = m.metta.space()
        with m.scope() as inner:
            child = m.metta.space()
            child += S.payload(9)
            store += S.field(S["scoped-value"], child)
            # rung: this value declares its edges and cleanup as native queries.
            m.fn["scope-defer"](
                S["scoped-value"],
                S.remove_atom(store, S.field(S["scoped-value"], V.old)),
                S.match(store, S.field(S["scoped-value"], V.current), V.current),
            ).one()
            root = inner.keep(S["scoped-value"])
        child_name = store[S.field(root, V.current)].one().current
        retained = m.metta.space(child_name)
        assert [row.value.value for row in retained[S.payload(V.value)]] == [9]


#: The complete twin declares three Python classes, including their constructor
#: signatures, checked writers and proxy ownership, then releases those programs.
#: The native example writes the equations used by its claims. Their measured
#: difference is the additional declaration and crossing work in this twin.
#: [measured: 14249592 twin and 2530741 native inferences; command=python
#: extensions/python/tools/twin_coverage.py --measure
#: examples/ch17-concurrency-and-the-loop/08-class_grains.metta; fixture=min of
#: three serial fresh processes after deleting engine/lib QLF; commit=9b0a084e534ddf7dd67980ad84c27c8279b877f1].
#: RE-PINNED 2026-09-13, 14249592 to 14248264 (-1328), Native import
#: reconciliation retains unchanged providers during class and scope cleanup;
#: the body and stored contents are unchanged [measured 2026-09-13: min-of-3
#: serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=518e67bc11d72ed28dfda7dd0646d1f48d14ac24].
#: RE-PINNED 2026-09-13, 14248264 to 14248453 (+189), Generated type checks use
#: inline control flow instead of a runtime once meta-call; their joint
#: witnesses and scalar validation are unchanged [measured 2026-09-13: min-of-3
#: serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=6c70946993db4811ebc46c618e8c68a18474694c].
#: RE-PINNED 2026-09-13, 14248453 to 14263254 (+14801). Reference maps
#: canonicalize argument constraints during class-space publication. The
#: constructors, field operations and stored content remain the same.
#: [measured: 14263254 twin inferences; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3
#: examples/ch17-concurrency-and-the-loop/08-class_grains.metta;
#: fixture=serial fresh processes after deleting engine/lib QLF; commit=a95e6c90c910db30c72311abadd58dee5349978c].
#: RE-PINNED 2026-09-13, 14263254 to 14262547 (-707). The shared effect
#: planner follows references through their defining modules and source bodies.
#: [measured: 14262547 twin inferences, min-of-3 fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --measure --rounds 3
#: examples/ch17-concurrency-and-the-loop/08-class_grains.metta;
#: fixture=built native engine after deleting engine/lib QLF; commit=89084b43ff1a758f703ce77cd96b026f56510116]
#: RE-PINNED 2026-09-15, 14262547 to 10400240 (-3862307). The added current-
#: field dependency claim uses public matching. Intervening reference repairs
#: and singleton memo retirement also contribute to the measured change.
#: [measured: 10400240 twin inferences, min-of-10 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin --rounds 10
#: --reason 'The current-field dependency claim and intervening reference repairs now use deterministic singleton memo retirement'
#: examples/ch17-concurrency-and-the-loop/08-class_grains.metta;
#: fixture=serial fresh processes after deleting engine/lib QLF; commit=bc30fbd0bbcbf535de217d5a9efad2910002f343].
#: RE-PINNED 2026-09-18, 10400240 to 7367057 (-3033183), the branch's landings
#: since the 09-10 pins, re-taken on the tip f06186a96: the compiled call law
#: (e59104ace: an Atom argument enters as written, a Python object crosses as a
#: value, a positional call of a bound callee is the plain application and a
#: compiled lambda is bare where it is applied), the one codec at the grounded
#: call (fd0af38f7, whose read of a call site's written keyword tail costs
#: about six inferences per translated site, read once since 7cc8fb863), the
#: runnable cache's dependency index written by the producer (a9e2c06d3, which
#: takes back the walk of the generated code 5416e741d charged at every miss),
#: the host patches of 09-17 and the class units of 09-13 to 09-16 the ladder
#: in docs/journal/2026-09-14-runnable-artifact-dependencies.md places; serial
#: minimum of three fresh processes through the lane's run_twin with
#: file_search_cache_time=9223372036854775807 set before child boot [measured
#: 2026-09-18: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=6944d06ce96fdbcd1faefb640f15dbfa0cf286dd].
#: RE-PINNED 2026-09-18, 7367057 to 7362845 (-4212), 49478d67a landed the
#: polynomial carrier, whose preset row and variable claim every catalog scan
#: reads, the product carriers and the guard read in the fixpoint door, and the
#: binding's five-element rule read: the examples that scan the catalog moved
#: with their twins (restricted_spaces +522, the three pln twins +63 each, the
#: two tabling twins +20 and +10, reflect_lib +6) and the twins that cross the
#: seat's declaration and query paths moved with their examples unmoved (the
#: class twins between -4212 and +2841, the reference twins +208 and +317, the
#: tagged fixpoint twin +610, the documentation twins -22 and -50, types_nondet
#: +5) [measured 2026-09-18: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=bf5f100591493a91324b1d7552b5ad2731601691].
#: RE-PINNED 2026-09-18, 7362845 to 7364227 (+1382), the trunk merged
#: (f97c4b0a3, petta's 61 commits since c75181adc) with the definition batch's
#: load pushed as the running load (2da1155e3): every example moved with the
#: engine, 279 of 294 cheaper (median -0.78%), through the compiled runnable
#: envelope executing each runnable form's fixed answer, name and fuel envelope
#: from compiled clauses, the trunk's trailed scopes and compiled context
#: readers (a b_getval/2 read per recorded assertion in place of the branch's
#: thread-local rows), the host listener door and the receipts loop probing the
#: owner once per set; serial minimum of three fresh processes through the
#: lane's run_twin [measured 2026-09-18: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=55d451b670949c2dc9d2ab7bc678f33f21094bd2].
#: RE-PINNED 2026-09-19, 7364227 to 7364363 (+136), cost follows the answer: a
#: block is charged for its own thread's work and for the workers whose answers
#: it used, so a race's losers, the branches par-any and par-forall stopped,
#: and a cancelled future or timer are joined through the engine's discarding
#: door (metta_join_measured/3) and their partial spend, which only the
#: schedule sized, is taken out; lib_thread's join no longer polls on the host
#: patched for swi-thread-join-detach-window, and the seat's counter doors read
#: the discarded tally outside the window they bracket (metta_py_stats/2,
#: metta_py_work/2) [measured 2026-09-19: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=32335687084e4d8ad43cf8800f2dedce707fa137].
#: ENVELOPED 2026-09-19: the point 7364363 becomes the envelope
#: 7364363..7387049 over 12: under the lane's own protocol (full-
#: lane/294/workers=32, ten rounds) the counter reads 7364363 every time, and
#: under the gate's concurrent lanes (three runs) it reads 7386719, 7387049,
#: each reading exact on its run; the extra mode is the same program's work
#: done on a different thread under load, a loader flight or a settle step the
#: foreground runs itself when the worker is late, which the join accounting
#: does not reach; an envelope states what was observed and the point was a lie
#: under the gate [measured 2026-09-19: the twins lane alone on the final tree
#: and under the gate's concurrent lanes, wt-battery-2 ai-full-
#: gate-10da82e4a.log, ai-full-gate-19fdb0b86.log, ai-lanes-exports-back.log;
#: commit=WORKTREE].
BUDGET = {
    "minimum": 7364363,
    "maximum": 7387049,
    "observations": 12,
    "protocol": "full-lane/294/workers=32/file-search-cache-time=9223372036854775807/before-boot"
}
#: The minimum measurements give a declaration and crossing gap of 11729673.
#: [measured: 14262547 twin and 2532874 native inferences;
#: command=python extensions/python/tools/twin_coverage.py --measure --rounds 3
#: examples/ch17-concurrency-and-the-loop/08-class_grains.metta;
#: fixture=serial fresh processes after deleting engine/lib QLF; commit=89084b43ff1a758f703ce77cd96b026f56510116].
#: Re-measured 2026-09-15 after the current-dependency claim and intervening
#: reference repairs. The full declaration and crossing gap is now 7710698.
#: [measured: 10400240 twin and 2689542 native inferences;
#: command=python extensions/python/tools/twin_coverage.py --measure --rounds 10
#: examples/ch17-concurrency-and-the-loop/08-class_grains.metta;
#: fixture=serial fresh processes after deleting engine/lib QLF; commit=bc30fbd0bbcbf535de217d5a9efad2910002f343].
OVERRUN = 7710698
