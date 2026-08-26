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
    commit=b1599bdc8201a04a3689c1a88707b6f4b53b4d22]
  - an assert-family head states one claim, and Python's `assert` is its image
    [source: engine/prelude.metta 56-103; ai-python-first-revamp-discussion.md
    section 9d rule 1, "assert and pytest for the assert family"]
Guarantees:
  - a twin that reaches the engine through MeTTa source text is REFUSED, both
    the five source doors and any string that is not a name or ground()-marked
    data [tested: test_the_source_scan_catches_a_planted_string]
  - a twin naming something the narrow core deleted is a finding that names the
    current spelling, so `val`, `sym`, `var`, `m.new_space`, `m.fn("name")`,
    `HERE`, `m.query(...)` and every `declare_*` method cannot pass as
    vocabulary [tested:
    test_a_retired_name_is_a_finding_naming_its_replacement; commit=5c67147566907276a95a5fbf059cf8f98b6685f1]
  - a twin importing the module the rename deleted is a finding, whichever
    spelling it reaches for: the distribution is `pymetta` and the module it
    installs is `metta`, so neither `petta` nor `pymetta` imports
    [tested: test_a_retired_module_import_is_a_finding; commit=5c67147566907276a95a5fbf059cf8f98b6685f1]
  - every door the surface tracks landed reads clean: the naming factories,
    the answer view with its defaulted cells, the keyword builders, the
    coordination verbs, the class door, the verdict builders under
    `@space.pre_add`, the head-named declaration methods, package `match`
    and `superpose`, `view()`, `@space.cache`, `limits(stack=)` and the
    standard-module mentions inside a compiled body
    [tested: test_the_landed_doors_read_clean; commit=0cfc68a483d8d64fb499e53bbe9a3cc63f68990f]
  - a bare vocabulary word at a head-named declaration door is a finding that
    names the exact StrEnum member, while pattern and name strings at those
    doors remain governed by the source-text rule
    [tested: test_a_bare_declaration_word_names_the_exact_member,
    test_a_declaration_takes_members_and_refuses_a_program; commit=417c6428f89aed9f514b9219db2dcd472d31fbe7]
  - a twin stating fewer claims than its example is a finding, so a skip
    cannot be silent [tested: test_a_twin_that_claims_less_is_a_finding]
  - a false claim fails the twin, because a raised AssertionError leaves the
    run in error [tested: test_a_failing_assertion_is_a_finding]
  - a twin's definitions are visible to `match` where the original's are, so a
    Python-authored definition cannot pass by hiding in Python-side state
    [tested: test_a_hidden_definition_is_a_finding]
  - answer groups compare as alpha-equivalent multisets, so renaming and
    enumeration order are irrelevant while duplicate counts remain semantic
    [tested: test_answer_multisets_ignore_order_and_alpha_names_but_keep_multiplicity;
    commit=8bfe05c3850776543ece25a85038242f10b1d841]
  - a twin writing MeTTa in Python punctuation is a finding naming the Python
    spelling it should have used [tested:
    test_a_dissolved_head_names_the_python_spelling_it_replaces,
    test_a_yielding_twin_is_a_finding]
  - empirical budgets license only the protocol that measured them, and the
    deterministic point tolerance never widens their observed extrema
    [tested: test_an_empirical_envelope_cannot_license_another_protocol;
    commit=b1599bdc8201a04a3689c1a88707b6f4b53b4d22]
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
    commit=b1599bdc8201a04a3689c1a88707b6f4b53b4d22]
  - a full-lane protocol fixes both corpus width and executor width; empirical
    observations can be reproduced with --observe [tested:
    test_the_full_lane_protocol_names_every_scheduling_input;
    commit=b1599bdc8201a04a3689c1a88707b6f4b53b4d22]
Fails when:
  - an example's answers are nondeterministically ordered, which the same
    comparison in example_parity already documents: groups are compared in
    order and a genuinely unordered answer set would read as a difference
  - a retired name can only be told from a live one by the RECEIVER'S TYPE.
    `m.space(name)` on a handle is deleted while `ctx.space(name)` is the live
    door, and reading types is not this lane's job, so the twin's own run
    reports it as `'Space' object has no attribute 'space'` instead
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
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

# The library's own word table, one source of truth: importing the mapping
# module is 17ms and boots no engine (the package root is lazy). It is what
# makes S.eq inside a compiled body the head `==`, so the lane must resolve
# the same word before its operator-head lookup or a new anti-pattern
# (spelling `a == b` as `S.eq(a, b)`) goes unreported. Script mode puts
# tools/ on sys.path rather than the package parent, so the parent is
# inserted first.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from metta._name_mapping import (  # noqa: I001  -- the path insert above is what makes the import resolve in script mode, so this line cannot join a sorted block
    attribute_name,
    operator_attribute_target,
)
from metta import vocabularies
from metta.atoms import Atom, _alpha_eq, _encode

import example_parity as parity

REPO = parity.REPO
TWINS = REPO / "bindings" / "python" / "tests" / "twins"
RESIDUE = TWINS / "residue.json"


def answer_multiset_diff(
    left: Iterable[object], right: Iterable[object]
) -> tuple[list[Atom], list[Atom]]:
    """Return unmatched answers under alpha equivalence and multiplicity.

    Enumeration order is deliberately absent from the comparison. Matching
    removes one occurrence at a time, so two copies never compare equal to one.
    """
    left_atoms = [_encode(value) for value in left]
    remaining = [_encode(value) for value in right]
    left_only: list[Atom] = []
    for atom in left_atoms:
        matched = next(
            (index for index, other in enumerate(remaining) if _alpha_eq(atom, other)),
            None,
        )
        if matched is None:
            left_only.append(atom)
        else:
            remaining.pop(matched)
    return left_only, remaining

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
#: was wrong and was right; commit=b1599bdc8201a04a3689c1a88707b6f4b53b4d22].
DEFINITION_WARMUP = 1456
DEFINITION_COST = 765

#: The tree's own POINT-counter allowance. It applies to an integer BUDGET
#: only; adding it to empirical extrema would silently widen what was observed
#: [source: bindings/python/metta/benchmarking.py _COUNTER_TOLERANCE;
#: commit=b1599bdc8201a04a3689c1a88707b6f4b53b4d22].
TOLERANCE = 4

#: A direct check is serial. The shipped lane fixes and names both its executor
#: width and corpus size, so either scheduling change invalidates an old
#: empirical claim visibly instead of changing the scheduler under one label
#: [tested: test_an_empirical_envelope_cannot_license_another_protocol;
#: commit=b1599bdc8201a04a3689c1a88707b6f4b53b4d22].
SERIAL_PROTOCOL = "serial"
FULL_LANE_PROTOCOL = "full-lane"
FULL_LANE_WORKERS = 32

#: The five doors that take MeTTa source text. A twin may not use any of them:
#: that is the whole of "zero s-expression strings". `forms` is the narrow
#: core's name for the old `parse_all`, and reads a whole program's worth of
#: source, so it belongs beside `parse` rather than outside the rule.
SOURCE_DOORS = frozenset({"run", "load", "parse", "save", "forms"})

#: Calls whose string argument is a NAME or a marked datum rather than a
#: program: `space` and `attach` name a space, and `ground`/`G` carry a Python
#: value whole. `space` takes an ATOM name too, and the ampersand belongs to
#: the STRING spelling alone: the door adds it to a symbol, which is why the
#: idiom check still reports `S["&kb"]` as a space named as a symbol
#: [measured 2026-08-24: `metta.space(S.users)` answers a handle whose `.name`
#: is '&users', and `metta.space("and-string")` refuses, naming the prefix;
#: commit=5c67147566907276a95a5fbf059cf8f98b6685f1]. The retired carriers `val`, `sym`, `var` and `new_space`
#: are NOT here; RETIRED_ROOT and RETIRED_HANDLE name them and their
#: replacements.
NAMING_CALLS = frozenset({
    "ground", "G", "space", "attach",
    # TypeVar("X") names a type variable exactly as S["x"] names an atom, and
    # a twin declaring a parametric type needs it [found 2026-08-22 by the
    # types agent, which worked around it with the name= keyword].
    "TypeVar",
    # `view(obj)` carries a Python container whole exactly as ground() carries
    # a Python value whole: it makes a LIVE provider over the object, so the
    # keys of `view({"port": 80})` are Python text and never a program
    # [source: ai-python-conventions.md 3.12, the three routes for Python data;
    # commit=5c67147566907276a95a5fbf059cf8f98b6685f1].
    "view",
})

#: Calls whose string arguments are HOST text rather than a program: a message
#: a twin prints, a filesystem path it opens. `println!` dissolves into
#: `print()` by the table below, so the scan has to let a twin print.
HOST_TEXT_CALLS = frozenset({"print", "Path", "open", "warning", "info", "debug"})

#: The head-named receiver methods that replaced the `declare_*` family: each
#: writes one declaration atom and its head IS the method name, so
#: `(capacity &pool 8)` is written `pool.capacity(8)` [source:
#: ai-narrow-core-renames.md rows 71-89, the fifteen replacements;
#: commit=5c67147566907276a95a5fbf059cf8f98b6685f1].
DECLARATION_CALLS = frozenset({
    "admits", "agenda", "algebra", "annotations", "capacity", "context",
    "emits", "events", "handles", "image", "merge", "on_error", "reaction",
    "source", "writes",
})

#: A declaration's closed option value is a StrEnum member, never its bare
#: wire string: `emits(AnswerPolicy.best_first)` and
#: `handles(pattern, Fidelity.Exact)`. The runtime accepts the equal string as
#: an escape hatch, but the authored corpus does not. The scanner keeps a bare
#: word permitted as declaration text first, then emits the more useful member
#: diagnostic for the typed option slots below; pattern and name strings do
#: not become false source findings merely because the same door also takes an
#: option [measured 2026-08-24: 0 bare option strings across all 218 twins
#: after the corpus-wide normalization pass; every generated StrEnum member is
#: a bare wire word; tested:
#: test_a_declaration_takes_members_and_refuses_a_program; commit=417c6428f89aed9f514b9219db2dcd472d31fbe7].
#:
#: A word, and nothing else: `reacts("(Job $n)", op)` still reports, because
#: a program carries a parenthesis, a space or a dollar and a vocabulary word
#: carries none of them. That is what keeps a `str | Atom` pattern parameter
#: from being a sixth source door
#: [tested: test_a_declaration_takes_members_and_refuses_a_program; commit=417c6428f89aed9f514b9219db2dcd472d31fbe7].
VOCABULARY_WORD = re.compile(r"[\w.-]+\Z")

#: The typed option slots of the head-named declaration doors. Mapping the
#: slot to the generated class makes the diagnostic use the library's own
#: exact spelling rather than a copied word table. Doors absent here take
#: names, patterns, numbers, or open user-defined vocabularies rather than a
#: closed option. The two variable-arity doors are resolved in
#: `_declaration_vocabulary_findings`.
DECLARATION_VOCABULARIES = {
    "agenda": ({0: vocabularies.AgendaPolicy}, {"policy": vocabularies.AgendaPolicy}),
    "context": ({0: vocabularies.World}, {"world": vocabularies.World}),
    "emits": ({0: vocabularies.AnswerPolicy}, {"policy": vocabularies.AnswerPolicy}),
    "events": (
        {0: vocabularies.Delivery, 1: vocabularies.EventOrder},
        {"delivery": vocabularies.Delivery, "order": vocabularies.EventOrder},
    ),
    "handles": (
        {1: vocabularies.Fidelity},
        {"fidelity": vocabularies.Fidelity, "det": vocabularies.Determinism},
    ),
    "image": ({1: vocabularies.ImageMode}, {"setting": vocabularies.ImageMode}),
    "merge": ({1: vocabularies.AnswerPolicy}, {"policy": vocabularies.AnswerPolicy}),
    "source": ({0: vocabularies.SourceKind}, {"kind": vocabularies.SourceKind}),
    "writes": ({0: vocabularies.Atomicity}, {"atomicity": vocabularies.Atomicity}),
}

#: The factories whose attribute or subscript spells a NAME rather than calling
#: a library door: `S.f` and `S["+"]` name an atom, `V.x` a variable, and
#: `fn.car_atom` and `m.fn["=="]` an engine function. A name reached through one
#: of them is never a source door, because naming a head that shares a door's
#: name builds the term instead of taking text.
NAMING_NAMESPACES = frozenset({"S", "V", "fn"})

#: The subset that mints ANY name, where attribute access reaches the same atom
#: the bracket spells. `fn` is deliberately absent: its catalog is generated and
#: closed, so a bracket name it does not alias has no attribute spelling at all
#: [source: bindings/python/metta/_name_mapping.py generated_aliases;
#: commit=8c057bb8055459cc13127d89b418deb634b90ae4].
MINTING_NAMESPACES = frozenset({"S", "V"})

#: Module-level constants a twin declares ABOUT itself rather than as
#: program text: the inference pin, and the reason it sits below the top
#: rung. Both are read from source the way the lane reads BUDGET.
DECLARATION_NAMES = frozenset({"BUDGET", "RUNG"})

#: The example heads that STATE A CLAIM. Their Python image is the `assert`
#: statement, so the lane counts them against the twin's assertions rather
#: than asking the twin to call them [source: engine/prelude.metta lines
#: 56-103, the assert family; commit=b1599bdc8201a04a3689c1a88707b6f4b53b4d22].
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
#: commit=b1599bdc8201a04a3689c1a88707b6f4b53b4d22]. A twin whose SUBJECT is one of these functions says so
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
    # One word at three positions, all three shipped: the subscript takes ONE
    # pattern, the receiver method takes a conjunction, and bare `match(...)`
    # is the expression-position function over the ambient context space
    # [source: ai-python-conventions.md Part 2, "match is one word at three
    # positions"; commit=5c67147566907276a95a5fbf059cf8f98b6685f1].
    "match": "space[pattern], space.match(...), or bare match(...) in expression position",
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
    # `if_` earns its place beside Python's own two spellings because it has
    # the arity the engine's `if` has: a one-armed `if_(c, t)` is a filter
    # Python's conditional expression cannot spell, and stored code is where
    # it is written [source: ai-python-conventions.md 3.8, the keyword family;
    # commit=5c67147566907276a95a5fbf059cf8f98b6685f1].
    "if": "Python's own if, its conditional expression, or if_(c, t, e) for stored code",
    "let": "assignment, or solve(pattern, subject) when the pattern must win what the subject produces",
    "let*": "a statement sequence",
    "case": "Python's match statement",
    "switch": "Python's match statement",
    "println!": "print()",
    "trace!": "print(), or logging",
    "format-args": "an f-string",
    "bind!": "a Python name binding",
    "new-space": "metta.space(), the one space-creation door",
    "get-type": "space.type(atom)",
    # The doc verb follows the same receiver/module pair as the type accessor:
    # a handle asks its own space and the module helper asks the process-default
    # space [tested: test_the_doc_verb_answers_the_structured_atom; commit=fa0a8c55035026a79f8fe67733332627e353872e].
    "get-doc": "space.doc(atom), or metta.doc(atom)",
}


#: Python names the narrow core DELETED, and the current spelling of each. A
#: twin naming one is writing the previous surface, and the message has to say
#: what replaced it or the author is left to guess. The table is keyed the way
#: Ruff's own TID251 `banned-api` is keyed, by the imported member, and it
#: carries that rule's honest scope: it flags accidental use and does not chase
#: every way a name could be reached [source:
#: https://docs.astral.sh/ruff/rules/banned-api; the rewrite map is
#: ai-narrow-core-renames.md's twin-visible table; commit=8c057bb8055459cc13127d89b418deb634b90ae4].
RETIRED_ROOT = {
    "Expr": "Expression",
    "Gnd": "Grounded",
    "Sym": "Symbol",
    "Var": "Variable",
    "MettaName": "Symbol",
    "SpaceName": "Handle",
    "PeTTa": "MeTTa, the runtime context",
    "DECLINE": "NotReducible",
    "Decline": "NotReducible",
    # The rename removed the root's own name for the context space. `_HERE` is
    # keyed beside it because that is how the name survived a mechanical sweep:
    # two twins reach past the root for the private atom rather than write the
    # receiver [measured 2026-08-24: `from metta.atoms import _HERE as HERE` in
    # tests/twins/reasoning/peano.py and tests/twins/reasoning/scallop_readme.py,
    # and nowhere else in the corpus; commit=5c67147566907276a95a5fbf059cf8f98b6685f1].
    "HERE": "the space handle itself; match(...) reads the ambient space",
    "_HERE": "the space handle itself; match(...) reads the ambient space",
    "REFLECTION_SPACE": "metta.reflection",
    "alpha_eq": "a.alpha_eq(b)",
    "atom_from_wire": "metta.wire.atom_from_wire(x)",
    "backend_info": "metta.engine().info()",
    "bridge": "a declaration, a fold, or the += pipe",
    "default_engine": "metta.engine()",
    "expr": "Expression(...), or calling the head",
    "fresh_space": "metta.space()",
    "is_ground": "not a.vars",
    "map_atoms": "a.map(f)",
    "object_view": "view(...)",
    "order_key": "sorted(atoms); atoms carry the engine's order",
    "parse_all": "metta.forms(source)",
    "pretty": "repr(a)",
    "record": "@space.define on the class",
    "register_object_repr": "metta.integrate.register_repr(...)",
    "register_object_repr_protocol": "metta.integrate.register_repr(...)",
    "sym": "S[...] or S.name",
    "unregister_object_repr": "metta.integrate, the owning satellite",
    "unregister_object_repr_protocol": "metta.integrate, the owning satellite",
    "val": "ground(...) or G(...)",
    "var": "V[...] or V.name",
    "variables": "a.vars",
}

#: The same table for verbs the handle lost, whose names nothing live shares.
#: These are read at every attribute position, not only at an import, because a
#: handle arrives as `twin`'s own parameter and is never imported. The verbs
#: whose names DO survive elsewhere are in RETIRED_CALL_SHAPES below, separated
#: by arity rather than by guessing the receiver's type. One case is neither:
#: `m.space(name)` on a handle is deleted while `ctx.space(name)` is the live
#: door, and only the receiver's type tells them apart, so the twin's own run
#: reports it as `'Space' object has no attribute 'space'`.
RETIRED_HANDLE = {
    "add_table": "metta.tables.add(space, head, data)",
    "disassemble": "no public door; diagnostics are internal",
    "new_space": "metta.space(name) or ctx.space(name)",
    # The rename renamed the ask itself, with no alias behind it: `Space.match`
    # is the door and `metta.match` is its ambient face
    # [measured 2026-08-24: neither `Space.query` nor `metta.query` exists;
    # source: CHANGELOG.md "Rename `Space.query` and `AsyncMeTTa.query` to
    # `match`"; commit=5c67147566907276a95a5fbf059cf8f98b6685f1].
    "query": "space.match(pattern), or space[pattern] for one pattern",
    "register_op": "space.op(...), or @space.op",
    "register_space": "metta.attach(name, provider)",
    "space_name": "space.name",
    "unregister": "space.unregister_op(...)",
    "unregister_space": "space.drop()",
    # The fifteen `declare_*` methods, each replaced by the head its atom
    # already had: the method IS the head, so `(capacity &pool 8)` is written
    # `pool.capacity(8)` and the ceremony is gone. Every entry is one row of
    # the rewrite map [source: ai-narrow-core-renames.md rows 71-89;
    # CHANGELOG.md "Remove all 15 synchronous `declare_*` methods";
    # commit=5c67147566907276a95a5fbf059cf8f98b6685f1].
    "declare_admits": "space.admits(...)",
    "declare_agenda": "space.agenda(...)",
    "declare_algebra": "space.algebra(...)",
    "declare_annotations": "space.annotations(...)",
    "declare_capacity": "space.capacity(...)",
    "declare_context": "space.context(...)",
    "declare_emits": "space.emits(...)",
    "declare_events": "space.events(...)",
    "declare_handles": "space.handles(...)",
    "declare_image": "space.image(...)",
    "declare_merge": "space.merge(...)",
    "declare_on_error": "space.on_error(...)",
    "declare_reaction": "space.reacts(...)",
    "declare_source": "space.source(...)",
    "declare_writes": "space.writes(...)",
}

#: Retired CALL SHAPES rather than retired names: each name survives on
#: another object, so only the number of POSITIONAL arguments separates the
#: deleted door from the live one. `answers.one()` and
#: `answers.first(default=...)` take none where `space.one(pattern)` took one;
#: `space.count()` took none where a sequence's own `count(value)` takes one;
#: and `fn` survives as the namespace and died as a function of a name string,
#: 366 times in the old corpus. Only a call through a RECEIVER is read, so a
#: twin's own local helper named `one` is nobody's business but its own
#: [source: bindings/python/metta/results.py Answers.one, Answers.first and
#: Answers.count; ai-report-p14-r3.md corpus counts; commit=8c057bb8055459cc13127d89b418deb634b90ae4]
#: [measured 2026-08-24: `Answers.one` and `Answers.first` are
#: `(self, *, default=...)`, so both defaults are KEYWORD-only and neither
#: live call has a positional argument to be confused with the deleted one;
#: commit=5c67147566907276a95a5fbf059cf8f98b6685f1].
RETIRED_CALL_SHAPES = {
    #  name: (positional arguments that mark the retired call, current spelling)
    "count": (0, "len(space)"),
    "first": (1, "answers.first(), or answers.first(default=...)"),
    "fn": (1, 'the fn namespace: fn.name, or fn["name"] for an exact spelling'),
    "one": (1, "answers.one(), or answers.one(default=...)"),
    "stream": (1, "iterating the answers"),
}

#: Import roots the rename deleted. The distribution is `pymetta` and the
#: module it installs is `metta`, so a twin that imports either of the old
#: names imports nothing at all; the finding says which name to write, where
#: `ModuleNotFoundError` says only that something is missing
#: [source: CHANGELOG.md "Rename the Python distribution to `pymetta` and its
#: import module to `metta` ... Neither `petta` nor `pymetta` remains an
#: importable module"; commit=5c67147566907276a95a5fbf059cf8f98b6685f1].
RETIRED_MODULES = {
    "petta": "metta",
    "pymetta": "metta",
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


def _factory(node: ast.expr) -> tuple[str, str] | None:
    """The namespace and name a factory access spells, or nothing.

    One reader for every spelling of the same door, because the namespace
    arrives bare (`S.f`, `fn["=="]`) and through a receiver (`m.fn.xor`,
    `metta.S.done`) and the rules below must not care which
    [tested: test_a_term_may_name_a_head_that_shares_a_source_doors_name;
    commit=8c057bb8055459cc13127d89b418deb634b90ae4].
    """
    if isinstance(node, ast.Attribute):
        root, name = node.value, node.attr
    elif isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant):
        if not isinstance(node.slice.value, str):
            return None
        root, name = node.value, node.slice.value
    else:
        return None
    if isinstance(root, ast.Name):
        namespace = root.id
    elif isinstance(root, ast.Attribute):
        namespace = root.attr
    else:
        return None
    return (namespace, name) if namespace in NAMING_NAMESPACES else None


#: Decorators that turn a Python body into stored equations. A string constant
#: inside one is a MeTTa string literal in an equation, the way
#: `(= (math-string) "s")` writes one, and not source text; the source doors
#: are still refused there, because a door is a call and the call rule does not
#: care where the call sits. `cache` compiles a body exactly as `define` does,
#: and `pre_add` compiles a RAW judge into the space before claiming the write
#: door, so a judge written without a `@define` beneath it is lowered too
#: [source: bindings/python/metta/_space.py Space.pre_add, "A raw function is
#: compiled into this space before claiming the hook"]
#: [measured 2026-08-24: a bare `@space.pre_add` judge stores
#: `(= (intake $a) (case ...))`, its match statement lowered to the case tower
#: and its `accept`/`refuse` verdicts intact; commit=5c67147566907276a95a5fbf059cf8f98b6685f1].
#: `rules` joined them when R3
#: landed the bundle door [source: ai-report-p14-r3.md, rules and per-yield
#: equation emission; commit=8c057bb8055459cc13127d89b418deb634b90ae4].
#:
#: A cached body still names the space its match reads, because the ambient
#: one-pattern form lowers to `(context-space)` and caching refuses that as
#: impure; the space is named by HANDLE, so the refusal costs no string
#: [measured 2026-08-24: `match(kb, S.entry(k, V.v), V.v)` under
#: `@space.cache` stores `(match &self (entry $k $v) $v)` where the
#: one-pattern form raises "caching refuses context-space/1: nothing declares
#: it pure"; found 2026-08-22 by the libraries agent, which lost the @m.cache
#: spelling and fn.cache_info() to this; commit=5c67147566907276a95a5fbf059cf8f98b6685f1].
COMPILING_DECORATORS = frozenset({"define", "cache", "pre_add", "rules"})

#: The subset whose body is LOWERED from Python syntax, where `a + b` emits
#: `(+ $a $b)`. A `@rules` body is EXECUTED instead, so its `a == b` is
#: Python's own structural equality and `.eq(...)` is the building spelling
#: there; the operator rule below would report a correct bundle
#: [source: bindings/python/metta/_rules.py rules, which calls the generator
#: with Variable arguments; commit=8c057bb8055459cc13127d89b418deb634b90ae4].
LOWERING_DECORATORS = frozenset({"define", "cache", "pre_add"})

#: Decorators whose body is HOST PYTHON rather than knowledge. An operation
#: RUNS in Python, so the `" "` in `title.replace(" ", "-")` is an argument to
#: a Python method and never a program; the guide's own exemplar for the door
#: is a string-slugging function. Without this the lane sent an author through
#: `space.op(...)`, which is what it tells a twin that wrote `register_op`, and
#: then refused the ordinary Python inside it [source: ai-python-conventions.md
#: section 3.11, the grounded boundary; commit=6b87bbfcd4666764cafe29d0f57ddf7082c33225]
#: [tested: test_a_host_operation_body_holds_python_text; commit=6b87bbfcd4666764cafe29d0f57ddf7082c33225].
HOST_BODY_DECORATORS = frozenset({"op"})

#: What the string rule reads: a compiled body's constants are MeTTa string
#: literals and a host body's are Python arguments, and neither is source text.
#: The source doors stay refused in both, because a door is a call and the call
#: rule does not care where the call sits.
LITERAL_BODY_DECORATORS = COMPILING_DECORATORS | HOST_BODY_DECORATORS


def _decorated(node: ast.FunctionDef | ast.ClassDef, names: frozenset[str]) -> bool:
    """Whether a definition carries one of `names` as a decorator."""
    for decorator in node.decorator_list:
        reached = decorator.func if isinstance(decorator, ast.Call) else decorator
        name = reached.attr if isinstance(reached, ast.Attribute) else getattr(reached, "id", None)
        if name in names:
            return True
    return False


def _prints_text(node: ast.AST | None) -> bool:
    """Whether a subtree reaches Python or MeTTa's textual repr door.

    The engine's own `repr` arrives through the function namespace as
    `m.fn.repr(atom)` or `m.fn["repr"](atom)`, so the factory reader answers
    the bracket spelling and `_callee` the attribute one.
    """
    for inner in ast.walk(node) if node is not None else ():
        if not isinstance(inner, ast.Call):
            continue
        reached = _factory(inner.func)
        if (_callee(inner) or (reached[1] if reached else None)) in {"repr", "str"}:
            return True
    return False


def _printing_strings(tree: ast.Module) -> set[int]:
    """Text literals that state what a printed atom or exception must say.

    The exemption follows data through one named fixture, enough for a table
    such as ``PRINTED = ((atom, "text"), ...)``. It does not exempt an
    unrelated string merely because the same function also prints something
    [source: ai-python-first-revamp-discussion.md section 9q.2;
    commit=b1599bdc8201a04a3689c1a88707b6f4b53b4d22].
    """
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
        # A class body's bare `balance: int` is an AnnAssign with NO value,
        # which the class door made ordinary: reading it as a subtree crashed
        # the whole lane on the first twin that declared a record
        # [tested: test_the_landed_doors_read_clean; commit=f0686267e8ecb2817758fb8a58cb9b1bef6dd6d4].
        if not isinstance(node, (ast.Assign, ast.AnnAssign)) or node.value is None:
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


def _text_ids(nodes: Iterable[ast.AST]) -> set[int]:
    """Every string constant of the given subtrees, by identity."""
    return {
        id(inner)
        for node in nodes
        for inner in ast.walk(node)
        if isinstance(inner, ast.Constant) and isinstance(inner.value, str)
    }


def _declared_strings(node: ast.Module | ast.FunctionDef | ast.ClassDef) -> set[int]:
    """The strings a definition writes ABOUT itself rather than as program text.

    The docstring; a declared rung's REASON, which is documentation exactly as
    the docstring above it is, so the source scan must not read it as a
    program; and an empirical BUDGET's protocol, which rides inside a literal
    mapping. Without the rung line the two checks contradict each other and
    declaring a rung turns the lane red, which makes the ladder's own escape
    unusable, found 2026-08-22 by two twin agents at once [tested:
    test_an_empirical_envelope_passes_its_observations_and_fails_new_spread;
    commit=6b87bbfcd4666764cafe29d0f57ddf7082c33225].
    """
    permitted: set[int] = set()
    head = node.body[0] if node.body else None
    if isinstance(head, ast.Expr) and isinstance(head.value, ast.Constant):
        permitted.add(id(head.value))
    permitted |= _text_ids(
        statement.value
        for statement in node.body
        if isinstance(statement, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id in DECLARATION_NAMES
            for target in statement.targets
        )
    )
    if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and _decorated(
        node, LITERAL_BODY_DECORATORS
    ):
        permitted |= _text_ids([node])
    return permitted


def _call_strings(node: ast.Call) -> set[int]:
    """The strings one call takes as data rather than as a program.

    A string in a KEYWORD argument is host data, never a program: the source
    doors are caught by call name, whatever shape their arguments take, so
    `names=["c-bump"]` and `path=Path("...")` need no ceremony [found
    2026-08-22 by the reasoning agent, which had to write `[S["c-bump"].name]`].
    A twin may also SAY things, since the dissolution table sends `println!` to
    print(); and a naming call takes names and marked data wherever they sit,
    keywords and nested containers included, so `space(grants=["file"])` names
    capabilities [found 2026-08-22 by the spaces agent, which had to write
    `S.file.name` to get past this]. A declaration may take one-word names and
    patterns, so a word stays permitted here; `_declaration_vocabulary_findings`
    separately rejects a bare word only in a typed option slot and names the
    exact member. A program is not a word and remains a source finding.
    """
    permitted = _text_ids(word.value for word in node.keywords)
    called = _callee(node)
    if called in HOST_TEXT_CALLS | NAMING_CALLS:
        permitted |= _text_ids([node])
    elif called in DECLARATION_CALLS:
        permitted.update(
            id(argument)
            for argument in node.args
            if isinstance(argument, ast.Constant)
            and isinstance(argument.value, str)
            and VOCABULARY_WORD.match(argument.value)
        )
    return permitted


def _member_finding(
    node: ast.expr, enum_class: type
) -> tuple[int, str] | None:
    """Name the exact member replacing one bare option string."""
    if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
        return None
    try:
        member = enum_class(node.value)
    except ValueError:
        return None
    return (
        node.lineno,
        f"the bare vocabulary word {node.value!r} is "
        f"{enum_class.__name__}.{member.name}; write the member",
    )


def _declaration_vocabulary_findings(node: ast.Call) -> list[tuple[int, str]]:
    """Bare StrEnum wire words in a declaration door's typed option slots.

    Slots matter: ``handles("Exact", Fidelity.Exact)`` may lawfully use the
    first string as a pattern, and ``det`` belongs to both Determinism and
    OpKind globally. The call and parameter position determine the member.
    """
    called = _callee(node)
    if called not in DECLARATION_CALLS:
        return []
    positional, keywords = DECLARATION_VOCABULARIES.get(called, ({}, {}))
    findings = [
        finding
        for index, argument in enumerate(node.args)
        if (enum_class := positional.get(index)) is not None
        if (finding := _member_finding(argument, enum_class)) is not None
    ]
    findings.extend(
        finding
        for keyword_argument in node.keywords
        if keyword_argument.arg is not None
        if (enum_class := keywords.get(keyword_argument.arg)) is not None
        if (finding := _member_finding(keyword_argument.value, enum_class)) is not None
    )
    if called != "on_error":
        return findings

    mode_keyword = next(
        (word for word in node.keywords if word.arg == "mode"), None
    )
    if mode_keyword is not None:
        finding = _member_finding(mode_keyword.value, vocabularies.OnError)
        return findings + ([finding] if finding is not None else [])
    if len(node.args) >= 3:
        finding = _member_finding(node.args[2], vocabularies.OnError)
    elif len(node.args) >= 2:
        finding = _member_finding(node.args[1], vocabularies.OnError)
    else:
        overloaded = next(
            (word for word in node.keywords if word.arg == "pattern_or_mode"),
            None,
        )
        finding = (
            _member_finding(overloaded.value, vocabularies.OnError)
            if overloaded is not None
            else None
        )
    return findings + ([finding] if finding is not None else [])


def _named_strings(tree: ast.Module) -> set[int]:
    """The string constants that are names, marked data, or documentation.

    Identity rather than value, so `ground("(f a)")` in one place does not
    excuse a bare `"(f a)"` in another.
    """
    permitted = _printing_strings(tree)
    for node in ast.walk(tree):
        # A raised message is prose for a reader, the same as a docstring.
        if isinstance(node, ast.Raise):
            permitted |= _text_ids([node])
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef)):
            permitted |= _declared_strings(node)
        elif isinstance(node, ast.Subscript):
            # Any subscript KEY is a name: `S["f"]` names an atom, `fn["=="]`
            # an engine function and `answers["x"]` a binding, and no door
            # takes MeTTa source text through a subscript.
            permitted.add(id(node.slice))
        elif isinstance(node, ast.Call):
            permitted |= _call_strings(node)
    return permitted


#: A line-level rung declaration, in the shape of the tree's noqa grammar.
RUNG_LINE = re.compile(r"#\s*rung:\s*\S")


#: Heads Python's own syntax already builds INSIDE A LOWERED BODY, so writing
#: them as a call or through Expression() there spells with a function what the
#: language spells with a character. The translator is the authority, not the
#: live dunder table, and the two disagree in three places
#: [measured 2026-08-24: one file per spelling under `@m.define`, read back
#: with `m.match(S['='](V.head, V.body))`. `a ** b` emits `(pow-math a b)`,
#: `a == b` emits `(py-eq a b)`, `a != b` emits `(not (py-eq a b))`, `a in b`
#: emits `(py-in a b)`, `not a` emits `(not (py-truthy a))`, and `a and b`
#: emits a `let*` over `py-truthy`; `a // b` and `a & b` REFUSE, naming
#: `floor_math(a / b)` and "MeTTa has no bitwise operators";
#: source: bindings/python/metta/_define_expression.py _BINOPS, _COMPARE,
#: _INSTEAD and _compare_link; commit=5c67147566907276a95a5fbf059cf8f98b6685f1].
#:
#: So `**` and `//` are NOT here: neither is an engine head, and demanding an
#: operator for `floor-math` would demand the one spelling the translator
#: refuses. `pow-math`, `py-eq` and `py-in` ARE, because they are exactly what
#: `**`, `==` and `in` emit. `and`, `or` and `not` stay because `&`, `|` and
#: `~` refuse inside a body, which leaves Python's own keywords as the only
#: operator spelling there; a twin that needs the bare `(and a b)` term rather
#: than Python's truthiness chain declares its rung on the line.
OPERATOR_HEADS = frozenset({
    "+", "-", "*", "/", "%", "pow-math", "==", "!=", "py-eq", "py-in",
    "<", ">", "<=", ">=", "and", "or", "not",
})


def _rung_reason(tree: ast.Module) -> str | None:
    """The twin's own declaration that it deliberately sits below the top
    rung, as `RUNG = "<reason>"`. A drop with a stated reason is
    documentation, which is why the ladder keeps every rung; a silent drop
    is the defect this check exists for.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "RUNG":
                value = node.value
                if isinstance(value, ast.Constant) and isinstance(value.value, str):
                    return value.value.strip() or None
    return None


def _subscripted_name(node: ast.Subscript) -> tuple[str, str, str] | None:
    """The namespace and name a redundant `S["foo"]` subscript spells.

    Redundant means attribute access reaches THE SAME atom. Rung 4's map is
    total, every underscore becoming a hyphen, so `S["my_var"]` is the atom
    `my_var` while `S.my_var` is `my-var`; and Python normalizes an identifier
    to NFKC while parsing, so a non-ASCII spelling changes at the attribute
    door too. Both keep the bracket, which is rung 5 doing its job
    [source: bindings/python/metta/_name_mapping.py attribute_name;
    commit=8c057bb8055459cc13127d89b418deb634b90ae4]
    [tested: test_an_exact_bracket_spelling_is_not_the_attribute_one;
    commit=8c057bb8055459cc13127d89b418deb634b90ae4].
    """
    reached = _factory(node)
    if reached is None or reached[0] not in MINTING_NAMESPACES:
        return None
    namespace, name = reached
    if name.isidentifier() and name.isascii() and not keyword.iskeyword(name) and "_" not in name:
        # An operator WORD keeps its bracket: the attribute door resolves it
        # through the word table to a DIFFERENT head (S.add is +), so
        # S["add"] is the one exact spelling of the symbol `add`. The two
        # composite words raise in the table and keep theirs the same way
        # (agent A measured following the old advice storing (= (+ 1 2) 3)).
        try:
            if operator_attribute_target(name) is not None:
                return None
        except AttributeError:
            return None
        return (namespace, name, name)
    # The map is total the OTHER way too: `S["foo-bar"]` is `S.foo_bar`,
    # because every attribute underscore becomes a hyphen. A name mixing
    # hyphens WITH underscores does not round-trip and keeps its bracket,
    # as does anything an identifier cannot spell (user, 2026-08-24: the
    # manual hyphen form where the map already serves is a finding).
    if "-" in name and "_" not in name:
        candidate = name.replace("-", "_")
        if (
            candidate.isidentifier()
            and candidate.isascii()
            and not keyword.iskeyword(candidate)
        ):
            return (namespace, name, candidate)
    return None


def _restated_define_names(node: ast.FunctionDef) -> list[tuple[int, str]]:
    """An explicit name= restating what the identifier already maps to.

    The manual half of rung 4 (user, 2026-08-24): `def find_divisor` IS
    `find-divisor`, so `name="find-divisor"` is dropped. A name the map
    cannot reach stays load-bearing - including the SOURCE identifier
    itself when it carries an underscore: `def h_old` installs `h-old`,
    so `name="h_old"` OVERRIDES the map to preserve the written head and
    is exactly the exact-name door working [measured 2026-08-24 by the
    functions twins agent, whose source-head audit needs it].
    """
    return [
        (
            decorator.lineno,
            f'name="{word.value.value}" is what '
            f"def {node.name} already names; drop it",
        )
        for decorator in node.decorator_list
        if isinstance(decorator, ast.Call)
        for word in decorator.keywords
        if word.arg == "name"
        and isinstance(word.value, ast.Constant)
        and isinstance(word.value.value, str)
        and word.value.value == attribute_name(node.name)
    ]


def _symbol_head(node: ast.expr) -> str | None:
    """The head of a term-building expression, when that head is a SYMBOL.

    `Expression((S.f, a))` says with a constructor what `S.f(a)` says with a
    call, but `Expression((V.x,))` has no shorter spelling at all: a
    variable-headed expression is the one shape the builders do not reach,
    because `Variable` is not callable
    [measured 2026-08-22: `V.x()` raises TypeError; filed as residue against
    P14.4].
    """
    reached = _factory(node)
    return reached[1] if reached is not None and reached[0] == "S" else None


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
    # term, which is inside a lowered body. Outside one `ground(5) + 5`
    # computes 10 and `S.x == 1` is Python's own structural equality, so naming
    # the head is the deliberate spelling [found 2026-08-22: 33 findings in
    # twins/libraries, every one of this shape and none of them a defect].
    lowered = {
        id(inner)
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.ClassDef))
        and _decorated(node, LOWERING_DECORATORS)
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
        if isinstance(node, ast.FunctionDef):
            findings.extend(_restated_define_names(node))
        if isinstance(node, ast.Subscript):
            reached = _factory(node)
            # A MINTING factory only: the engine's own catalog holds function
            # names such as `&&&` and `&^&`, so `fn["&&&"]` names a combinator
            # and not a space [source: bindings/python/tests/twins/libraries/
            # roman_test.py; tested: test_an_engine_function_may_be_named_with_
            # an_ampersand; commit=8c057bb8055459cc13127d89b418deb634b90ae4].
            if (
                reached is not None
                and reached[0] in MINTING_NAMESPACES
                and reached[1].startswith("&")
            ):
                findings.append((
                    node.lineno,
                    f"{reached[1]!r} names a SPACE as a symbol; a space is a "
                    f"handle, and every context-relative door hangs off it",
                ))
            redundant = _subscripted_name(node)
            if redundant is not None:
                namespace, written, attribute = redundant
                findings.append(
                    (node.lineno, f'{namespace}["{written}"] is {namespace}.{attribute}')
                )
        elif isinstance(node, ast.Call):
            parts = _expression_parts(node)
            head = _symbol_head(parts[0]) if parts else None
            if head is not None:
                findings.append(
                    (node.lineno, "Expression(...) builds what calling the head builds")
                )
            reached = _factory(node.func)
            called = reached[1] if reached is not None else None
            # An operator WORD written at a factory call resolves to its head
            # before the operator rule, so `S.eq(a, b)` in a compiled body
            # reports as the transliteration of `a == b` it now stores. Only
            # the ATTRIBUTE door consults, exactly as the compiler does:
            # `S["eq"](a, b)` is the exact door for the data symbol `eq`,
            # which the word table took from the attribute spelling, and
            # agents A and F both measured the undistinguished form
            # misreporting it. The two composite words raise in the table;
            # the compiler refuses them itself, so a raise is no resolution.
            spoken = called
            if called is not None and isinstance(node.func, ast.Attribute):
                try:
                    spoken = operator_attribute_target(called) or called
                except AttributeError:
                    spoken = called
            operator = spoken if spoken in OPERATOR_HEADS else head
            dissolved = DISSOLVED.get(called or "") or DISSOLVED.get(head or "")
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
                and id(node) in lowered
                and arity == (1 if operator == "not" else 2)
            ):
                findings.append((
                    node.lineno,
                    f"the head {operator!r} is what a Python operator writes "
                    f"inside a compiled body",
                ))
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
    CONSTANT in a position that is neither a name nor `ground()`-marked data,
    so a mention inside a comment or a docstring is not a finding and a door
    reached through a receiver is.
    """
    tree = _parse(twin)
    if tree is None:
        return ["does not parse as Python, so nothing about it can be read"]
    permitted = _named_strings(tree)
    findings: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            findings.extend(_declaration_vocabulary_findings(node))
        if (
            isinstance(node, ast.Call)
            and _callee(node) in SOURCE_DOORS
            # `S.parse(text)` BUILDS the term `(parse text)` and `m.fn.parse`
            # names the engine's own function; only a real call takes MeTTa
            # source. Without this a twin cannot name a head that shares a
            # door's name at all, because the idiom check refuses the
            # subscripted spelling too [found 2026-08-22 by the functions
            # agent, which had no other spelling for the head].
            and _factory(node.func) is None
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
                    f"the string {node.value!r} is neither a name nor ground() data",
                )
            )
    return [f"line {line}: {what}" for line, what in sorted(findings)]


def retired(twin: Path) -> list[str]:
    """Where a twin names something the narrow core deleted.

    An import from `metta` and an attribute on the handle are the two places a
    retired name can still be written and read as ordinary Python, so those are
    the two places this reads. Every finding names the current spelling, which
    is the whole value of the check: an `ImportError` three seconds later says
    the name is gone and nothing about what replaced it.

    The MODULE is read the same way and for the same reason. A twin written
    against the old package imports a name that no longer exists at all, and
    `ModuleNotFoundError: No module named 'petta'` says nothing about the
    rename that caused it.

    A FACTORY access is never either one, whatever it spells: `V.query` is the
    variable `$query` and `fn.first` is the engine's own `first`, so the tables
    are read at doors and not at names [measured 2026-08-24: reading them at
    every attribute reported both, `V.query` twice in
    tests/twins/reasoning/nilbc.py and `fn.first` wherever the catalog's own
    `first` is mentioned; commit=5c67147566907276a95a5fbf059cf8f98b6685f1].
    """
    tree = _parse(twin)
    if tree is None:
        return []
    findings: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            findings.extend(
                (node.lineno, f"{alias.name} is retired; write import {current}")
                for alias in node.names
                if (current := RETIRED_MODULES.get(alias.name.split(".")[0]))
            )
        elif isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".")[0]
            current = RETIRED_MODULES.get(root)
            if current is not None:
                findings.append(
                    (node.lineno, f"{node.module} is retired; import from {current}")
                )
            findings.extend(
                (node.lineno, f"{alias.name} is retired; write {RETIRED_ROOT[alias.name]}")
                for alias in node.names
                if root == "metta" and alias.name in RETIRED_ROOT
            )
        elif isinstance(node, ast.Attribute) and _factory(node) is None:
            package = isinstance(node.value, ast.Name) and node.value.id == "metta"
            current = RETIRED_HANDLE.get(node.attr) or (
                RETIRED_ROOT.get(node.attr) if package else None
            )
            if current is not None:
                findings.append(
                    (node.lineno, f"{node.attr} is retired; write {current}")
                )
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and _factory(node.func) is None
        ):
            shape = RETIRED_CALL_SHAPES.get(node.func.attr)
            if shape is not None and len(node.args) == shape[0]:
                findings.append(
                    (node.lineno, f"{node.func.attr}(...) is retired; write {shape[1]}")
                )
    return [f"line {line}: {what}" for line, what in sorted(set(findings))]


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
    "from metta import Expression, MeTTa, S, V\n"
    "def _key(head):\n"
    "    if isinstance(head, Expression) and head.children:\n"
    "        return f'{head.children[0]}/{len(head.children) - 1}'\n"
    "    return f'{head}/0'\n"
    "m = MeTTa(petta_path='.').self\n"
)

_EPILOGUE = (
    "for group in groups:\n"
    "    written = '" + DECLINED + "' if group is None else "
    "'(' + ' '.join(str(a) for a in group) + ')'\n"
    "    print('" + parity.MARKER + "' + written)\n"
    "print('" + COST + "' + str(spent.inferences))\n"
    "heads = {_key(row.head) for row in m.match(S['='](V.head, V.body))}\n"
    "print('" + HEADS + "' + ' '.join(sorted(heads)))\n"
)


def _read(text: str, outcome: parity.Outcome) -> Run:
    """One run's marker lines, the cost and heads read beside the groups."""
    cost: int | None = None
    heads: tuple[str, ...] = ()
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
#: both live in /usr/bin here [commit=b1599bdc8201a04a3689c1a88707b6f4b53b4d22].
#:
#: It is PASSED to the child, never written into this process. Writing it into
#: `os.environ` is what the first version did, and under pytest that escaped
#: the lane: `test_twin_coverage.py` calls run_twin, so every later test in the
#: same process lost `~/.elan/bin` from PATH and the two LeaTTa conformance
#: tests failed to find `lake` [source: bindings/python/metta/benchmarking.py
#: builds its child environment the same way and says why; commit=b1599bdc8201a04a3689c1a88707b6f4b53b4d22].
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
        f"_spec = importlib.util.spec_from_file_location('metta_twin', {str(twin)!r})\n"
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
    commit=b1599bdc8201a04a3689c1a88707b6f4b53b4d22].
    """

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
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
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
    findings += [f"{relative}: {finding}" for finding in retired(twin)]

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
    to match is wrong by this test"; commit=b1599bdc8201a04a3689c1a88707b6f4b53b4d22].
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
#: commit=b1599bdc8201a04a3689c1a88707b6f4b53b4d22].
ENGINE_FLOOR = 100


def _budget_findings(
    relative: str, twin: Path, right: Run, protocol: str
) -> list[str]:
    """The pinned-cost claim: what the twin declared against what it spent.

    The budget is TWO-SIDED. A twin that suddenly costs far less has most
    likely stopped doing the work and started answering the expected
    value, which is the failure mode a fixed public conformance corpus
    invites: "matching their text is a far cheaper route to pass the tests
    than implementing the spec" [source:
    https://www.christianfindlay.com/blog/basilisk-conformance-apology,
    the python/typing conformance suite, 2026-08; commit=c7191d87d9cbfce2870e586057168ec9103845ca]. Inferences
    are deterministic across processes here, so pinning both sides costs
    nothing in flakiness and catches a twin that stopped being one. The
    benchmark baseline adopted the same two-sided band on 2026-08-25, after
    a stale-high pin (file-load at 8704891 against a 722264 tree) sat
    green for days and masked that margin of regression headroom
    [source: metta/benchmarking.py, _compare_counter].
    """
    try:
        budget = budget_of(twin)
    except (TypeError, ValueError) as error:
        # A malformed declaration reports the error and stops there; reading it
        # as a number below raised TypeError out of the lane instead
        # [tested: test_a_malformed_budget_is_reported_and_not_a_traceback;
        # commit=8c057bb8055459cc13127d89b418deb634b90ae4].
        return [f"{relative}: {error}"]
    if budget is None:
        return [f"{relative}: the twin states no BUDGET"]
    if isinstance(budget, EmpiricalBudget):
        if budget.protocol != protocol:
            return [
                f"{relative}: the empirical budget was measured under "
                f"{budget.protocol!r} over {budget.observations} observations, "
                f"but the current protocol is {protocol!r}; one scheduler's "
                "envelope cannot license another"
            ]
        if right.cost is not None and not (
            budget.minimum <= right.cost <= budget.maximum
        ):
            moved = "above" if right.cost > budget.maximum else "BELOW"
            return [
                f"{relative}: the twin cost {right.cost} inferences, {moved} "
                f"its empirical budget {budget.minimum}..{budget.maximum} "
                f"(spread {budget.spread}) measured under {budget.protocol!r} "
                f"over {budget.observations} observations; the {TOLERANCE}-"
                "inference deterministic tolerance is not added to empirical "
                "bounds"
            ]
    elif right.cost is not None and abs(right.cost - budget) > TOLERANCE:
        moved = "above" if right.cost > budget else "BELOW"
        return [
            f"{relative}: the twin cost {right.cost} inferences, {moved} its "
            f"pinned budget of {budget} by more than the {TOLERANCE} "
            "deterministic allowance"
        ]
    return []


def _price(
    relative: str,
    twin: Path,
    left: Run,
    right: Run,
    stated: bool = False,  # noqa: FBT001, FBT002  -- one flag, and the call site reads better positionally than with a keyword
    *,
    protocol: str = SERIAL_PROTOCOL,
) -> list[str]:
    """The three cost claims: the pinned budget, the engine floor, and the band
    against the original.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    findings = _budget_findings(relative, twin, right, protocol)
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
    decorator a reader sees in the diff. A decorated CLASS, a `@rules` bundle
    and a raw `@space.pre_add` judge author equations the same way a decorated
    function does, so the count reads every door in COMPILING_DECORATORS
    [assumed 2026-08-24: the per-definition figure below was measured on
    `@define` functions and is applied to the class, bundle and judge doors
    without a second measurement; the band is loosened, never tightened, by the
    extension; commit=5c67147566907276a95a5fbf059cf8f98b6685f1].
    """
    tree = _parse(twin)
    return sum(
        isinstance(node, (ast.FunctionDef, ast.ClassDef))
        and _decorated(node, COMPILING_DECORATORS)
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
    samples: dict[Path, list[int]] = {example: [] for example in examples}
    failures: dict[Path, list[str]] = {example: [] for example in examples}
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
        missed = failures[example]
        if not observed:
            print(
                f"{example.relative_to(REPO)} protocol={protocol!r} "
                f"observations=0 failures={len(missed)} samples=[]"
            )
            continue
        minimum, maximum = min(observed), max(observed)
        print(
            f"{example.relative_to(REPO)} protocol={protocol!r} "
            f"observations={len(observed)} failures={len(missed)} "
            f"minimum={minimum} maximum={maximum} spread={maximum - minimum} "
            f"samples={observed!r}"
        )
        for failure in missed:
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
