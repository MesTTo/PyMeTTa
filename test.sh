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
#     narrows the run without repeating the flags that make it correct, a
#     caller's own flag overrides a default, so `-n 0` runs in one process, and
#     a caller who passes only FLAGS still gets the whole suite.
#   - every process this starts has faulthandler armed for its whole life,
#     interpreter shutdown included, which is where a finaliser fault lands.
#   - the exit status is pytest's, unpiped.
# Open Obligations:
#   To Do: None
#   Hacks: None
#   Future Enhancements: None

set -eu

HERE=$(cd -- "$(dirname -- "$0")" && pwd)

METTA_ROOT="$HERE/../.."
. "$HERE/../../tools/select-python.sh"
[ -n "$PY" ] || {
    echo "extensions/python/test.sh: no python found (set CHECK_PY)" >&2
    exit 2
}

# Each worker is a process with its own engine. Keeping one test file whole
# preserves module fixtures.
#
# A crashed worker is REPLACED, and that is not a retry. xdist builds the
# crashed test's report with outcome="failed" in `handle_crashitem` BEFORE it
# decides whether to restart, so the test fails either way and nothing is run
# a second time; `--reruns`, which would, is separately refused below and by
# test_the_pytest_lane_is_deterministic_under_load_protocol. What
# `--max-worker-restart=0` actually did was `triggershutdown()`, so the queue
# the crashed worker had not reached was never served: this lane reported on
# 4761 of 8129 collected tests, and the ~3368 it never reached were all of
# tests/repository, because test_mork_space.py aborts a worker on the MORK
# backend's 4 GiB arena [measured 2026-09-22 against gate-ship3, whose own
# summary reads "2 failed, 4679 passed, 80 skipped"]. Three real failures sat
# in that unreported remainder.
#
# The budget is the worker count: one crash each is an isolated fault and the
# suite is still worth finishing, while more than that is systematic and
# stopping is the honest answer. xdist prints "replacing crashed worker" and
# the run still fails, which is what was wanted.
#
# SIXTEEN, measured rather than assumed, and the old four was not a ceiling on
# this box but a cost: the whole suite runs in 392.91s at sixteen where four
# was killed by the lane's own 3600s bound having reached 98 per cent. A lane
# that is killed reports NOTHING, and the 27 failures this tree actually has
# went unnamed for that reason; thirteen of them reproduce with `-p no:xdist`,
# so they are the suite's own and not an artefact of splitting it
# [measured 2026-09-23, 32 cores, `--durations=40`: the makespan floor is one
# test, test_statistics_geometric_mean_precision_and_bounds at 244.44s, which
# is 62 per cent of the run, so workers past sixteen buy nothing until that
# test does].
# The benchmark plugin is disabled because it refuses parallel timing; the
# dedicated benchmark lanes own those measurements. Four workers is the fixed
# load-tested ceiling rather than a machine-size-dependent `auto` expansion
# [tested: test_the_pytest_lane_is_deterministic_under_load_protocol;
# commit=dcfc20be4933c19140ccb5759291401d13058301].
#
# Through bounded.sh, so the four xdist workers and everything they spawn share
# this process's fate; conftest.py bounds each worker's own children in turn.
# Spelled as the path rather than through a `bounded` function, because a
# function cannot be exec'd and this file's exit status must stay pytest's.
cd "$HERE"

# faulthandler armed by the ENVIRONMENT, so it covers the whole life of every
# interpreter this starts. pytest enables it in pytest_configure and disables it
# again in pytest_unconfigure, re-enabling afterwards only what was enabled
# BEFORE, so a fault raised during interpreter shutdown -- which is where this
# week's finaliser crashes landed -- prints nothing at all unless the
# environment armed it first
# [source: _pytest/faulthandler.py, pytest_configure and pytest_unconfigure].
# It also covers the xdist workers and every child conftest.py spawns, none of
# which pytest's own ini value reaches before their own configure.
PYTHONFAULTHANDLER=1
export PYTHONFAULTHANDLER

# ONE command. The defaults come BEFORE "$@" so that a caller's own flag wins:
# pytest and xdist take the last value of a repeated option, and with the
# defaults after the arguments a caller's `-n 0` was silently overridden, so
# every "serial" run of this script stayed parallel [measured 2026-09-06: the
# order-dependency inventory had to bypass this file to run in one process].
#
# The suite's root is `testpaths` in pyproject.toml rather than a trailing
# argument here. Spelled here it had to be dropped whenever the caller passed
# anything, so a caller who passed only FLAGS silently lost it: `sh
# extensions/python/test.sh -n 0 --durations=25` collected the whole of
# extensions/python, benchmarks/conftest.py included, and died in collection
# with `PluginValidationError: unknown hook
# 'pytest_benchmark_update_machine_info'` -- raised by the plugin this same
# command disables [measured 2026-09-06]. pytest is the one that can tell a path
# argument from a flag, so the default belongs in its configuration.
exec sh "$HERE/../../tools/bounded.sh" \
    "$PY" -m pytest -q -p no:benchmark -n 16 --dist loadfile --max-worker-restart=16 "$@"
