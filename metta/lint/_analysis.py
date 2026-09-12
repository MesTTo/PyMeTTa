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
  - finite Literal constructor domains are checked as complete terms, while
    constructors with unrestricted fields retain head coverage [tested:
    test_finite_constructor_coverage_preserves_field_correlations;
    commit=WORKTREE]
  - a body calling a translator special form is not a finding, so the
    commonest shape in MeTTa, an equation whose body branches on `if`, lints
    clean [tested test_calling_a_special_form_is_not_an_undefined_reference]
  - nine adopted advisory kinds cover first-letter roles, interpreter
    shadows, Python/engine crossings, unordered answer views, import-time
    calls, and synchronous async-body driving without refusing execution
    [tested: extensions/python/tests/ch14_seeing_your_program/test_lint_family.py; commit=acb40f1912f131ae088083d1af29b4b283019bea]
  - exact named source intents suppress only their bound finding, while the
    intent remains queryable in &metta [tested:
    test_a_named_metta_ok_intent_suppresses_only_its_bound_rule; commit=acb40f1912f131ae088083d1af29b4b283019bea]
  - a compiled ``py(...)`` island retained under a repeated loop equation is
    reported once per source island with its Python coordinates [tested:
    test_py_host_island_inside_loops_emits_exact_findings; commit=3f0a1d237a3c969b2d4ad0d48b2195ce196b631a]
  - duplicate-binder follows the engine's clause-scoped variable identity
    through both ``let`` and ``let*``, including binders in sibling forms
    [tested: test_plain_let_duplicate_binders_are_reported_across_one_clause,
    test_plain_let_duplicates_inside_binding_values_are_reported,
    test_let_star_duplicate_binder_controls_keep_reporting,
    test_distinct_plain_let_binders_are_clean_and_keep_their_pair_answer;
    commit=43bf074ce97adb6bfe599ae20faa5f38ef524bd7]
  - a body variable is unbound when the head never bound it and no written
    position leaves it unevaluated, which the engine answers per form
    (`metta_form_unevaluated_variable_paths/3`): a `let` or `match` pattern
    binds its names, a defined function's `Atom` parameter may bind what it
    is handed, and a call's evaluated argument never does [tested:
    test_unbound_body_variables, test_let_bound_variables_are_not_flagged,
    test_a_variable_used_only_in_an_evaluated_position_is_reported,
    test_a_match_pattern_binds_its_fresh_variables,
    test_an_atom_typed_parameter_may_bind_the_variable_it_is_handed;
    commit=e492f2a5bb995b6c2b86bdeb90cb1d2f27282b07]
  - a declared slot contradicts a ground argument exactly when the engine's
    own admission refuses it (`metta_argument_admitted/3`), so a metatype
    slot and a user typing rule in the space decide there with nothing here
    to change [tested: test_a_metatype_slot_follows_the_engines_admission,
    test_a_user_typing_rule_reaches_the_type_mismatch_check; commit=e492f2a5bb995b6c2b86bdeb90cb1d2f27282b07]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from itertools import product
from typing import TYPE_CHECKING, Any, TypeGuard

import metta.doors as _doors
import metta.lint as _lint_module
from metta._atoms.factories import (
    Atom,
    Expression,
    Grounded,
    Symbol,
    Variable,
    _alpha_eq,
    _map_atoms,
    _variables,
)
from metta._catalog.meaning import EngineRegistry, head_meaning
from metta._compile.islands import _HostIsland
from metta._errors.errors import Remedy
from metta._spaces.intents import (
    LintInvocation,
    authority_for,
    detail_for,
    events_for,
    is_suppressed,
)
from metta.lint._model import Finding

if TYPE_CHECKING:
    import metta._faces.space as _space_face
else:
    import metta._faces.space as _space_face


def _is_arrow_head(name: str) -> bool:
    """Whether a signature head is an arrow, in either spelling.

    `->` is the implicit spelling; `-[det]->`, `-[semidet,pure]->` and
    `-[$e]->` are the explicit ones. Only the FRAME is matched. Which
    cardinalities and effect classes are legal belongs to
    `metta_arrow_type_shape/5` in engine/metta/types.pl, and copying that
    table here would be a second closed value set to keep in step with the
    first. The two directions of error are not symmetric: being too
    permissive lints a declaration the engine refuses anyway, while being
    too restrictive SILENTLY skips a valid one and leaves the arity,
    declared-function and type diagnostics reporting healthily on a
    declaration they never saw.
    """
    return name == "->" or (
        name.startswith("-[") and name.endswith("]->") and len(name) > len("-[]->")
    )

def _arrow_inputs(declaration: Atom) -> int | None:
    """Return the input count of an arrow declaration, either spelling."""
    if (
        isinstance(declaration, Expression)
        and len(declaration) >= 2
        and isinstance(head := declaration[0], Symbol)
        and _is_arrow_head(head.name)
    ):
        return len(declaration) - 2
    return None

def _arrow_head_name(declaration: Atom) -> str | None:
    """The head atom of an arrow-framed signature, or None if it is not one."""
    if (
        isinstance(declaration, Expression)
        and len(declaration) >= 2
        and isinstance(head := declaration[0], Symbol)
        and _is_arrow_head(head.name)
    ):
        return head.name
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

def _walk_atoms(atom: Atom):
    """Yield every atom iteratively, including non-symbol expression heads."""
    stack = [atom]
    while stack:
        current = stack.pop()
        yield current
        if isinstance(current, Expression):
            stack.extend(reversed(current.children))

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

def _first_letter_role_findings(atoms: list[Atom], equations: list[Expression]) -> list[Finding]:
    """Report data/function heads whose first alphabetic character has the wrong role."""
    authority = authority_for("first-letter-role-convention")
    findings: list[Finding] = []
    for equation in equations:
        name = _symbol_head(equation[1])
        if name is not None and name[:1].isupper():
            findings.append(
                Finding(
                    "first-letter-role-convention",
                    name,
                    "an equation gives a capitalized data head function behavior; "
                    "function and control heads start lowercase",
                    equation,
                    severity="warning",
                    payload={"authority": authority, "role": "function"},
                )
            )
    for atom in atoms:
        name = _symbol_head(atom)
        if name is None or name in ("=", ":") or not name[:1].islower():
            continue
        findings.append(
            Finding(
                "first-letter-role-convention",
                name,
                "a stored data head starts lowercase; data constructors start capitalized",
                atom,
                severity="warning",
                payload={"authority": authority, "role": "data"},
            )
        )
    return findings

def _claims_det(signature: Atom) -> bool:
    """Whether an arrow promises EXACTLY ONE answer.

    A plain `->` promises nothing about answer count, so a function under one
    is an ordinary relation and neither too few answers nor too many is a
    defect. `-[semidet]->` and `-[nondet]->` are the honest spellings for
    those, and are what the findings that read this recommend rather than
    second defects to report.
    """
    arrow = _arrow_head_name(signature) or ""
    return "det" in arrow and "semidet" not in arrow and "nondet" not in arrow

def _overlapping_det_findings(
    equations: list[Expression], declarations: list[Expression]
) -> list[Finding]:
    """Report a `det` claim two equations with the same head are guaranteed to break.

    `(: two (-[det]-> Number Number))` with `(= (two $x) $x)` and
    `(= (two $x) (+ $x 1))` answers 1 AND 2: two answers from a function
    declared to give exactly one. Neither existing overlap rule reaches it,
    and correctly so: the equations are not duplicates, since their bodies
    differ, and neither is a strict instance of the other, since the heads are
    variants. What makes this one wrong is the declaration.

    Alpha-equivalent HEADS, so the overlap is total and no argument can
    separate them: both equations are TRIED for every call. Whether both
    ANSWER is a question about the bodies, which this does not ask, so the
    finding is a hint rather than a proof. A guard makes it wrong:

        (= (guarded $x) $x)
        (= (guarded $x) (if (> $x 100) 999 (empty)))

    answers once for 1 and twice for 200, so the claim holds for some calls
    and breaks for others. Deciding which needs the body analysis the
    typechecker audit refused as interprocedural; reporting the overlap costs
    an alpha-key comparison.

    A PARTIAL overlap is not reported at all: `(= (f 1) 10)` beside
    `(= (f $x) $x)` does answer twice for `(f 1)`, and deciding it needs
    unification against every stored head.
    """
    authority = authority_for("det-equations-overlap")
    claims = {
        name.name
        for declaration in declarations
        if len(declaration) == 3
        and isinstance(name := declaration[1], Symbol)
        and _claims_det(declaration[2])
    }
    seen: dict[tuple[str, Any], Expression] = {}
    findings: list[Finding] = []
    for equation in equations:
        head_name = _symbol_head(equation[1])
        if head_name is None or head_name not in claims:
            continue
        key = (head_name, _alpha_key(equation[1]))
        first = seen.get(key)
        if first is None:
            seen[key] = equation
            continue
        findings.append(
            Finding(
                "det-equations-overlap",
                head_name,
                "this arrow claims det, so exactly one answer, and two "
                "equations share a head up to variable renaming, so both are "
                "tried for every call: the claim holds only while at most one "
                "body succeeds, which nothing checks. Merge them, separate "
                "their heads, or declare -[nondet]-> and mean it",
                equation,
                severity="hint",
                payload={"authority": authority},
            )
        )
    return findings

def _declared_type_members(declarations: list[Expression]) -> dict[str, set[Atom]]:
    """Enumerate finite constructors, retaining unrestricted ones by head.

    `(: Red Colour)` makes `Red` a member of `Colour`. An arrow-framed
    A constructor whose inputs are all Literal refinements has an enumerable
    domain. Other constructor signatures contribute their head, so a pattern
    covering any of their fields prevents a claim that the constructor has
    no answers. A parametric result has no plain finite type to check here.
    """
    members: dict[str, set[Atom]] = {}
    for declaration in declarations:
        if len(declaration) != 3 or not isinstance(subject := declaration[1], Symbol):
            continue
        kind = declaration[2]
        if isinstance(kind, Symbol):
            members.setdefault(kind.name, set()).add(subject)
            continue
        # A constructor is a member of the type it RETURNS:
        # `(: Circle (-> Number Shape))` makes Circle one of Shape's, beside
        # the nullary `(: Point Shape)` above. Without this the check sees
        # only enums and misses every algebraic type, which is the shape the
        # upstream exhaustiveness fixture is written in.
        if _arrow_inputs(kind) is None or len(kind) < 2:
            continue
        result = kind[len(kind) - 1]
        if isinstance(result, Symbol):
            inputs = list(kind.children[1:-1])
            cases = members.setdefault(result.name, set())
            if all(isinstance(item, Expression) and len(item) == 3
                   and _symbol_head(item) == "Annotated"
                   and _symbol_head(item[2]) == "Literal" for item in inputs):
                cases.update(Expression([subject, *arguments])
                             for arguments in product(*(item[2].children[1:] for item in inputs)))
            else:
                cases.add(subject)
    return members

def _uncovered_constructor_findings(
    equations: list[Expression], declarations: list[Expression]
) -> list[Finding]:
    """Report a `det` claim a finite declared type's uncovered member breaks.

    A plain `->` promises nothing about how many answers come back, so a
    partial function is ordinary MeTTa and gets no finding here. `-[det]->`
    promises EXACTLY ONE, and a constructor no equation covers answers zero, so
    the declaration and the equations contradict each other. That is the
    finding: a broken promise, not partiality.

    The remedy is a choice and the message names both halves of it, following
    the upstream typechecker's own fixture for this case: cover the missing
    member, or say `-[semidet]->` and mean it.

    Two limits, both deliberate. This is NOT general exhaustiveness, which
    needs totality and is undecidable; it is the decidable corner where the
    members were declared one by one and are therefore enumerable. And the
    verdict is a LOWER BOUND on incompleteness rather than a totality
    guarantee, because a constructor declared later, or in another file not
    yet loaded, cannot be seen from the space as it stands; `lint()` reports
    what is there when it is called.

    A variable in that position covers the whole type. Finite constructor
    terms also retain repeated-variable constraints in their patterns.
    """
    authority = authority_for("uncovered-constructor")
    members = _declared_type_members(declarations)
    findings: list[Finding] = []
    for declaration in declarations:
        if len(declaration) != 3 or not isinstance(name := declaration[1], Symbol):
            continue
        signature = declaration[2]
        if _arrow_inputs(signature) is None:
            continue
        if not _claims_det(signature):
            continue
        rows = [e for e in equations if _symbol_head(e[1]) == name.name]
        if not rows:
            continue  # declared-but-undefined is a different finding
        for position in range(1, len(signature) - 1):
            kind = signature[position]
            if not isinstance(kind, Symbol):
                continue
            declared = members.get(kind.name)
            if not declared:
                continue
            arguments = [head[position] for equation in rows
                         if isinstance(head := equation[1], Expression) and len(head) > position]
            missing = {
                member for member in declared
                if not any(_instantiates(argument, member) or (
                    isinstance(member, Symbol) and _symbol_head(argument) == member.name
                ) for argument in arguments)
            }
            if not arguments or not missing:
                continue
            declared_names = sorted(map(str, declared))
            missing_names = sorted(map(str, missing))
            findings.append(
                Finding(
                    "uncovered-constructor",
                    name.name,
                    f"this arrow claims det, so exactly one answer, but argument "
                    f"{position} is declared {kind.name}, whose members are "
                    f"{declared_names}, and no equation covers {missing_names}: "
                    f"a call with one answers zero. Cover it, or declare "
                    f"-[semidet]-> and mean it",
                    declaration,
                    severity="warning",
                    payload={"authority": authority, "missing": missing_names},
                )
            )
    return findings

def _builtin_shadow_findings(
    equations: list[Expression], registry: EngineRegistry
) -> list[Finding]:
    """Report local equations that redefine a head the engine ships.

    The dangerous cases already refuse by name: `metta_engine_goal_redefinition`
    for a head the engine compiles into function bodies, and
    `metta_builtin_redefinition` for a protected core predicate. What was
    silent is the case the engine PERMITS, where the equation compiles into
    this space's own module and shadows the builtin there, leaving the
    engine's and every other space's alone. `!(max-atom (1 5 3))` answers 5
    before such an equation and `shadowed` after, with nothing said.

    That is a lawful, space-scoped capability, so this is a warning about
    intent rather than an error: the same weight `interpreter-equation-shadow`
    carries for the translator's heads, of which this is the sibling for the
    engine's.
    """
    authority = authority_for("builtin-equation-shadow")
    findings: list[Finding] = []
    for equation in equations:
        name = _symbol_head(equation[1])
        if name is None or registry.is_special_form(name):
            continue
        if not registry.is_builtin(name):
            continue
        findings.append(
            Finding(
                "builtin-equation-shadow",
                name,
                "this equation shadows a builtin the engine ships; the write is "
                "lawful and scoped to this space, but calls here stop reaching "
                "the engine's version",
                equation,
                severity="warning",
                payload={"authority": authority},
            )
        )
    return findings

def _interpreter_shadow_findings(
    equations: list[Expression], registry: EngineRegistry
) -> list[Finding]:
    """Report local equations on translator-owned interpreter heads."""
    authority = authority_for("interpreter-equation-shadow")
    findings: list[Finding] = []
    for equation in equations:
        name = _symbol_head(equation[1])
        if name is None or not registry.is_special_form(name):
            continue
        findings.append(
            Finding(
                "interpreter-equation-shadow",
                name,
                "this writable equation shadows a head the interpreter translates; "
                "the write is lawful but changes evaluation in this space",
                equation,
                severity="warning",
                payload={"authority": authority},
            )
        )
    return findings

def _operation_in_higher_order_call(
    call: Expression, registry: EngineRegistry
) -> tuple[str, str] | None:
    """Find the operation invoked per element by one engine iterator form."""
    head = _symbol_head(call)
    candidate: Atom | None = None
    body: Atom | None = None
    # policy-inventory-exempt: mechanism-internal; reason=map-atom and filter-atom are the two higher-order engine iterator heads whose callback position has the same crossing shape; evidence=extensions/python/metta/lint/_analysis.py:_operation_in_higher_order_call
    if head in {"map-atom", "filter-atom"}:
        if len(call) == 3:
            candidate = call[2]
        elif len(call) == 4:
            body = call[3]
    elif head == "foldl-atom":
        if len(call) == 4:
            candidate = call[3]
        elif len(call) == 6:
            body = call[5]
    names: list[str] = []
    if isinstance(candidate, Symbol):
        names.append(candidate.name)
    if body is not None:
        names.extend(
            nested[0].name
            for nested in _walk_heads(body)
            if isinstance(nested[0], Symbol)
        )
    for name in names:
        effect = registry.operation_effect(name)
        if effect is not None:
            return name, effect
    return None

def _hot_higher_order_crossing_findings(
    equations: list[Expression], registry: EngineRegistry
) -> list[Finding]:
    """Report map/filter/fold forms that invoke Python once per item."""
    authority = authority_for("operation-crossing-in-loop")
    findings: list[Finding] = []
    seen: set[tuple[str, Expression]] = set()
    for equation in equations:
        for call in _walk_heads(equation[2]):
            operation = _operation_in_higher_order_call(call, registry)
            if operation is None:
                continue
            name, effect = operation
            key = name, equation
            if key in seen:
                continue
            seen.add(key)
            findings.append(
                Finding(
                    "operation-crossing-in-loop",
                    name,
                    detail_for("operation-crossing-in-loop"),
                    equation,
                    severity="warning",
                    payload={"authority": authority, "effect": effect},
                )
            )
    return findings

def _event_findings(space: Any) -> list[Finding]:
    """Turn retained source evidence into the public Finding shape."""
    findings: list[Finding] = []
    for event in events_for(space):
        payload: dict[str, Any] = {
            "file": event.path,
            "line": event.line,
            "column": event.column,
            "authority": event.authority,
        }
        if event.effect is not None:
            payload["effect"] = event.effect
        findings.append(
            Finding(
                event.kind,
                event.subject,
                detail_for(event.kind),
                event.atom or event.fact(str(space.name)),
                severity="warning",
                payload=payload,
            )
        )
    return findings

def _unsuppressed(
    space: Any, findings: list[Finding], invocation: LintInvocation | None
) -> list[Finding]:
    """Apply exact named intents after every analysis has had the same view."""
    kept: list[Finding] = []
    for finding in findings:
        payload = finding.payload if isinstance(finding.payload, Mapping) else {}
        path = payload.get("file")
        line = payload.get("line")
        if not is_suppressed(
            space,
            finding.kind,
            path=path if isinstance(path, str) else None,
            line=line if isinstance(line, int) else None,
            invocation=invocation,
        ):
            kept.append(finding)
    return kept

def _prefer_source_evidence(findings: list[Finding]) -> list[Finding]:
    """Drop an atom-only duplicate when the same finding has a source event."""
    sourced = {
        (finding.kind, finding.subject, finding.atom)
        for finding in findings
        if isinstance(finding.payload, Mapping)
        and isinstance(finding.payload.get("file"), str)
    }
    return [
        finding
        for finding in findings
        if not (
            (finding.kind, finding.subject, finding.atom) in sourced
            and not (
                isinstance(finding.payload, Mapping)
                and isinstance(finding.payload.get("file"), str)
            )
        )
    ]

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

def _call_typing_names(
    declarations: list[Expression], registry: EngineRegistry
) -> set[str]:
    """The names whose declaration the ENGINE honours as a call type.

    Narrower than `_arrowed_names`, and deliberately so. The frame is what an
    author's INTENT looks like, which is the right question for arity and
    declared-function diagnostics. Whether a call is actually checked is the
    engine's answer, and the two disagree today for `-[det]->`.
    """
    names: set[str] = set()
    for declaration in declarations:
        name_atom = declaration[1]
        if not isinstance(name_atom, Symbol):
            continue
        head = _arrow_head_name(declaration[2])
        if head is not None and registry.types_a_call(head):
            names.add(name_atom.name)
    return names

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
    #A declaration can fail to type a call two ways, and they read differently.
    #Naming an ordinary type is the plain case. Writing an arrow SPELLING the
    #engine parses but does not honour looks correct and is not, so the message
    #says which of the two happened rather than calling an arrow "not an arrow".
    if _arrow_head_name(signature) is not None:
        reason = (
            f"declared {signature}; the engine does not read that arrow "
            f"spelling as a call type, so every ({name} ...) compiles "
            f"unchecked and answers IncorrectNumberOfArguments"
        )
    else:
        reason = (
            f"declared {signature}, which is not an arrow, so it types the "
            f"symbol and not a call: every ({name} ...) compiles unchecked"
        )
    return Finding(
        "declaration-types-the-symbol",
        name,
        reason,
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
    #The names the ENGINE honours, not the ones carrying an arrow frame. A
    #declaration whose spelling the engine does not read leaves the call
    #unchecked exactly as a non-arrow declaration does, and this rule is the
    #only place that difference is caught: the loader judges a definition's own
    #forms, so a declaration loaded apart from its definition never meets it.
    honoured = _call_typing_names(declarations, registry)
    for declaration in declarations:
        name_atom, signature = declaration[1], declaration[2]
        if not isinstance(name_atom, Symbol):
            continue
        name = name_atom.name
        inputs = _arrow_inputs(signature)
        head = _arrow_head_name(signature)
        if inputs is None or (head is not None and not registry.types_a_call(head)):
            finding = _types_the_symbol(
                space, declaration, name, honoured, defined_here
            )
            if finding:
                findings.append(finding)
            if inputs is None:
                continue
            #An arrow the engine will not honour still STATES an arity, and a
            #disagreement with it is a second, independent fact. Reporting only
            #the spelling would surface the arity error on the next pass, after
            #the author had already fixed one thing.
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
                    remedy=Remedy(
                        "remove the duplicate equation",
                        "quickfix",
                        "machine",
                        replace=(equation, None),
                    ),
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

def _at(atom: Atom, path: tuple[int, ...]) -> Atom:
    """The atom at one child path, the head counting as child 0."""
    for index in path:
        atom = atom.children[index]
    return atom

def _unbound_findings(
    equation: Expression, head: Atom, body: Atom, registry: EngineRegistry, space: str
) -> list[Finding]:
    """A body variable the head never bound and no written position leaves
    unevaluated. The engine says where each form leaves a variable
    unevaluated (a pattern, a binder, a quoted atom, a write payload), so a
    `let` or `match` pattern binds its names, a defined function's `Atom`
    parameter may bind the variable handed to it, and a call's evaluated
    argument never does.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    head_vars = set(_variables(head))
    unevaluated: set[str] = set()
    for call in _walk_heads(body):
        for path in registry.unevaluated_paths(space, call):
            unevaluated.update(_variables(_at(call, path)))
    loose = sorted(
        name
        for name in set(_variables(body))
        if name not in head_vars and name not in unevaluated and name != "_"
    )
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

def _call_findings(
    equation: Expression,
    body: Atom,
    fact_heads: set[str],
    registry: EngineRegistry,
) -> list[Finding]:
    """Diagnose every call in one body from the shared head verdict.

    A bare symbol with no arguments is data by construction and is never
    asked about; everything else goes to head_meaning, which is the same
    question why() asks, answered once.
    """
    findings: list[Finding] = []
    for call in _walk_heads(body):
        name = call[0].name
        arguments = len(call) - 1
        if arguments == 0:
            continue
        meaning = head_meaning(name, arguments, registry, fact_heads)
        if meaning.wrong_arity:
            findings.append(
                Finding(
                    "arity-mismatch",
                    name,
                    f"called with {arguments} argument(s) but defined for "
                    f"{sorted(meaning.arities)}",
                    equation,
                    severity="error",
                )
            )
        elif not meaning.carried:
            findings.append(
                Finding(
                    "possibly-undefined-reference",
                    name,
                    "no function, special form, builtin, or stored fact carries "
                    "this head; a call to it stays unreduced (heuristic: it may "
                    "be data on purpose)",
                    equation,
                    severity="hint",
                    suggestion=meaning.suggestion,
                    remedy=_rename_remedy(equation, call, meaning.suggestion),
                )
            )
    return findings

def _equation_findings(
    equations: list[Expression], fact_heads: set[str], registry: EngineRegistry, space: str
) -> list[Finding]:
    findings: list[Finding] = []
    for equation in equations:
        head, body = equation[1], equation[2]
        findings.extend(_unbound_findings(equation, head, body, registry, space))
        findings.extend(_call_findings(equation, body, fact_heads, registry))
    return findings

def _host_island_findings(equations: list[Expression]) -> list[Finding]:
    """Report every explicit host crossing retained in repeated loop code."""
    findings: list[Finding] = []
    for equation in equations:
        for atom in _walk_atoms(equation[2]):
            if not isinstance(atom, Grounded):
                continue
            island = getattr(atom, "value", None)
            if not isinstance(island, _HostIsland) or not island.in_loop:
                continue
            findings.append(
                Finding(
                    "host-island-in-loop",
                    island.source,
                    "crosses from the engine into Python on every loop iteration; "
                    "move invariant host work before the loop, batch the crossing, "
                    "or register a named @metta.op when repetition is intentional",
                    equation,
                    severity="warning",
                    payload={"file": island.path, "line": island.line},
                )
            )
    return findings

def _is_truth(atom: Atom, value: bool) -> bool:  # noqa: FBT001  -- the boolean is established API data and positional compatibility is part of the call shape
    """Whether the atom is the boolean literal, under either spelling the
    engine stores: True and true are one term there, arriving here as a
    ground bool or as the symbol.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    if isinstance(atom, Grounded):
        return getattr(atom, "value", None) is value
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

def _binder_simplified(
    inner: Expression, seen: set[str] | None = None
) -> tuple[str, str, Atom | None] | None:
    head = _symbol_head(inner)
    if head == "let":
        if len(inner) != 4:
            return None
        # Annotated because the other branch below builds a variable-length
        # tuple, and a bare 1-tuple here infers the narrower fixed shape.
        patterns: tuple[Atom, ...] = (inner[1],)
    elif head == "let*":
        if len(inner) < 2 or not isinstance(inner[1], Expression):
            return None
        patterns = tuple(
            binding.children[0]
            for binding in inner[1].children
            if isinstance(binding, Expression) and binding.children
        )
    else:
        return None

    seen = set() if seen is None else seen
    duplicate = None
    for pattern in patterns:
        for name in _variables(pattern):
            if name in seen and duplicate is None:
                duplicate = name
            seen.add(name)
    if duplicate is None:
        return None
    return (
        "duplicate-binder",
        f"${duplicate} is bound twice in one equation; let and let* use "
        f"clause-scoped variables, so the second binding unifies rather "
        f"than shadows. If an equality constraint is meant, say == instead",
        None,
    )

_SIMPLIFIERS = {
    "if": _if_simplified,
    "superpose": _superpose_simplified,
    "let": _binder_simplified,
    "let*": _binder_simplified,
}

def _simplified(
    inner: Expression, seen_binders: set[str] | None = None
) -> tuple[str, str, Atom | None] | None:
    """One nested expression's simplification, or None: (kind, detail,
    replacement), replacement None when the finding has no rewrite.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    simplifier = _SIMPLIFIERS.get(_symbol_head(inner) or "")
    if simplifier is None:
        return None
    if simplifier is _binder_simplified:
        return _binder_simplified(inner, seen_binders)
    return simplifier(inner)

def _replaced(stored: Expression, target: Atom, replacement: Atom) -> Atom:
    """The stored atom with exactly this occurrence rewritten, by identity."""
    return _map_atoms(stored, lambda a: replacement if a is target else a)

def _rename_remedy(
    equation: Expression, call: Expression, suggestion: str | None
) -> Remedy | None:
    """The near-miss rename as an edit, or None when nothing is near enough.

    LSP's own shape for a "did you mean" hint: the diagnostic offers the
    corrected spelling as a quickfix. `maybe` rather than `machine` because
    the head may be data on purpose, which is why this finding is a hint.
    """
    if suggestion is None:
        return None
    corrected = Expression([Symbol(suggestion), *call.children[1:]])
    return Remedy(
        f"rename {call.children[0]} to {suggestion}",
        "quickfix",
        "maybe",
        replace=(equation, _replaced(equation, call, corrected)),
    )

def _simplification_findings(equations: list[Expression]) -> list[Finding]:
    findings: list[Finding] = []
    for equation in equations:
        seen_binders: set[str] = set()
        for call in _walk_heads(equation[2]):
            found = _simplified(call, seen_binders)
            if found is None:
                continue
            kind, detail, replacement = found
            autofix = (
                None if replacement is None else _replaced(equation, call, replacement)
            )
            findings.append(
                Finding(
                    kind,
                    str(call),
                    detail,
                    equation,
                    severity="information",
                    payload={"expression": call, "replacement": replacement},
                    autofix=autofix,
                    remedy=(
                        None
                        if autofix is None
                        else Remedy(
                            f"rewrite {call} as {replacement}",
                            "quickfix",
                            "machine",
                            replace=(equation, autofix),
                        )
                    ),
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

def _declared_arrows(declarations: list[Expression]) -> dict[str, tuple[Atom, ...]]:
    """Each declared name's arrow input slots, first declaration winning."""
    arrows: dict[str, tuple[Atom, ...]] = {}
    for declaration in declarations:
        name_atom, signature = declaration[1], declaration[2]
        if (
            isinstance(name_atom, Symbol)
            and isinstance(signature, Expression)
            and (head := _symbol_head(signature)) is not None
            and _is_arrow_head(head)
        ):
            arrows.setdefault(name_atom.name, signature.children[1:-1])
    return arrows

def _slot_mismatch(
    slot: Atom, argument: Atom, registry: EngineRegistry, space: str
) -> tuple[str, str] | None:
    """(declared, actual) when the engine's own admission refuses one ground
    argument for one declared slot, else None. A parametric slot and a
    non-ground argument pass, keeping the check conservative; a nested call
    is the engine's own hoisted check's. Admission is the engine's answer
    (`metta_argument_admitted/3`), so `Atom`, `%Undefined%`, a metatype and
    a user typing rule all decide there rather than in a list here.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    if not isinstance(slot, Symbol) or isinstance(argument, (Variable, Expression)):
        return None
    if registry.admits(space, argument, slot.name):
        return None
    return slot.name, registry.type_of(argument)

def _type_findings(
    equations: list[Expression],
    declarations: list[Expression],
    registry: EngineRegistry,
    space: str,
) -> list[Finding]:
    """A ground argument the engine would refuse for the declared slot.

    Admission is one cached engine question per distinct (argument, slot)
    pair, and only concrete Symbol-against-Symbol disagreements report.
    """
    arrows = _declared_arrows(declarations)
    findings: list[Finding] = []
    for equation in equations:
        for call in _walk_heads(equation[2]):
            slots = arrows.get(call[0].name)
            if slots is None or len(call) - 1 != len(slots):
                continue
            for slot, argument in zip(slots, call.children[1:], strict=True):
                mismatch = _slot_mismatch(slot, argument, registry, space)
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

def analyze(
    space: Any,
    atoms: list[Atom],
    registry: EngineRegistry,
    invocation: LintInvocation | None = None,
) -> list[Finding]:
    """Analyze one enumerated space against one registry snapshot."""
    equations, declarations, fact_heads, defined_here = _index_atoms(atoms)
    findings = [
        *(
            []
            if str(space.name) == "&metta"
            else _first_letter_role_findings(atoms, equations)
        ),
        *_interpreter_shadow_findings(equations, registry),
        *_builtin_shadow_findings(equations, registry),
        *_uncovered_constructor_findings(equations, declarations),
        *_overlapping_det_findings(equations, declarations),
        *_declaration_findings(space, declarations, defined_here, registry),
        *_duplicate_findings(equations),
        *_subsumed_findings(equations),
        *_tabling_findings(equations, registry),
        *_hot_higher_order_crossing_findings(equations, registry),
        *_host_island_findings(equations),
        *_equation_findings(equations, fact_heads, registry, str(space.name)),
        *_simplification_findings(equations),
        *_inconsistent_arity_findings(equations, declarations),
        *_type_findings(equations, declarations, registry, str(space.name)),
        *_event_findings(space),
    ]
    return _unsuppressed(space, _prefer_source_evidence(findings), invocation)

@_doors.door(
    kind=_doors.Kind.introspection,
    answers=_doors.AnswersAs.sequence,
    effect=_doors.EffectClass.readOnlyLookup,
    determinism=_doors.Determinism.det,
    tiers=(_doors.Tier.sync, _doors.Tier.async_),
    evidence=('extensions/python/tests/ch14_seeing_your_program/test_lint.py::test_a_canonicalised_read_of_a_tabled_function_is_not_a_finding', 'extensions/python/tests/ch14_seeing_your_program/test_lint.py::test_a_declaration_for_a_name_with_no_equations_is_data', 'extensions/python/tests/ch14_seeing_your_program/test_lint.py::test_a_declaration_that_cannot_type_its_function'),
)
def lint(space: _space_face.Space) -> list[Finding]:
    """Diagnose this space for the silently-wrong class: declared
    types nothing defines, arity mismatches, unbound body variables,
    duplicate equations, and references no function or fact carries.
    Answers metta.lint.Finding records, empty when nothing looks
    wrong.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    return _lint_module.lint(space)
