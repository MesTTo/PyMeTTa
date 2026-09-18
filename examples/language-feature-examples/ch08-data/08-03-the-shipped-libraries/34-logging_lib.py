"""Purpose: structured messages, topic controls and explicit capture handlers.

Guarantees: the same 28 claims as 34-logging_lib.metta.
[tested: python extensions/python/tools/twin_coverage.py examples/ch08-data/08-03-the-shipped-libraries/34-logging_lib.metta; commit=cf6b111ffad74477d9fa7169b215379dcabe721c].
"""

import metta
from metta import FALSE, TRUE, Expression, G, S, V, fn, lib
from metta._errors.errors import MettaError


def twin(m):
    """Capture structured events, preserve payload syntax and route by topic."""
    m += lib.logging
    records = metta.space(S.log_records)

    @m.define
    def record_log(label: str, event: Expression) -> bool:
        return fn.add_atom(records, S.captured(label, event))

    def refused(call):
        """Read a native refusal through the evaluation boundary."""
        try:
            list(m.eval(call))
        except MettaError:
            return True
        return False

    enabled, topic = m.fn.log_enabled, m.fn["log-topic!"]
    log, log_to = m.fn["log!"], m.fn["log-to!"]
    name = G("library-example")
    payload = S["+"](1, 2)
    consume = S["|->"]((V.event,), TRUE)

    assert list(m.fn.log_levels().one()) == [S.debug, S.informational, S.warning, S.error]
    assert enabled(name) == [False]
    assert list(m.fn.log_topics().one()) == []
    assert list(log_to(S.missing_handler, name, S.error, payload).one()) == []
    assert m.fn.log_format(name, S.debug, payload) == [G("library-example [debug] (+ 1 2)")]
    assert list(topic(name, TRUE).one()) == []
    assert enabled(name) == [True]
    assert [tuple(row) for row in m.fn.log_topics().one()] == [(S.log_topic, name, True)]

    assert list(log(name, S.informational, G("hello")).one()) == []
    assert list(log_to(S.record_log(G("first")), name, S.debug, payload).one()) == []
    pattern = S.captured(G("first"), S.log_event(V.topic, V.level, V.payload))
    captured = records[pattern].one()
    assert len(captured.payload) == 3
    assert captured.payload == payload
    assert list(log_to(S.record_log(G("second")), name, S.informational,
                       S.loaded(G("data.csv"))).one()) == []
    assert list(log_to(consume, name, S.warning, S.retry(2)).one()) == []
    assert list(log_to(consume, name, S.error, S.failed(G("input"))).one()) == []
    assert len(records) == 2
    assert list(log_to(S["|->"]((V.event,), FALSE), name, S.informational, G("visible")).one()) == []

    assert refused(S["log-to!"](S["|->"]((V.event,), 7), name, S.debug, S.x))
    assert refused(S["log-to!"](S["|->"]((V.event,), S.empty()), name, S.debug, S.x))
    assert refused(S["log-to!"](S.missing_handler, name, S.debug, S.x))
    assert refused(S["log!"](name, S.fatal, S.x))
    assert refused(S.log_format(name, S.fatal, S.x))
    assert list(topic(name, FALSE).one()) == []
    assert enabled(name) == [False]
    assert list(log_to(S.missing_handler, name, S.error, S.x).one()) == []
    assert [tuple(row) for row in m.fn.log_topics().one()] == [(S.log_topic, name, False)]
    assert refused(S["log!"](name, S.fatal, S.x))
    assert enabled(G("library-example.child")) == [False]


#: MEASURED: all 28 claims, including the compiled capture handler and both
#: native printing and explicit capture. The example pays 53732 inferences.
#: [measured 2026-09-12: 54976 inferences, minimum of three fresh serial processes;
#: command=python extensions/python/tools/twin_coverage.py --measure --rounds 3
#: examples/ch08-data/08-03-the-shipped-libraries/34-logging_lib.metta;
#: fixture=lib_logging at its functional commit with engine/lib QLF artifacts purged;
#: commit=cf6b111ffad74477d9fa7169b215379dcabe721c].
BUDGET = 54976
