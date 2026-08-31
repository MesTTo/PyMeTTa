"""Purpose: exercise conformance increment 2 through both Python-facing doors.

Assumes: each test uses unique MeTTa names because the engine module outlives a
Python handle. Guarantees: a call compiled into an equation body and the same
term passed to `eval` produce the LeaTTa 9ea9f9d answer.
"""

from __future__ import annotations

import pytest

from metta import MeTTa
from metta.errors import AssertionFailure


def answers(space, program: str) -> list[str]:
    """Flatten every answer group while preserving answer order."""
    return [str(atom) for group in space.run(program) for atom in group]


def both_doors(space, name: str, expression: str, expected: list[str]) -> None:
    """Compare a source-compiled equation body with a runtime eval term."""
    space.run(f"(= ({name}) {expression})")
    assert answers(space, f"!({name})") == expected
    assert answers(space, f"!(eval {expression})") == expected


def test_symbol_rules_apply_to_declared_and_undeclared_functions() -> None:
    """Eager symbol evaluation is a runtime rule, not a compile-time guess.

    A symbol in ARGUMENT position reduces through its own equation, so
    `(= mypi 3)` makes `(+ 1 mypi)` four. Upstream never reduces a symbol
    anywhere and aborts that call outright, so this is a capability rather
    than a different answer [measured 2026-08-30 against PeTTa@ae66fa8]. It
    does not reach a BARE symbol on either side: `!mypi` is `mypi`.

    `quote` answers its operand rather than the quoted form, which is
    upstream's `Out = Expr` for it.
    """
    space = MeTTa().self
    space.run(
        "(: c2-py-symbol (-> Symbol %Undefined%))\n"
        "(= (c2-py-symbol $x) (quote $x))\n"
        "(= (c2-py-symbol-caller) (c2-py-symbol c2-py-before))\n"
        "(= (c2-py-symbol-open $x) (quote $x))\n"
        "(= c2-py-before c2-py-after)"
    )
    both_doors(
        space,
        "c2-py-symbol-door",
        "(c2-py-symbol-caller)",
        ["c2-py-after"],
    )
    both_doors(
        space,
        "c2-py-symbol-open-door",
        "(c2-py-symbol-open c2-py-before)",
        ["c2-py-after"],
    )


def test_declared_parameter_and_result_rules_match_the_arbiter() -> None:
    """Grounded, Variable, Rest, and arity rules agree through both doors."""
    space = MeTTa().self
    space.run(
        "(: c2-py-grounded (-> Grounded %Undefined%))\n"
        "(= (c2-py-grounded $x) (quote $x))\n"
        "(: c2-py-variable-result (-> Atom Variable))\n"
        "(= (c2-py-variable-result $x) $x)\n"
        "(: c2-py-rest (-> Symbol (%Rest% Atom) %Undefined%))\n"
        "(= (c2-py-rest $tag $x $y $z) (quote ($tag $x $y $z)))\n"
        "(: c2-py-arity (-> Atom Atom %Undefined%))\n"
        "(= (c2-py-arity $x) (quote $x))"
    )
    both_doors(
        space,
        "c2-py-grounded-door",
        "(c2-py-grounded (+ 1 2))",
        ["(Error (c2-py-grounded (+ 1 2)) (BadArgType 1 Grounded Number))"],
    )
    both_doors(
        space,
        "c2-py-variable-result-door",
        "(c2-py-variable-result ((+ 1 2)))",
        [],
    )
    both_doors(
        space,
        "c2-py-rest-door",
        "(c2-py-rest keep (+ 1 2) (+ 3 4) (+ 5 6))",
        ["(keep (+ 1 2) (+ 3 4) (+ 5 6))"],
    )
    both_doors(
        space,
        "c2-py-arity-door",
        "(c2-py-arity (+ 1 2))",
        ["(Error (c2-py-arity (+ 1 2)) IncorrectNumberOfArguments)"],
    )


def test_an_open_equation_result_is_not_the_not_reducible_marker() -> None:
    """A fresh result variable remains a value rather than matching the mark."""
    space = MeTTa().self
    space.run("(= (c2-py-open-result (: $x $t)) $t)")
    both_doors(
        space,
        "c2-py-open-result-door",
        "(let $r (c2-py-open-result $q) (get-metatype $r))",
        ["Variable"],
    )


def test_dynamic_head_errors_carriers_and_builtin_results_match() -> None:
    """The runtime-head and native operation seams preserve source semantics."""
    space = MeTTa().self
    rows = (
        (
            "c2-py-head-door",
            # c2-py-leaf, not `tail`, and not any name this suite defines: a
            # bare `(name)` is the one-element expression only while nothing
            # gives `name` arguments. Two other files define a `tail` of one
            # argument and this file declares c2-py-rest with four, and in
            # either case `(name)` curries into `(partial name ())` and the row
            # reads a partial application instead of data. The engine is right
            # both ways; the name has to be one nothing else claims.
            "(let $head cons-atom ($head (+ 20 22) (c2-py-leaf)))",
            ["(42 c2-py-leaf)"],
        ),
        (
            "c2-py-car-door",
            "(car-atom ())",
            ['(Error (car-atom ()) "car-atom expects a non-empty expression as an argument")'],
        ),
        (
            "c2-py-cdr-door",
            "(cdr-atom ())",
            ['(Error (cdr-atom ()) "cdr-atom expects a non-empty expression as an argument")'],
        ),
        (
            "c2-py-carrier-door",
            "(collapse-bind (superpose (left right)))",
            ["((left (bindings)) (right (bindings)))"],
        ),
        ("c2-py-id-door", "(id (noeval (+ 20 22)))", ["42"]),
    )
    for name, expression, expected in rows:
        both_doors(space, name, expression, expected)


def test_collapse_evaluates_a_masked_runtime_operand() -> None:
    """A held operand is syntax until collapse receives it, then it branches."""
    space = MeTTa().self
    space.run(
        "(: c2-py-collapse (-> Atom %Undefined%))\n"
        "(= (c2-py-collapse $x) (collapse $x))\n"
        "(= (c2-py-many) one)\n"
        "(= (c2-py-many) two)"
    )
    both_doors(
        space,
        "c2-py-collapse-door",
        "(c2-py-collapse (c2-py-many))",
        ["(one two)"],
    )


def test_assert_equal_to_result_compares_result_bags() -> None:
    """Result order is ignored while duplicate multiplicity still matters."""
    space = MeTTa().self
    space.run("(: c2-py-type-order First)\n(: c2-py-type-order Second)")
    both_doors(
        space,
        "c2-py-type-order-door",
        "(get-type c2-py-type-order)",
        ["First", "Second"],
    )
    reordered = (
        "(assertEqualToResult (superpose (first second)) (second first))"
    )
    both_doors(space, "c2-py-assert-bag-order-door", reordered, ["True"])

    mismatched = (
        "(assertEqualToResult (superpose (same same other)) "
        "(same other other))"
    )
    space.run(f"(= (c2-py-assert-bag-count-door) {mismatched})")
    with pytest.raises(AssertionFailure):
        answers(space, "!(c2-py-assert-bag-count-door)")
    with pytest.raises(AssertionFailure):
        answers(space, f"!(eval {mismatched})")


def test_reference_interpret_entry_runs_typed_evaluation() -> None:
    """The reference's public spelling reaches typed evaluation through both doors."""
    space = MeTTa().self
    space.run(
        "(: c2-py-interpreted (-> Number Number))\n"
        "(= (c2-py-interpreted $x) (+ $x 1))"
    )
    both_doors(
        space,
        "c2-py-interpret-door",
        "(interpret (c2-py-interpreted 41) Number &self)",
        ["42"],
    )


def test_not_reducible_is_control_at_eval_and_data_at_the_boundary() -> None:
    """Bare and function-returned markers retain their calls outside chain."""
    space = MeTTa().self
    space.run(
        "(: c2-py-nr (-> Atom Atom))\n"
        "(= (c2-py-nr $x) NotReducible)\n"
        "(: c2-py-frame-nr (-> Atom %Undefined%))\n"
        "(= (c2-py-frame-nr $x) (function (return NotReducible)))\n"
        "(= (c2-py-frame-body-nr) NotReducible)"
    )
    # NotReducible written in a body is DATA and stays the answer, which is
    # what upstream answers for the same forms
    # [measured 2026-08-30 against PeTTa@ae66fa8].
    assert answers(space, "!(c2-py-nr q)") == ["NotReducible"]
    assert answers(space, "!(eval (c2-py-nr q))") == ["NotReducible"]
    assert answers(
        space, "!(chain (eval (c2-py-nr q)) $r (quote $r))"
    ) == ["NotReducible"]
    # The function/return FRAME is this engine's own: upstream has no such
    # operation and leaves `(function ...)` as data, answering
    # `(function (return NotReducible))` where these run the frame and answer
    # what it returned.
    assert answers(space, "!(c2-py-frame-nr q)") == ["NotReducible"]
    assert answers(space, "!(function (c2-py-frame-body-nr))") == ["NotReducible"]
    assert answers(space, "!(function (c2-py-frame-no-rule))") == [
        "(Error (function (c2-py-frame-no-rule)) NoReturn)"
    ]
    assert answers(
        space, "!(chain (eval (c2-py-frame-nr q)) $r (quote $r))"
    ) == ["NotReducible"]
    assert answers(space, "!(eval ())") == ["()"]
    assert answers(space, "!(collapse (eval ()))") == ["(())"]


def test_tail_calls_preserve_the_innermost_irreducible_call() -> None:
    """A recursive tail passes its callee's result through unchanged.

    `NotReducible` written in a body is DATA and stays the answer; the marker
    that means "answer the call as written" is the engine's own and shares no
    name with anything a program can write
    [measured 2026-08-30 against PeTTa@ae66fa8, which answers NotReducible].
    """
    space = MeTTa().self
    space.run(
        "(= (c2-py-tail Z) NotReducible)\n"
        "(= (c2-py-tail (S $n)) (c2-py-tail $n))"
    )
    both_doors(
        space,
        "c2-py-tail-door",
        "(c2-py-tail (S (S Z)))",
        ["NotReducible"],
    )


def test_forward_callers_are_repaired_before_a_same_source_runnable(
    tmp_path,
) -> None:
    """File and string sources settle earlier definitions before `!`."""
    space = MeTTa().self
    file_program = tmp_path / "forward-prefix.metta"
    file_program.write_text(
        "(= (c2-py-file-forward-f) (c2-py-file-forward-g))\n"
        "(= (c2-py-file-forward-g) 42)\n"
        "!(c2-py-file-forward-f)\n",
        encoding="utf-8",
    )
    assert [[str(atom) for atom in group] for group in space.load(file_program)] == [
        ["42"]
    ]
    assert answers(
        space,
        "(= (c2-py-run-forward-f) (c2-py-run-forward-g))\n"
        "(= (c2-py-run-forward-g) 42)\n"
        "!(c2-py-run-forward-f)",
    ) == ["42"]


def test_reduce_answers_an_irreducible_operand_through_both_doors() -> None:
    """Reduce answers its OPERAND when no reduction applies, not its own frame.

    Upstream's reducer ends `Out = [F|Args]` for a head it cannot call, so
    `!(reduce (nofib 5))` is `(nofib 5)` there
    [measured 2026-08-30 against PeTTa@ae66fa8]. The empty operand is this
    engine's own: upstream aborts the run on `(reduce ())`.
    """
    space = MeTTa().self
    both_doors(
        space,
        "c2-py-reduce-door",
        "(reduce (c2-py-reduce-unknown))",
        ["(c2-py-reduce-unknown)"],
    )
    both_doors(space, "c2-py-reduce-empty-door", "(reduce ())", ["()"])
    both_doors(space, "c2-py-reduce-value-door", "(reduce (+ 20 22))", ["42"])


def test_a_deferred_library_call_keeps_empty_as_a_losing_race_branch() -> None:
    """Imported operation masks and Empty pruning survive both call doors."""
    space = MeTTa().self
    space.run(
        "!(import! &self (library lib_thread))\n"
        "(= (c2-py-race-inc $x) (+ $x 1))"
    )
    both_doors(
        space,
        "c2-py-race-door",
        "(par-race ((superpose ()) (c2-py-race-inc 41)))",
        ["42"],
    )
