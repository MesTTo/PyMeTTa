"""Purpose: query source coverage and error frames from a MeTTa program.

Guarantees: repeated source text keeps separate positions and observing a
program preserves its answers and writes [tested: test_coverage_distinguishes_identical_branches,
test_observation_executes_writes_and_retains_error_answers; commit=df1367c75148ca6c7262134a8736b237e1150383].
"""

import uuid

from metta import MeTTa, S


def _observe(metta, source, label="observed.metta"):
    metta.run("!(import! &self (library lib_observe))")
    (report,) = metta.eval(S["observe-source"](metta.self, label, source))
    return list(metta.eval(S["get-atoms"](report)))


def _rows(atoms, name):
    return [atom.children[1:] for atom in atoms if atom.children[0] == S[name]]


def test_coverage_distinguishes_identical_branches():
    """Only the taken occurrence of the identical addition has a hit."""
    source = "(= (pick $flag $x)\n  (if $flag\n    (+ $x 2)\n    (+ $x 2)))\n!(pick True 1)"
    with MeTTa() as metta:
        atoms = _observe(metta, source)
    assert _rows(atoms, "observation-status") == [(S.complete,)]
    assert _rows(atoms, "observation-answer") == [(0, 3)]
    coverage = _rows(atoms, "source-coverage")
    taken = [row for row in coverage if row[1:5] == (3, 5, 3, 13)]
    untaken = [row for row in coverage if row[1:5] == (4, 5, 4, 13)]
    assert len(taken) == len(untaken) == 1
    assert taken[0][-1].value > 0
    assert untaken[0][-1] == 0


def test_error_frames_point_to_the_failing_subterm_and_its_caller():
    """The division and its caller survive as separate attributed frames."""
    source = (
        "(= (divide $x)\n  (+ 1 (/ 1 $x)))\n"
        "(= (caller $x)\n  (+ 2 (divide $x)))\n!(caller 0)"
    )
    with MeTTa() as metta:
        atoms = _observe(metta, source, "division.metta")
    errors = _rows(atoms, "source-error")
    assert any(str(row[1]) == "(Error (/ 1 0) DivisionByZero)" for row in errors)
    frames = _rows(atoms, "source-frame")
    assert any(
        row[2:] == (S.divide, "division.metta", 2, 8, 2, 16, S.exact)
        for row in frames
    )
    assert any(
        row[2:] == (S.caller, "division.metta", 4, 8, 4, 19, S.exact)
        for row in frames
    )


def test_generated_meta_call_names_its_generating_construct():
    """A generated closure admits its origin instead of inventing precision."""
    source = "(= (collect $x)\n  (collapse (+ 1 (/ 1 $x))))\n!(collect 0)"
    with MeTTa() as metta:
        atoms = _observe(metta, source, "generated.metta")
    assert _rows(atoms, "source-error")
    frames = _rows(atoms, "source-frame")
    assert any(str(row[-1]) == "(generated-by collapse)" for row in frames)


def test_observation_executes_writes_and_retains_error_answers():
    """Observing runs source for real and preserves ordinary Error data."""
    with MeTTa() as metta:
        atoms = _observe(
            metta,
            "!(add-atom &self (observed-value 7))\n!(/ 1 0)",
        )
        assert metta.run("!(match &self (observed-value $x) $x)") == [[7]]
        answers = _rows(atoms, "observation-answer")
        assert any(str(row[1]) == "(Error (/ 1 0) DivisionByZero)" for row in answers)
        assert metta.run("!(/ 1 0)") == [[S.Error(S["/"](1, 0), S.DivisionByZero)]]


def test_host_exception_is_queryable_with_source_frames():
    """An exception becomes an observation outcome, with its failing location."""
    source = "(= (check $x)\n  (assertEqual $x 3))\n!(check 0)"
    with MeTTa() as metta:
        atoms = _observe(metta, source)
    assert _rows(atoms, "observation-status") == [(S.exception,)]
    assert _rows(atoms, "observation-exception")
    assert any(row[2] == S.check for row in _rows(atoms, "source-frame"))


def test_observation_sessions_do_not_share_documents_or_errors():
    """Cleanup retires diagnostic state before the next observation."""
    with MeTTa() as metta:
        first = _observe(metta, "!(/ 1 0)", "first.metta")
        second = _observe(metta, "!(+ 1 2)", "second.metta")
        assert _rows(first, "source-error")
        assert not _rows(second, "source-error")
        assert all(row[0] == "second.metta" for row in _rows(second, "source-coverage"))
        assert _rows(second, "observation-answer") == [(0, 3)]


def test_previously_compiled_function_admits_missing_source_metadata():
    """Code loaded before observation cannot acquire invented coordinates."""
    with MeTTa() as metta:
        metta.run("(= (earlier $x) (/ 1 $x)) !(earlier 1)")
        atoms = _observe(metta, "!(earlier 0)", "call.metta")
    assert (S.earlier, S["source-not-observed"]) in _rows(atoms, "source-function-unavailable")
    assert any(
        row[2:] == (S.earlier, S["source-not-observed"])
        for row in _rows(atoms, "source-frame-unavailable")
    )


def _settled_cost(metta, call, answer):
    """The steady-state inference cost of one evaluation, min of three.

    A single reading is not the steady state. Repeating the same evaluation in
    one context reads 3,149 inferences and then 3,151 about once every ten,
    at an arbitrary position rather than as a warm-up: over twenty-five fresh
    contexts, eight readings each, fourteen contexts carried exactly one 3,151
    and it sat at position 0 through 7 [measured 2026-09-05, and the same
    before the shared-head cost repair, so it is the engine's own periodic
    housekeeping and not that change]. Comparing two single samples therefore
    fails about one run in five for a reason that has nothing to do with the
    observation. The minimum is the repository's statistic for this everywhere
    else, and it makes the equality below exact again.
    """
    readings = []
    for _ in range(3):
        with metta.stats() as block:
            assert list(metta.eval(call)) == answer
        readings.append(block.inferences)
    return min(readings)


def test_observation_restores_the_cost_of_ordinary_successful_execution():
    """An observation leaves no counter or wrapper in an ordinary hot path."""
    with MeTTa() as metta:
        metta.run("(= (sum-down $n $a) (if (== $n 0) $a (sum-down (- $n 1) (+ $a $n))))")
        call = S["sum-down"](500, 0)
        assert list(metta.eval(call)) == [125250]
        before = _settled_cost(metta, call, [125250])
        _observe(metta, "(= (observed $x) (+ $x 2)) !(observed 3)")
        after = _settled_cost(metta, call, [125250])
    assert after == before


def test_never_called_definition_has_zero_entry_coverage():
    """Lazy compilation must not remove an unused definition from the report."""
    definition = "(= (unused $x) (+ $x 2))"
    with MeTTa() as metta:
        atoms = _observe(metta, definition + "\n!(+ 1 2)")
    coverage = _rows(atoms, "source-coverage")
    assert any(
        row[1:] == (1, 1, 1, len(definition) + 1, 0)
        for row in coverage
    )


def test_runtime_columns_count_unicode_codepoints():
    """A non-BMP character before an error does not become four columns."""
    definition = '(= (δ $x) (cons-atom "😀" (/ 1 $x)))'
    column = definition.index("(/ 1 $x)") + 1
    with MeTTa() as metta:
        atoms = _observe(metta, definition + "\n!(δ 0)", "unicode.metta")
    assert any(
        row[2:] == (S["δ"], "unicode.metta", 1, column, 1, column + 8, S.exact)
        for row in _rows(atoms, "source-frame")
    )


def test_coverage_survives_a_registered_python_import_rewriter(tmp_path):
    """A Python import registers a form rewriter that rebuilds every form it reads."""
    module_name = f"observed_rewriter_{uuid.uuid4().hex}"
    (tmp_path / f"{module_name}.py").write_text("def origin(): return 31\n")
    source = "(= (pick $flag $x)\n  (if $flag\n    (+ $x 2)\n    (+ $x 2)))\n!(pick True 1)"
    with MeTTa() as metta:
        metta.run(f'!(import! &self "{tmp_path / f"{module_name}.py"}")')
        assert metta.runtime.must("seam:form_rewriter(Rewriter)")["Rewriter"] == "bind_python_calls"
        atoms = _observe(metta, source)
    assert _rows(atoms, "observation-answer") == [(0, 3)]
    coverage = _rows(atoms, "source-coverage")
    (taken,) = [row for row in coverage if row[1:5] == (3, 5, 3, 13)]
    (untaken,) = [row for row in coverage if row[1:5] == (4, 5, 4, 13)]
    assert taken[-1].value > 0
    assert untaken[-1] == 0
    assert not _rows(atoms, "source-coverage-unavailable")
