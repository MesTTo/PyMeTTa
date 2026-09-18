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
#: extensions/python/tools/twin_coverage.py --repin; commit=6944d06ce96fdbcd1faefb640f15dbfa0cf286dd].
#: RE-PINNED 2026-09-18, 5144705 to 5147546 (+2841), 49478d67a landed the
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
#: RE-PINNED 2026-09-18, 5147546 to 5157029 (+9483), the trunk merged
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
#: RE-PINNED 2026-09-19, 5157029 to 5157302 (+273), cost follows the answer: a
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
#: ENVELOPED 2026-09-19: the point 5157302 becomes the envelope
#: 5157302..5178578 over 11: under the lane's own protocol (full-
#: lane/294/workers=32, ten rounds) the counter reads 5157302 every time, and
#: under the gate's concurrent lanes (three runs) it reads 5178578, each
#: reading exact on its run; the extra mode is the same program's work done on
#: a different thread under load, a loader flight or a settle step the
#: foreground runs itself when the worker is late, which the join accounting
#: does not reach; an envelope states what was observed and the point was a lie
#: under the gate [measured 2026-09-19: the twins lane alone on the final tree
#: and under the gate's concurrent lanes, wt-battery-2 ai-full-
#: gate-10da82e4a.log, ai-full-gate-19fdb0b86.log, ai-lanes-exports-back.log;
#: commit=1ccbb142315d16a719807cd2c9754e4a2fcefdf1].
BUDGET = {
    "minimum": 5157302,
    "maximum": 5178578,
    "observations": 11,
    "protocol": "full-lane/294/workers=32/file-search-cache-time=9223372036854775807/before-boot"
}
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
