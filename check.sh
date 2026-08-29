# Purpose: this component's own gate lanes, in the root gate's vocabulary.
# Assumes: it is SOURCED by check.sh, not executed. That is what lets it use
#   `run`, `in_py`, `$PY`, `$PYDIR`, `$HERE` and the shared summary table, so
#   one component's lanes cannot report their own status differently from
#   another's, and a child's exit code cannot be lost on the way back up -- the
#   hazard a driver that EXECUTES its children has to solve and this one does
#   not have. The two memory-scale temporary files the lanes below write are
#   the root driver's too, because its EXIT trap is what removes them.
# Guarantees: every path a lane runs is written literally. tests/checks/
#   evidence_runners.py models which files a lane covers by READING this text
#   and resolving $HERE/ and $PYDIR/, so a path reached through a local variable
#   is a path the evidence gate cannot see.
# Open Obligations:
#   To Do: None
#   Hacks: None
#   Future Enhancements: None

# The Python host: the `metta` library, the test tree beside it, the benchmark
# suite and its committed baselines, and the static analysis that reads all
# three. This was the largest block of lanes in the root gate and the root was
# never their subject. Most run inside extensions/python through `in_py`, which
# is `( cd "$PYDIR" && "$@" )`; the rest start from the repository root, or from
# tests/prolog in determinism's case, because what a lane CHECKS is what decides
# whose it is, not the directory it starts in.

# The suite, through the seat's own entry point rather than a command spelled
# here. The parallel configuration and the reasons for it live in
# extensions/python/test.sh, so a developer running that file gets the settings
# that make the run correct instead of a plainer pytest invocation that shares
# one engine across workers.
run GATE pytest       env CHECK_PY="$PY" sh "$HERE/extensions/python/test.sh"
run GATE gallery      sh -c "cd '$PYDIR' && '$PY' -m pytest tests/repository/test_executable_docs.py tests/repository/test_gallery.py tests/repository/test_twin_coverage.py::test_answer_multisets_ignore_order_and_alpha_names_but_keep_multiplicity -q --rootdir=. -c pyproject.toml"
run GATE benchmarks   in_py "$PY" bench.py --counter-only --keep-going
run GATE instructions in_py "$PY" -m benchmarks.check_instructions

# The complexity CLASS, which every other pin here is structurally unable to
# see: 32 of the 36 rows in baseline.json are one number at one input size. Each
# family declares a class and a ladder, the exponent of a log-log fit is gated
# against that class, and a separate looser guard on each size against its
# pinned row catches a constant-factor loss the class hides. Two planted
# controls ride along permanently and the lane fails if either stops failing:
# one is quadratic while declared linear, the other costs three times its pinned
# row with its class untouched.
#
# It gates on inferences, which are deterministic, so it needs no quiet box: all
# eight families returned identical counts across three processes at loadavg
# 3.40 and again at 5.97. The retired-instruction curve that LAW 2 wants beside
# a family whose work crosses into C is `--paired`, and it is deliberately NOT
# here: it needs a quiet box, and it is the evidence for a CHANGE that moves
# work across the boundary rather than something every run should pay.
run GATE scaling      in_py "$PY" -m benchmarks.scaling

# Run the complete fresh-process, min-of-three instrument once and reuse its
# verdict for the adjacent gate. The report includes process PSS/private/RSS/
# HWM metrics, but memory-scale-baseline.json promotes only exact SWI bytes,
# counts and controlled instruction/inference shapes. Promote a process metric
# only after ten independent suites spanning the observed load bands keep its
# min-of-three spread within 2%, and a planted max(5%, eight-page) retention is
# detected in every suite. Until then allocator and scheduler noise is printed,
# measured and pinned, but cannot turn a loaded host red.
memory_scale_report() {
    in_py "$PY" bench.py --memory-scale --memory-repetitions 3 \
        --timeout 200 --keep-going --json "$MEMORY_SCALE_DATA"
    memory_scale_result=$?
    printf '%s\n' "$memory_scale_result" > "$MEMORY_SCALE_STATUS"
    return "$memory_scale_result"
}

memory_scale_gate() {
    if [ ! -s "$MEMORY_SCALE_STATUS" ]; then
        memory_scale_report
    fi
    if [ ! -s "$MEMORY_SCALE_DATA" ]; then
        echo "memory-scale gate: REPORT produced no measurement document" >&2
        return 1
    fi
    memory_scale_result=$(cat "$MEMORY_SCALE_STATUS")
    if [ "$memory_scale_result" != 0 ]; then
        echo "memory-scale gate: REPORT exited $memory_scale_result" >&2
        return 1
    fi
}

run REPORT memory-scale      memory_scale_report
run GATE   memory-scale-gate memory_scale_gate

run GATE packaged sh -c "cd '$HERE' && sh tests/shell/test_packaged_cli.sh"

# The example corpus is the executable semantics documentation, and until this
# lane existed it only ever ran through the ENGINE: the examples gate below
# invokes swipl on engine/main.pl, test.sh and test_metta_examples.py shell to
# run.sh, and the plunit suites load engine/metta.pl without extensions/python/metta/shim.pl.
# So the configuration users actually ship was gated by unit tests alone, and
# defects lived there under green lanes: !(py-atom "()") answered () in the
# engine and raised out of the library, and a declared type on a Python object
# was kept in one and dropped in the other, both with a green plunit test above
# them because plunit loads the engine without the shim.
#
# REPORT rather than GATE, and the reason is written down rather than absorbed:
# it found SEVEN examples that passed in the engine and failed in the library,
# all one root: run() and load() did not register a source's function
# signatures before processing its forms the way engine/filereader.pl does, so a
# ! naming a function defined LOWER DOWN in the same file failed there. Both
# paths share prepare_parsed_forms/1 now and all seven pass either way, so
# this is a GATE [measured 2026-08-18: 200/200 agree, verified on the merged
# tree; 199 of the 200 by both ANSWERING and examples/ch20-extending-the-engine/20-02-metta-written-in-metta/04-minimal_metta.metta
# by both failing until its two library files were committed].
#
# It reads the engine through tests/conformance/leatta_run.pl, which already
# existed to print one answer GROUP per runnable form, and compares the groups
# as VALUES rather than as text. Both matter and both were got wrong first:
# comparing flat lines could not tell !(superpose (1 2 3)) then !(+ 1 1) from
# !(superpose (1 2)) then !(superpose (3 2)), and comparing text reported the
# engine's `true` against the library's `True` on 191 of 200 files, which is
# a spelling and not an answer.
run GATE   parity      sh -c "cd '$HERE' && '$PY' extensions/python/tools/example_parity.py"
run REPORT twins       sh -c "cd '$HERE' && '$PY' extensions/python/tools/twin_coverage.py"

# Every operation MeTTa's standard library declares, and what you write in
# Python instead. The rows live in extensions/python/tools/phrasebook_entries.py,
# one per LeaTTa-declared name; the lane runs BOTH sides of each row and
# compares three columns, the MeTTa form on LeaTTa as the oracle, the same form
# on this engine, and the Python spelling here. The MeTTa column is frozen from
# LeaTTa in phrasebook_answers.json and re-measured only under --learn, so this
# needs no LeaTTa checkout and costs 0.3s. It enters as a GATE rather than a
# REPORT because it was proven to see: breaking one row's executable Python
# column, `e[0]` to `e[1]`, produces three findings, against the recorded
# answer, against this engine and against LeaTTa.
run GATE   phrasebook  sh -c "cd '$HERE' && '$PY' extensions/python/tools/phrasebook.py --gate"

# Structural checks with a clean baseline today, so a regression is a failure.
run GATE slotscheck in_py "$PY" -m slotscheck -m metta
run GATE vulture    in_py "$PY" -m vulture

# Import Linter checks the runtime dependency graph. TYPE_CHECKING annotations
# are excluded at the root, while four verified function-local crossings are
# exact exceptions: the leaf facade/algebra calls and the core's two deferred
# satellite calls. Unmatched exceptions are errors, so an import moving or
# disappearing cannot leave stale policy behind.
#
# Not `-m importlinter.cli`, which is how this lane was written from the day
# check.sh existed until 2026-08-26 and why it checked nothing for that whole
# time: that module only DEFINES its click commands, so runpy imported it, ran
# no command, printed nothing and exited 0, while 62 real violations
# accumulated behind the silence. Calling the command object is what makes the
# lane able to fail, and
# test_every_module_invocation_in_the_gate_reaches_an_entry_point refuses any
# `-m` target in this file that has no entry point.
run GATE imports in_py "$PY" -c \
    "from importlinter.cli import lint_imports_command; lint_imports_command()"

# Copy the same config and package, prove the clean copy passes, then plant one
# module-level core-to-satellite edge. The same command must exit nonzero and
# name the planted route, so this lane proves the import gate discriminates.
run GATE imports-selftest "$PY" "$HERE/tests/checks/check_imports_selftest.py"

# EXTENDING.md's cost table, remeasured and held to a committed baseline. It
# was produced by a throwaway outside the repo that hardcoded an absolute path
# and was run by nobody, so one of its five rows stopped reproducing with
# nothing to say so.
#
# A REPORT until 2026-08-16, on the reasoning that these numbers compare tiers
# rather than fix a budget. That was wrong in the way that matters: a
# with_metta_module/2 fast path moved the annotated @m.define tier from 20.00
# to 22.00 and the run said nothing, and it was found by reading the table. The
# counts are exact and reproduce identically across rounds, so there is nothing
# to be tolerant of. Rebaseline deliberately with --update when a row is meant
# to move, which is the same contract the other counter gates hold.
run GATE extcost       in_py "$PY" -m benchmarks.extension_cost

# Which registered library predicates declare their determinism, and which do
# not. A leftover choice point costs its caller about twice and is invisible to
# the inference counter, and two things already catch one: plunit fails the
# gate on a test that succeeds with a choicepoint, and det/1 raises at the
# predicate's own door for anything declared. This reports the gap between
# them, a predicate no test happens to call that declares nothing.
#
# A REPORT rather than a GATE because plenty of them are correctly
# nondeterministic (get-keys answers one key per solution, the way get-atoms
# does), so a gate would demand a declaration for its own sake. The list is
# for deciding, once, which each one is.
check_determinism_coverage() {
    ( cd "$HERE/tests/prolog" && swipl -q determinism_coverage.pl )
}
run REPORT determinism check_determinism_coverage

# Two residuals remain: the CLI executes a fixed argv without a shell, and
# upstream's import-overhaul fixture owns its import grouping.
# The language-feature corpus is named because it moved into `examples` out of
# `tests`, and 219 files that were linted as part of `tests` would otherwise
# have gone quiet without one lane turning red. It is named PRECISELY rather
# than as `examples`, which would newly lint the topical examples beside it:
# those carry 184 findings of their own that predate this and belong to their
# own burn-down, not to a folder move.
run GATE   ruff        in_py "$PY" -m ruff check metta tests examples/language-feature-examples bench.py
# ledger C2: 65 errors in 13 files
run GATE   mypy        in_py "$PY" -m mypy
# ledger C2: 67 diagnostics, independent engine
run GATE   ty          in_py "$PY" -m ty check --python "$(dirname "$(dirname "$PY")")" metta
# Residual Pylint findings describe deliberate facades, compiler mixins,
# resource cleanup catches, and public compatibility surfaces.
run GATE   pylint      in_py "$PY" -m pylint metta --score=n
# Perflint remains a measured queue. A suggestion moves only after the exact
# instruction counter proves a win; the first attractive rewrite regressed.
#
# Where the queue stands, 2026-08-17, so its FAIL is a state and not a backlog.
# 296 findings: 217 loop-invariant-statement, which flags expressions whose
# CALLEE is invariant while the argument varies, so isinstance(child, seq) in
# the codec reads as hoistable and is not; and 79 loop-global-usage and
# dotted-import-in-loop, every one of them in import-time, plugin-discovery,
# @m.define compile-time or benchmarking code. The hot paths the benchmark
# suite actually measures report ZERO of the latter two, because the hoists
# are already there and carry their measurement: _atom_wire.py binds
# wire_sym, gnd and seq before its loop.
#
# One finding sits on a per-call path, _rebox looked up per yield in
# dispatch_raw_many. Hoisting it was measured on a workload that is nothing
# but raw generator yields, 1.2M of them, min of 3:
# 20,329,291,854 to 20,307,302,649 instructions:u, -0.108%. Not taken: a
# tenth of a percent in the most favourable case buys less than the line costs
# a reader, and 79 of them in cold code buys nothing at all.
run REPORT perflint    in_py "$PY" -m pylint --load-plugins=perflint --disable=all --enable=W8201,W8202,W8204,W8205 metta --score=n
# Complexity is REPORTED, not gated, by the user's ruling 2026-08-18. It was a
# GATE at max-absolute C, which measurement shows sat exactly on the tree's own
# ceiling: 1,669 blocks are 1,456 rank A, 200 rank B and 13 rank C, average A
# at 2.83, with nothing at D or worse. So one new rank-C block passed and one
# rank-D block failed the build, on a codebase whose interpreter dispatch is
# inherently branchy and whose next phases rewrite exactly those files.
#
# A per-block ceiling gates the wrong thing here. The signal worth keeping is a
# slide across a whole MODULE or the package AVERAGE, so those stay at A and
# still print; max-absolute moves to D so a single hairy function does not
# shout. Nothing is silenced: a REPORT prints everything it finds.
run REPORT xenon       in_py "$PY" -m xenon metta --max-absolute D --max-modules A --max-average A
# Refurb's residual type-normalization and clarity rewrites are not semantic
# equivalents at the package boundaries they flag.
run GATE   refurb      in_py "$PY" -m refurb metta bench.py
# Both Bandit findings are the fixed swipl argv call with shell mode disabled.
run GATE   bandit      in_py "$PY" -m bandit -q -c pyproject.toml -r metta
# These packages enter through deliberate lazy imports, which deptry cannot
# observe statically; each one is declared in its matching extra.
run GATE   deptry      in_py "$PY" -m deptry .
run GATE   audit       in_py "$PY" -m pip_audit --progress-spinner off
# ledger F: public API documentation is held above the 80% target
run GATE   interrogate in_py "$PY" -m interrogate metta
