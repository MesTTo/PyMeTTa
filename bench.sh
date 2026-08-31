#!/bin/sh
# Purpose: run this seat's benchmark suite against its committed baselines, as
#   the gate runs it.
# Assumes:
#   - an interpreter with a working janus_swi, named by CHECK_PY or found the
#     way check.sh finds it, so the two cannot disagree about which Python ran.
# Guarantees:
#   - both deciding counters run, and the second runs even when the first
#     fails. The engine-backed cases are decided by inferences and the
#     engine-free ones by retired instructions; reporting only the first would
#     leave a whole class of case unmeasured whenever the other class regressed.
#   - the exit status is nonzero when either half reports a regression, and the
#     status is not piped through anything.
#   - arguments pass through to the counter half, which is where a case name
#     means something: `sh extensions/python/bench.sh query-2k-rows`.
# Open Obligations:
#   To Do: None
#   Hacks: None
#   Future Enhancements: None

set -u

HERE=$(cd -- "$(dirname -- "$0")" && pwd)

METTA_ROOT="$HERE/../.."
. "$HERE/../../select-python.sh"
[ -n "$PY" ] || {
    echo "extensions/python/bench.sh: no python found (set CHECK_PY)" >&2
    exit 2
}

cd "$HERE"
status=0

# --keep-going because one regression must not hide another: the counter half
# reports every case before it exits.
"$PY" bench.py --counter-only --keep-going "$@" || status=1
# The instruction half runs whatever happened above, for the same reason.
"$PY" -m benchmarks.check_instructions || status=1

exit "$status"
