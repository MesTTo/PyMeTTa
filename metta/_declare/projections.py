"""Purpose: bind immutable constructor fields in the native method equation.

Guarantees:
  - one equation body retains its receiver across declared descendant layouts
    [tested: test_method_field_projection_preserves_captures_and_rebinding; commit=WORKTREE]
  - changed field contracts retain their original accessor calls
    [tested: test_method_projection_preserves_differing_field_contracts; commit=WORKTREE]
  - a replaced native equation is never overwritten by declaration refresh
    [tested: test_native_method_rewrite_survives_later_class_declarations; commit=WORKTREE]
Owns resources:
  - the method retains exact occurrence tokens for the equations it publishes;
    its declaring transaction owns replacement and rollback
    [tested: test_method_projection_rolls_back_a_descendant_layout; commit=WORKTREE]
"""

from __future__ import annotations

from typing import Any

from metta._atoms.factories import Atom, Expression, Grounded, S, Symbol, Variable, _expr
from metta._declare import classes, operations


def _getter(atom: Atom, owner: Any, fields: dict[Symbol, str]) -> tuple[Variable, str] | None:
    if isinstance(atom, Expression) and atom.head == S.evalc and len(atom.args) == 2 and atom.args[1] == Symbol(owner.space.name):
        atom = atom.args[0]
    if isinstance(atom, Expression) and len(atom.args) == 1 and isinstance(atom.args[0], Variable) and isinstance(atom.head, Symbol) and atom.head in fields:
        return atom.args[0], fields[atom.head]
    return None


def _walk(atom: Atom, visit: Any) -> Atom:
    replacement = visit(atom)
    if replacement is not atom:
        return replacement
    if not isinstance(atom, Expression) or atom.head in (S.noeval, S.quote):
        return atom
    return Expression([_walk(child, visit) for child in atom.children])


def equation(owner: Any, source: Expression, layouts: tuple[Any, ...]) -> Expression:
    """A value field is a constructor position in each admitted layout."""
    if source.head != S["="]:
        return source
    head, body = source.args
    fields = {
        owner.accessor(field.name): field.name for field in owner.stored_fields
        if all((candidate := layout.field(field.name)) is not None and candidate.annotation == field.annotation
               for layout in layouts)
    }
    receivers = {argument for argument in head.args if isinstance(argument, Variable)}
    reads: dict[Variable, dict[str, None]] = {}

    def collect(atom: Atom) -> Atom:
        read = _getter(atom, owner, fields)
        if read is not None and read[0] in receivers:
            reads.setdefault(read[0], {})[read[1]] = None
        return atom

    _walk(body, collect)
    reads = {receiver: names for receiver, names in reads.items() if len(names) >= 2}
    if not reads:
        return source
    used = {variable.name for variable in source.vars}

    def fresh(label: str) -> Variable:
        while label in used:
            label += "-"
        used.add(label)
        return Variable(label)

    values = {(receiver, name): fresh(f"projection-{index}-{name}")
              for index, (receiver, names) in enumerate(reads.items()) for name in names}

    def replace(atom: Atom) -> Atom:
        getter = _getter(atom, owner, fields)
        return values.get(getter, atom) if getter is not None else atom

    body = _walk(body, replace)
    for index, (receiver, names) in reversed(tuple(enumerate(reads.items()))):
        choices = []
        for layout in layouts:
            parts = [values[receiver, field.name] if field.name in names else fresh(f"projection-unused-{index}-{field.name}")
                     for field in layout.stored_fields]
            choices.append(_expr(S.let, _expr(S.noeval, layout.term(*parts)), _expr(S.noeval, receiver), Grounded(value=True)))
        selection = choices[0] if len(choices) == 1 else _expr(S.superpose, Expression(choices))
        body = _expr(S.chain, selection, fresh(f"projection-layout-{index}"), body)
    return _expr(S["="], head, body)


def refresh(method: Any, plans: tuple[Any, ...]) -> None:
    """Replace only the still-owned equations when the known layouts change."""
    if method.owner.grain != "value" or method.compiled is None:
        return
    layouts = tuple(sorted(
        (plan for plan in plans if method.owner.cls in plan.cls.__mro__ and plan.grain == "value"),
        key=lambda plan: plan.name,
    ))
    projected = tuple(equation(method.owner, source, layouts) for source in method.equations)
    if projected == method.projected:
        return
    # A native writer can replace any equation, including a lifted helper.
    # Its new occurrence belongs to that writer, so a later class declaration
    # cannot resurrect the original source under the old declaration's token.
    rows = [[token, source.to_wire()] for (_home, token), source in zip(method.rows, method.projected, strict=True)]
    if not method.owner.space._rt.once(
        "forall(member([_Token,_Wire],Rows),"
        "(metta_py_decode_shared(_Wire,_Source,_),spaces:metta_space_pair(Space,_Source,_Token,_)))",
        Space=method.owner.space.name, Rows=rows,
    ):
        return
    previous_rows, previous_source = method.rows, method.projected

    def restore() -> None:
        method.rows, method.projected = previous_rows, previous_source

    operations._record_registry_undo(restore, description=f"constructor projections in {method.name}")
    classes._withdraw_rows(method.owner.space._rt, method.rows)
    method.projected = projected
    method.rows = [row for source in projected for row in classes._owned_add(method.owner.space, source)]
