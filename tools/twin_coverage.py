"""Purpose: turn "how much of MeTTa can be written in pure Python today" into a
measured number with a derived backlog. Each example under `examples/` may gain
a Python TWIN under `bindings/python/tests/twins/`, mirroring its path; this
lane runs the example and its twin, requires the twin to prove every claim the
example makes, to make the example's definitions matchable, to use no MeTTa
source text, and to spell in Python what Python already spells. Whatever a twin
cannot say is a RESIDUE entry naming the missing spelling and the plan row it
lands on, so the backlog derives itself instead of being believed.

A TWIN IS AN ORDINARY PYTHON PROGRAM, and its shape is its own. Until
2026-08-22 this lane required one yielded answer group per runnable form of the
example, in source order, and compared the groups pairwise. That contract made
TRANSLITERATION MANDATORY: the ledger's own worked example, `@m.define` plus
`assert f(1) == [1]`, scored zero forms and zero coverage, because it yields
nothing and never calls `test`; the only passing shape was
`yield m.eval(S.test(...))` once per form, which is why the corpus that grew
under it held 1,313 of those and not one `assert`. The check above it read
punctuation, so tightening it made better transliterations rather than fewer
[measured 2026-08-22: the idiomatic twin refused by the old lane, restored;
ai-python-first-revamp-discussion.md sections 7, 9b and 9k are the design
authority and the corpus contradicted all three].

What replaced the pairwise comparison is a count against a count. The example
states a claim per assert-family form; the twin states one per `assert`; a twin
that runs to completion has PROVED every claim it states, because a false
assertion raises. Nothing about either file's shape is observed, so a twin may
loop where the example repeats, may name an intermediate, and may do in Python
what the example asked the engine to do.

Assumes:
  - discovery comes from example_parity.corpus/1 and nowhere else, so a twin's
    path is DERIVED from its example's path rather than walked separately
    [tested: test_the_twin_set_is_derived_from_the_one_corpus]
  - a point budget is deterministic within TOLERANCE; a counter that varies
    declares an empirical minimum, maximum, observation count, and protocol
    instead [tested: test_a_budget_is_two_sided,
    test_an_empirical_envelope_passes_its_observations_and_fails_new_spread;
    commit=WORKTREE]
  - an assert-family head states one claim, and Python's `assert` is its image
    [source: engine/prelude.metta 56-103; ai-python-first-revamp-discussion.md
    section 9d rule 1, "assert and pytest for the assert family"]
Guarantees:
  - a twin that reaches the engine through MeTTa source text is REFUSED, both
    the four source doors and any string that is not a name or val()-marked
    data [tested: test_the_source_scan_catches_a_planted_string]
  - a twin stating fewer claims than its example is a finding, so a skip
    cannot be silent [tested: test_a_twin_that_claims_less_is_a_finding]
  - a false claim fails the twin, because a raised AssertionError leaves the
    run in error [tested: test_a_failing_assertion_is_a_finding]
  - a twin's definitions are visible to `match` where the original's are, so a
    Python-authored definition cannot pass by hiding in Python-side state
    [tested: test_a_hidden_definition_is_a_finding]
  - a twin writing MeTTa in Python punctuation is a finding naming the Python
    spelling it should have used [tested:
    test_a_dissolved_head_names_the_python_spelling_it_replaces,
    test_a_yielding_twin_is_a_finding]
  - empirical budgets license only the protocol that measured them, and the
    deterministic point tolerance never widens their observed extrema
    [tested: test_an_empirical_envelope_cannot_license_another_protocol;
    commit=WORKTREE]
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
  - an integer BUDGET is a point claim; a mapping BUDGET is an empirical
    envelope with exactly minimum, maximum, observations, and protocol, so a
    reviewer can falsify both its bounds and the conditions that produced it
    [tested: test_an_empirical_envelope_requires_complete_measurement_metadata;
    commit=WORKTREE]
  - a full-lane protocol fixes both corpus width and executor width; empirical
    observations can be reproduced with --observe [tested:
    test_the_full_lane_protocol_names_every_scheduling_input;
    commit=WORKTREE]
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
import json
import keyword
import os
import re
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

#: What AUTHORING a compiled definition costs, which the band must allow
#: because the example it is priced against has no definition to author. The
#: decorator writes reflection facts the container door never writes, and the
#: compiler warms up once per process. MEASURED 2026-08-22, min of three fresh
#: processes over files holding 0 to 4 one-line decorated definitions: 5,
#: 2221, 2986, 3751, 4516 inferences, so the fit is exact and linear, 1456 once
#: plus 765 for each definition. Without this the band SELECTED FOR
#: TRANSLITERATION on exactly the files where Python's spelling is clearest:
#: examples/control/if.metta costs 2092 with a ceiling of 2301, so one
#: decorated definition could not fit and six control twins had to stay at the
#: container door [found 2026-08-22 by the control agent, which said the rule
#: was wrong and was right; commit=WORKTREE].
DEFINITION_WARMUP = 1456
DEFINITION_COST = 765

#: The tree's own POINT-counter allowance. It applies to an integer BUDGET
#: only; adding it to empirical extrema would silently widen what was observed
#: [source: bindings/python/petta/benchmarking.py _COUNTER_TOLERANCE;
#: commit=WORKTREE].
TOLERANCE = 4

#: A direct check is serial. The shipped lane fixes and names both its executor
#: width and corpus size, so either scheduling change invalidates an old
#: empirical claim visibly instead of changing the scheduler under one label
#: [tested: test_an_empirical_envelope_cannot_license_another_protocol;
#: commit=WORKTREE].
SERIAL_PROTOCOL = "serial"
FULL_LANE_PROTOCOL = "full-lane"
FULL_LANE_WORKERS = 32

#: The four doors that take MeTTa source text. A twin may not use any of them:
#: that is the whole of "zero s-expression strings".
SOURCE_DOORS = frozenset({"run", "load", "parse", "save"})

#: Calls whose string argument is a NAME or a marked datum rather than a
#: program: sym/var name an atom, fn names an engine function, space and
#: new_space name a space, and val carries a Python value whole.
NAMING_CALLS = frozenset({
    "sym", "var", "val", "fn", "space", "new_space",
    # TypeVar("X") names a type variable exactly as sym("x") names an atom,
    # and a twin declaring a parametric type needs it [found 2026-08-22 by the
    # types agent, which worked around it with the name= keyword].
    "TypeVar",
})

#: Calls whose string arguments are HOST text rather than a program: a message
#: a twin prints, a filesystem path it opens. `println!` dissolves into
#: `print()` by the table below, so the scan has to let a twin print.
HOST_TEXT_CALLS = frozenset({"print", "Path", "open", "warning", "info", "debug"})

#: The two factories whose subscript is an atom's name.
NAMING_NAMESPACES = frozenset({"S", "V"})

#: Module-level constants a twin declares ABOUT itself rather than as
#: program text: the inference pin, and the reason it sits below the top
#: rung. Both are read from source the way the lane reads BUDGET.
DECLARATION_NAMES = frozenset({"BUDGET", "RUNG"})

#: The example heads that STATE A CLAIM. Their Python image is the `assert`
#: statement, so the lane counts them against the twin's assertions rather
#: than asking the twin to call them [source: engine/prelude.metta lines
#: 56-103, the assert family; commit=WORKTREE].
ASSERT_HEADS = frozenset({
    "test", "test-no-answer", "assert", "assertEqual", "assertAlphaEqual",
    "assertEqualToResult", "assertAlphaEqualToResult", "assertIncludes",
    "assertEqualMsg", "assertAlphaEqualMsg", "assertEqualToResultMsg",
    "assertAlphaEqualToResultMsg",
})

#: What Python already spells, and how. A twin naming one of these heads is
#: writing MeTTa in Python punctuation: the concept exists in Python and rule
#: 1 of the terminology law takes Python's spelling where it does
#: [source: ai-python-first-revamp-discussion.md section 9e, the
#: dissolves-into-Python-protocols bucket, and section 9d rule 1;
#: commit=WORKTREE]. A twin whose SUBJECT is one of these functions says so
#: on the line, `# rung: <reason>`, which is how the ladder keeps the rung
#: while making the drop visible.
DISSOLVED = {
    "test": "Python's own assert",
    "assert": "Python's own assert",
    "assertEqual": "Python's own assert",
    "assertAlphaEqual": "assert, with a.alpha_eq(b)",
    "assertEqualToResult": "Python's own assert",
    "assertAlphaEqualToResult": "assert, with a.alpha_eq(b)",
    "assertIncludes": "assert, with Python's `in`",
    "add-atom": "space += atom",
    "add-reduct": "space += the evaluated atom",
    "remove-atom": "space -= atom",
    "match": "space[pattern], the subscript door",
    "collapse": "list()",
    "car-atom": "e[0]",
    "cdr-atom": "e[1:]",
    "decons-atom": "head, *tail = e",
    "cons-atom": "building the term by calling its head",
    "size-atom": "len(e)",
    "index-atom": "e[i]",
    "map-atom": "a comprehension, or map()",
    "filter-atom": "a comprehension, or filter()",
    "foldl-atom": "functools.reduce",
    "max-atom": "max()",
    "min-atom": "min()",
    "sort-strings": "sorted()",
    "if": "Python's own if, or its conditional expression",
    "let": "assignment",
    "let*": "assignment",
    "case": "Python's match statement",
    "switch": "Python's match statement",
    "println!": "print()",
    "trace!": "print(), or logging",
    "format-args": "an f-string",
    "bind!": "a Python name binding",
    "new-space": "space.new_space()",
    # NOT here, though section 9e assigns them: `get-type` and `get-doc`. The
    # ledger DESIGNS `space.type(atom)` and `space.doc(atom)`; the surface has
    # not shipped either, so naming the head is the only spelling a twin has
    # and demanding another would be demanding a door that does not exist
    # [measured 2026-08-22: `MeTTa.type` is the class-declaration decorator
    # and `MeTTa` has no `doc`; P14.25 is the row that closes them].
}


def example_forms(example: Path) -> list[str]:
    """The head of every runnable `!` form of an example, in source order.

    Read by balancing parentheses over the source rather than by running the
    engine, so the lane can say what KIND of claim a form makes without
    paying for a second run of an example that costs 260 million inferences
    [tested: test_the_form_reader_agrees_with_the_engines_own_count].
    """
    text, out, index, size = example.read_text(encoding="utf-8"), [], 0, 0
    source = text
    size = len(source)
    while index < size:
        char = source[index]
        if char == ";":
            index = source.find("\n", index)
            if index < 0:
                break
            continue
        if char == '"':
            index = _past_string(source, index)
            continue
        if char == "!" and index + 1 < size and source[index + 1] == "(":
            start = index
            index = _past_form(source, index + 1)
            head = re.match(r"!\(\s*([^\s()]+)", source[start:index])
            out.append(head.group(1) if head else "")
            continue
        index += 1
    return out


def _past_string(source: str, index: int) -> int:
    """The index just past a double-quoted literal starting at `index`."""
    index += 1
    while index < len(source) and source[index] != '"':
        index += 2 if source[index] == "\\" else 1
    return index + 1


def _past_form(source: str, index: int) -> int:
    """The index just past the parenthesised form opening at `index`."""
    depth, size = 0, len(source)
    while index < size:
        char = source[index]
        if char == ";":
            index = source.find("\n", index)
            if index < 0:
                return size
            continue
        if char == '"':
            index = _past_string(source, index)
            continue
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return index + 1
        index += 1
    return size


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
        # `cache` compiles a body exactly as `define` does, and a cached
        # definition's match() must name its space as a string constant,
        # because the two-argument form lowers to (context-space) which
        # caching refuses as impure [found 2026-08-22 by the libraries agent,
        # which lost the @m.cache spelling and fn.cache_info() to this].
        if name in {"define", "cache"}:
            return True
    return False


def _prints_text(node: ast.AST) -> bool:
    """Whether a subtree reaches Python or MeTTa's textual repr door."""
    for inner in ast.walk(node):
        if not isinstance(inner, ast.Call):
            continue
        if _callee(inner) in {"repr", "str"}:
            return True
        called = inner.func
        if (
            isinstance(called, ast.Call)
            and _callee(called) == "fn"
            and called.args
            and isinstance(called.args[0], ast.Constant)
            and called.args[0].value == "repr"
        ):
            return True
    return False


def _printing_strings(tree: ast.Module) -> set[int]:
    """Text literals that state what a printed atom or exception must say.

    The exemption follows data through one named fixture, enough for a table
    such as ``PRINTED = ((atom, "text"), ...)``. It does not exempt an
    unrelated string merely because the same function also prints something
    [source: ai-python-first-revamp-discussion.md section 9q.2;
    commit=WORKTREE].
    """  # noqa: D205 -- the second paragraph states the dataflow boundary
    printed_names = {
        target.id
        for node in ast.walk(tree)
        if isinstance(node, (ast.Assign, ast.AnnAssign)) and _prints_text(node.value)
        for target in (node.targets if isinstance(node, ast.Assign) else [node.target])
        if isinstance(target, ast.Name)
    }
    comparisons = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Compare):
            continue
        loaded = {
            inner.id
            for inner in ast.walk(node)
            if isinstance(inner, ast.Name) and isinstance(inner.ctx, ast.Load)
        }
        if _prints_text(node) or loaded & printed_names:
            comparisons.append(node)
    names = {
        inner.id
        for comparison in comparisons
        for inner in ast.walk(comparison)
        if isinstance(inner, ast.Name) and isinstance(inner.ctx, ast.Load)
    }
    permitted = {
        id(inner)
        for comparison in comparisons
        for inner in ast.walk(comparison)
        if isinstance(inner, ast.Constant) and isinstance(inner.value, str)
    }
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        if not any(isinstance(target, ast.Name) and target.id in names for target in targets):
            continue
        permitted.update(
            id(inner)
            for inner in ast.walk(node.value)
            if isinstance(inner, ast.Constant) and isinstance(inner.value, str)
        )
    return permitted


def _named_strings(tree: ast.Module) -> set[int]:
    """The string constants that are names, marked data, or documentation.

    Identity rather than value, so `val("(f a)")` in one place does not
    excuse a bare `"(f a)"` in another.
    """
    permitted = _printing_strings(tree)
    for node in ast.walk(tree):
        # A raised message is prose for a reader, the same as a docstring.
        if isinstance(node, ast.Raise):
            permitted.update(
                id(inner)
                for inner in ast.walk(node)
                if isinstance(inner, ast.Constant) and isinstance(inner.value, str)
            )
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef)):
            head = node.body[0] if node.body else None
            if isinstance(head, ast.Expr) and isinstance(head.value, ast.Constant):
                permitted.add(id(head.value))
            # A declared rung's REASON is documentation, exactly like the
            # docstring above it, so the source scan must not read it as a
            # program. Without this the two checks contradict each other and
            # declaring a rung turns the lane red, which makes the ladder's
            # own escape unusable [found 2026-08-22 by two twin agents at once].
            for statement in node.body:
                if not isinstance(statement, ast.Assign) or not any(
                    isinstance(target, ast.Name) and target.id in DECLARATION_NAMES
                    for target in statement.targets
                ):
                    continue
                # An empirical BUDGET carries a protocol string inside a
                # literal mapping. It is declaration metadata, just as a
                # scalar RUNG reason is, and never program source [tested:
                # test_an_empirical_envelope_passes_its_observations_and_fails_new_spread;
                # commit=WORKTREE].
                permitted.update(
                    id(inner)
                    for inner in ast.walk(statement.value)
                    if isinstance(inner, ast.Constant)
                    and isinstance(inner.value, str)
                )
            if isinstance(node, ast.FunctionDef) and _defines(node):
                permitted.update(
                    id(inner)
                    for inner in ast.walk(node)
                    if isinstance(inner, ast.Constant) and isinstance(inner.value, str)
                )
        elif isinstance(node, ast.Subscript):
            # Any subscript KEY is a name: `S["f"]` names an atom and
            # `answers["x"]` names a binding, and no door takes MeTTa source
            # text through a subscript.
            permitted.add(id(node.slice))
        elif isinstance(node, ast.Call):
            # A string in a KEYWORD argument is host data, never a program:
            # the four source doors are caught by call name above, whatever
            # shape their arguments take, so `names=["c-bump"]` and
            # `path=Path("...")` need no ceremony [found 2026-08-22 by the
            # reasoning agent, which had to write `[S["c-bump"].name]`].
            permitted.update(
                id(inner)
                for word in node.keywords
                for inner in ast.walk(word.value)
                if isinstance(inner, ast.Constant) and isinstance(inner.value, str)
            )
            # A twin may SAY things. The dissolution table sends `println!` to
            # print(), so refusing print's own message contradicted this
            # module's own rule, and three C-extension twins returned silently
            # where their example says why it skipped.
            if _callee(node) in HOST_TEXT_CALLS:
                permitted.update(
                    id(inner)
                    for inner in ast.walk(node)
                    if isinstance(inner, ast.Constant) and isinstance(inner.value, str)
                )
            if _callee(node) in NAMING_CALLS:
                # Every argument, keyword and nested container included: a
                # naming call takes names and marked data wherever they sit,
                # and `new_space(grants=["file"])` names capabilities
                # [found 2026-08-22 by the spaces agent, which had to write
                # `S.file.name` to get past this].
                permitted.update(
                    id(inner)
                    for inner in ast.walk(node)
                    if isinstance(inner, ast.Constant) and isinstance(inner.value, str)
                )
            permitted.update(
                id(keyword.value) for keyword in node.keywords if keyword.arg == "name"
            )
    return permitted


#: Heads Python's own syntax already builds, so writing them as a call or
#: through Expression() spells with a function what the language spells with a
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
    written `S.f`, `S["+"]`, or the first item of `Expression((...))`.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
        return node.attr if node.value.id in NAMING_NAMESPACES else None
    if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name):
        key = node.slice
        if node.value.id in NAMING_NAMESPACES and isinstance(key, ast.Constant):
            return key.value if isinstance(key.value, str) else None
    return None


def _symbol_head(node: ast.expr) -> str | None:
    """The head of a term-building expression, when that head is a SYMBOL.

    `Expression((S.f, a))` says with a constructor what `S.f(a)` says with a
    call, but `Expression((V.x,))` has no shorter spelling at all: a
    variable-headed expression is the one shape the builders do not reach,
    because `Var` is not callable
    [measured 2026-08-22: `V.x()` raises TypeError; filed as residue against
    P14.4].
    """
    named = _head_symbol(node)
    if named is None:
        return None
    root = node.value if isinstance(node, (ast.Attribute, ast.Subscript)) else None
    return named if isinstance(root, ast.Name) and root.id == "S" else None


def _expression_parts(node: ast.Call) -> list[ast.expr] | None:
    """Literal ordered parts passed to Expression, when visible in syntax."""
    if _callee(node) != "Expression" or len(node.args) != 1 or node.keywords:
        return None
    value = node.args[0]
    if not isinstance(value, (ast.Tuple, ast.List)):
        return None
    return value.elts


def idiom(twin: Path) -> list[str]:
    """Where a twin spells in library calls what Python's own syntax spells.

    A twin avoiding MeTTa source text can still be MeTTa source text with
    Python punctuation, which is the failure this catches: `S["merge"]` where
    `S.merge` reads, `Expression((S["="], a, b))` where `S["="](a, b)` reads,
    and `Expression((S["+"], a, b))` where `a + b` already builds that term.
    The design
    authority is ai-python-first-revamp-discussion.md, sections 9c and 9k.
    A twin that declares `RUNG = "<reason>"` is exempt, because a drop with a
    stated reason is what the ladder is for.
    """
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
    findings: list[tuple[int, str]] = [
        (node.lineno, "twin() yields, so it mirrors the example FORM BY FORM; "
                      "a twin is an ordinary function that does what the "
                      "example does")
        for node in _twin_body(tree)
        if isinstance(node, (ast.Yield, ast.YieldFrom))
    ]
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript):
            spelled = _head_symbol(node)
            if spelled is not None and spelled.startswith("&"):
                findings.append((
                    node.lineno,
                    f"{spelled!r} names a SPACE as a symbol; a space is a "
                    f"handle, and every context-relative door hangs off it",
                ))
            name = _subscripted_name(node)
            if name is not None:
                namespace = node.value.id
                findings.append(
                    (node.lineno, f'{namespace}["{name}"] is {namespace}.{name}')
                )
        elif isinstance(node, ast.Call):
            parts = _expression_parts(node)
            head = _symbol_head(parts[0]) if parts else None
            if head is not None:
                findings.append(
                    (node.lineno, "Expression(...) builds what calling the head builds")
                )
            called = _head_symbol(node.func)
            operator = called if called in OPERATOR_HEADS else head
            dissolved = DISSOLVED.get(called) or DISSOLVED.get(head)
            if dissolved is not None:
                findings.append((
                    node.lineno,
                    f"the head {(called or head)!r} is {dissolved}",
                ))
            # At the operator's OWN arity only: `S["+"](1)` is a partial
            # application, which Python has no operator spelling for.
            arity = len(parts) - 1 if parts is not None else len(node.args)
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


def _twin_body(tree: ast.Module) -> list[ast.AST]:
    """Every node of the twin's own `twin(m)` body, excluding the nested
    functions it defines: a `@m.define`-compiled generator SHOULD yield,
    because there yield is nondeterminism, while a yield in twin() itself is
    the form-by-form mirror this lane exists to refuse.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "twin":
            nested = {
                id(inner)
                for statement in ast.walk(node)
                if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda))
                and statement is not node
                for inner in ast.walk(statement)
            }
            return [
                inner for inner in ast.walk(node)
                if id(inner) not in nested
            ]
    return []


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
    outcome, text = parity._run(
        [sys.executable, "-c", source], root, env=_environment()
    )
    return _read(text, outcome)


#: The environment every measurement runs in. It is BUILT rather than
#: inherited, which is the discipline benchmarking.py already applies for the
#: same reason: a measurement that moves with the caller is not a measurement.
#: Measured 2026-08-22 on examples/integration/git_import.metta, whose
#: `git-import!` reaches for an executable: 2 PATH entries cost 46390
#: inferences, 3 cost 46435 and 6 cost 46570, exactly 45 per entry, so
#: something walks PATH inside a counted path and the same twin read a
#: different figure under `sh check.sh` than run directly. `git` and `swipl`
#: both live in /usr/bin here [commit=WORKTREE].
#:
#: It is PASSED to the child, never written into this process. Writing it into
#: `os.environ` is what the first version did, and under pytest that escaped
#: the lane: `test_twin_coverage.py` calls run_twin, so every later test in the
#: same process lost `~/.elan/bin` from PATH and the two LeaTTa conformance
#: tests failed to find `lake` [source: bindings/python/petta/benchmarking.py
#: builds its child environment the same way and says why; commit=WORKTREE].
MEASURED_PATH = (str(Path(sys.executable).resolve().parent), "/usr/bin", "/bin")

#: What the child keeps from this process, beside the pinned PATH. HOME and the
#: loader variables are what an engine launch needs; nothing else is inherited,
#: so the environment BLOCK is the same size whoever runs the lane.
MEASURED_ENVIRONMENT = ("HOME", "LD_LIBRARY_PATH", "SWI_HOME_DIR", "LEATTA_PATH")


def _environment() -> dict[str, str]:
    """The child environment for one measurement, built from nothing."""
    kept = {
        name: os.environ[name]
        for name in MEASURED_ENVIRONMENT
        if name in os.environ
    }
    return kept | {"PATH": os.pathsep.join(MEASURED_PATH), "LC_ALL": "C"}


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
    """The twin, in its own process, priced the same way.

    `twin(m)` is an ordinary function and its assertions are the claims it
    proves, so running it to completion IS the check: an AssertionError
    propagates and the lane reads it as a failed claim. Nothing about the
    twin's SHAPE is observed here, which is the point of the contract change
    [tested: test_a_failing_assertion_is_a_finding].
    """
    return _launch(
        _PREAMBLE
        + "import importlib.util\n"
        f"_spec = importlib.util.spec_from_file_location('petta_twin', {str(twin)!r})\n"
        "_module = importlib.util.module_from_spec(_spec)\n"
        "_spec.loader.exec_module(_module)\n"
        "groups = []\n"
        "with m.stats() as spent:\n"
        "    _module.twin(m)\n"
        + _EPILOGUE,
        root,
    )


@dataclass(frozen=True, slots=True)
class EmpiricalBudget:
    """Observed extrema from repeated runs under one named protocol.

    This is an empirical envelope, not a confidence interval. Google
    Benchmark keeps repetition count separate from dispersion statistics and
    supports a maximum statistic for a hard bound; Criterion keeps sample
    count and measurement environment explicit and retains outliers. The lane
    therefore records absolute extrema and observations, never mean +/-
    standard deviation [source:
    https://github.com/google/benchmark/blob/192ef10025eb2c4cdd392bc502f0c852196baa48/docs/user_guide.md#L1145-L1196;
    commit=WORKTREE].
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

    minimum: int
    maximum: int
    observations: int
    protocol: str

    @property
    def spread(self) -> int:
        """The measured max-minus-min spread."""
        return self.maximum - self.minimum


def full_lane_protocol(examples: int) -> str:
    """The scheduler protocol for one complete concurrent corpus run."""
    if isinstance(examples, bool) or not isinstance(examples, int) or examples <= 0:
        msg = f"full-lane protocol needs a positive example count, got {examples!r}"
        raise ValueError(msg)
    return f"{FULL_LANE_PROTOCOL}/{examples}/workers={FULL_LANE_WORKERS}"


def _empirical_budget(value: dict, twin: Path) -> EmpiricalBudget:
    """Validate one literal empirical BUDGET declaration."""
    required = {"minimum", "maximum", "observations", "protocol"}
    if set(value) != required:
        msg = (
            f"{twin}: BUDGET empirical envelope must contain exactly "
            f"{sorted(required)!r}"
        )
        raise ValueError(msg)
    minimum, maximum = value["minimum"], value["maximum"]
    observations, protocol = value["observations"], value["protocol"]
    bounds_are_ints = all(
        isinstance(bound, int) and not isinstance(bound, bool)
        for bound in (minimum, maximum)
    )
    if not bounds_are_ints or minimum <= 0 or maximum <= minimum:
        msg = (
            f"{twin}: BUDGET empirical envelope needs positive integer "
            "minimum < maximum"
        )
        raise ValueError(msg)
    if (
        isinstance(observations, bool)
        or not isinstance(observations, int)
        or observations < 2
    ):
        msg = f"{twin}: BUDGET empirical envelope needs at least 2 observations"
        raise ValueError(msg)
    if not isinstance(protocol, str) or not protocol.strip():
        msg = f"{twin}: BUDGET empirical envelope needs a non-empty protocol"
        raise ValueError(msg)
    return EmpiricalBudget(minimum, maximum, observations, protocol)


def budget_of(twin: Path) -> int | EmpiricalBudget | None:
    """The twin's own pinned inference count, read from its BUDGET
    assignment without importing it: reading the source keeps this usable
    on a twin that cannot run.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    tree = _parse(twin)
    for node in tree.body if tree else []:
        targets = node.targets if isinstance(node, ast.Assign) else []
        for target in targets:
            if isinstance(target, ast.Name) and target.id == "BUDGET":
                value = ast.literal_eval(node.value)
                if isinstance(value, dict):
                    return _empirical_budget(value, twin)
                if (
                    isinstance(value, bool)
                    or not isinstance(value, int)
                    or value <= 0
                ):
                    msg = f"{twin}: BUDGET point must be a positive integer"
                    raise ValueError(msg)
                return value
    return None


# ------------------------------------------------------------------ comparison


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


def assertions(twin: Path) -> int:
    """How many claims the twin STATES, counted as `assert` statements.

    Python's own assert is the image of the example's assert family (rule 1
    of the terminology law: where Python has the concept, Python's spelling
    wins), so this is the twin's side of what the example claims. Counted
    from source rather than from a run, so a twin that raises before its last
    assertion still reports how many it meant to make.
    """
    tree = _parse(twin)
    return sum(isinstance(node, ast.Assert) for node in ast.walk(tree)) if tree else 0


def compare(
    relative: str, example: Path, twin: Path, declared: set[int | None]
) -> tuple[int, int, list[str]]:
    """The claims the example makes, the ones the twin proves, and what is
    wrong with the difference.

    The example states a claim per assert-family form; the twin states one
    per `assert`. A twin that runs to completion has PROVED every claim it
    states, because a false assertion raises. So the comparison is a count
    against a count, and nothing about either file's shape enters it. What
    stops a twin from claiming less than its example is the count itself;
    what stops it from claiming something cheap instead is the two-sided
    budget in `_price`, which a twin that answers constants cannot meet.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    heads = example_forms(example)
    claims = sum(head in ASSERT_HEADS for head in heads)
    declined = len([index for index in declared if index is not None])
    owed = max(0, claims - declined)
    stated = assertions(twin)

    findings = []
    if stated < owed:
        findings.append(
            f"{relative}: the example states {claims} claims and the twin "
            f"{stated} assertions, {owed - stated} short; a claim a twin "
            f"cannot make is a residue entry, never a silent gap"
        )
    return owed, min(stated, owed), findings


def check(
    example: Path,
    entries: list[dict],
    root: Path = REPO,
    *,
    protocol: str = SERIAL_PROTOCOL,
) -> Verdict:
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
        claims = sum(head in ASSERT_HEADS for head in example_forms(example))
        return Verdict(example, claims, 0, None, None, tuple(findings))

    claims, covered, differences = compare(
        relative, example, twin, _declined(entries, relative)
    )
    findings.extend(differences)
    findings.extend(_visible(relative, left, right))
    stated = any(entry["example"] == relative for entry in entries)
    findings.extend(_price(relative, twin, left, right, stated, protocol=protocol))
    return Verdict(example, claims, covered, left.cost, right.cost, tuple(findings))


def _visible(relative: str, left: Run, right: Run) -> list[str]:
    """The reflectivity check, and the one thing here that no restructuring
    may weaken: a Python-authored definition must land as an ordinary atom
    the space answers a `(= $head $body)` match with, never as Python-side
    state [source: ai-python-first-revamp-discussion.md section 1b point 2,
    "any revamp design that would make a Python-defined function invisible
    to match is wrong by this test"; commit=WORKTREE].
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    missing = set(left.heads) - set(right.heads)
    if not missing:
        return []
    return [
        f"{relative}: the twin's space does not answer a (= $head $body) "
        f"match with {' '.join(sorted(missing))}, so a definition the "
        f"example makes matchable is hidden in Python"
    ]


#: Below this a twin did nothing an engine was needed for. Python's own
#: structure operations on atoms already held in Python cost NO crossing at
#: all, which the ladder wants; but a twin that never reaches the engine is
#: not twinning a MeTTa example, it is only agreeing with it. Pinned from the
#: two measured ends: a twin doing all of its example's work in Python cost 5
#: inferences, and the cheapest twin that still queries a space cost 449
#: [measured 2026-08-22: examples/control/caseconstrain.metta and
#: examples/spaces/spaces3.metta, `twin_coverage.py --measure`;
#: commit=WORKTREE].
ENGINE_FLOOR = 100


def _price(
    relative: str,
    twin: Path,
    left: Run,
    right: Run,
    stated: bool = False,  # noqa: FBT001, FBT002  -- one flag, and the call site reads better positionally than with a keyword
    *,
    protocol: str = SERIAL_PROTOCOL,
) -> list[str]:
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
    try:
        budget = budget_of(twin)
    except (TypeError, ValueError) as error:
        budget = None
        findings.append(f"{relative}: {error}")
    if budget is None and not findings:
        findings.append(f"{relative}: the twin states no BUDGET")
    elif isinstance(budget, EmpiricalBudget):
        if budget.protocol != protocol:
            findings.append(
                f"{relative}: the empirical budget was measured under "
                f"{budget.protocol!r} over {budget.observations} observations, "
                f"but the current protocol is {protocol!r}; one scheduler's "
                "envelope cannot license another"
            )
        elif right.cost is not None and not (
            budget.minimum <= right.cost <= budget.maximum
        ):
            moved = "above" if right.cost > budget.maximum else "BELOW"
            findings.append(
                f"{relative}: the twin cost {right.cost} inferences, {moved} "
                f"its empirical budget {budget.minimum}..{budget.maximum} "
                f"(spread {budget.spread}) measured under {budget.protocol!r} "
                f"over {budget.observations} observations; the {TOLERANCE}-"
                "inference deterministic tolerance is not added to empirical "
                "bounds"
            )
    elif right.cost is not None and abs(right.cost - budget) > TOLERANCE:
        moved = "above" if right.cost > budget else "BELOW"
        findings.append(
            f"{relative}: the twin cost {right.cost} inferences, {moved} its "
            f"pinned budget of {budget} by more than the {TOLERANCE} "
            "deterministic allowance"
        )
    if right.cost is not None and right.cost < ENGINE_FLOOR and not stated:
        findings.append(
            f"{relative}: the twin cost {right.cost} inferences, under the "
            f"{ENGINE_FLOOR} floor, so it never reached the engine; doing an "
            f"example's work in Python where Python does it is right, but an "
            f"example the library is never asked about is a residue entry"
        )
    if left.cost and right.cost is not None:
        defined = definitions(twin)
        authoring = DEFINITION_WARMUP + DEFINITION_COST * defined if defined else 0
        ceiling = left.cost * (1.0 + BAND_PERCENT / 100.0) + authoring
        if right.cost > ceiling:
            allowed = (
                f" plus {authoring} to author {defined} compiled "
                f"definition{'s' if defined != 1 else ''}"
                if authoring
                else ""
            )
            findings.append(
                f"{relative}: the twin cost {right.cost} inferences against "
                f"the example's {left.cost}, past the {BAND_PERCENT:g}% band "
                f"ceiling of {ceiling:.0f}{allowed}"
            )
    return findings


def definitions(twin: Path) -> int:
    """How many compiled definitions the twin AUTHORS.

    Counted from source, so the allowance cannot be inflated without adding a
    decorator a reader sees in the diff.
    """
    tree = _parse(twin)
    return sum(
        isinstance(node, ast.FunctionDef) and _defines(node)
        for node in ast.walk(tree)
    ) if tree else 0


# --------------------------------------------------------------------- reporting


def _folders(verdicts: list[Verdict], root: Path) -> dict[str, tuple[int, ...]]:
    """Per folder: files passing, files in the corpus, claims proved, claims made.

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
    print(f"{'example':44} {'claims':>6} {'proved':>6} {'metta':>8} {'twin':>8} {'ratio':>6}")
    for verdict in verdicts:
        ratio = verdict.ratio
        print(
            f"{verdict.example.relative_to(root)!s:44} "
            f"{verdict.forms:6} {verdict.covered:6} "
            f"{verdict.example_cost if verdict.example_cost is not None else '-':>8} "
            f"{verdict.twin_cost if verdict.twin_cost is not None else '-':>8} "
            f"{f'{ratio:.2f}' if ratio else '-':>6}"
        )

    print()
    folders = _folders(verdicts, root)
    for folder, (passing, corpus_files, covered, forms) in sorted(folders.items()):
        answering = (
            f", {covered}/{forms} claims of those files proved"
            if forms
            else ""
        )
        print(f"coverage {folder}: {passing}/{corpus_files} files{answering}")
    totals = [sum(counts[index] for counts in folders.values()) for index in range(4)]
    print(
        f"coverage TOTAL: {totals[0]}/{totals[1]} files twinned and passing, "
        f"{totals[2]}/{totals[3]} claims of those files proved"
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


def _full_lane_round(examples: list[Path], entries: list[dict]) -> list[Verdict]:
    """One observation of the same scheduler and work mix the gate runs."""
    protocol = full_lane_protocol(len(examples))
    with ThreadPoolExecutor(max_workers=FULL_LANE_WORKERS) as pool:
        return list(
            pool.map(
                lambda path: check(path, entries, protocol=protocol),
                examples,
            )
        )


def _observe(examples: list[Path], entries: list[dict], rounds: int) -> None:
    """Report empirical extrema without changing any declaration."""
    samples = {example: [] for example in examples}
    failures = {example: [] for example in examples}
    for round_number in range(1, rounds + 1):
        for verdict in _full_lane_round(examples, entries):
            if verdict.twin_cost is None:
                failed = "; ".join(
                    finding for finding in verdict.findings if "failed to run" in finding
                ) or "the lane produced no twin cost"
                failures[verdict.example].append(f"round {round_number}: {failed}")
            else:
                samples[verdict.example].append(verdict.twin_cost)

    protocol = full_lane_protocol(len(examples))
    for example in examples:
        observed = samples[example]
        failed = failures[example]
        if not observed:
            print(
                f"{example.relative_to(REPO)} protocol={protocol!r} "
                f"observations=0 failures={len(failed)} samples=[]"
            )
            continue
        minimum, maximum = min(observed), max(observed)
        print(
            f"{example.relative_to(REPO)} protocol={protocol!r} "
            f"observations={len(observed)} failures={len(failed)} "
            f"minimum={minimum} maximum={maximum} spread={maximum - minimum} "
            f"samples={observed!r}"
        )
        for failure in failed:
            print(f"  {failure}")


def main() -> int:
    """Run the lane, or measure it."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--measure", action="store_true",
                      help="print serial min-of-N point costs, and change nothing")
    mode.add_argument(
        "--observe",
        action="store_true",
        help="report repeated full-lane empirical extrema, and change nothing",
    )
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

    if arguments.observe:
        if named:
            parser.error("--observe measures the complete lane; omit individual paths")
        if arguments.rounds < 10:
            parser.error("--observe needs at least 10 full-lane observations")
        _observe(examples, residue(), arguments.rounds)
        return 0

    if arguments.measure:
        for example in examples:
            twin = twin_for(example)
            left = min(run_example(example).cost or 0 for _ in range(arguments.rounds))
            right = min(run_twin(twin).cost or 0 for _ in range(arguments.rounds))
            share = right / left if left else 0.0
            print(f"{example.relative_to(REPO)} metta={left} twin={right} ratio={share:.4f}")
        return 0

    entries = residue()
    verdicts = _full_lane_round(examples, entries)

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
