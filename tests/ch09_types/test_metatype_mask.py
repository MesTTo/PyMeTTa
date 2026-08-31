"""Purpose: pin what a declared parameter type does to its argument.

Each row asks, per declared type, whether the argument reaches a user function
AS WRITTEN or reduced, and the shipped expression family is asked the same
question. The mask set is the arbiter's own one-line rule, not a set
inferred from behaviour: a parameter is held back exactly when its declared
evaluation view is `Atom`, `Variable` or `Expression`
[source: LeaTTa MettaHyperonFull/Core/Modifiers.lean:118-124,
`declaredTypeEvaluates`, consumed by `argMask` at
MettaHyperonFull/Minimal/Interpreter.lean:3760-3784].
Assumes:
  - `quote` freezes what it received, which is what makes the answers here
    discriminating; a body such as `(got $x)` re-reduces the member through
    ordinary tuple-member evaluation and shows nothing
  - each row uses its OWN probe name. A fresh MeTTa isolates stored state,
    not declarations: a declaration is asserted into a module-global store
    that outlives the handle, so two rows declaring `probe` differently see
    each other's arrow and the second answers under the first
Guarantees:
  - Symbol and Grounded parameters EVALUATE, which is the boundary a
    black-box probe is most likely to get wrong
    [measured 2026-08-24 against LeaTTa 9ea9f9d: `(: sf (-> Symbol
    %Undefined%))` with `(= foo bar)` answers `(quote bar)`]
  - a type-position modifier holds its argument and checks its value type
    [measured the same day: `(: mf (-> (:Atom Number) %Undefined%))` answers
    `(quote (+ 1 2))` and refuses a String with `(BadArgType 1 Number String)`]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import pytest

from metta import MeTTa

# (declared parameter type, program tail, expected single answer).
#
# The probe body is `(quote $x)`, and a quote is an EVALUATION BARRIER: it
# answers its payload with no wrapper, so every row below lost the `(quote
# ...)` it used to carry [source: PeTTa@ae66fa8 src/translator.pl:320]. `Atom`
# is the only masked parameter type, so `Expression` and `Variable` moved from
# holding to evaluating with it.
#
# The five rows upstream can also express were run through BOTH engines on
# 2026-08-30 and agree: Atom, Variable, Number, %Undefined% and Bool. The two
# `(:...)` rows are this engine's own type-position modifier, which upstream
# cannot name at all.
MASK_ROWS = [
    ("Atom", "!(probe (+ 1 2))", "(+ 1 2)"),
    ("Variable", "!(probe $y)", "$y"),
    ("Number", "!(probe (+ 1 2))", "3"),
    ("%Undefined%", "!(probe (+ 1 2))", "3"),
    ("Bool", "!(probe (> 2 1))", "True"),
    ("(:Atom Number)", "!(probe (+ 1 2))", "(+ 1 2)"),
    ("(:Expression Number)", "!(probe (+ 1 2))", "(+ 1 2)"),
]

# A parameter type the argument's own type contradicts is refused, and the
# refusal names the type that decided rather than the declaration that carried
# it.
REFUSAL_ROWS = [
    ("Expression", "!(probe 5)", "(Error (probe 5) (BadArgType 1 Expression Number))"),
    ("Variable", "!(probe (+ 1 2))",
     "(Error (probe (+ 1 2)) (BadArgType 1 Variable Number))"),
    ("(:Atom Number)", '!(probe "s")',
     '(Error (probe "s") (BadArgType 1 Number String))'),
]


def answers(program: str) -> list[str]:
    """Every answer one program produces, flattened across its bang forms."""
    groups = MeTTa().self.run(program)
    return [str(atom) for group in groups for atom in group]


def probe_name(declared: str) -> str:
    """A name no other row declares, derived from the row's own parameter type."""
    return "probe-" + "".join(c if c.isalnum() else "-" for c in declared)


def probe_program(declared: str, call: str) -> tuple[str, str]:
    """One row's source and the name it declared, with `probe` renamed."""
    name = probe_name(declared)
    body = (f"(: {name} (-> {declared} %Undefined%))\n"
            f"(= ({name} $x) (quote $x))\n" + call.replace("probe", name))
    return body, name


@pytest.mark.parametrize(("declared", "call", "expected"), MASK_ROWS)
def test_a_declared_parameter_holds_or_reduces_as_the_arbiter_does(
    declared, call, expected
):
    """Each declared parameter type routes its argument as the arbiter measured."""
    program, name = probe_program(declared, call)
    assert answers(program) == [expected.replace("probe", name)]


def test_an_evaluated_argument_its_declared_type_rules_out_has_no_answer():
    """An evaluating position is checked, and a failed check leaves no answer.

    `Expression` no longer holds, so `(+ 1 2)` reaches the check as 3, which is
    neither an Expression by type nor by metatype. Upstream appends exactly
    this check for every declared type that is not `Atom` or `%Undefined%` and
    answers nothing when it fails [source: PeTTa@ae66fa8
    src/translator.pl:392-396; measured 2026-08-30, both engines answer
    nothing for this program].

    The literal spelling is the REFUSAL_ROWS row below: a check that can be
    decided while compiling is an Error answer rather than a silent failure.
    """
    program, _ = probe_program("Expression", "!(probe (+ 1 2))")
    assert answers(program) == []


@pytest.mark.parametrize(("declared", "call", "expected"), REFUSAL_ROWS)
def test_a_masked_parameter_still_refuses_an_argument_its_type_rules_out(
    declared, call, expected
):
    """A masked position holds its argument and still applies the type check."""
    program, name = probe_program(declared, call)
    assert answers(program) == [expected.replace("probe", name)]


def test_a_symbol_parameter_evaluates_its_argument():
    """The one boundary a probe alone gets wrong: Symbol is NOT in the mask."""
    program = (
        "(: probe-symbol (-> Symbol %Undefined%))\n"
        "(= (probe-symbol $x) (quote $x))\n"
        "(= mask-foo mask-bar)\n"
        "!(probe-symbol mask-foo)"
    )
    #The quote is a barrier, so the body answers the evaluated symbol itself.
    assert answers(program) == ["mask-bar"]


# The shipped family, whose declarations are already arbiter-identical. Each
# row carries a reducible operand in a masked position, so it fails if the
# mask stops applying.
FAMILY_ROWS = [
    ("!(cons-atom (+ 1 2) (b))", "(3 b)"),
    ("!(cons-atom a ((+ 1 2) c))", "(a 3 c)"),
    ("!(decons-atom ((+ 1 2) b))", "(3 (b))"),
    ("!(decons-atom (cdr-atom (a b c)))", "(b (c))"),
    ("!(cdr-atom (cdr-atom (a b c)))", "(c)"),
    ("!(index-atom ((+ 1 2) b) 0)", "3"),
    ("!(size-atom ((+ 1 2) b))", "2"),
    # car-atom's %Undefined% result re-enters evaluation, so the operand it
    # extracted unreduced reduces here and nowhere earlier.
    ("!(car-atom ((+ 1 2) b))", "3"),
    ("!(chain (+ 1 2) $x (quote $x))", "3"),
    ("!(atom-subst (+ 1 2) $x ($x $x))", "((+ 1 2) (+ 1 2))"),
    # let evaluates its value, which is the whole difference from chain.
    ("!(let $x (+ 1 2) (cons-atom $x (b)))", "(3 b)"),
    # A tuple member still evaluates: the mask is a property of a declared
    # parameter and not of nesting.
    ("!((+ 1 2) b)", "(3 b)"),
]


@pytest.mark.parametrize(("call", "expected"), FAMILY_ROWS)
def test_the_expression_family_answers_what_the_arbiter_answers(call, expected):
    """Each shipped expression-family call answers the arbiter's own answer."""
    assert answers(call) == [expected]


def test_a_term_built_at_run_time_answers_as_the_written_call_does():
    """The dynamic door is the same translator, so the two cannot drift."""
    written = answers("!(cons-atom (+ 1 2) (b))")
    through_eval = answers("!(eval (cons-atom (+ 1 2) (b)))")
    through_metta = answers("!(metta (cons-atom (+ 1 2) (b)) %Undefined% &self)")
    #cons-atom evaluates its operands, so the sum is 3 at every door; what
    #this row asserts is that the three doors AGREE.
    assert written == through_eval == through_metta == ["(3 b)"]


def test_atom_subst_refuses_a_second_operand_that_is_not_a_variable():
    """Its body chains on that operand, so a non-variable binder never returns."""
    assert answers("!(atom-subst 1 (car-atom ($x)) ($x $x))") == [
        "(Error (atom-subst 1 (car-atom ($x)) ($x $x)) NoReturn)"
    ]


# The three collection forms declare their list `Expression` and foldl-atom
# declares its seed `Atom`, so both cross as written in either spelling and the
# fold runs over the parts of an unrun call. Measured on LeaTTa 9ea9f9d on
# 2026-08-24 through its default door.
COLLECTION_ROWS = [
    ("!(map-atom (cdr-atom (a b)) $y (q $y))", "((q b))"),
    ("!(map-atom (cdr-atom (a b)) (|-> ($y) (q $y)))", "((q b))"),
    ("!(filter-atom (cdr-atom (a b)) $y (== $y b))", "(b)"),
    ("!(filter-atom (cdr-atom (a b)) (|-> ($y) (== $y b)))", "(b)"),
    ("!(foldl-atom (cdr-atom (a b)) 0 $a $b (+ 1 $a))", "1"),
    ("!(foldl-atom (cdr-atom (a b)) 0 (|-> ($a $b) (+ 1 $a)))", "1"),
    # The seed is Atom, so `(size-atom (+ 1 2))` counts the held three-element
    # term; an evaluated seed would refuse a Number.
    ("!(foldl-atom (1) (+ 1 2) $a $b (size-atom $a))", "()"),
]


@pytest.mark.parametrize(("call", "expected"), COLLECTION_ROWS)
def test_a_collection_form_holds_its_list_in_either_spelling(call, expected):
    """Both spellings read one declared mask, so neither reduces the list."""
    assert answers(call) == [expected]


def test_a_python_comprehension_names_its_intermediate():
    """The Python surface reaches the same held list through `let`.

    A comprehension's source and each stage's answer are calls, so the
    lowering names them; written straight into the next stage's list position
    they would be folded over as data. The engine and the Python twin agree on
    the result, which is what makes the naming invisible to the author.
    """
    metta = MeTTa().self

    @metta.define
    def mask_pairs(xs):
        return [(x, y) for x in xs for y in xs if x < y]

    @metta.define
    def mask_total(xs):
        return sum([x * x for x in xs if x > 0])

    # The engine answers one MeTTa expression where Python answers a list of
    # tuples, so the two are compared as the same sequence of pairs.
    (pairs,) = mask_pairs((0, 0, 0, 1))
    assert [tuple(int(n) for n in pair) for pair in pairs] == mask_pairs.py(
        (0, 0, 0, 1)
    )
    assert mask_total((0, 0, 0, 1)) == [mask_total.py((0, 0, 0, 1))]


def test_add_reduct_reduces_a_plain_atom_and_an_equation_body():
    """It reduces what it stores, a plain atom included.

    A call nothing heads still reduces its members: `(total (+ 1 2))` is
    stored `(total 3)`, which is what the arbiter stores
    [measured 2026-08-24 against LeaTTa 9ea9f9d].
    """
    assert answers(
        "!(let $s (new-space) (let $w (add-reduct $s (total (+ 1 2)))"
        " (collapse (get-atoms $s))))"
    ) == ["((total 3))"]
    assert answers(
        "!(let $s (new-space) (let $w (add-reduct $s (= (addreduct) (+ 1 3)))"
        " (collapse (get-atoms $s))))"
    ) == ["((= (addreduct) 4))"]
