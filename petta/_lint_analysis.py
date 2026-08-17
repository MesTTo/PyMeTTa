"""Purpose: analyze stored equations, declarations, variables, and calls.
Guarantees:
  - duplicate equations are found by one canonicalization per equation
    [tested test_each_extra_duplicate_equation_is_reported]
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
  Future Enhancements: None
"""

from __future__ import annotations

from collections import Counter
from typing import Any, TypeGuard

from ._lint_model import EngineRegistry, Finding
from .atoms import Atom, Expr, Sym, Var, map_atoms, variables

_BINDING_HEADS = {"let", "let*", "match", "unify", "case", "chain", "bind!"}


def _arrow_inputs(declaration: Atom) -> int | None:
    """Return the input count of an arrow declaration."""
    if isinstance(declaration, Expr) and len(declaration) >= 2 and declaration[0] == Sym("->"):
        return len(declaration) - 2
    return None


def _walk_heads(atom: Atom):
    """Yield each nested expression whose head is a symbol."""
    stack = [atom]
    while stack:
        current = stack.pop()
        if not isinstance(current, Expr) or len(current) == 0:
            continue
        if isinstance(current[0], Sym):
            yield current
        stack.extend(reversed(current.children))


def _contains_binding_form(atom: Atom) -> bool:
    return any(call[0].name in _BINDING_HEADS for call in _walk_heads(atom))


def _alpha_key(atom: Atom) -> Atom:
    """Canonicalize variable names once for equality and hashing."""
    names: dict[str, Var] = {}

    def rename(item: Atom) -> Atom:
        if not isinstance(item, Var):
            return item
        replacement = names.get(item.name)
        if replacement is None:
            replacement = Var(f"lint-variable-{len(names)}")
            names[item.name] = replacement
        return replacement

    return map_atoms(atom, rename)


def _is_form(atom: Atom, head: Sym) -> TypeGuard[Expr]:
    return isinstance(atom, Expr) and len(atom) == 3 and atom[0] == head


def _symbol_head(atom: Atom) -> str | None:
    if isinstance(atom, Expr) and len(atom) > 0 and isinstance(atom[0], Sym):
        return atom[0].name
    return None


def _index_atoms(
    atoms: list[Atom],
) -> tuple[list[Expr], list[Expr], set[str], set[str]]:
    equals, colon = Sym("="), Sym(":")
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


def _arrowed_names(declarations: list[Expr]) -> set[str]:
    """The names carrying at least one arrow declaration.

    Decided over the whole space before any declaration is judged, because one
    arrow among a name's declarations is enough.
    """
    return {
        name_atom.name
        for declaration in declarations
        if isinstance(name_atom := declaration[1], Sym)
        and _arrow_inputs(declaration[2]) is not None
    }


def _types_the_symbol(
    space: Any,
    declaration: Expr,
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
    if name in arrowed or signature == Sym("%Undefined%") or isinstance(signature, Var):
        return None
    if name not in defined_here and not space.is_function_here(name):
        return None
    return Finding(
        "declaration-types-the-symbol",
        name,
        f"declared {signature}, which is not an arrow, so it types the "
        f"symbol and not a call: every ({name} ...) compiles unchecked",
        declaration,
    )


def _declaration_findings(
    space: Any,
    declarations: list[Expr],
    defined_here: set[str],
    registry: EngineRegistry,
) -> list[Finding]:
    findings: list[Finding] = []
    arrowed = _arrowed_names(declarations)
    for declaration in declarations:
        name_atom, signature = declaration[1], declaration[2]
        if not isinstance(name_atom, Sym):
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
    if head is None or head in _CANONICALISERS or not isinstance(atom, Expr):
        return None
    if head == "collapse":
        return _symbol_head(atom[1]) if len(atom) == 2 else None
    found = (_uncanonicalised_collapse(child) for child in atom.children[1:])
    return next((name for name in found if name is not None), None)


def _order_read(equation: Expr, tabled: frozenset[str]) -> str | None:
    """The tabled function this equation reads out of a collapse by position."""
    for call in _walk_heads(equation[2]):
        if call[0].name in _POSITIONAL_READERS and len(call) >= 2:
            read = _uncanonicalised_collapse(call[1])
            if read in tabled:
                return read
    return None


def _tabling_findings(equations: list[Expr], registry: EngineRegistry) -> list[Finding]:
    """Report a positional read of a tabled function's collapsed answers.

    Tabling preserves the answer SET and not the answer sequence: an untabled
    function answers in clause order and a tabled one answers from its trie,
    so which order comes out moves when something unrelated moves. Measured in
    lib_tabling.pl's own header: adding three facts nothing calls to
    src/translator.pl flipped (collapse (pick a)) from (one two) to (two one).

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
        )
        for equation in equations
        if (read := _order_read(equation, tabled)) is not None
    ]


def _duplicate_findings(equations: list[Expr]) -> list[Finding]:
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
                )
            )
    return findings


def _unbound_findings(equation: Expr, head: Atom, body: Atom) -> list[Finding]:
    if _contains_binding_form(body):
        return []
    head_vars = set(variables(head))
    loose = sorted(name for name in set(variables(body)) if name not in head_vars and name != "_")
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
    equation: Expr,
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
                    )
                )
        elif _nothing_carries(name, arguments, fact_heads, registry):
            findings.append(
                Finding(
                    "possibly-undefined-reference",
                    name,
                    "no function, special form, builtin, or stored fact carries "
                    "this head; a call to it stays unreduced (heuristic: it may "
                    "be data on purpose)",
                    equation,
                )
            )
    return findings


def _equation_findings(
    equations: list[Expr], fact_heads: set[str], registry: EngineRegistry
) -> list[Finding]:
    findings: list[Finding] = []
    for equation in equations:
        head, body = equation[1], equation[2]
        findings.extend(_unbound_findings(equation, head, body))
        findings.extend(_call_findings(equation, body, fact_heads, registry))
    return findings


def analyze(space: Any, atoms: list[Atom], registry: EngineRegistry) -> list[Finding]:
    """Analyze one enumerated space against one registry snapshot."""
    equations, declarations, fact_heads, defined_here = _index_atoms(atoms)
    return [
        *_declaration_findings(space, declarations, defined_here, registry),
        *_duplicate_findings(equations),
        *_tabling_findings(equations, registry),
        *_equation_findings(equations, fact_heads, registry),
    ]
