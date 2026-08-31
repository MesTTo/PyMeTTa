"""Purpose: pin the minimal metta-thread full evaluator at Python-facing doors.

The expected rows are the type-directed argument fold, evaluated collapse
carrier, and nondeterministic equation loop specified by LeaTTa's `mettaEval`
[source: MettaHyperonFull/Minimal/Interpreter.lean:3682-3700, 7361-7524].
"""

from __future__ import annotations

from metta import MeTTa


def answers(space, program: str) -> list[str]:
    """Flatten one program's answers without changing their order."""
    return [str(atom) for group in space.run(program) for atom in group]


def both_doors(space, name: str, expression: str, expected: list[str]) -> None:
    """Compare a compiled equation body with the same runtime eval term."""
    space.run(f"(= ({name}) {expression})")
    assert answers(space, f"!({name})") == expected
    assert answers(space, f"!(eval {expression})") == expected


def test_metta_thread_evaluates_only_eager_arguments_to_a_fixpoint() -> None:
    """The Bool argument completes while the Atom argument remains syntax."""
    space = MeTTa().self
    space.run(
        "(: c2-py-thread-choice (-> Bool Atom %Undefined%))\n"
        "(= (c2-py-thread-choice False $held) (quote $held))"
    )
    both_doors(
        space,
        "c2-py-thread-choice-door",
        "(metta-thread (c2-py-thread-choice (if-equal Number Atom True "
        "(if-equal Number Grounded True False)) (+ 1 2)) %Undefined% &self)",
        ["3"],
    )


def test_metta_thread_preserves_atom_results_and_collapse_carriers() -> None:
    """Prepared arguments and reflected alternatives are evaluated once."""
    space = MeTTa().self
    space.run(
        "(: c2-py-thread-hold (-> Atom Atom))\n"
        "(= (c2-py-thread-hold $value) $value)\n"
        "(: c2-py-thread-observe (-> %Undefined% Atom))\n"
        "(= (c2-py-thread-observe $value) (quote $value))"
    )
    both_doors(
        space,
        "c2-py-thread-once-door",
        "(metta-thread (c2-py-thread-observe "
        "(c2-py-thread-hold (+ 1 2))) %Undefined% &self)",
        ["(quote (+ 1 2))"],
    )
    both_doors(
        space,
        "c2-py-thread-carrier-door",
        "(metta-thread (collapse-bind (superpose (left right))) "
        "%Undefined% &self)",
        ["((left (bindings)) (right (bindings)))"],
    )


def test_function_and_metta_thread_keep_duplicate_equation_answers() -> None:
    """A minimal step branches once per matching equation, including duplicates."""
    space = MeTTa().self
    space.run(
        "(: c2-py-thread-many (-> %Undefined%))\n"
        "(= (c2-py-thread-many) c2-py-thread-answer)\n"
        "(= (c2-py-thread-many) c2-py-thread-answer)"
    )
    expected = ["c2-py-thread-answer", "c2-py-thread-answer"]
    both_doors(
        space,
        "c2-py-thread-function-door",
        "(function (chain (evalc (c2-py-thread-many) &self) "
        "$value (return $value)))",
        expected,
    )
    both_doors(
        space,
        "c2-py-thread-many-door",
        "(metta-thread (c2-py-thread-many) %Undefined% &self)",
        expected,
    )
