#!/bin/sh
# Purpose: run this seat's test suite, as the gate runs it.
# Assumes:
#   - an interpreter with a working janus_swi. CHECK_PY names it; without that
#     the same candidates check.sh tries are tried here, in the same order, so
#     the two cannot disagree about which Python ran.
# Guarantees:
#   - the gate's `pytest` lane and a developer typing `sh extensions/python/
#     test.sh` run ONE command with one set of flags. The Node and C seats
#     already worked that way and this seat did not, so its lane's parallel
#     configuration lived in check.sh alone and a hand run silently used
#     different settings.
#   - arguments pass through, so `sh extensions/python/test.sh tests/ch04_spaces_and_matching`
#     narrows the run without repeating the flags that make it correct.
#   - the exit status is pytest's, unpiped.
# Open Obligations:
#   To Do: None
#   Hacks: None
#   Future Enhancements: None

set -eu

HERE=$(cd -- "$(dirname -- "$0")" && pwd)

PY=${CHECK_PY:-}
if [ -z "$PY" ]; then
    for candidate in "$HOME/Dev/.venv-pypetta/bin/python" "$HERE/../../.venv/bin/python" python3; do
        if command -v "$candidate" >/dev/null 2>&1; then PY="$candidate"; break; fi
    done
fi
command -v "$PY" >/dev/null 2>&1 || {
    echo "extensions/python/test.sh: no python found (set CHECK_PY)" >&2
    exit 2
}

# Each worker is a process with its own engine. Keeping one test file whole
# preserves module fixtures, and a worker crash fails instead of being retried.
# The benchmark plugin is disabled because it refuses parallel timing; the
# dedicated benchmark lanes own those measurements. Four workers is the fixed
# load-tested ceiling rather than a machine-size-dependent `auto` expansion
# [tested: test_the_pytest_lane_is_deterministic_under_load_protocol;
# commit=dcfc20be4933c19140ccb5759291401d13058301].
cd "$HERE"
if [ "$#" -gt 0 ]; then
    exec "$PY" -m pytest "$@" -q -p no:benchmark -n 4 --dist loadfile --max-worker-restart=0
fi
exec "$PY" -m pytest tests -q -p no:benchmark -n 4 --dist loadfile --max-worker-restart=0
