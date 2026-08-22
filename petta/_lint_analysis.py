"""Purpose: analyze stored equations, declarations, variables, and calls.
Guarantees:
  - duplicate equations are found by one canonicalization per equation
    [tested test_each_extra_duplicate_equation_is_reported]
  - a strict instance of a stored equation is reported as subsumed, with
    the pairwise bound stated in the finding [tested
    test_a_semantically_redundant_equation_is_reported_with_its_bound]
  - atom traversal treats expression depth as data [tested
    test_lint_walks_deep_expression_trees_iteratively]
  - possible undefined calls remain explicitly labelled as heuristic
    [tested test_possibly_undefined_reference_is_labeled_a_heuristic]
  - a body calling a translator special form is not a finding, so the
    commonest shape in MeTTa, an equation whose body branches on `if`, lints
    clean [tested test_calling_a_special_form_is_not_an_undefined_reference]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

from collections import Counter
from difflib import get_close_matches
from typing import Any, TypeGuard

from ._lint_model import EngineRegistry, Finding
from .atoms import Atom, Expression, Grounded, Symbol, Variable, _alpha_eq, _map_atoms, _variables

_BINDING_HEADS = {"let", "let*", "match", "unify", "case", "chain", "bind!"}


def _arrow_inputs(declaration: Atom) -> int | None:
    """Return the input count of an arrow declaration."""
    if isinstance(declaration, Expression) and len(declaration) >= 2 and declaration[0] == Symbol("->"):
        return len(declaration) - 2
    return None


def _walk_heads(atom: Atom):
    """Yield each nested expression whose head is a symbol."""
    stack = [atom]
    while stack:
        current = stack.pop()
        if not isinstance(current, Expression) or len(current) == 0:
            continue
        if isinstance(current[0], Symbol):
            yield current
        stack.extend(reversed(current.children))


def _contains_binding_form(atom: Atom) -> bool:
    return any(call[0].name in _BINDING_HEADS for call in _walk_heads(atom))


def _alpha_key(atom: Atom) -> Atom:
    """Canonicalize variable names once for equality and hashing."""
    names: dict[str, Variable] = {}

    def rename(item: Atom) -> Atom:
        if not isinstance(item, Variable):
            return item
        replacement = names.get(item.name)
        if replacement is None:
            replacement = Variable(f"lint-variable-{len(names)}")
            names[item.name] = replacement
        return replacement

    return _map_atoms(atom, rename)


def _is_form(atom: Atom, head: Symbol) -> TypeGuard[Expression]:
    return isinstance(atom, Expression) and len(atom) == 3 and atom[0] == head


def _symbol_head(atom: Atom) -> str | None:
    if isinstance(atom, Expression) and len(atom) > 0 and isinstance(atom[0], Symbol):
        return atom[0].name
    return None


def _index_atoms(
    atoms: list[Atom],
) -> tuple[list[Expression], list[Expression], set[str], set[str]]:
    equals, colon = Symbol("="), Symbol(":")
    equations = [atom for atom in atoms if _is_form(atom, equals)]
    declarations = [atom for atom in atoms if _is_form(atom, colon)]
    fact_heads = {
        name
        for atom in atoms
        if (name := _symbol_head(atom)) is not None and name not in ("=", ":")
    }
    defined_here = {
        name for equation in equations if (name := _symbol_head(equation[1])) is not None
    }
    return equations, declarations, fact_heads, defined_here


def _arrowed_names(declarations: list[Expression]) -> set[str]:
    """The names carrying at least one arrow declaration.

    Decided over the whole space before any declaration is judged, because one
    arrow among a name's declarations is enough.
    """
    return {
        name_atom.name
        for declaration in declarations
        if isinstance(name_atom := declaration[1], Symbol)
        and _arrow_inputs(declaration[2]) is not None
    }


def _types_the_symbol(
    space: Any,
    declaration: Expression,
    name: str,
    arrowed: set[str],
    defined_here: set[str],
) -> Finding | None:
    """Report a declaration that types the symbol where a call needs an arrow.

    The engine refuses this at load over a source's own forms. What reaches
    here came in some other way, most often add_atom from Python, and the
    space is the only place a name's finished set of declarations can be seen.
    """
    signature = declaration[2]
    if name in arrowed or signature == Symbol("%Undefined%") or isinstance(signature, Variable):
        return None
    if name not in defined_here and not space.is_function_here(name):
        return None
    return Finding(
        "declaration-types-the-symbol",
        name,
        f"declared {signature}, which is not an arrow, so it types the "
        f"symbol and not a call: every ({name} ...) compiles unchecked",
        declaration,
        severity="warning",
    )


def _declaration_findings(
    space: Any,
    declarations: list[Expression],
    defined_here: set[str],
    registry: EngineRegistry,
) -> list[Finding]:
    findings: list[Finding] = []
    arrowed = _arrowed_names(declarations)
    for declaration in declarations:
        name_atom, signature = declaration[1], declaration[2]
        if not isinstance(name_atom, Symbol):
            continue
        name = name_atom.name
        inputs = _arrow_inputs(signature)
        if inputs is None:
            finding = _types_the_symbol(
                space, declaration, name, arrowed, defined_here
            )
            if finding:
                findings.append(finding)
            continue
        if name not in defined_here and not space.is_function_here(name):
            findings.append(
                Finding(
                    "declared-but-undefined",
                    name,
                    f"declared {signature} but nothing defines it; every call will stay unreduced",
                    declaration,
                    severity="warning",
                )
            )
            continue
        compiled = registry.arities(name)
        if compiled and (inputs + 1) not in compiled:
            arities = sorted(arity - 1 for arity in compiled)
            findings.append(
                Finding(
                    "arrow-arity-mismatch",
                    name,
                    f"the arrow declares {inputs} input(s) but its equations take {arities}",
                    declaration,
                    severity="error",
                )
            )
    return findings


# Readers that pick an answer out of a collapse BY POSITION. sort-atom and
# unique-atom are the canonicalisers that make a positional read safe, so an
# expression that goes through one of those is not reported.
_POSITIONAL_READERS = {"car-atom", "cdr-atom", "index-atom"}
_CANONICALISERS = {"sort-atom", "unique-atom", "msort"}


_ORDER_READ_DETAIL = (
    "picks by position out of a collapse of {name}, which is tabled; tabling "
    "preserves the answer set and not its order, so wrap the collapse in "
    "sort-atom or do not table {name}"
)


def _uncanonicalised_collapse(atom: Atom) -> str | None:
    """The head of a (collapse (f ...)) reachable without a canonicaliser.

    `(car-atom (sort-atom (collapse (f $x))))` is safe and answers None;
    `(car-atom (collapse (f $x)))` answers "f".
    """
    head = _symbol_head(atom)
    if head is None or head in _CANONICALISERS or not isinstance(atom, Expression):
        return None
    if head == "collapse":
        return _symbol_head(atom[1]) if len(atom) == 2 else None
    found = (_uncanonicalised_collapse(child) for child in atom.children[1:])
    return next((name for name in found if name is not None), None)


def _order_read(equation: Expression, tabled: frozenset[str]) -> str | None:
    """The tabled function this equation reads out of a collapse by position."""
    for call in _walk_heads(equation[2]):
        if call[0].name in _POSITIONAL_READERS and len(call) >= 2:
            read = _uncanonicalised_collapse(call[1])
            if read in tabled:
                return read
    return None


def _tabling_findings(equations: list[Expression], registry: EngineRegistry) -> list[Finding]:
    """Report a positional read of a tabled function's collapsed answers.

    Tabling preserves the answer SET and not the answer sequence: an untabled
    function answers in clause order and a tabled one answers from its trie,
    so which order comes out moves when something unrelated moves. Measured in
    lib_tabling.pl's own header: adding three facts nothing calls to
    engine/translator.pl flipped (collapse (pick a)) from (one two) to (two one).

    A finding rather than a refusal, because a positional read is right
    whenever the function is deterministic, and the linter cannot know that.
    """
    tabled = registry.tabled()
    return [
        Finding(
            "tabled-answer-order-read",
            read,
            _ORDER_READ_DETAIL.format(name=read),
            equation,
            severity="warning",
        )
        for equation in equations
        if (read := _order_read(equation, tabled)) is not None
    ]


def _duplicate_findings(equations: list[Expression]) -> list[Finding]:
    keys = [_alpha_key(equation) for equation in equations]
    remaining = Counter(keys)
    findings: list[Finding] = []
    for equation, key in zip(equations, keys, strict=True):
        remaining[key] -= 1
        if remaining[key] > 0:
            findings.append(
                Finding(
                    "duplicate-equation",
                    str(equation[1]),
                    "an alpha-equivalent equation is stored twice; every "
                    "call answers the duplicate as an extra result",
                    equation,
                    severity="warning",
                )
            )
    return findings


def _instantiates(general: Atom, specific: Atom) -> bool:
    """One-way matching: does binding general's variables yield specific?

    Iterative for the same reason the walker is: expression depth is data.
    A bound variable must reproduce the identical subtree on every later
    occurrence, so shared variables constrain the whole equation at once.
    """
    bindings: dict[str, Atom] = {}
    stack: list[tuple[Atom, Atom]] = [(general, specific)]
    while stack:
        into_general, into_specific = stack.pop()
        if isinstance(into_general, Variable):
            bound = bindings.get(into_general.name)
            if bound is None:
                bindings[into_general.name] = into_specific
            elif bound != into_specific:
                return False
        elif isinstance(into_general, Expression):
            if not isinstance(into_specific, Expression) or len(into_general) != len(
                into_specific
            ):
                return False
            stack.extend(zip(into_general, into_specific, strict=True))
        elif into_general != into_specific:
            return False
    return True


def _subsumed_findings(equations: list[Expression]) -> list[Finding]:
    """Plotkin's reduction step, bounded to pairwise instance subsumption.

    Plotkin (1972, theorem 3.3.1.2) reduces a program by dropping any
    clause the REST of the program subsumes. The general test needs
    resolution, so this check keeps the decidable pair of it: an equation
    that is a strict instance of one other stored equation answers nothing
    the general equation does not already answer, and calls on the overlap
    answer twice. Alpha-equivalent twins stay `duplicate-equation`'s.
    """
    keys = [_alpha_key(equation) for equation in equations]
    by_head: dict[tuple[str | None, int], list[int]] = {}
    for position, equation in enumerate(equations):
        head = equation[1]
        arity = len(head) if isinstance(head, Expression) else 0
        by_head.setdefault((_symbol_head(head), arity), []).append(position)
    findings: list[Finding] = []
    for group in by_head.values():
        for specific in group:
            for general in group:
                if specific == general or keys[specific] == keys[general]:
                    continue
                if _instantiates(equations[general], equations[specific]):
                    findings.append(
                        Finding(
                            "subsumed-equation",
                            str(equations[specific][1]),
                            "an instance of another stored equation: every "
                            "answer it gives, the general equation gives "
                            "too, so calls on the overlap answer twice. The "
                            "check is pairwise against single equations, "
                            "Plotkin's reduction step; redundancy through "
                            "combinations of equations is not searched",
                            equations[specific],
                            severity="information",
                        )
                    )
                    break
    return findings


def _unbound_findings(equation: Expression, head: Atom, body: Atom) -> list[Finding]:
    if _contains_binding_form(body):
        return []
    head_vars = set(_variables(head))
    loose = sorted(name for name in set(_variables(body)) if name not in head_vars and name != "_")
    if not loose:
        return []
    pretty = ["$" + name for name in loose if not name.startswith("_")]
    renamed = len(loose) - len(pretty)
    if renamed:
        pretty.append(f"{renamed} engine-renamed variable(s)")
    return [
        Finding(
            "unbound-variable",
            str(head),
            f"{', '.join(pretty)} appear(s) in the body but not in the head; "
            f"an unbound variable never matches what you meant",
            equation,
            severity="error",
        )
    ]


def _nothing_carries(
    name: str,
    arguments: int,
    fact_heads: set[str],
    registry: EngineRegistry,
) -> bool:
    """Whether nothing in the engine or the space gives this head meaning.

    The engine gives one two ways, and the check has to ask both: fun/1 for
    a function, and metta_translated_head/1 for a form the translator
    compiles. Asking fun/1 alone reported every correct use of `if`, `case`
    and `collapse` as undefined. A bare symbol with no arguments is data by
    construction and is never asked about.
    """
    return (
        arguments > 0
        and name not in fact_heads
        and not registry.is_special_form(name)
    )


def _call_findings(
    equation: Expression,
    body: Atom,
    fact_heads: set[str],
    registry: EngineRegistry,
) -> list[Finding]:
    findings: list[Finding] = []
    for call in _walk_heads(body):
        name = call[0].name
        arguments = len(call) - 1
        if registry.is_function(name):
            compiled = registry.arities(name)
            if compiled and (arguments + 1) not in compiled:
                arities = sorted(arity - 1 for arity in compiled)
                findings.append(
                    Finding(
                        "arity-mismatch",
                        name,
                        f"called with {arguments} argument(s) but defined for {arities}",
                        equation,
                        severity="error",
                    )
                )
        elif _nothing_carries(name, arguments, fact_heads, registry):
            close = get_close_matches(
                name, registry.known_names() | fact_heads, n=1, cutoff=0.8
            )
            findings.append(
                Finding(
                    "possibly-undefined-reference",
                    name,
                    "no function, special form, builtin, or stored fact carries "
                    "this head; a call to it stays unreduced (heuristic: it may "
                    "be data on purpose)",
                    equation,
                    severity="hint",
                    suggestion=close[0] if close else None,
                )
            )
    return findings


def _equation_findings(
    equations: list[Expression], fact_heads: set[str], registry: EngineRegistry
) -> list[Finding]:
    findings: list[Finding] = []
    for equation in equations:
        head, body = equation[1], equation[2]
        findings.extend(_unbound_findings(equation, head, body))
        findings.extend(_call_findings(equation, body, fact_heads, registry))
    return findings




# The seven syntactic simplification rules the TS linter carries, each
# rewriting to something the engine provably answers identically, plus the
# structural cases that cannot rewrite. The autofix is the STORED atom with
# the inner expression replaced, so applying it is remove-then-add.
def _is_truth(atom: Atom, value: bool) -> bool:  # noqa: FBT001  -- the boolean is established API data and positional compatibility is part of the call shape
    """Whether the atom is the boolean literal, under either spelling the
    engine stores: True and true are one term there, arriving here as a
    ground bool or as the symbol.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    if isinstance(atom, Grounded):
        return atom.value is value
    return atom in (Symbol(str(value)), Symbol(str(value).lower()))


def _if_simplified(inner: Expression) -> tuple[str, str, Atom | None] | None:
    if len(inner) != 4:
        return None
    _, condition, then_branch, else_branch = inner.children
    if _is_truth(condition, True):  # noqa: FBT003  -- the boolean literal is atom or wire data at this site, not a behavior switch
        return ("constant-if-true", "the condition is literally True; only the then-branch can answer", then_branch)
    if _is_truth(condition, False):  # noqa: FBT003  -- the boolean literal is atom or wire data at this site, not a behavior switch
        return ("constant-if-false", "the condition is literally False; only the else-branch can answer", else_branch)
    if _alpha_eq(then_branch, else_branch):
        return ("if-same-branches", "both branches are the same expression; the condition decides nothing", then_branch)
    if _is_truth(then_branch, True) and _is_truth(else_branch, False):  # noqa: FBT003  -- the boolean literal is atom or wire data at this site, not a behavior switch
        return ("if-true-false", "(if c True False) answers exactly what c answers", condition)
    return None


def _superpose_simplified(inner: Expression) -> tuple[str, str, Atom | None] | None:
    if len(inner) != 2 or not isinstance(inner[1], Expression):
        return None
    branches = inner[1].children
    if not branches:
        return ("superposed-empty", "a superpose of nothing answers nothing; every containing expression dies here", None)
    if len(branches) == 1:
        return ("superposed-single", "a superpose of one thing is that thing", branches[0])
    return None


def _binder_simplified(inner: Expression) -> tuple[str, str, Atom | None] | None:
    if len(inner) < 2 or not isinstance(inner[1], Expression):
        return None
    seen: set[str] = set()
    for binding in inner[1].children:
        if not (isinstance(binding, Expression) and binding.children):
            continue
        for name in _variables(binding.children[0]):
            if name in seen:
                return (
                    "duplicate-binder",
                    f"${name} is bound twice in one let*; the second binding "
                    f"unifies rather than shadows, so if an equality "
                    f"constraint is meant, say == instead",
                    None,
                )
            seen.add(name)
    return None


_SIMPLIFIERS = {"if": _if_simplified, "superpose": _superpose_simplified, "let*": _binder_simplified}


def _simplified(inner: Expression) -> tuple[str, str, Atom | None] | None:
    """One nested expression's simplification, or None: (kind, detail,
    replacement), replacement None when the finding has no rewrite.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    simplifier = _SIMPLIFIERS.get(_symbol_head(inner) or "")
    return None if simplifier is None else simplifier(inner)


def _replaced(stored: Expression, target: Atom, replacement: Atom) -> Atom:
    """The stored atom with exactly this occurrence rewritten, by identity."""
    return _map_atoms(stored, lambda a: replacement if a is target else a)


def _simplification_findings(equations: list[Expression]) -> list[Finding]:
    findings: list[Finding] = []
    for equation in equations:
        for call in _walk_heads(equation[2]):
            found = _simplified(call)
            if found is None:
                continue
            kind, detail, replacement = found
            findings.append(
                Finding(
                    kind,
                    str(call),
                    detail,
                    equation,
                    severity="information",
                    payload={"expression": call, "replacement": replacement},
                    autofix=None if replacement is None else _replaced(equation, call, replacement),
                )
            )
    return findings


def _arities_by_name(equations: list[Expression]) -> dict[str, dict[int, Expression]]:
    """Each defined name's arities, with one witness equation per arity."""
    by_name: dict[str, dict[int, Expression]] = {}
    for equation in equations:
        head = equation[1]
        if isinstance(head, Expression) and head.children and isinstance(head.children[0], Symbol):
            by_name.setdefault(head.children[0].name, {}).setdefault(
                len(head.children) - 1, equation
            )
    return by_name


def _inconsistent_arity_findings(
    equations: list[Expression], declarations: list[Expression]
) -> list[Finding]:
    """Equations for one name at differing arities with no arrow saying so.

    Multi-arity dispatch is legal and sometimes meant, which is why this is
    information rather than an error, and why an arrow declaration silences
    it: the arrow states the intent, and disagreement with an arrow is
    already arrow-arity-mismatch.
    """
    arrowed = _arrowed_names(declarations)
    by_name = _arities_by_name(equations)
    return [
        Finding(
            "inconsistent-arity",
            name,
            f"defined at arities {sorted(arities)} with no arrow declaring "
            f"either; if the spread is deliberate dispatch, an arrow per "
            f"arity says so",
            arities[min(arities)],
            severity="information",
            payload={"arities": sorted(arities)},
        )
        for name, arities in by_name.items()
        if len(arities) > 1 and name not in arrowed
    ]


#: Declared slots these names admit anything of their kind, so a concrete
#: argument type can never contradict them.
_METATYPES = frozenset(
    {"Atom", "Expression", "Symbol", "Grounded", "Variable", "%Undefined%", "Type"}
)


def _declared_arrows(declarations: list[Expression]) -> dict[str, tuple[Atom, ...]]:
    """Each declared name's arrow input slots, first declaration winning."""
    arrows: dict[str, tuple[Atom, ...]] = {}
    for declaration in declarations:
        name_atom, signature = declaration[1], declaration[2]
        if (
            isinstance(name_atom, Symbol)
            and isinstance(signature, Expression)
            and _symbol_head(signature) == "->"
        ):
            arrows.setdefault(name_atom.name, signature.children[1:-1])
    return arrows


def _slot_mismatch(
    slot: Atom, argument: Atom, registry: EngineRegistry
) -> tuple[str, str] | None:
    """(declared, actual) when the engine type contradicts one declared
    slot, else None. A parametric slot, a metatype slot, a non-ground
    argument, and an argument answering %Undefined% all pass, keeping the
    check conservative; a nested call is the engine's own hoisted check's.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    if not isinstance(slot, Symbol) or slot.name in _METATYPES:
        return None
    if isinstance(argument, (Variable, Expression)):
        return None
    actual = registry.type_of(argument)
    if actual in ("%Undefined%", slot.name):
        return None
    return slot.name, actual


def _type_findings(
    equations: list[Expression], declarations: list[Expression], registry: EngineRegistry
) -> list[Finding]:
    """A ground argument whose engine type contradicts the declared slot.

    get-type/2 is total here, so the check is one cached engine question
    per distinct argument, and only concrete Symbol-against-Symbol
    disagreements report.
    """
    arrows = _declared_arrows(declarations)
    findings: list[Finding] = []
    for equation in equations:
        for call in _walk_heads(equation[2]):
            slots = arrows.get(call[0].name)
            if slots is None or len(call) - 1 != len(slots):
                continue
            for slot, argument in zip(slots, call.children[1:], strict=True):
                mismatch = _slot_mismatch(slot, argument, registry)
                if mismatch is None:
                    continue
                declared, actual = mismatch
                findings.append(
                    Finding(
                        "type-mismatch",
                        call[0].name,
                        f"{argument} is {actual} where the declared arrow "
                        f"wants {declared}",
                        equation,
                        severity="error",
                        payload={"expected": slot, "actual": actual, "argument": argument},
                    )
                )
    return findings


def analyze(space: Any, atoms: list[Atom], registry: EngineRegistry) -> list[Finding]:
    """Analyze one enumerated space against one registry snapshot."""
    equations, declarations, fact_heads, defined_here = _index_atoms(atoms)
    return [
        *_declaration_findings(space, declarations, defined_here, registry),
        *_duplicate_findings(equations),
        *_subsumed_findings(equations),
        *_tabling_findings(equations, registry),
        *_equation_findings(equations, fact_heads, registry),
        *_simplification_findings(equations),
        *_inconsistent_arity_findings(equations, declarations),
        *_type_findings(equations, declarations, registry),
    ]
