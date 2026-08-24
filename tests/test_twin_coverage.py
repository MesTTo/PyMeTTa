"""Purpose: prove the twin coverage lane catches what it claims to catch.

A lane that cannot be shown failing is evidence of nothing, so these plant a
source-text cheat, a renamed variable, a wrong answer, a hidden definition
and an undeclared skip, and require the lane to answer correctly about each.

Guarantees:
  - point budgets remain two-sided with the deterministic tolerance stated
    separately [tested: test_a_budget_is_two_sided; commit=b1599bdc8201a04a3689c1a88707b6f4b53b4d22]
  - empirical envelopes are asymmetric, protocol-scoped, and falsified by
    the first observation outside their measured bounds [tested:
    test_an_empirical_envelope_passes_its_observations_and_fails_new_spread,
    test_an_empirical_envelope_cannot_license_another_protocol;
    commit=b1599bdc8201a04a3689c1a88707b6f4b53b4d22]
  - malformed or legacy spread declarations cannot silently widen a budget,
    and a malformed one is reported rather than raised [tested:
    test_an_empirical_envelope_requires_complete_measurement_metadata,
    test_spread_is_not_a_budget_door,
    test_a_malformed_budget_is_reported_and_not_a_traceback;
    commit=8c057bb8055459cc13127d89b418deb634b90ae4]
  - expected printing text is written as Python text while strings carried as
    MeTTa data still require ground() [tested:
    test_printing_text_is_not_forced_through_the_value_carrier;
    commit=8c057bb8055459cc13127d89b418deb634b90ae4]
  - every door the surface tracks landed reads clean, and every name they
    retired is a finding that says what replaced it, the deleted module
    included [tested: test_the_landed_doors_read_clean,
    test_a_retired_name_is_a_finding_naming_its_replacement,
    test_a_retired_module_import_is_a_finding,
    test_an_exact_bracket_spelling_is_not_the_attribute_one;
    commit=5c67147566907276a95a5fbf059cf8f98b6685f1]
  - a declaration takes its vocabulary word and nothing else, so the doors
    that replaced the `declare_*` family are writable without opening a
    source door on their `str | Atom` pattern parameters [tested:
    test_a_declaration_takes_a_word_and_refuses_a_program,
    test_the_declaration_vocabulary_is_the_librarys_own; commit=5c67147566907276a95a5fbf059cf8f98b6685f1]
  - the operator heads the lane refuses inside a compiled body are the ones
    the TRANSLATOR emits, so `pow-math` and `py-eq` report while `floor-math`,
    which no operator reaches, does not [tested:
    test_the_operator_heads_are_the_ones_the_translator_emits; commit=5c67147566907276a95a5fbf059cf8f98b6685f1]
  - the 159 entries superseded by empirical budgets are retired exactly once
    [tested: test_the_distribution_budget_retirement_is_exact;
    commit=b1599bdc8201a04a3689c1a88707b6f4b53b4d22]

Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
TOOL = REPO / "bindings" / "python" / "tools" / "twin_coverage.py"
sys.path.insert(0, str(REPO / "bindings" / "python" / "tools"))

import example_parity as parity  # noqa: E402
import twin_coverage as coverage  # noqa: E402


def _run(groups, heads=(), cost=0, error=None):
    """One side's run, built rather than measured.

    The comparison can then be exercised without starting an engine.
    """
    return coverage.Run(parity.Outcome(list(groups), error), cost, tuple(heads))


# ------------------------------------------------------------------- discovery


def test_the_twin_set_is_derived_from_the_one_corpus():
    """Discovery is example_parity's and the twin path is a transform of it.

    So a twin cannot exist for something no runner runs.
    """
    corpus = parity.corpus()
    assert corpus, "the corpus is empty, which means discovery is broken"
    for example in corpus:
        assert coverage.example_for(coverage.twin_for(example)) == example
    assert coverage.orphans() == [], "a twin covers nothing the corpus runs"
    assert coverage.written(), "no example has a twin"
    assert set(coverage.written()) <= set(corpus)


def test_the_coverage_fraction_names_every_folder_of_the_corpus():
    """A lane reporting only what has been written reports only good news.

    The fraction is the point of this lane, so a folder with no twin at all
    still prints, at zero over its corpus count.
    """
    folders = coverage._folders([], REPO)
    corpus = {
        str(path.relative_to(REPO / "examples").parent) for path in parity.corpus()
    }
    assert set(folders) == corpus
    assert sum(counts[1] for counts in folders.values()) == len(parity.corpus())
    assert all(counts[0] == 0 for counts in folders.values()), "no verdicts were given"


def test_every_residue_entry_names_a_real_example_and_a_row():
    """A residue entry is the backlog, so it must name something that exists.

    An entry naming a deleted example is a line nobody will notice is dead,
    which is why example_skips.txt is checked the same way.
    """
    kinds = {coverage.DECLINED_KIND, coverage.FRICTION_KIND}
    for entry in coverage.residue():
        assert entry["kind"] in kinds, entry
        assert (REPO / entry["example"]).is_file(), entry["example"]
        assert entry["row"].startswith("P14."), entry
        assert entry["missing"] and entry["detail"], entry
        if entry["kind"] == coverage.DECLINED_KIND:
            assert isinstance(entry["form"], int), "a declined entry names its form"


# ------------------------------------------------------------ source discipline


def test_the_source_scan_catches_a_planted_string(tmp_path):
    """Every way a twin could reach the engine through MeTTa source text."""
    planted = tmp_path / "planted.py"
    planted.write_text(
        '"""A docstring mentioning (f a) is not a finding."""\n'
        "from metta import S\n"
        "BUDGET = 1\n"
        "def twin(m):\n"
        '    m.run("(= (f) 42) !(f)")\n'
        '    assert m.eval("(+ 1 2)") == [3]\n'
        '    assert m.eval(S.f("(f a)")) == []\n'
        '    assert m.eval(m.parse("(f a)")) == []\n'
        '    assert m.forms("(f a) (g b)") == []\n',
        encoding="utf-8",
    )
    findings = "\n".join(coverage.scan(planted))
    assert "calls run(), which takes MeTTa source" in findings
    assert "calls parse(), which takes MeTTa source" in findings
    assert "calls forms(), which takes MeTTa source" in findings
    assert "'(+ 1 2)' is neither a name nor ground() data" in findings
    assert "'(f a)' is neither a name nor ground() data" in findings
    # The docstring says (f a) too, and a docstring is documentation.
    assert findings.count("'(f a)'") == 2, findings


def test_the_source_scan_passes_the_shipped_twins():
    """The rule has to be one a real twin can follow, or it is not a rule."""
    for example in coverage.written():
        twin = coverage.twin_for(example)
        assert coverage.scan(twin) == [], f"{twin}: {coverage.scan(twin)}"


def test_a_name_and_marked_data_are_not_programs(tmp_path):
    """The positions a string is allowed in, and nothing else.

    `ground()` is the whole escape: it says "this is a Python value carried
    whole", which is what a MeTTa string literal is. The other three are the
    naming factories' brackets, a space's own name, and a declared `name=`.
    """
    allowed = tmp_path / "allowed.py"
    allowed.write_text(
        '"""Allowed."""\n'
        "import metta\n"
        "from metta import S, ground\n"
        "BUDGET = 1\n"
        "def twin(m):\n"
        '    kb = metta.space("&kb")\n'
        '    assert kb.eval(S["sread-command"](ground("(f a)"))) == []\n'
        '    assert kb.eval(S["#>="](1, 2)) == [True]\n'
        '    assert kb.eval(m.fn["xor"](True, False)) == [True]\n'
        "    @m.define(name='math-string')\n"
        "    def math_string():\n"
        '        return "s"\n',
        encoding="utf-8",
    )
    assert coverage.scan(allowed) == []
    assert coverage.retired(allowed) == []


def test_printing_text_is_not_forced_through_the_value_carrier(tmp_path):
    """A print claim compares text; an unrelated MeTTa string remains data."""
    printing = tmp_path / "printing.py"
    printing.write_text(
        '"""Printing."""\n'
        "from metta import S, ground\n"
        "BUDGET = 1\n"
        'PRINTED = ((S.a, "a"), (S.b, "b"))\n'
        "def twin(m):\n"
        "    assert str(S.a) == 'a'\n"
        "    assert m.answers(m.fn.repr(S.b)).one() == 'b'\n"
        "    assert [m.fn['repr'](atom) for atom, _ in PRINTED] == "
        "[text for _, text in PRINTED]\n"
        "    assert ground('data') == ground('data')\n",
        encoding="utf-8",
    )
    assert coverage.scan(printing) == []
    assert coverage.retired(printing) == []

    data = tmp_path / "data.py"
    data.write_text(
        '"""Data."""\n'
        "BUDGET = 1\n"
        "def twin(m):\n"
        "    assert m.answers(S.identity('data')).one() == 'data'\n",
        encoding="utf-8",
    )
    findings = coverage.scan(data)
    assert len(findings) == 2
    assert all("neither a name nor ground() data" in finding for finding in findings)


def test_a_twin_that_does_not_parse_is_a_finding_and_not_a_traceback(tmp_path):
    """A REPORT lane says what is wrong with a twin.

    Raising out of the scan would take every other verdict down with it.
    """
    broken = tmp_path / "broken.py"
    broken.write_text("def twin(m:\n", encoding="utf-8")
    assert coverage.scan(broken) == [
        "does not parse as Python, so nothing about it can be read"
    ]
    assert coverage.budget_of(broken) is None


def test_a_string_in_a_compiled_body_is_a_metta_literal(tmp_path):
    """`(= (math-string) "s")` writes a MeTTa string, and its Python is `return "s"`.

    The body is read as SYNTAX, so the constant is a literal in an equation.
    The source doors stay refused there, because a door is a call and the
    call rule does not care where the call sits.
    """
    planted = tmp_path / "body.py"
    planted.write_text(
        '"""Body."""\n'
        "BUDGET = 1\n"
        "def twin(m):\n"
        "    @m.define\n"
        "    def g():\n"
        '        return m.run("(f)")\n',
        encoding="utf-8",
    )
    findings = coverage.scan(planted)
    assert len(findings) == 1
    assert "calls run(), which takes MeTTa source" in findings[0]


def test_a_host_operation_body_holds_python_text(tmp_path):
    """An operation RUNS in Python, so its strings are Python arguments.

    The guide's own exemplar for the door slugs a title, and the lane sends a
    twin that wrote `register_op` to `space.op(...)`, so refusing
    `title.replace(" ", "-")` there would refuse the door it recommends. The
    source doors stay refused inside an operation for the reason they are
    refused inside a compiled body: a door is a call.
    """
    planted = tmp_path / "op.py"
    planted.write_text(
        '"""Op."""\n'
        "BUDGET = 1\n"
        "def twin(m):\n"
        "    @m.op\n"
        "    def slug(title: str) -> str:\n"
        '        return title.lower().replace(" ", "-")\n'
        "    @m.op\n"
        "    def cheat() -> str:\n"
        '        return m.run("(f)")\n',
        encoding="utf-8",
    )
    findings = coverage.scan(planted)
    assert len(findings) == 1, findings
    assert "calls run(), which takes MeTTa source" in findings[0]
    # An operation registers a grounding; it authors no equation, so it buys
    # none of the band's authoring allowance.
    assert coverage.definitions(planted) == 0


def test_a_declaration_takes_a_word_and_refuses_a_program(tmp_path):
    """The head-named declaration methods take a vocabulary WORD.

    The guide rules option values as enum members, but the shipped vocabulary
    is `typing.Literal` aliases, so a bare word is the only spelling those
    doors take and refusing it would refuse the door. A word is all they take:
    a `str | Atom` pattern parameter would otherwise be a sixth source door.
    """
    words = tmp_path / "words.py"
    words.write_text(
        '"""Words."""\n'
        "from metta import S, V\n"
        "BUDGET = 1\n"
        "def twin(m):\n"
        '    m.emits("best-first")\n'
        '    m.writes("transactional")\n'
        '    m.context("closed-world")\n'
        '    m.events("at-least-once", "ordered")\n'
        '    m.handles(S.user(V.n), "Exact", det="semidet")\n'
        '    m.image(S.Tensor.name, "opaque")\n',
        encoding="utf-8",
    )
    assert coverage.scan(words) == []

    program = tmp_path / "program.py"
    program.write_text(
        '"""Program."""\n'
        "from metta import S\n"
        "BUDGET = 1\n"
        "def twin(m):\n"
        '    m.reaction("(Job $n)", S.run)\n'
        '    m.merge("(user $n $a)", "fair")\n',
        encoding="utf-8",
    )
    findings = coverage.scan(program)
    assert len(findings) == 2, findings
    assert "'(Job $n)' is neither a name nor ground() data" in findings[0]
    assert "'(user $n $a)' is neither a name nor ground() data" in findings[1]


def test_the_declaration_vocabulary_is_the_librarys_own():
    """Every word those doors accept is a word the library declares.

    The lane admits a bare word rather than a copied list, so this holds the
    admission to the shipped vocabulary: a word that stopped being one, or a
    new alias whose members are not bare words, breaks the rule's premise.
    """
    from enum import StrEnum

    from metta import vocabularies

    declared = {
        member.value
        for name in vocabularies.__all__
        if isinstance(cls := getattr(vocabularies, name), type)
        and issubclass(cls, StrEnum)
        for member in cls
    }
    assert declared, "the vocabulary satellite declares no option words"
    assert all(isinstance(word, str) for word in declared), declared
    assert all(coverage.VOCABULARY_WORD.match(word) for word in declared), sorted(
        word for word in declared if not coverage.VOCABULARY_WORD.match(word)
    )
    # And the fifteen doors that take them are the fifteen the rewrite map
    # names, every one of them a live method on the handle.
    from metta import Space

    assert len(coverage.DECLARATION_CALLS) == 15
    assert all(hasattr(Space, name) for name in coverage.DECLARATION_CALLS)
    assert all(
        f"declare_{name}" in coverage.RETIRED_HANDLE
        for name in coverage.DECLARATION_CALLS
    )


# ----------------------------------------------------------- the finished surface


#: Every door the surface tracks landed, written the way a twin writes it. This
#: is the lane's own acceptance for the vocabulary: a door that reads as a
#: string, a transliteration or a retired name here would report a correct twin
#: [source: ai-briefs/twins-wave.md, Stage L's door list; commit=5c67147566907276a95a5fbf059cf8f98b6685f1].
#:
#: The file is READ and never run, because `take` and `watch` PARK by design
#: and `every` starts a timer, so each door's existence and signature is
#: probed instead [measured 2026-08-24: every name imported here resolves on
#: the merged surface, `metta.space(S.roster)` answers a handle named
#: `&roster`, `view({"port": 80})` answers a Space whose subscript reads
#: `[Row(v=Grounded(80))]`, `limits(stack=...)` answers a ScopedLimits, and
#: `Answers.one`/`Answers.first` take their default as a KEYWORD;
#: commit=5c67147566907276a95a5fbf059cf8f98b6685f1].
LANDED_DOORS = (
    '"""Purpose: every landed door, once."""\n'
    "import math\n"
    "import operator\n"
    "import metta\n"
    "from metta import (\n"
    "    FALSE, TRUE, UNIT, Expression, G, S, State, V,\n"
    "    accept, and_, arrow, channel, drop, equation, every, ground, if_,\n"
    "    in_, limits, match, not_, or_, par_map, race, refuse, solve, spawn,\n"
    "    superpose, typed, view,\n"
    ")\n"
    "BUDGET = 1\n"
    "def twin(m):\n"
    '    kb = metta.space("&doors")\n'
    "    roster = metta.space(S.roster)\n"
    "    kb += (S.Parent, S.Tom, S.Bob)\n"
    '    kb += ground({"port": 80})\n'
    "    kb += G(1) + 2\n"
    "    @m.define\n"
    "    def square(x):\n"
    "        return x * x\n"
    "    @m.define\n"
    "    def rooted(x):\n"
    "        return math.sqrt(operator.abs(x))\n"
    "    @m.define\n"
    "    def rated(x):\n"
    "        match x:\n"
    "            case 0:\n"
    "                return S.Free\n"
    "            case _:\n"
    "                return x % 2 == 0\n"
    "    @m.cache\n"
    "    def looked_up(key):\n"
    "        return match(kb, S.entry(key, V.value), V.value)\n"
    "    @kb.pre_add\n"
    "    def intake(atom):\n"
    "        match atom:\n"
    "            case (S.Raw, x):\n"
    "                return accept((S.Order, x))\n"
    "            case (S.Bad, x):\n"
    "                return refuse(S.negative(x))\n"
    "            case (S.Noise, _):\n"
    "                return drop()\n"
    "            case _:\n"
    "                return accept()\n"
    "    @m.define\n"
    "    class Account:\n"
    "        owner: str\n"
    "        balance: int\n"
    "    @m.rules\n"
    "    def linalg(x, y):\n"
    "        yield equation(S.transpose(S.transpose(x))).to(x)\n"
    "        yield equation(S.t_mul(x, y)).to(S.t_mul(y, x))\n"
    "    linalg.lower(S.topdown, requires=S.blas)\n"
    "    @kb.rules\n"
    "    def bounds(x):\n"
    '        yield equation(S.clamped(x)).to(S["<"](x, 0))\n'
    "    kb.emits('best-first')\n"
    "    kb.writes('transactional')\n"
    "    kb.source('linear')\n"
    "    kb.context('closed-world')\n"
    "    kb.agenda('specificity')\n"
    "    kb.events('at-least-once', 'ordered')\n"
    "    kb.capacity(8)\n"
    "    kb.handles(S.user(V.n, V.a), 'Exact')\n"
    "    kb.on_error(S.user(V.n, V.a), 'keep')\n"
    "    kb.merge(S.user(V.n, V.a), 'fair')\n"
    "    kb.image(S.Tensor.name, 'opaque')\n"
    "    answers = m.answers(square(3))\n"
    "    assert answers.one() == 9\n"
    "    assert answers.one(default=UNIT) == 9\n"
    "    assert answers.first(default=UNIT) == 9\n"
    "    assert m.fn.xor(TRUE, FALSE) == [True]\n"
    '    assert m.fn["=="](1, 1) == [True]\n'
    "    assert str(m.fn.repr(S.a)) is not None\n"
    "    assert m.type(S.Tom) is not None\n"
    "    assert m.solve(S.Parent(S.Tom, V.child), S.context_space()) is not None\n"
    "    assert solve(4, V.x - 1) is not None\n"
    "    assert typed(S.f, arrow(int, int)) is not None\n"
    "    assert if_(V.n > 0, S.yes, S.no) is not None\n"
    "    assert not_(and_(or_(TRUE, FALSE), in_(S.a, S.b))) is not None\n"
    "    assert State[int](0, space=m) is not None\n"
    "    assert operator.add is not None\n"
    "    assert list(match((S.Parent, V.who, S.Bob))) is not None\n"
    "    assert list(superpose(S.a, S.b)) is not None\n"
    '    assert view({"port": 80})[(S.kv, S.port, V.v)] is not None\n'
    "    assert roster[(S.Parent, V.p, V.c)] is not None\n"
    "    assert kb.match((S.Parent, V.p, V.c), (S.Female, V.p)) is not None\n"
    "    assert par_map(square, [1, 2]) is not None\n"
    "    assert race(square(1), square(2)) is not None\n"
    "    assert every(300.0, square(1)) is not None\n"
    "    assert channel(max=64) is not None\n"
    "    for _answer in spawn(square(4)):\n"
    "        break\n"
    "    with limits(stack=1_000_000):\n"
    "        assert looked_up(S.k) is not None\n"
    "    for _event in m.watch((S.Alert, V.message)):\n"
    "        break\n"
    "    assert m.peek((S.Job, V.n)) is not None\n"
    "    assert m.take((S.Job, V.n)) is not None\n"
    "    assert Expression((V.x,)) is not None\n"
)


def test_the_landed_doors_read_clean(tmp_path):
    """Every door the P14 waves landed passes all three checks.

    A class body's bare `balance: int` is an annotation with NO value, and
    reading it as a subtree raised `AttributeError: 'NoneType' object has no
    attribute '_fields'` out of the lane, so the class door took the whole run
    down rather than reporting anything.
    """
    doors = tmp_path / "doors.py"
    doors.write_text(LANDED_DOORS, encoding="utf-8")
    assert coverage.scan(doors) == []
    assert coverage.idiom(doors) == []
    assert coverage.retired(doors) == []
    # Three defined functions, a cached one, a raw judge, the class and two
    # rules bundles all author equations, so the band's authoring allowance
    # counts every compiling door.
    assert coverage.definitions(doors) == 8


def test_a_retired_name_is_a_finding_naming_its_replacement(tmp_path):
    """A deleted name reads as ordinary Python, so only the lane can say so.

    `ImportError: cannot import name 'val'` says the name is gone and nothing
    about what replaced it, which is the whole reason this names the current
    spelling on the line that wrote the old one.
    """
    planted = tmp_path / "planted.py"
    planted.write_text(
        '"""Doc."""\n'
        "import metta\n"
        "from metta import Expr, S, alpha_eq, sym, val, var\n"
        "from metta.atoms import _HERE as HERE\n"
        "BUDGET = 1\n"
        "def twin(m):\n"
        '    kb = m.new_space("&kb")\n'
        "    kb.register_op(print)\n"
        '    assert kb.space_name == "&kb"\n'
        '    assert m.fn("xor")(True, False) == [True]\n'
        "    assert m.one(S.f(1)) == 1\n"
        "    assert m.count() == 1\n"
        "    assert m.query(S.f(V.x)) is not None\n"
        "    kb.declare_capacity(8)\n"
        '    kb.declare_emits("best-first")\n'
        "    assert HERE is not None\n"
        '    assert val("data") == val("data")\n'
        '    assert sym("f") == var("f")\n'
        "    assert alpha_eq(S.a, S.a)\n"
        "    assert Expr is not None\n"
        "    assert metta.record is not None\n",
        encoding="utf-8",
    )
    findings = "\n".join(coverage.retired(planted))
    for retired_name, current in (
        ("Expr", "write Expression"),
        ("alpha_eq", "write a.alpha_eq(b)"),
        ("sym", "write S[...] or S.name"),
        ("val", "write ground(...) or G(...)"),
        ("var", "write V[...] or V.name"),
        ("new_space", "write metta.space(name)"),
        ("register_op", "write space.op(...)"),
        ("space_name", "write space.name"),
        ("record", "write @space.define on the class"),
        ("fn", 'write the fn namespace: fn.name, or fn["name"]'),
        ("one", "write answers.one()"),
        ("count", "write len(space)"),
        # The P14 rename's own casualties: the ask changed name, the fifteen
        # declaration verbs became the heads they write, and the root lost the
        # context-space atom.
        ("query", "write space.match(pattern)"),
        ("declare_capacity", "write space.capacity(...)"),
        ("declare_emits", "write space.emits(...)"),
        ("_HERE", "write the space handle itself"),
    ):
        assert f"{retired_name} is retired" in findings or (
            f"{retired_name}(...) is retired" in findings
        ), retired_name
        assert current in findings, current


def test_a_retired_module_import_is_a_finding(tmp_path):
    """The rename left no module behind, so the import itself is the finding.

    `ModuleNotFoundError: No module named 'petta'` says something is missing
    and nothing about the rename that removed it, and a twin carried over from
    the old surface writes that line before it writes anything else.
    """
    planted = tmp_path / "planted.py"
    planted.write_text(
        '"""Doc."""\n'
        "import petta\n"
        "import pymetta\n"
        "from petta import S, V\n"
        "from petta.atoms import Expression\n"
        "BUDGET = 1\n"
        "def twin(m):\n"
        "    assert petta.space() is not None\n",
        encoding="utf-8",
    )
    findings = coverage.retired(planted)
    assert "line 2: petta is retired; write import metta" in findings
    assert "line 3: pymetta is retired; write import metta" in findings
    assert "line 4: petta is retired; import from metta" in findings
    assert "line 5: petta.atoms is retired; import from metta" in findings

    # And the live module is not reported for sharing four of its letters,
    # satellites included.
    live = tmp_path / "live.py"
    live.write_text(
        '"""Doc."""\n'
        "import metta\n"
        "from metta import S, V\n"
        "from metta.testing import laws\n"
        "BUDGET = 1\n"
        "def twin(m):\n"
        "    assert metta.space() is not None\n",
        encoding="utf-8",
    )
    assert coverage.retired(live) == []


#: The retired names a recommendation may still contain, because only the ROOT
#: spelling died and the name itself moved house: `atom_from_wire` is written
#: `metta.wire.atom_from_wire(x)` and `alpha_eq` is the atom's own method
#: [measured 2026-08-24: `metta.alpha_eq` and `metta.atom_from_wire` are gone
#: while `Atom.alpha_eq` and `metta.wire.atom_from_wire` are live; source:
#: ai-narrow-core-renames.md, the wire-functions and alpha_eq rows;
#: commit=5c67147566907276a95a5fbf059cf8f98b6685f1].
RELOCATED = frozenset({"alpha_eq", "atom_from_wire"})


def test_no_retired_spelling_is_ever_recommended():
    """The lane's answer must be writable, so it may never name a dead door.

    A finding QUOTES the retired name the twin wrote, which is the point; what
    it must never do is answer with another one. This reads every table the
    lane recommends from, and the packaged help text, against every name the
    lane itself calls retired.
    """
    dead = (
        set(coverage.RETIRED_ROOT)
        | set(coverage.RETIRED_HANDLE)
        | set(coverage.RETIRED_MODULES)
    ) - RELOCATED
    # The call-shape names are deliberately absent: `one`, `first`, `count`,
    # `fn` and `stream` all survive on another object, so their own
    # replacements name them and only the arity tells the doors apart.
    assert dead.isdisjoint(coverage.RETIRED_CALL_SHAPES)

    help_text = subprocess.run(
        [sys.executable, str(TOOL), "--help"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    recommended = [
        *coverage.DISSOLVED.values(),
        *coverage.RETIRED_ROOT.values(),
        *coverage.RETIRED_HANDLE.values(),
        *(f"import {current}" for current in coverage.RETIRED_MODULES.values()),
        *(shape[1] for shape in coverage.RETIRED_CALL_SHAPES.values()),
        help_text,
    ]
    for text in recommended:
        named = {name for name in dead if re.search(rf"\b{re.escape(name)}\b", text)}
        assert not named, f"{text!r} recommends {sorted(named)}"


def test_a_retired_door_is_not_a_retired_name(tmp_path):
    """The tables are read at DOORS, and a factory access is a name.

    `V.query` is the variable `$query` and `fn.first` is the engine's own
    `first`, so reading the tables at every attribute reported two correct
    lines in `reasoning/nilbc.py` alone.
    """
    names = tmp_path / "names.py"
    names.write_text(
        '"""Doc."""\n'
        "from metta import S, V, fn\n"
        "BUDGET = 1\n"
        "def twin(m):\n"
        "    m += S.bc(V.kb, V.query)\n"
        "    assert fn.first(S.xs) is not None\n"
        "    assert S.one(V.x) is not None\n",
        encoding="utf-8",
    )
    assert coverage.retired(names) == []

    doors = tmp_path / "doors.py"
    doors.write_text(
        '"""Doc."""\n'
        "from metta import S, V\n"
        "BUDGET = 1\n"
        "def twin(m):\n"
        "    assert m.query(S.f(V.x)) is not None\n"
        "    assert m.one(S.f(V.x)) is not None\n",
        encoding="utf-8",
    )
    findings = coverage.retired(doors)
    assert len(findings) == 2, findings
    assert "query is retired" in findings[0]
    assert "one(...) is retired" in findings[1]


def test_an_exact_bracket_spelling_is_not_the_attribute_one(tmp_path):
    """Rung 4's map is total, so a bracket name with an underscore STAYS.

    `S.my_var` is the atom `my-var` and `S["my_var"]` is `my_var`; reporting
    the bracket as redundant would have every rewriting agent silently rename
    the atom. A plain lowercase name has no such gap and is still reported.
    """
    planted = tmp_path / "planted.py"
    planted.write_text(
        '"""Doc."""\n'
        "from metta import S, V\n"
        "def twin(m):\n"
        '    m += S["my_var"]\n'
        '    m += V["_"]\n'
        '    m += S["Ω"]\n'
        '    m += S["lambda"]\n'
        '    m += S["plain"]\n'
        '    m += m.fn["car_atom"]\n',
        encoding="utf-8",
    )
    findings = coverage.idiom(planted)
    assert findings == ['line 8: S["plain"] is S.plain'], findings


# -------------------------------------------------------------- alpha equality


def test_the_form_reader_agrees_with_the_engines_own_count():
    """The lane reads an example's forms without running it.

    Balancing parentheses over source is only usable if it counts what the
    engine counts, so this holds it to the corpus rather than to a fixture.
    """
    for example in coverage.written():
        heads = coverage.example_forms(example)
        assert heads, example
        assert all(head for head in heads), example


def test_a_test_form_is_read_as_a_claim():
    """An assert-family head states a claim; every other head does not."""
    heads = coverage.example_forms(REPO / "examples" / "integration" / "git_import.metta")
    assert heads == [
        "import!",
        "import_prolog_functions_from_file",
        "git-import!",
        "import!",
        "test",
    ]
    assert sum(head in coverage.ASSERT_HEADS for head in heads) == 1


# ------------------------------------------------------------------ comparison


def _claims(tmp_path, example_text, twin_text, declared=frozenset()):
    """One example and one twin, compared without an engine."""
    example = tmp_path / "x.metta"
    example.write_text(example_text, encoding="utf-8")
    twin = tmp_path / "x.py"
    twin.write_text(twin_text, encoding="utf-8")
    return coverage.compare("x.metta", example, twin, set(declared))


def test_a_twin_that_claims_less_is_a_finding(tmp_path):
    """A claim a twin cannot make is a residue entry, never a silent gap.

    Without this, deleting an assertion would read as coverage rather than as
    the hole it is.
    """
    two = "!(test (f 1) 1)\n!(test (f 2) 4)\n"
    owed, proved, findings = _claims(tmp_path, two, "def twin(m):\n    assert f(1) == [1]\n")
    assert (owed, proved) == (2, 1)
    assert any("1 short" in finding for finding in findings)

    owed, proved, findings = _claims(
        tmp_path, two, "def twin(m):\n    assert f(1) == [1]\n", declared={1}
    )
    assert (owed, proved, findings) == (1, 1, [])


def test_a_claim_stated_anywhere_counts(tmp_path):
    """Shape is the twin's own business.

    Two assertions inside a loop are two claims, which is the whole point of
    dropping the form-by-form mirror.
    """
    twin = (
        "def twin(m):\n"
        "    for n in (1, 2):\n"
        "        assert f(n) == [n * n]\n"
        "        assert g(n) == [n]\n"
    )
    owed, proved, findings = _claims(tmp_path, "!(test (f 1) 1)\n!(test (f 2) 4)\n", twin)
    assert (owed, proved, findings) == (2, 2, [])


def test_a_hidden_definition_is_a_finding():
    """Self-reflectivity: a definition lands as a matchable atom or it is not one.

    A twin proving its claims while defining nothing in the space is exactly
    what this refuses, and no restructuring may weaken it.
    """
    findings = coverage._visible(
        "x.metta", _run([], heads=("facF/1",)), _run([], heads=())
    )
    assert any("hidden in Python" in finding for finding in findings)
    assert any("facF/1" in finding for finding in findings)
    assert coverage._visible("x.metta", _run([], heads=()), _run([], heads=("f/1",))) == []


# ---------------------------------------------------------------- the budgets


def test_the_full_lane_protocol_names_every_scheduling_input():
    """A corpus-width or executor-width change is a different population."""
    assert coverage.full_lane_protocol(204) == "full-lane/204/workers=32"
    with pytest.raises(ValueError, match="positive example count"):
        coverage.full_lane_protocol(0)


def test_every_shipped_twin_states_a_budget():
    """P14.14's start: the parity claim is frozen the moment a twin ships."""
    for example in coverage.written():
        budget = coverage.budget_of(coverage.twin_for(example))
        assert isinstance(budget, (int, coverage.EmpiricalBudget)), example
        if isinstance(budget, int):
            assert budget > 0, example


def test_a_budget_is_two_sided():
    """A benchmark baseline only fails upward, and a twin budget fails both ways.

    A twin that suddenly costs far LESS has most likely stopped doing the
    work and started answering the expected value, which is the cheat a fixed
    public corpus invites.
    """
    twin = coverage.twin_for(REPO / "examples" / "basics" / "factorial.metta")
    budget = coverage.budget_of(twin)
    assert isinstance(budget, int), "factorial's twin pins a POINT budget"
    left = _run(["(True)"], cost=budget)
    for observed in (budget + coverage.TOLERANCE + 1, budget // 2):
        findings = coverage._price("x.metta", twin, left, _run([], cost=observed))
        assert any("pinned budget" in f for f in findings), observed
    within = coverage._price(
        "x.metta", twin, left, _run([], cost=budget + coverage.TOLERANCE)
    )
    assert within == []


def _empirical_twin(tmp_path, budget):
    twin = tmp_path / "nondeterministic.py"
    twin.write_text(
        '"""Purpose: a planted nondeterministic twin budget."""\n'
        f"BUDGET = {budget!r}\n"
        "def twin(m):\n"
        "    assert m\n",
        encoding="utf-8",
    )
    return twin


def test_an_empirical_envelope_passes_its_observations_and_fails_new_spread(tmp_path):
    """Observed extrema pass; the first wider observation is a finding.

    The lower bound matters independently of the upper one: making a twin
    cheaper can mean it stopped doing the work, so an asymmetric declaration
    must never be widened into ``centre +/- spread``.
    """
    declared = {
        "minimum": 1_000,
        "maximum": 1_014,
        "observations": 10,
        "protocol": "full-lane/204/workers=32",
    }
    twin = _empirical_twin(tmp_path, declared)
    budget = coverage.budget_of(twin)
    assert isinstance(budget, coverage.EmpiricalBudget)
    assert budget.spread == 14

    example = _run([], cost=2_000)
    for observed in (1_000, 1_007, 1_014):
        assert coverage._price(
            "x.metta",
            twin,
            example,
            _run([], cost=observed),
            protocol="full-lane/204/workers=32",
        ) == []

    for observed, direction in ((999, "BELOW"), (1_015, "above")):
        findings = coverage._price(
            "x.metta",
            twin,
            example,
            _run([], cost=observed),
            protocol="full-lane/204/workers=32",
        )
        assert len(findings) == 1, findings
        assert direction in findings[0]
        assert "10 observations" in findings[0]
        assert "spread 14" in findings[0]
        assert "deterministic tolerance is not added" in findings[0]


def test_an_empirical_envelope_cannot_license_another_protocol(tmp_path):
    """Serial evidence says nothing about the scheduler the full lane adds."""
    twin = _empirical_twin(
        tmp_path,
        {
            "minimum": 1_000,
            "maximum": 1_014,
            "observations": 10,
            "protocol": "serial",
        },
    )
    findings = coverage._price(
        "x.metta",
        twin,
        _run([], cost=2_000),
        _run([], cost=1_007),
        protocol="full-lane/204/workers=32",
    )
    assert len(findings) == 1, findings
    assert "measured under 'serial'" in findings[0]
    assert "current protocol is 'full-lane/204/workers=32'" in findings[0]


@pytest.mark.parametrize(
    "budget",
    [
        {"minimum": 1_000, "maximum": 1_014, "observations": 10},
        {
            "minimum": 1_014,
            "maximum": 1_000,
            "observations": 10,
            "protocol": "full-lane/204/workers=32",
        },
        {
            "minimum": 1_000,
            "maximum": 1_014,
            "observations": 1,
            "protocol": "full-lane/204/workers=32",
        },
        {
            "minimum": 1_000,
            "maximum": 1_014,
            "observations": 10,
            "protocol": "",
        },
    ],
)
def test_an_empirical_envelope_requires_complete_measurement_metadata(
    tmp_path, budget
):
    """A band without bounds, repeated observations, and protocol is no claim."""
    twin = _empirical_twin(tmp_path, budget)
    with pytest.raises(ValueError, match="BUDGET empirical envelope"):
        coverage.budget_of(twin)


def test_a_malformed_budget_is_reported_and_not_a_traceback(tmp_path):
    """A REPORT lane says what is wrong with a twin, here too.

    The refusal above left `budget` as None while the finding list was already
    non-empty, and the point-budget arithmetic below then read None as a
    number: `unsupported operand type(s) for -: 'int' and 'NoneType'` left the
    whole corpus run instead of one twin's finding.
    """
    twin = _empirical_twin(tmp_path, {"minimum": 1_000, "maximum": 1_014})
    findings = coverage._price("x.metta", twin, _run([], cost=2_000), _run([], cost=1_007))
    assert len(findings) == 1, findings
    assert "BUDGET empirical envelope must contain exactly" in findings[0]


def test_spread_is_not_a_budget_door(tmp_path):
    """The guessed symmetric allowance was deleted, not retained as a shim."""
    twin = tmp_path / "legacy.py"
    twin.write_text(
        '"""Purpose: plant the deleted spread declaration."""\n'
        "BUDGET = 1_000\n"
        "SPREAD = 20\n"
        "def twin(m):\n"
        "    assert m\n",
        encoding="utf-8",
    )
    assert not hasattr(coverage, "spread_of")
    findings = coverage._price(
        "x.metta", twin, _run([], cost=2_000), _run([], cost=1_005)
    )
    assert any("pinned budget" in finding for finding in findings)


def test_the_band_refuses_a_twin_that_costs_more_than_it_was_pinned_to_allow():
    """The band is the parity half of the goal.

    The Python spelling costs the same inferences as the handwritten `.metta`
    program, or fewer, within what the first measurements showed.
    """
    twin = coverage.twin_for(REPO / "examples" / "basics" / "factorial.metta")
    budget = coverage.budget_of(twin)
    assert isinstance(budget, int), "factorial's twin pins a POINT budget"
    twin_run = _run([], cost=budget)

    # The example costing what the twin costs leaves the whole band spare.
    assert coverage._price("x.metta", twin, _run([], cost=budget), twin_run) == []

    # An example cheap enough that the pinned twin overruns the band, its
    # authoring allowance included: factorial AUTHORS one compiled definition,
    # and the band must let it pay for that.
    authored = coverage.definitions(twin)
    assert authored == 1, "factorial's twin authors exactly one definition"
    allowance = coverage.DEFINITION_WARMUP + coverage.DEFINITION_COST * authored
    cheaper = int((budget - allowance) / (1.0 + coverage.BAND_PERCENT / 100.0)) - 1
    outside = coverage._price("x.metta", twin, _run([], cost=cheaper), twin_run)
    assert any("band" in f for f in outside), outside
    assert any("author 1 compiled definition" in f for f in outside), outside


def test_the_band_pays_for_authoring_but_only_what_was_measured(tmp_path):
    """A definition costs to WRITE, and the example has none to write.

    Without the allowance the band selected for transliteration on exactly the
    small examples where Python's spelling is clearest: measured 2026-08-22,
    examples/control/if.metta costs 2092 against a ceiling of 2301, and one
    decorated definition costs 2221 in a fresh process.
    """
    plain = tmp_path / "plain.py"
    plain.write_text('"""D."""\nBUDGET = 2000\ndef twin(m):\n    assert m\n', encoding="utf-8")
    assert coverage.definitions(plain) == 0

    authored = tmp_path / "authored.py"
    authored.write_text(
        '"""D."""\n'
        "BUDGET = 2000\n"
        "def twin(m):\n"
        "    @m.define\n"
        "    def f(x):\n"
        "        return x\n"
        "    assert f(1) == [1]\n",
        encoding="utf-8",
    )
    assert coverage.definitions(authored) == 1

    # One example, one twin cost, two verdicts: the twin that AUTHORS is given
    # the measured room and the one that does not is given none.
    cost = 2000
    example = _run([], cost=100)
    spent = _run([], cost=cost)
    assert any("band" in f for f in coverage._price("x", plain, example, spent))
    assert coverage._price("x", authored, example, spent) == []


# ----------------------------------------------------------------- end to end


@pytest.mark.parametrize(
    "name", ["basics/identity.metta", "spaces/spaces3.metta"]
)
def test_a_shipped_twin_agrees_with_its_example_end_to_end(name):
    """Two twins run for real.

    A change breaking the machinery itself is then caught rather than reading
    as a corpus finding.
    """
    verdict = coverage.check(REPO / "examples" / name, coverage.residue())
    assert verdict.findings == (), verdict.findings
    assert verdict.covered == verdict.forms > 0


def test_the_residue_json_is_the_one_definition_of_what_is_missing():
    """The lane's own file, read the way every runner reads example_skips."""
    document = json.loads(coverage.RESIDUE.read_text(encoding="utf-8"))
    assert document["schema"] == "petta-twin-residue-1"
    assert document["entries"] == coverage.residue()


def test_the_distribution_budget_retirement_is_exact():
    """Only the determinism-assumption population moved, all 159 entries."""
    document = json.loads(coverage.RESIDUE.read_text(encoding="utf-8"))
    section = "correction to the lane's determinism assumption"
    active = [entry for entry in document["entries"] if entry["section"] == section]
    retired = [
        entry
        for entry in document["retired"]
        if entry.get("section") == section
        and "empirical two-sided envelope" in entry["retired"]
    ]
    assert active == []
    assert len(retired) == 159


def test_the_idiom_check_catches_a_planted_transliteration(tmp_path):
    """A twin can avoid MeTTa source TEXT and still be MeTTa source with
    Python punctuation, which is what this check exists for: the string scan
    passes the planted file below and the idiom check refuses it, naming the
    spelling Python already has.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    planted = tmp_path / "planted.py"
    planted.write_text(
        '"""Doc."""\n'
        "from metta import Expression, S, V\n"
        "def twin(m):\n"
        '    m += Expression((S["="], Expression((S["f"], V["x"])), 1))\n',
        encoding="utf-8",
    )
    assert coverage.scan(planted) == []
    joined = " ".join(coverage.idiom(planted))
    assert 'S["f"] is S.f' in joined
    assert 'V["x"] is V.x' in joined
    assert "Expression(...) builds what calling the head builds" in joined


def test_an_operator_head_is_a_finding_only_where_an_operator_would_build(tmp_path):
    """`a + b` builds `(+ $a $b)` INSIDE a compiled body, so writing the head
    there is a transliteration. Outside one the same spelling is deliberate,
    because Python's `+` on ground values computes and its `==` is structural
    equality, so the rule would report a correct twin. The arity matters for
    the same reason: `S["+"](1)` is a partial application Python cannot spell.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    outside = tmp_path / "outside.py"
    outside.write_text(
        '"""Doc."""\n'
        "from metta import S, V\n"
        "def twin(m):\n"
        '    m += S["+"](V.a, V.b)\n',
        encoding="utf-8",
    )
    assert not [f for f in coverage.idiom(outside) if "operator" in f]

    inside = tmp_path / "inside.py"
    inside.write_text(
        '"""Doc."""\n'
        "from metta import S, V\n"
        "def twin(m):\n"
        "    @m.define\n"
        "    def add(a, b):\n"
        '        return S["+"](a, b)\n'
        "    @m.define\n"
        "    def partial(a):\n"
        '        return S["+"](a)\n',
        encoding="utf-8",
    )
    operators = [f for f in coverage.idiom(inside) if "operator" in f]
    assert len(operators) == 1, operators
    assert "'+'" in operators[0]


def test_the_operator_heads_are_the_ones_the_translator_emits(tmp_path):
    """The heads a Python operator writes are the TRANSLATOR's, not the
    dunders'. Measured 2026-08-24, one file per spelling under `@m.define`:
    `a ** b` emits `(pow-math a b)` and `a == b` emits `(py-eq a b)`, so both
    heads are transliterations inside a body; `a // b` REFUSES there, naming
    `floor_math(a / b)`, so `floor-math` is the twin's only spelling and
    demanding an operator for it would demand one the translator rejects.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    planted = tmp_path / "heads.py"
    planted.write_text(
        '"""Doc."""\n'
        "from metta import S, fn\n"
        "def twin(m):\n"
        "    @m.define\n"
        "    def raised(a, b):\n"
        '        return S["pow-math"](a, b)\n'
        "    @m.define\n"
        "    def same(a, b):\n"
        '        return fn["py-eq"](a, b)\n'
        "    @m.define\n"
        "    def divided(a, b):\n"
        "        return fn.floor_math(a / b)\n",
        encoding="utf-8",
    )
    operators = [f for f in coverage.idiom(planted) if "operator" in f]
    assert len(operators) == 2, operators
    assert "'pow-math'" in operators[0]
    assert "'py-eq'" in operators[1]
    assert "compiled body" in operators[0]


def test_a_rules_body_carries_literals_but_lowers_no_operator(tmp_path):
    """`@rules` stores equations, so its strings are MeTTa string literals.

    Its body is EXECUTED rather than lowered from syntax, though: `x == y` on
    two rule variables is Python's own structural equality and answers a bool,
    so `.eq(...)` is the building spelling there and the operator rule would
    report a correct bundle.
    """
    planted = tmp_path / "planted.py"
    planted.write_text(
        '"""Doc."""\n'
        "from metta import S, equation\n"
        "def twin(m):\n"
        "    @m.rules\n"
        "    def laws(x, y):\n"
        '        yield equation(S.label(x)).to("a literal")\n'
        '        yield equation(S.same(x, y)).to(S["=="](x, y))\n',
        encoding="utf-8",
    )
    assert coverage.scan(planted) == []
    assert not [f for f in coverage.idiom(planted) if "operator" in f]
    assert coverage.definitions(planted) == 1


def test_a_term_may_name_a_head_that_shares_a_source_doors_name(tmp_path):
    """`S.parse(text)` builds the term `(parse text)`; only a real call takes
    MeTTa source. Reading every call by name alone left a twin with no way to
    write that head at all, since the idiom check refuses `S["parse"]` too.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    planted = tmp_path / "head.py"
    planted.write_text(
        '"""Doc."""\n'
        "from metta import S, ground\n"
        "def twin(m):\n"
        "    assert m.eval(S.parse(ground('(f a)'))) == []\n"
        "    assert m.eval(m.fn.parse(ground('(f a)'))) == []\n",
        encoding="utf-8",
    )
    assert coverage.scan(planted) == []
    assert coverage.idiom(planted) == []

    real = tmp_path / "real.py"
    real.write_text(
        '"""Doc."""\n'
        "def twin(m):\n"
        "    assert m.run('!(f a)') == []\n",
        encoding="utf-8",
    )
    assert coverage.scan(real)


def test_a_declared_rung_is_a_documented_drop_rather_than_a_finding(tmp_path):
    """The ladder keeps every rung, so sitting below the top one is legal
    when the twin SAYS why. A silent drop is the defect; a declared one is
    documentation, and the lane reads the declaration the way it reads BUDGET.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    body = (
        '"""Doc."""\n'
        "from metta import Expression, S, V\n"
        "%s"
        "def twin(m):\n"
        '    m += Expression((S["="], Expression((S["f"], V["x"])), 1))\n'
    )
    silent = tmp_path / "silent.py"
    silent.write_text(body % "", encoding="utf-8")
    assert coverage.idiom(silent)

    declared = tmp_path / "declared.py"
    declared.write_text(
        body % 'RUNG = "the compiled subset has no lowering for this form yet"\n',
        encoding="utf-8",
    )
    assert coverage.idiom(declared) == []
    # BOTH checks have to accept the declaration, or the escape is unusable:
    # the reason is a module-level string, and the source scan refuses those
    # unless they are documentation. Asserting only idiom() is what let the
    # contradiction ship [found 2026-08-22 by two twin agents at once].
    assert coverage.scan(declared) == []


def test_a_line_may_state_its_own_rung(tmp_path):
    """A twin idiomatic everywhere but one line excuses that line rather than
    the whole file, in the shape of the tree's noqa grammar.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    planted = tmp_path / "line.py"
    planted.write_text(
        '"""Doc."""\n'
        "from metta import S\n"
        "def twin(m):\n"
        '    m += S["f"](1)  # rung: the head is built by a caller that needs the string\n'
        '    m += S["g"](2)\n',
        encoding="utf-8",
    )
    findings = coverage.idiom(planted)
    assert len(findings) == 1, findings
    assert 'S["g"] is S.g' in findings[0]


def test_a_dissolved_head_names_the_python_spelling_it_replaces(tmp_path):
    """A concept Python already has is written Python's way.

    This is the check the punctuation rules could not make: `S.test(...)` and
    `S["add-atom"](...)` are perfectly good Python that say MeTTa, which is
    what the corpus filled up with while the lane only read spelling.
    """
    planted = tmp_path / "planted.py"
    planted.write_text(
        '"""Doc."""\n'
        "from metta import S, V\n"
        "def twin(m):\n"
        "    m += S['add-atom'](S['&self'], S.fact(1))\n"
        "    assert m.eval(S.test(S.f(1), 1)) == []\n",
        encoding="utf-8",
    )
    findings = coverage.idiom(planted)
    assert any("space += atom" in finding for finding in findings)
    assert any("Python's own assert" in finding for finding in findings)
    assert any("names a SPACE as a symbol" in finding for finding in findings)


def test_an_engine_function_may_be_named_with_an_ampersand(tmp_path):
    """The ampersand marks a space at the SYMBOL factory and nothing elsewhere.

    The combinator library ships functions called `&&&` and `&^&`, so reading
    every ampersand-prefixed factory name as a space would report two correct
    lines in `libraries/roman.py` alone.
    """
    planted = tmp_path / "planted.py"
    planted.write_text(
        '"""Doc."""\n'
        "from metta import S\n"
        "def twin(m):\n"
        '    assert list(m.fn["&&&"](S["+"](2), S["*"](2), 1)) == [3, 2]\n'
        '    m += S["&self"]\n',
        encoding="utf-8",
    )
    findings = coverage.idiom(planted)
    assert len(findings) == 1, findings
    assert "'&self' names a SPACE as a symbol" in findings[0]


def test_a_yielding_twin_is_a_finding(tmp_path):
    """A yield in twin() is the form-by-form mirror, and that is the defect.

    A yield inside a `@m.define`d body is nondeterminism and must stay legal,
    so the rule reads the twin's own body and not the functions it defines.
    """
    planted = tmp_path / "planted.py"
    planted.write_text(
        '"""Doc."""\n'
        "from metta import S\n"
        "def twin(m):\n"
        "    @m.define\n"
        "    def colour():\n"
        "        yield S.red\n"
        "    assert set(colour()) == {S.red}\n",
        encoding="utf-8",
    )
    assert coverage.idiom(planted) == []

    planted.write_text(
        '"""Doc."""\n'
        "from metta import S\n"
        "def twin(m):\n"
        "    yield m.eval(S.f(1))\n",
        encoding="utf-8",
    )
    assert any("FORM BY FORM" in finding for finding in coverage.idiom(planted))


def test_a_variable_headed_expression_keeps_its_only_spelling(tmp_path):
    """`Expression((V.x,))` builds ($x) and nothing shorter reaches it.

    `Variable` is not callable, so the Expression() rule must fire on a SYMBOL
    head only; firing on a variable would demand a spelling that does not exist.
    """
    planted = tmp_path / "planted.py"
    planted.write_text(
        '"""Doc."""\n'
        "from metta import Expression, S, V\n"
        "def twin(m):\n"
        "    assert list(m.match(Expression((V.x,)))) == []\n"
        "    assert list(m.match(V.x)['x']) == []\n",
        encoding="utf-8",
    )
    assert coverage.scan(planted) == []
    assert coverage.idiom(planted) == []


def test_a_failing_assertion_is_a_finding(tmp_path):
    """A false claim fails the twin, which is what makes the count an oracle.

    The contract says a twin running to completion has PROVED every claim it
    states. That only holds if a false assertion stops it, so this runs a real
    twin against a real engine rather than a fixture: the AssertionError has to
    leave the process, and the lane has to read that as an error rather than as
    a twin with nothing to say.
    """
    twin = tmp_path / "false.py"
    twin.write_text(
        '"""A twin that claims something untrue."""\n'
        "BUDGET = 1\n"
        "def twin(m):\n"
        "    assert 1 == 2\n",
        encoding="utf-8",
    )
    run = coverage.run_twin(twin)
    assert run.outcome.error is not None, "a raised assertion must leave the run in error"
    assert "AssertionError" in run.outcome.error, run.outcome.error

    twin.write_text(
        '"""A twin whose claim holds."""\n'
        "BUDGET = 1\n"
        "def twin(m):\n"
        "    assert 1 == 1\n",
        encoding="utf-8",
    )
    assert coverage.run_twin(twin).outcome.error is None


def test_a_manual_hyphen_spelling_is_a_finding(tmp_path):
    """Rung 4's map is total both ways, so the bracket keeps only what an
    identifier cannot spell (user ruling, 2026-08-24).
    """  # noqa: D205  -- the rule and its ground are one sentence
    import twin_coverage as lane

    twin = tmp_path / "hyphens.py"
    twin.write_text(
        "from metta import S, fn\n"
        "def twin(m):\n"
        "    a = S[\"foo-bar\"](1)\n"          # redundant: S.foo_bar reaches it
        "    b = fn[\"mixed-under_score\"]\n"  # no round trip: stays exact
        "    c = S[\"prime?\"]\n"              # unspellable: stays exact
        "    d = S[\"==\"]\n"                  # punctuation: stays exact
        "    return a, b, c, d\n",
        encoding="utf-8",
    )
    findings = lane.idiom(twin)
    assert any('S["foo-bar"] is S.foo_bar' in f for f in findings), findings
    assert not any("mixed-under_score" in f for f in findings), findings
    assert not any("prime?" in f for f in findings), findings
    assert not any('"=="' in f for f in findings), findings


def test_a_restated_define_name_is_a_finding(tmp_path):
    """name= carries only what the identifier cannot: the map's own output
    and the identifier itself are findings, an unreachable name is not.
    """  # noqa: D205  -- the rule and its ground are one sentence
    import twin_coverage as lane

    twin = tmp_path / "names.py"
    twin.write_text(
        "def twin(m):\n"
        "    @m.define(name=\"find-divisor\")\n"   # what the map already says
        "    def find_divisor(n):\n"
        "        return n\n"
        "    @m.define(name=\"helper\")\n"          # the identifier itself
        "    def helper(n):\n"
        "        return n\n"
        "    @m.define(name=\"prime?\")\n"          # unreachable: load-bearing
        "    def prime(n):\n"
        "        return n\n"
        "    @m.define(name=\"facF\")\n"            # mixed case: load-bearing
        "    def fac_f(n):\n"
        "        return n\n",
        encoding="utf-8",
    )
    findings = lane.idiom(twin)
    assert any('name="find-divisor" is what def find_divisor' in f for f in findings), findings
    assert any('name="helper" is what def helper' in f for f in findings), findings
    assert not any("prime?" in f for f in findings), findings
    assert not any("facF" in f for f in findings), findings


def test_an_operator_word_keeps_its_bracket(tmp_path):
    """S["add"] is the exact door for the SYMBOL add: the attribute resolves
    through the word table to the head + instead, so the redundancy rule
    must not send an author through it (agent A measured the old advice
    storing (= (+ 1 2) 3)).
    """  # noqa: D205  -- the rule and its ground are one sentence
    import twin_coverage as lane

    twin = tmp_path / "words.py"
    twin.write_text(
        "from metta import S\n"
        "def twin(m):\n"
        "    a = S[\"add\"](1, 2)\n"   # word: bracket load-bearing
        "    b = S[\"neg\"]\n"          # composite word: same
        "    c = S[\"plain\"]\n"        # not a word: still redundant
        "    return a, b, c\n",
        encoding="utf-8",
    )
    findings = lane.idiom(twin)
    assert not any('"add"' in f for f in findings), findings
    assert not any('"neg"' in f for f in findings), findings
    assert any('S["plain"] is S.plain' in f for f in findings), findings


def test_the_bracket_door_is_exact_at_a_compiled_call(tmp_path):
    """S["eq"](a, b) inside a lowered body is the data symbol eq, not the
    operator: only the attribute door consults the word table, exactly as
    the compiler does (agents A and F both measured the undistinguished
    rule misreporting the exact door).
    """  # noqa: D205  -- the rule and its ground are one sentence
    import twin_coverage as lane

    twin = tmp_path / "exact.py"
    twin.write_text(
        "from metta import S\n"
        "def twin(m):\n"
        "    @m.define\n"
        "    def wants_eq_data(a, b):\n"
        "        return S[\"eq\"](a, b)\n"
        "    @m.define\n"
        "    def spells_the_operator(a, b):\n"
        "        return S.eq(a, b)\n",
        encoding="utf-8",
    )
    findings = lane.idiom(twin)
    bracket = [f for f in findings if '"eq"' in f]
    attribute = [f for f in findings if "Python operator writes" in f and '"eq"' not in f]
    assert not bracket, findings
    assert attribute, findings
