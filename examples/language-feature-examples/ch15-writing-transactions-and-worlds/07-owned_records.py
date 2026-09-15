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
BUDGET = 6051
