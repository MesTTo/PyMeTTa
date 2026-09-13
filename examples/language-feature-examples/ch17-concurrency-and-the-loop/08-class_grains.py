"""Purpose: examples/ch17-concurrency-and-the-loop/08-class_grains.metta in Python.

A frozen dataclass is a value. A mutable dataclass shares its class population.
A Space subclass owns private facts and rules. Both notations query those rows.
[tested: examples/ch17-concurrency-and-the-loop/08-class_grains.metta and its
Python twin; commit=518e67bc11d72ed28dfda7dd0646d1f48d14ac24]
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
BUDGET = 14263254
#: The minimum measurements give a declaration and crossing gap of 11730385.
#: [measured: 14263254 twin and 2532869 native inferences;
#: command=python extensions/python/tools/twin_coverage.py --measure --rounds 3
#: examples/ch17-concurrency-and-the-loop/08-class_grains.metta;
#: fixture=serial fresh processes after deleting engine/lib QLF; commit=a95e6c90c910db30c72311abadd58dee5349978c].
OVERRUN = 11730385
