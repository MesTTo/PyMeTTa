"""Purpose: examples/ch17-concurrency-and-the-loop/10-class_entities.metta in Python.

An ordinary dataclass is an entity: `@m.define` mints a token handle for each
instance and keeps its fields as facts in the class space, a field write is
the derived writer inside the caller's transaction, a method that raises
leaves nothing half-written, and the population is one query. The example
writes those rows by hand; this twin declares the class and proves the same
claims.
"""

from dataclasses import dataclass

from metta import MettaError, S, Symbol, V


def twin(m):
    """Declare the entity class and prove the example's six claims."""
    @m.define
    @dataclass
    class Account:
        owner: Symbol
        balance: int

        def deposit(self, amount: int) -> bool:
            self.balance = self.balance + amount
            return True

        def withdraw(self, amount: int) -> bool:
            if self.balance < amount:
                msg = "overdraft"
                raise ValueError(msg)
            self.balance = self.balance - amount
            return True

    alice, bob = Account(S.alice, 40), Account(S.bob, 80)
    # !(test (Account-deposit &alice 25) True)
    assert alice.deposit(25) is True
    # !(test (Account-balance &alice) 65)
    assert alice.balance == 65
    # !(test (if-error (transaction (Account-withdraw &alice 500)) refused unexpected) refused)
    try:
        m.transaction(lambda: alice.withdraw(500))
    except MettaError:
        refused = True
    else:
        refused = False
    assert refused
    # !(test (Account-balance &alice) 65)
    assert alice.balance == 65
    # !(test (Account-withdraw &bob 30) True)
    assert bob.withdraw(30) is True
    # !(test (msort (collapse (match &Account (_field-balance $account $n) $n))) (50 65))
    accounts = m.metta.space(S.Account)
    assert sorted(row.n.value for row in accounts[S["_field-balance"](V.account, V.n)]) == [50, 65]


#: The twin declares its classes, whose grains, accessors, method equations,
#: dispatch rows, call contracts and Python proxies the declaration derives,
#: and then proves the example's claims through them; the native example
#: writes only the rows its claims read. The difference is that declaration
#: and crossing work, the OVERRUN declared below.
#: [measured: 5161225 twin and 83143 native inferences; command=python
#: extensions/python/tools/twin_coverage.py --measure
#: examples/ch17-concurrency-and-the-loop/10-class_entities.metta; fixture=min of three
#: serial fresh processes in a provisioned battery worktree with the .qlf set
#: warm; commit=a8cfae1f5c0be628bc40eb7c18b07749d995e9a0].
#: RE-PINNED 2026-09-18, 5161225 to 5161376 (+151), The classes package's
#: special-method and decorator rows: the twin declares its classes and the
#: declaration derives the arrows, dispatch and binding contracts and
#: documentation rows beside the equations the example writes by hand [measured
#: 2026-09-18: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=a8cfae1f5c0be628bc40eb7c18b07749d995e9a0].
#: RE-PINNED 2026-09-18, 5161376 to 5144705 (-16671), the branch's landings
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
#: extensions/python/tools/twin_coverage.py --repin; commit=WORKTREE].
BUDGET = 5144705
OVERRUN = 5078082

#: DIVERGED 2026-09-18, the example holds 0 atoms the twin does not (none) and
#: the twin holds 29 atoms the example does not (28 :, 1 @doc): The twin's
#: @m.define derives the class's arrows, application and binding contracts and
#: documentation rows into the class space beside the equations the example
#: writes by hand, so the referenced content differs by exactly those derived
#: rows [measured 2026-09-18: the two stored-atom surpluses, one fresh process
#: per side; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=a8cfae1f5c0be628bc40eb7c18b07749d995e9a0].
DIVERGENCE = "faeeea409059c7d1cb1f46057cca72ff0ef555ba95b034f0038ef40a16102f41"
