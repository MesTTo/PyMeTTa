"""Purpose: configure process-wide runtime and presentation settings, which are
`(limit ...)` rows in `&metta` once an engine is running.

Startup settings freeze after the first engine consult. Every other bound is a
row a MeTTa program reads and rewrites, so a long-running host adjusts one
without restarting its engine and a program can see what it is set to.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

from _common import check, done

import metta
from metta import MeTTa, S, V, config


before = config.as_dict()
check(
    "the complete setting roster is inspectable",
    set(before),
    {
        "stack_limit",
        "heartbeat_interval",
        "declaration_limit",
        "display_rows",
        "chunk_cap",
        "subscription_queue",
        "repr_items",
    },
)

config.configure(
    heartbeat_interval=25_000,
    declaration_limit=64,
    display_rows=7,
)

with MeTTa() as context:
    check("the configured runtime starts", context.eval("(+ 20 22)"), [42])

    # Every bound but the two the boot itself takes is a row a program reads.
    # `metta.catalog` is reached HERE rather than imported at the top: it is
    # the `&metta` space, and asking for it starts the engine, which is what
    # freezes the two startup settings this file configures above.
    rows = {
        str(answer.name): answer.value.value
        for answer in metta.catalog.match(S.limit(V.name, V.value))
    }
    check("the bounds are rows", rows["display-rows"], 7)
    check(
        "the two startup settings are not rows",
        {"stack-limit", "heartbeat-interval"} & set(rows),
        set(),
    )

    # And a MeTTa program rewrites one, which is what `config` then answers.
    context.run("!(add-atom &metta (limit display-rows 3))")
    check("a rewritten row is what the seat reads", config.display_rows, 3)

try:
    config.heartbeat_interval = 50_000
except RuntimeError as refusal:
    check("startup settings freeze", "runtime has started" in str(refusal))
else:
    raise AssertionError("a startup setting changed after the runtime started")

config.display_rows = 5
check("presentation settings remain live", config.display_rows, 5)

done("runtime_configuration")
