"""Purpose: diagnostics for the silently-wrong class. MeTTa fails open:
a call to a misspelled function stays an unreduced expression, a call
with the wrong argument count never matches an equation, and a type
declaration for a name nothing defines promises a function that cannot
answer. lint(space) walks the space's declarations and equations against
the engine's own registries (every builtin and defined function is a
fun/1 fact, every compiled arity an arity/2 fact) and answers findings,
each naming its kind, its subject, and the atom it stands on. Checks
that rest on a heuristic say so in their kind: an expression head that
is no known function may be data on purpose.
Guarantees:
  - engine registry lookups cross once per distinct name in a lint pass and
    arities cross as native lists [tested
    test_registry_queries_are_native_and_cached_per_name]
  - duplicate equations are found by one canonicalization per equation
    [tested test_each_extra_duplicate_equation_is_reported]
  - tree traversal treats expression depth as data [tested
    test_lint_walks_deep_expression_trees_iteratively]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any, TypeGuard

from .atoms import Atom, Expr, Sym, Var, map_atoms, variables
from .errors import EngineError

__all__ = ["Finding", "lint"]

#Forms whose subterms introduce variable bindings of their own: the
#first argument of let, each pair head of let*, and a match pattern all
#bind, so a body variable under them is not unbound.
_BINDING_HEADS = {"let", "let*", "match", "unify", "case", "chain", "bind!"}


@dataclass(frozen=True)
class Finding:
    """One diagnostic: kind names the check, subject the offending name,
    detail says what holds, atom is the evidence."""

    kind: str
    subject: str
    detail: str
    atom: Atom

    def __str__(self) -> str:
        return f"[{self.kind}] {self.subject}: {self.detail}"


class _EngineRegistry:
    """One immutable view of engine function facts during a lint pass."""

    __slots__ = ("_arities", "_functions", "_runtime")

    def __init__(self, runtime: Any) -> None:
        self._runtime = runtime
        self._functions: dict[str, bool] = {}
        self._arities: dict[str, frozenset[int]] = {}

    def is_function(self, name: str) -> bool:
        known = self._functions.get(name)
        if known is None:
            row = self._runtime.once(
                "( fun(F) -> T = true ; T = false )", F=name
            )
            known = row.get("T") in ("true", True)
            self._functions[name] = known
        return known

    def arities(self, name: str) -> frozenset[int]:
        cached = self._arities.get(name)
        if cached is not None:
            return cached
        row = self._runtime.once("findall(_A, arity(F, _A), L)", F=name)
        raw = row.get("L")
        if not isinstance(raw, (list, tuple)) or any(
            isinstance(value, bool) or not isinstance(value, int)
            for value in raw
        ):
            raise EngineError(
                f"engine arity registry returned an invalid list for {name!r}: "
                f"{raw!r}"
            )
        result = frozenset(raw)
        self._arities[name] = result
        return result


def _arrow_inputs(declaration: Atom) -> int | None:
    """(-> In1 .. InN Out) declares N inputs; anything else is not an
    arrow and constrains no arity."""
    if (
        isinstance(declaration, Expr)
        and len(declaration) >= 2
        and declaration[0] == Sym("->")
    ):
        return len(declaration) - 2
    return None


def _walk_heads(atom: Atom):
    """Every (head arg...) subexpression with a symbol head, the shapes
    that could be calls."""
    stack = [atom]
    while stack:
        current = stack.pop()
        if not isinstance(current, Expr) or len(current) == 0:
            continue
        if isinstance(current[0], Sym):
            yield current
        stack.extend(reversed(current.children))


def _contains_binding_form(atom: Atom) -> bool:
    """Whether any subexpression introduces bindings of its own (let,
    let*, match, ...): under one, a body-only variable is legitimate,
    so the unbound-variable check stands down for the whole equation
    rather than guessing scopes."""
    return any(
        call[0].name in _BINDING_HEADS for call in _walk_heads(atom)
    )


def _alpha_key(atom: Atom) -> Atom:
    """Canonicalize variable names once so equality and hashing deduplicate."""
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
    return (
        isinstance(atom, Expr)
        and len(atom) == 3
        and atom[0] == head
    )


def _symbol_head(atom: Atom) -> str | None:
    if (
        isinstance(atom, Expr)
        and len(atom) > 0
        and isinstance(atom[0], Sym)
    ):
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
        if (name := _symbol_head(atom)) is not None
        and name not in ("=", ":")
    }
    defined_here = {
        name
        for equation in equations
        if (name := _symbol_head(equation[1])) is not None
    }
    return equations, declarations, fact_heads, defined_here


def _declaration_findings(
    space: Any,
    declarations: list[Expr],
    defined_here: set[str],
    registry: _EngineRegistry,
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
                    f"declared {signature} but nothing defines it; every call "
                    f"will stay unreduced",
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
                    f"the arrow declares {inputs} input(s) but its equations "
                    f"take {arities}",
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
    loose = sorted(
        name
        for name in set(variables(body))
        if name not in head_vars and name != "_"
    )
    if not loose:
        return []
    # The engine renames stored variables, so the author's spelling survives
    # only sometimes. Report only what remains observable.
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
    registry: _EngineRegistry,
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
                        f"called with {arguments} argument(s) but defined for "
                        f"{arities}",
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
    equations: list[Expr],
    fact_heads: set[str],
    registry: _EngineRegistry,
) -> list[Finding]:
    findings: list[Finding] = []
    for equation in equations:
        head, body = equation[1], equation[2]
        findings.extend(_unbound_findings(equation, head, body))
        findings.extend(_call_findings(equation, body, fact_heads, registry))
    return findings


def lint(space) -> list[Finding]:
    """Diagnose a space. Answers findings, empty when nothing looks
    wrong; print them or branch on .kind."""
    from .foreign import require_capability

    require_capability(space.space_name, "enumerate", "lint")
    atoms = space.atoms()
    equations, declarations, fact_heads, defined_here = _index_atoms(atoms)
    registry = _EngineRegistry(space.runtime)
    return [
        *_declaration_findings(space, declarations, defined_here, registry),
        *_duplicate_findings(equations),
        *_equation_findings(equations, fact_heads, registry),
    ]
