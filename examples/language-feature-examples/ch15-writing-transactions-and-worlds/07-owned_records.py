"""Purpose: examples/ch15-writing-transactions-and-worlds/07-owned_records.metta in Python: declare an owned record and read it as data.

An empty record reads (), a written row reads whole with its stored expression
unevaluated, a replacement inside a transaction reads the new row, and a second
value for one key is refused at the outer commit [tested:
python extensions/python/tools/twin_coverage.py examples/ch15-writing-transactions-and-worlds/07-owned_records.metta;
commit=dbb95d0bff10a93f2fef0453195b2331918f92dc].
"""

import metta
from metta import Expression, S, V
from metta._errors.errors import EngineError


def twin(m):
    """Declare one balance per account, then read, replace and refuse."""
    ledger = metta.space()
    account = S.Account(1)
    key = S["@owned-record"](ledger, account, ledger, S.balance(account))
    metta.space("&metta").add(S["@owned-record"](ledger, V.account, ledger, S.balance(V.account)))
    ledger.add(S.owned_by(account))

    assert m.eval(S.owned_record_read(key)) == [Expression()]

    held = S["+"](5, 5)
    ledger.add(S.balance(account, held))
    assert m.eval(S.owned_record_read(key)) == [Expression([S.balance(account, held)])]

    def replace():
        ledger.remove(S.balance(account, held))
        ledger.add(S.balance(account, 12))

    m.transaction(replace)
    assert m.eval(S.owned_record_read(key)) == [Expression([S.balance(account, 12)])]

    refused = None
    try:
        m.transaction(lambda: ledger.add(S.balance(account, 13)))
    except EngineError as error:
        refused = error
    assert refused is not None
    assert m.eval(S.owned_record_read(key)) == [Expression([S.balance(account, 12)])]


#: Three rounds agree on 6051 twin inferences against 9285 native inferences
#: [measured: 6051 inferences;
#: command=python extensions/python/tools/twin_coverage.py --measure examples/ch15-writing-transactions-and-worlds/07-owned_records.metta;
#: fixture=SWI-Prolog 10.1.13, five assertions, one fresh space and one &metta declaration; commit=dbb95d0bff10a93f2fef0453195b2331918f92dc].
#: RE-PINNED 2026-09-16, 6051 to 6058 (+7), the reader answers a problem term
#: and each door throws its own remedy, and every native change checks whether
#: it admits a key [measured 2026-09-16: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=e4fdf699f9dedb73f1fe0de7446334b60bd8dc36].
#: RE-PINNED 2026-09-18, 6058 to 6377 (+319), the branch's landings since the
#: 09-10 pins, re-taken on the tip f06186a96: the compiled call law (e59104ace:
#: an Atom argument enters as written, a Python object crosses as a value, a
#: positional call of a bound callee is the plain application and a compiled
#: lambda is bare where it is applied), the one codec at the grounded call
#: (fd0af38f7, whose read of a call site's written keyword tail costs about six
#: inferences per translated site, read once since 7cc8fb863), the runnable
#: cache's dependency index written by the producer (a9e2c06d3, which takes
#: back the walk of the generated code 5416e741d charged at every miss), the
#: host patches of 09-17 and the class units of 09-13 to 09-16 the ladder in
#: docs/journal/2026-09-14-runnable-artifact-dependencies.md places; serial
#: minimum of three fresh processes through the lane's run_twin with
#: file_search_cache_time=9223372036854775807 set before child boot [measured
#: 2026-09-18: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=6944d06ce96fdbcd1faefb640f15dbfa0cf286dd].
#: RE-PINNED 2026-09-18, 6377 to 6419 (+42), the trunk merged (f97c4b0a3,
#: petta's 61 commits since c75181adc) with the definition batch's load pushed
#: as the running load (2da1155e3): every example moved with the engine, 279 of
#: 294 cheaper (median -0.78%), through the compiled runnable envelope
#: executing each runnable form's fixed answer, name and fuel envelope from
#: compiled clauses, the trunk's trailed scopes and compiled context readers (a
#: b_getval/2 read per recorded assertion in place of the branch's thread-local
#: rows), the host listener door and the receipts loop probing the owner once
#: per set; serial minimum of three fresh processes through the lane's run_twin
#: [measured 2026-09-18: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=WORKTREE].
BUDGET = 6419
