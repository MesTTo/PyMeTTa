"""Purpose: analyze stored equations, declarations, variables, and calls.
Guarantees:
  - duplicate equations are found by one canonicalization per equation
    [tested test_each_extra_duplicate_equation_is_reported]
  - atom traversal treats expression depth as data [tested
    test_lint_walks_deep_expression_trees_iteratively]
  - possible undefined calls remain explicitly labelled as heuristic
    [tested test_possibly_undefined_reference_is_labeled_a_heuristic]
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


def _declaration_findings(
    space: Any,
    declarations: list[Expr],
    defined_here: set[str],
    registry: EngineRegistry,
) -> list[Finding]:
    findings: list[Finding] = []
    for declaration in declarations:
        name_atom, signature = declaration[1], declaration[2]
        if not isinstance(name_atom, Sym):
            continue
        name = name_atom.name
        inputs = _arrow_inputs(signature)
        if inputs is None:
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
        elif name not in fact_heads and arguments > 0:
            findings.append(
                Finding(
                    "possibly-undefined-reference",
                    name,
                    "no function, builtin, or stored fact carries this head; "
                    "a call to it stays unreduced (heuristic: it may be data "
                    "on purpose)",
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
        *_equation_findings(equations, fact_heads, registry),
    ]
