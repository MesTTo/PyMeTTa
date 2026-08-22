"""Purpose: turn "how much of MeTTa can be written in pure Python today" into a
measured number with a derived backlog. Each example under `examples/` may gain
a Python TWIN under `bindings/python/tests/twins/`, mirroring its path; this
lane runs the example and its twin, requires their answers to agree under
ALPHA-EQUIVALENCE, requires the twin to have used no MeTTa source text, and
prices the twin against the original on the engine's own inference counter.
Whatever a twin cannot say is a RESIDUE entry naming the missing spelling and
the plan row it lands on, so the backlog derives itself instead of being
believed.

Assumes:
  - discovery comes from example_parity.corpus/1 and nowhere else, so a twin's
    path is DERIVED from its example's path rather than walked separately
    [tested: test_the_twin_set_is_derived_from_the_one_corpus]
  - inferences are deterministic across processes, so one sample decides a
    budget [measured 2026-08-22: examples/basics/factorial.metta answered 4748
    inferences on three fresh interpreters, 0.0000% spread; commit=c7191d87d9cbfce2870e586057168ec9103845ca]
Guarantees:
  - a twin that reaches the engine through MeTTa source text is REFUSED, both
    the four source doors and any string that is not a name or val()-marked
    data [tested: test_the_source_scan_catches_a_planted_string]
  - answers are compared up to consistent renaming of variables, never by the
    spelling of a variable name [tested: test_a_renamed_variable_still_agrees,
    test_a_wrong_answer_is_still_refused]
  - a twin's definitions are visible to `match` where the original's are, so a
    Python-authored definition cannot pass by hiding in Python-side state
    [tested: test_a_hidden_definition_is_a_finding]
  - every form a twin declines carries a residue entry, so a skip cannot be
    silent [tested: test_an_undeclared_skip_is_a_finding]
Decides:
  - twins live under `bindings/python/tests/twins/<folder>/<name>.py`, the
    example's own relative path with a Python suffix. The mapping is a pure
    path transform over the corpus, which is why there is no second walker;
    and `tests/**` is already inside ruff's and codespell's reach, so the
    twins are linted and spell-checked without a runner learning about them
  - process isolation per twin, matching example_parity's own reading: it is
    affordable and it cannot leak a definition from one twin into the next
  - the budget lives in the twin as BUDGET, not in a side table, so a twin
    file is the whole of what it claims and the number is reviewed in the
    same diff as the code it prices
Fails when:
  - an example's answers are nondeterministically ordered, which the same
    comparison in example_parity already documents: groups are compared in
    order and a genuinely unordered answer set would read as a difference
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""  # noqa: D205  -- the lane's contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import argparse
import ast
import keyword
import re
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

import example_parity as parity

REPO = parity.REPO
TWINS = REPO / "bindings" / "python" / "tests" / "twins"
RESIDUE = TWINS / "residue.json"

#: One inference count, and the heads the space answers a `(= $head $body)`
#: match with, on their own marker lines beside the answer groups.
COST = "P14C-COST "
HEADS = "P14C-HEADS "

#: What a twin yields for a form it cannot say in Python. It is not a group,
#: so it can never collide with one: a group is always parenthesised.
DECLINED = "-"

#: How much more than the `.metta` original a twin may cost. PINNED FROM THE
#: FIRST MEASUREMENTS: over the eighteen basics/ examples the twins measured
#: between 0.2277x and 1.0887x of their originals, min-of-3, seventeen of the
#: eighteen at or under 1.00x. 10% is the one observed overrun rounded up to
#: the next whole point, so the band admits what was measured and nothing
#: looser; the overrun itself is priced with its mechanism in
#: ai-report-p14-coverage.md rather than hidden inside the band
#: [measured 2026-08-22: `twin_coverage.py --measure`, ai-tmp/p14c-measure.log;
#: commit=c7191d87d9cbfce2870e586057168ec9103845ca].
BAND_PERCENT = 10.0

#: The tree's own counter allowance, so a budget here reads the way a
#: benchmark baseline reads [source: bindings/python/petta/benchmarking.py
#: _COUNTER_TOLERANCE; commit=c7191d87d9cbfce2870e586057168ec9103845ca].
TOLERANCE = 4

#: The four doors that take MeTTa source text. A twin may not use any of them:
#: that is the whole of "zero s-expression strings".
SOURCE_DOORS = frozenset({"run", "load", "parse", "save"})

#: Calls whose string argument is a NAME or a marked datum rather than a
#: program: sym/var name an atom, fn names an engine function, space and
#: new_space name a space, and val carries a Python value whole.
NAMING_CALLS = frozenset({"sym", "var", "val", "fn", "space", "new_space"})

#: The two factories whose subscript is an atom's name.
NAMING_NAMESPACES = frozenset({"S", "V"})

#: Module-level constants a twin declares ABOUT itself rather than as
#: program text: the inference pin, and the reason it sits below the top
#: rung. Both are read from source the way the lane reads BUDGET.
DECLARATION_NAMES = frozenset({"BUDGET", "RUNG"})


def twin_for(example: Path, root: Path = REPO) -> Path:
    """The twin that would cover this example. A pure path transform, so the
    corpus stays the single definition of what exists.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    return TWINS / example.relative_to(root / "examples").with_suffix(".py")


def example_for(twin: Path, root: Path = REPO) -> Path:
    """The example a twin covers, the transform above run backwards."""
    return root / "examples" / twin.relative_to(TWINS).with_suffix(".metta")


def written(root: Path = REPO) -> list[Path]:
    """Every example that has a twin, in the corpus's own order."""
    return [path for path in parity.corpus(root) if twin_for(path, root).is_file()]


def orphans(root: Path = REPO) -> list[Path]:
    """Twins covering nothing the corpus discovers: a renamed or deleted
    example leaves one behind, and a twin nothing runs proves nothing.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    known = {twin_for(path, root) for path in parity.corpus(root)}
    return sorted(path for path in TWINS.rglob("*.py") if path not in known)


# ------------------------------------------------------------- source discipline


def _callee(node: ast.Call) -> str | None:
    """The plain name a call reaches, receiver or not: both `m.run(...)` and
    a bare `run(...)` answer "run".
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    if isinstance(node.func, ast.Name):
        return node.func.id
    return None


def _defines(node: ast.FunctionDef) -> bool:
    """Whether a function is compiled into equations. Its body is Python read
    as SYNTAX, so a string constant inside it is a MeTTa string literal in an
    equation, the way `(= (math-string) "s")` writes one, and not source
    text. The source doors are still refused there, because a door is a call
    and the call rule does not care where the call sits.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    for decorator in node.decorator_list:
        reached = decorator.func if isinstance(decorator, ast.Call) else decorator
        name = reached.attr if isinstance(reached, ast.Attribute) else getattr(reached, "id", None)
        if name == "define":
            return True
    return False


def _named_strings(tree: ast.Module) -> set[int]:
    """The string constants that are names, marked data, or documentation.

    Identity rather than value, so `val("(f a)")` in one place does not
    excuse a bare `"(f a)"` in another.
    """
    permitted: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef)):
            head = node.body[0] if node.body else None
            if isinstance(head, ast.Expr) and isinstance(head.value, ast.Constant):
                permitted.add(id(head.value))
            # A declared rung's REASON is documentation, exactly like the
            # docstring above it, so the source scan must not read it as a
            # program. Without this the two checks contradict each other and
            # declaring a rung turns the lane red, which makes the ladder's
            # own escape unusable [found 2026-08-22 by two twin agents at once].
            permitted.update(
                id(statement.value)
                for statement in node.body
                if isinstance(statement, ast.Assign)
                and isinstance(statement.value, ast.Constant)
                and any(
                    isinstance(target, ast.Name) and target.id in DECLARATION_NAMES
                    for target in statement.targets
                )
            )
            if isinstance(node, ast.FunctionDef) and _defines(node):
                permitted.update(
                    id(inner)
                    for inner in ast.walk(node)
                    if isinstance(inner, ast.Constant) and isinstance(inner.value, str)
                )
        elif isinstance(node, ast.Subscript):
            named = isinstance(node.value, ast.Name) and node.value.id in NAMING_NAMESPACES
            if named:
                permitted.add(id(node.slice))
        elif isinstance(node, ast.Call):
            if _callee(node) in NAMING_CALLS:
                permitted.update(id(argument) for argument in node.args)
            permitted.update(
                id(keyword.value) for keyword in node.keywords if keyword.arg == "name"
            )
    return permitted


#: Heads Python's own syntax already builds, so writing them as a call or
#: through expr() spells with a function what the language spells with a
#: character. The lowering table in petta._operator_lowerings is the
#: authority for which these are; this is the subset a twin can reach.
#: A line-level rung declaration, in the shape of the tree's noqa grammar.
RUNG_LINE = re.compile(r"#\s*rung:\s*\S")


OPERATOR_HEADS = frozenset({
    "+", "-", "*", "/", "//", "%", "**", "==", "!=", "<", ">", "<=", ">=",
    "and", "or", "not",
})


def _rung_reason(tree: ast.Module) -> str | None:
    """The twin's own declaration that it deliberately sits below the top
    rung, as `RUNG = "<reason>"`. A drop with a stated reason is
    documentation, which is why the ladder keeps every rung; a silent drop
    is the defect this check exists for.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    for node in tree.body:
        targets = node.targets if isinstance(node, ast.Assign) else []
        for target in targets:
            if isinstance(target, ast.Name) and target.id == "RUNG":
                value = node.value
                if isinstance(value, ast.Constant) and isinstance(value.value, str):
                    return value.value.strip() or None
    return None


def _subscripted_name(node: ast.Subscript) -> str | None:
    """The name a `S["foo"]` or `V["x"]` subscript spells, when that name is
    an ordinary Python identifier and attribute access would have reached it.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    if not (isinstance(node.value, ast.Name) and node.value.id in NAMING_NAMESPACES):
        return None
    key = node.slice
    if not (isinstance(key, ast.Constant) and isinstance(key.value, str)):
        return None
    name = key.value
    return name if name.isidentifier() and not keyword.iskeyword(name) else None


def _head_symbol(node: ast.expr) -> str | None:
    """The MeTTa head a term-building expression is rooted at, whether it was
    written `S.f`, `S["+"]`, or the first argument of `expr(...)`.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
        return node.attr if node.value.id in NAMING_NAMESPACES else None
    if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name):
        key = node.slice
        if node.value.id in NAMING_NAMESPACES and isinstance(key, ast.Constant):
            return key.value if isinstance(key.value, str) else None
    return None


def idiom(twin: Path) -> list[str]:
    """Where a twin spells in library calls what Python's own syntax spells.

    A twin avoiding MeTTa source text can still be MeTTa source text with
    Python punctuation, which is the failure this catches: `S["merge"]` where
    `S.merge` reads, `expr(S["="], a, b)` where `S["="](a, b)` reads, and
    `expr(S["+"], a, b)` where `a + b` already builds that term. The design
    authority is ai-python-first-revamp-discussion.md, sections 9c and 9k.
    A twin that declares `RUNG = "<reason>"` is exempt, because a drop with a
    stated reason is what the ladder is for.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    tree = _parse(twin)
    if tree is None or _rung_reason(tree) is not None:
        return []
    # A line may state its own reason, for a twin that is idiomatic
    # everywhere else: `# rung: <reason>` reads like the noqa grammar the
    # rest of the tree uses, and keeps the exemption next to what it excuses.
    excused = {
        number
        for number, line in enumerate(twin.read_text(encoding="utf-8").splitlines(), 1)
        if RUNG_LINE.search(line)
    }
    # The operator rule below only holds where an operator would BUILD the
    # term, which is inside a compiled body. Outside one `val(5) + 5` computes
    # 10 and `S.x == 1` is Python's own structural equality, so naming the head
    # is the deliberate spelling [found 2026-08-22: 33 findings in
    # twins/libraries, every one of this shape and none of them a defect].
    compiled = {
        id(inner)
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and _defines(node)
        for inner in ast.walk(node)
    }
    findings: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript):
            name = _subscripted_name(node)
            if name is not None:
                namespace = node.value.id
                findings.append(
                    (node.lineno, f'{namespace}["{name}"] is {namespace}.{name}')
                )
        elif isinstance(node, ast.Call):
            head = _head_symbol(node.args[0]) if _callee(node) == "expr" and node.args else None
            if head is not None:
                findings.append(
                    (node.lineno, f"expr(...) builds what calling the head builds")
                )
            called = _head_symbol(node.func)
            operator = called if called in OPERATOR_HEADS else head
            # At the operator's OWN arity only: `S["+"](1)` is a partial
            # application, which Python has no operator spelling for.
            arity = len(node.args) - (1 if head is not None else 0)
            if (
                operator in OPERATOR_HEADS
                and id(node) in compiled
                and arity == (1 if operator == "not" else 2)
            ):
                findings.append(
                    (node.lineno, f"the head {operator!r} is what a Python operator builds")
                )
    return [
        f"line {line}: {what}"
        for line, what in sorted(set(findings))
        if line not in excused
    ]


def _parse(twin: Path) -> ast.Module | None:
    """The twin as syntax, or nothing when it does not parse. A twin that
    does not parse is a finding for this lane to REPORT, not a traceback out
    of it: the lane's job is to say what is wrong with a twin.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    try:
        return ast.parse(twin.read_text(encoding="utf-8"), filename=str(twin))
    except SyntaxError:
        return None


def scan(twin: Path) -> list[str]:
    """What a twin says that is MeTTa source text rather than Python.

    Read as syntax, not as text: a door is a CALL and a program is a string
    CONSTANT in a position that is neither a name nor `val()`-marked data, so
    a mention inside a comment or a docstring is not a finding and a door
    reached through a receiver is.
    """
    tree = _parse(twin)
    if tree is None:
        return ["does not parse as Python, so nothing about it can be read"]
    permitted = _named_strings(tree)
    findings: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and _callee(node) in SOURCE_DOORS
            # `S.parse(text)` BUILDS the term `(parse text)`; only a real call
            # takes MeTTa source. Without this a twin cannot name a head that
            # shares a door's name at all, because the idiom check refuses the
            # subscripted spelling too [found 2026-08-22 by the functions
            # agent, which had to fall back to sym("parse")].
            and _head_symbol(node.func) is None
        ):
            findings.append(
                (node.lineno, f"calls {_callee(node)}(), which takes MeTTa source")
            )
        elif (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and id(node) not in permitted
        ):
            findings.append(
                (
                    node.lineno,
                    f"the string {node.value!r} is neither a name nor val() data",
                )
            )
    return [f"line {line}: {what}" for line, what in sorted(findings)]


# ---------------------------------------------------------------------- running


@dataclass(frozen=True, slots=True)
class Run:
    """What one side made of one example: the answer groups example_parity
    already reads, the inferences the engine spent, and the heads a
    `(= $head $body)` match answers.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

    outcome: parity.Outcome
    cost: int | None
    heads: tuple[str, ...]


_PREAMBLE = (
    "import sys; sys.path.insert(0, 'bindings/python')\n"
    "from petta import Expr, MeTTa, S, V\n"
    "def _key(head):\n"
    "    if isinstance(head, Expr) and head.children:\n"
    "        return f'{head.children[0]}/{len(head.children) - 1}'\n"
    "    return f'{head}/0'\n"
    "m = MeTTa(petta_path='.')\n"
)

_EPILOGUE = (
    "for group in groups:\n"
    "    written = '" + DECLINED + "' if group is None else "
    "'(' + ' '.join(str(a) for a in group) + ')'\n"
    "    print('" + parity.MARKER + "' + written)\n"
    "print('" + COST + "' + str(spent.inferences))\n"
    "heads = {_key(row.head) for row in m.query(S['='](V.head, V.body))}\n"
    "print('" + HEADS + "' + ' '.join(sorted(heads)))\n"
)


def _read(text: str, outcome: parity.Outcome) -> Run:
    """One run's marker lines, the cost and heads read beside the groups."""
    cost, heads = None, ()
    for line in text.splitlines():
        if line.startswith(COST):
            cost = int(line[len(COST):].strip())
        elif line.startswith(HEADS):
            heads = tuple(line[len(HEADS):].split())
    return Run(outcome, cost, heads)


def _launch(source: str, root: Path) -> Run:
    outcome, text = parity._run([sys.executable, "-c", source], root)
    return _read(text, outcome)


def run_example(path: Path, root: Path = REPO) -> Run:
    """The `.metta` original through the shipped library, priced. load()
    already answers the per-form groups, so this preserves the structure the
    comparator reads and measures the whole of getting the program in and
    running it, which is what the twin's own cost measures too.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    return _launch(
        _PREAMBLE
        + "with m.stats() as spent:\n"
        + f"    groups = m.load({str(path.relative_to(root))!r})\n"
        + _EPILOGUE,
        root,
    )


def run_twin(twin: Path, root: Path = REPO) -> Run:
    """The twin, in its own process, priced the same way. The module's
    twin(m) is a generator, so consuming it inside the block counts the
    definitions it installs as well as the forms it evaluates.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    return _launch(
        _PREAMBLE
        + "import importlib.util\n"
        f"_spec = importlib.util.spec_from_file_location('petta_twin', {str(twin)!r})\n"
        "_module = importlib.util.module_from_spec(_spec)\n"
        "_spec.loader.exec_module(_module)\n"
        "with m.stats() as spent:\n"
        "    groups = [None if g is None else list(g) for g in _module.twin(m)]\n"
        + _EPILOGUE,
        root,
    )


def budget_of(twin: Path) -> int | None:
    """The twin's own pinned inference count, read from its BUDGET
    assignment without importing it: reading the source keeps this usable
    on a twin that cannot run.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    tree = _parse(twin)
    for node in tree.body if tree else []:
        targets = node.targets if isinstance(node, ast.Assign) else []
        for target in targets:
            if isinstance(target, ast.Name) and target.id == "BUDGET":
                return ast.literal_eval(node.value)
    return None


# ------------------------------------------------------------------ comparison


def agree(left: str, right: str) -> bool:
    """Two written answer groups, compared up to consistent renaming of
    variables. `=alpha` is the law's own relation and the library ships it;
    comparing the spelling of a variable name instead would make two
    identical answers differ because the two sides numbered a fresh variable
    differently.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    from petta.atoms import (  # noqa: PLC0415  -- deferred so the corpus queries above need no engine
        Atom,
        alpha_eq,
    )

    first, second = parity._value(left), parity._value(right)
    if isinstance(first, Atom) and isinstance(second, Atom):
        return alpha_eq(first, second)
    return first == second


#: A form no Python spelling reaches, so the twin declines it; and a form a
#: twin does reach, but only around a hole in the surface. Both derive
#: backlog and only the first costs coverage, which is why they are one table
#: with two kinds rather than a table and a paragraph.
DECLINED_KIND = "declined"
FRICTION_KIND = "friction"


def residue() -> list[dict]:
    """The declared residue: what no Python spelling reaches and what only an
    indirect one does, each naming the spelling that is missing and the row
    it lands on.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    document = json.loads(RESIDUE.read_text(encoding="utf-8"))
    return document["entries"]


def _declined(entries: list[dict], example: str) -> set[int | None]:
    return {
        entry["form"]
        for entry in entries
        if entry["example"] == example and entry["kind"] == DECLINED_KIND
    }


@dataclass(frozen=True, slots=True)
class Verdict:
    """One example's coverage: what it was asked, what its twin answered."""

    example: Path
    forms: int
    covered: int
    example_cost: int | None
    twin_cost: int | None
    findings: tuple[str, ...]

    @property
    def ratio(self) -> float | None:  # noqa: D102  -- the enclosing type and implemented protocol supply this method contract
        if not self.example_cost or self.twin_cost is None:
            return None
        return self.twin_cost / self.example_cost


def compare(
    relative: str, left: Run, right: Run, declared: set[int | None]
) -> tuple[int, list[str]]:
    """How many of the example's forms the twin answered alpha-equal, and
    everything that is wrong with the rest. A pure function of two runs, so
    the comparison can be shown failing without an engine.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    forms = len(left.outcome.groups)
    if len(right.outcome.groups) != forms:
        return 0, [
            f"{relative}: the twin answered {len(right.outcome.groups)} forms, "
            f"the example {forms}"
        ]

    covered, findings = 0, []
    for index, (want, got) in enumerate(
        zip(left.outcome.groups, right.outcome.groups, strict=True)
    ):
        if got == DECLINED:
            if index not in declared:
                findings.append(
                    f"{relative}: form {index} is declined by the twin and "
                    f"declared by no residue entry"
                )
            continue
        if not agree(want, got):
            findings.append(
                f"{relative}: form {index} answers {got} where the example "
                f"answers {want}"
            )
            continue
        covered += 1

    missing = set(left.heads) - set(right.heads)
    if missing:
        findings.append(
            f"{relative}: the twin's space does not answer a (= $head $body) "
            f"match with {' '.join(sorted(missing))}, so a definition the "
            f"example makes matchable is hidden in Python"
        )
    return covered, findings


def check(example: Path, entries: list[dict], root: Path = REPO) -> Verdict:
    """Run one example and its twin, and answer everything the lane claims."""
    twin = twin_for(example, root)
    relative = str(example.relative_to(root))
    findings = [f"{relative}: {finding}" for finding in scan(twin)]
    findings += [f"{relative}: {finding}" for finding in idiom(twin)]

    left, right = run_example(example, root), run_twin(twin, root)
    if left.outcome.error or right.outcome.error:
        side = "the example" if left.outcome.error else "the twin"
        error = left.outcome.error or right.outcome.error
        findings.append(f"{relative}: {side} failed to run: {error}")
        return Verdict(example, len(left.outcome.groups), 0, None, None, tuple(findings))

    covered, differences = compare(
        relative, left, right, _declined(entries, relative)
    )
    findings.extend(differences)
    findings.extend(_price(relative, twin, left, right))
    return Verdict(
        example,
        len(left.outcome.groups),
        covered,
        left.cost,
        right.cost,
        tuple(findings),
    )


def _price(relative: str, twin: Path, left: Run, right: Run) -> list[str]:
    """The two cost claims: a pinned budget, and a band against the original.

    The budget is TWO-SIDED, which a benchmark baseline is not. A benchmark
    only cares about getting slower; a twin that suddenly costs far less has
    most likely stopped doing the work and started answering the expected
    value, which is the failure mode a fixed public conformance corpus
    invites: "matching their text is a far cheaper route to pass the tests
    than implementing the spec" [source:
    https://www.christianfindlay.com/blog/basilisk-conformance-apology,
    the python/typing conformance suite, 2026-08; commit=c7191d87d9cbfce2870e586057168ec9103845ca]. Inferences
    are deterministic across processes here, so pinning both sides costs
    nothing in flakiness and catches a twin that stopped being one.
    """
    findings = []
    budget = budget_of(twin)
    if budget is None:
        findings.append(f"{relative}: the twin states no BUDGET")
    elif right.cost is not None and abs(right.cost - budget) > TOLERANCE:
        moved = "above" if right.cost > budget else "BELOW"
        findings.append(
            f"{relative}: the twin cost {right.cost} inferences, {moved} its "
            f"pinned budget of {budget} by more than the {TOLERANCE} allowance"
        )
    if left.cost and right.cost is not None:
        ceiling = left.cost * (1.0 + BAND_PERCENT / 100.0)
        if right.cost > ceiling:
            findings.append(
                f"{relative}: the twin cost {right.cost} inferences against "
                f"the example's {left.cost}, past the {BAND_PERCENT:g}% band "
                f"ceiling of {ceiling:.0f}"
            )
    return findings


# --------------------------------------------------------------------- reporting


def _folders(verdicts: list[Verdict], root: Path) -> dict[str, tuple[int, ...]]:
    """Per folder: files passing, files in the corpus, forms covered, forms asked.

    A file passes when its twin has NOTHING wrong with it, so a twin that runs
    but disagrees, overruns its budget or smuggles source text buys nothing.
    EVERY folder of the corpus appears, including the ones with no twin at
    all: a lane that reports only what has been written reports only good
    news, and the fraction is the point.
    """
    totals: dict[str, list[int]] = {}
    for path in parity.corpus(root):
        folder = str(path.relative_to(root / "examples").parent)
        totals.setdefault(folder, [0, 0, 0, 0])[1] += 1
    for verdict in verdicts:
        folder = str(verdict.example.relative_to(root / "examples").parent)
        entry = totals[folder]
        entry[0] += not verdict.findings
        entry[2] += verdict.covered
        entry[3] += verdict.forms
    return {folder: tuple(counts) for folder, counts in totals.items()}


def _print_report(verdicts: list[Verdict], entries: list[dict], root: Path) -> None:
    print(f"{'example':44} {'forms':>5} {'twinned':>7} {'metta':>8} {'twin':>8} {'ratio':>6}")
    for verdict in verdicts:
        ratio = verdict.ratio
        print(
            f"{verdict.example.relative_to(root)!s:44} "
            f"{verdict.forms:5} {verdict.covered:7} "
            f"{verdict.example_cost if verdict.example_cost is not None else '-':>8} "
            f"{verdict.twin_cost if verdict.twin_cost is not None else '-':>8} "
            f"{f'{ratio:.2f}' if ratio else '-':>6}"
        )

    print()
    folders = _folders(verdicts, root)
    for folder, (passing, corpus_files, covered, forms) in sorted(folders.items()):
        answering = (
            f", {covered}/{forms} forms of those files answering alpha-equal"
            if forms
            else ""
        )
        print(f"coverage {folder}: {passing}/{corpus_files} files{answering}")
    totals = [sum(counts[index] for counts in folders.values()) for index in range(4)]
    print(
        f"coverage TOTAL: {totals[0]}/{totals[1]} files twinned and passing, "
        f"{totals[2]}/{totals[3]} forms of those files answering alpha-equal"
    )

    for kind in (DECLINED_KIND, FRICTION_KIND):
        chosen = [entry for entry in entries if entry["kind"] == kind]
        print()
        if not chosen:
            print(f"{kind}: none declared")
            continue
        print(f"{kind:44} {'form':>4} {'row':>6}  missing spelling")
        for entry in chosen:
            form = entry["form"]
            print(
                f"{entry['example']:44} {form if form is not None else '*':>4} "
                f"{entry['row']:>6}  {entry['missing']}"
            )


def main() -> int:
    """Run the lane, or measure it."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--measure", action="store_true",
                        help="print min-of-3 costs for pinning, and change nothing")
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("paths", nargs="*", help="examples, default every twinned one")
    arguments = parser.parse_args()

    sys.path.insert(0, str(REPO / "bindings" / "python"))
    named = [Path(p).resolve() for p in arguments.paths]
    for example in named:
        if not twin_for(example).is_file():
            print(f"{example}: no twin at {twin_for(example)}", file=sys.stderr)
            return 2
    examples = named or written()

    if arguments.measure:
        for example in examples:
            twin = twin_for(example)
            left = min(run_example(example).cost or 0 for _ in range(arguments.rounds))
            right = min(run_twin(twin).cost or 0 for _ in range(arguments.rounds))
            share = right / left if left else 0.0
            print(f"{example.relative_to(REPO)} metta={left} twin={right} ratio={share:.4f}")
        return 0

    entries = residue()
    with ThreadPoolExecutor() as pool:
        verdicts = list(pool.map(lambda path: check(path, entries), examples))

    findings = [finding for verdict in verdicts for finding in verdict.findings]
    findings.extend(
        f"{path.relative_to(REPO)}: twins an example the corpus does not run"
        for path in orphans()
    )
    _print_report(verdicts, entries, REPO)
    print()
    for finding in findings:
        print(finding)
    print(f"{len(findings)} findings over {len(examples)} twinned examples")
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
