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
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

from dataclasses import dataclass

from .atoms import Atom, Expr, Sym, Var, alpha_eq, variables

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


def _is_function(runtime, name: str) -> bool:
    row = runtime.once(
        "( fun(F) -> T = true ; T = false )", F=name
    )
    return row.get("T") == "true" or row.get("T") is True


def _arities(runtime, name: str) -> set[int]:
    row = runtime.once(
        "findall(_A, arity(F, _A), _L), term_string(_L, Out)", F=name
    )
    text = row["Out"].strip("[]")
    return {int(part) for part in text.split(",") if part.strip()}


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
    if isinstance(atom, Expr) and len(atom) > 0:
        if isinstance(atom[0], Sym):
            yield atom
        for item in atom:
            yield from _walk_heads(item)


def _contains_binding_form(atom: Atom) -> bool:
    """Whether any subexpression introduces bindings of its own (let,
    let*, match, ...): under one, a body-only variable is legitimate,
    so the unbound-variable check stands down for the whole equation
    rather than guessing scopes."""
    return any(
        call[0].name in _BINDING_HEADS for call in _walk_heads(atom)
    )


def lint(space) -> list[Finding]:
    """Diagnose a space. Answers findings, empty when nothing looks
    wrong; print them or branch on .kind."""
    from .foreign import require_capability

    require_capability(space.space_name, "enumerate", "lint")
    runtime = space.runtime
    findings: list[Finding] = []
    atoms = space.atoms()

    equations = [a for a in atoms if isinstance(a, Expr) and len(a) == 3
                 and a[0] == Sym("=")]
    declarations = [a for a in atoms if isinstance(a, Expr) and len(a) == 3
                    and a[0] == Sym(":")]
    fact_heads = {
        str(a[0]) for a in atoms
        if isinstance(a, Expr) and len(a) > 0 and isinstance(a[0], Sym)
        and a[0] not in (Sym("="), Sym(":"))
    }
    defined_here = {
        str(eq[1][0]) for eq in equations
        if isinstance(eq[1], Expr) and len(eq[1]) > 0
        and isinstance(eq[1][0], Sym)
    }

    for declaration in declarations:
        name_atom, signature = declaration[1], declaration[2]
        if not isinstance(name_atom, Sym):
            continue
        name = name_atom.name
        inputs = _arrow_inputs(signature)
        if inputs is None:
            continue
        if name not in defined_here and not _is_function(runtime, name):
            findings.append(Finding(
                "declared-but-undefined", name,
                f"declared {signature} but nothing defines it; every call "
                f"will stay unreduced", declaration,
            ))
            continue
        compiled = _arities(runtime, name)
        if compiled and (inputs + 1) not in compiled:
            arities = sorted(a - 1 for a in compiled)
            findings.append(Finding(
                "arrow-arity-mismatch", name,
                f"the arrow declares {inputs} input(s) but its equations "
                f"take {arities}", declaration,
            ))

    for index, equation in enumerate(equations):
        for other in equations[index + 1:]:
            if alpha_eq(equation, other):
                findings.append(Finding(
                    "duplicate-equation", str(equation[1]),
                    "an alpha-equivalent equation is stored twice; every "
                    "call answers the duplicate as an extra result",
                    equation,
                ))
                break

    for equation in equations:
        head, body = equation[1], equation[2]
        head_vars = set(variables(head))
        if not _contains_binding_form(body):
            loose = sorted(
                name for name in set(variables(body))
                if name not in head_vars and name != "_"
            )
            if loose:
                #The engine renames stored variables, so the author's
                #spelling survives only sometimes; say what is knowable.
                pretty = ["$" + n for n in loose if not n.startswith("_")]
                renamed = len(loose) - len(pretty)
                if renamed:
                    pretty.append(f"{renamed} engine-renamed variable(s)")
                names = ", ".join(pretty)
                findings.append(Finding(
                    "unbound-variable", str(head),
                    f"{names} appear(s) in the body but not in the head; "
                    f"an unbound variable never matches what you meant",
                    equation,
                ))
        for call in _walk_heads(body):
            head = call[0].name
            args = len(call) - 1
            if _is_function(runtime, head):
                compiled = _arities(runtime, head)
                if compiled and (args + 1) not in compiled:
                    arities = sorted(a - 1 for a in compiled)
                    findings.append(Finding(
                        "arity-mismatch", head,
                        f"called with {args} argument(s) but defined for "
                        f"{arities}", equation,
                    ))
            elif (
                head not in fact_heads
                and not any(isinstance(item, Var) for item in call)
                and args > 0
            ):
                findings.append(Finding(
                    "possibly-undefined-reference", head,
                    f"no function, builtin, or stored fact carries this "
                    f"head; a call to it stays unreduced (heuristic: it "
                    f"may be data on purpose)", equation,
                ))
    return findings
