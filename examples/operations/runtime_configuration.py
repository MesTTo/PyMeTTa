"""Purpose: configure process-wide runtime and presentation settings.

Startup settings freeze after the first engine consult. Presentation and
declaration limits remain live, so a long-running host can adjust them without
restarting its engine.
"""

from _common import check, done

from metta import MeTTa, config


before = config.as_dict()
check(
    "the complete setting roster is inspectable",
    set(before),
    {"stack_limit", "heartbeat_interval", "declaration_limit", "display_rows"},
)

config.configure(
    heartbeat_interval=25_000,
    declaration_limit=64,
    display_rows=7,
)

with MeTTa() as context:
    check("the configured runtime starts", context.eval("(+ 20 22)"), [42])

try:
    config.heartbeat_interval = 50_000
except RuntimeError as refusal:
    check("startup settings freeze", "runtime has started" in str(refusal))
else:
    raise AssertionError("a startup setting changed after the runtime started")

config.display_rows = 5
check("presentation settings remain live", config.display_rows, 5)

done("runtime_configuration")
