"""Purpose: prove catalog, root, documentation and lineage projections see drift.

Owns resources: pytest's tmp_path owns fixtures and mypy caches. Source mutations
use monkeypatch or mypy shadow files; checked-in artifacts are never changed.
"""

from __future__ import annotations

import ast
import builtins
import json
import math
import operator
import subprocess
import sys
from pathlib import Path

import pytest
from pygments.token import Keyword, Name, Text

ROOT = Path(__file__).resolve().parents[4]
SEAT = ROOT / "extensions/python"
sys.path.insert(0, str(SEAT / "tools"))

import codecdoc  # noqa: E402
import doorfaces  # noqa: E402
import doorgen  # noqa: E402
import example_origins  # noqa: E402
import ledger  # noqa: E402
import libdoc  # noqa: E402
import pygmentsgen  # noqa: E402
import rootgen  # noqa: E402
import vocabgen  # noqa: E402


def test_source_bindings_cache_uses_the_current_source(tmp_path):
    """Changing an import in the same module cannot reuse the old binding."""
    path = tmp_path / "extensions/python/metta/_fixture.py"
    path.parent.mkdir(parents=True)
    path.write_text("from collections.abc import Mapping as Contract\n", encoding="utf-8")
    assert doorfaces._bindings("metta._fixture", tmp_path)["Contract"] == ("collections.abc", "Mapping")
    path.write_text("from collections.abc import Sequence as Contract\n", encoding="utf-8")
    assert doorfaces._bindings("metta._fixture", tmp_path)["Contract"] == ("collections.abc", "Sequence")


def test_root_exports_and_new_carrier_reach_runtime_and_consumer(tmp_path, monkeypatch):
    """A named root import and catalog member reach all their derived faces."""
    from metta import vocabularies

    core = tmp_path / "extensions/python/metta"
    core.mkdir(parents=True)
    stub = core / "__init__.pyi"
    stub.write_text(
        "from ._atoms.factories import Symbol as FixtureSymbol\n"
        "# isort: split\n"
        "# begin generated root imports\n# end generated root imports\n"
        "# isort: split\n"
        "__all__ = ['FixtureSymbol']\n"
        "# begin generated root declarations\n# end generated root declarations\n"
        "# begin generated algebra declaration\n# end generated algebra declaration\n", encoding="utf-8",
    )
    original = rootgen.projections((), root=tmp_path)
    monkeypatch.setattr(vocabularies, "Semiring", (*vocabularies.Semiring, "fixture-carrier"))
    changed = rootgen.projections((), root=tmp_path)
    runtime = ast.parse(changed[core / "__init__.py"])
    declarations = {node.targets[0].id: ast.literal_eval(node.value) for node in runtime.body
                    if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name)}
    assert declarations["__all__"] == ["FixtureSymbol"]
    assert declarations["__lazy_exports__"]["FixtureSymbol"] == ("metta._atoms.factories", "Symbol")
    assert "fixture_carrier: _DeclaredAlgebra" in changed[stub]
    probe = tmp_path / "extensions/python/tests/typing/algebra_surface.py"
    assert "assert_type(metta.algebra.fixture_carrier, DeclaredAlgebra)" in changed[probe]
    assert {path for path in changed if changed[path] != original[path]} == {stub, probe}
    with pytest.raises(ValueError, match="root exports lack declarations: absent"):
        rootgen.exports("__all__ = ['absent']\n")


def test_root_consumer_rejects_any_and_non_callable_exports(tmp_path):
    """Run the shipped consumer against the real stub and two type mutations."""
    stub = SEAT / "metta/__init__.pyi"
    original = stub.read_text(encoding="utf-8")
    assert "algebra: _AlgebraModule" in original
    shadow = tmp_path / "root.pyi"
    # Mypy substitutes source without changing module identity or imports.
    # https://mypy.readthedocs.io/en/v2.3.1/command_line.html#cmdoption-mypy-shadow-file
    command = [sys.executable, "-m", "mypy", "--cache-dir", str(tmp_path / "cache"),
               "--shadow-file", str(stub), str(shadow), "tests/typing/algebra_surface.py"]
    for declaration, finding in (
        ("algebra: _AlgebraModule", None),
        ("algebra: _Any", "[assert-type]"),
        ("from types import ModuleType as _PlantedModule\nalgebra: _PlantedModule", "[operator]"),
    ):
        shadow.write_text(original.replace("algebra: _AlgebraModule", declaration), encoding="utf-8")
        result = subprocess.run(command, cwd=SEAT, capture_output=True, text=True, check=False)
        assert result.returncode == int(finding is not None), result.stdout + result.stderr
        if finding:
            assert finding in result.stdout, result.stdout


def test_root_implementation_checks_annotations_and_forwarded_arguments(tmp_path):
    """Root annotations and the forwarding call retain their concrete types."""
    implementation = SEAT / "metta/__init__.py"
    original = implementation.read_text(encoding="utf-8")
    call = "engine().self.run(source, timeout=timeout, inferences=inferences, **values)"
    assert original.count(call) == 1
    shadow = tmp_path / "root.py"
    command = [sys.executable, "-m", "mypy", "--cache-dir", str(tmp_path / "cache"),
               "--shadow-file", str(implementation), str(shadow), "metta/__init__.py"]
    for source, refused in (
        (original + '\nrun("!(+ 1 2)")\n', False),
        (original + "\nrun(42)\n", True),
        (original.replace(call, call.replace("run(source,", "run(42,")), True),
    ):
        shadow.write_text(source, encoding="utf-8")
        result = subprocess.run(command, cwd=SEAT, capture_output=True, text=True, check=False)
        assert result.returncode == int(refused), result.stdout + result.stderr
        if refused:
            assert "[arg-type]" in result.stdout, result.stdout


def test_setting_configuration_preserves_the_public_value_type(tmp_path):
    """An omitted value and an integer pass; arbitrary objects are rejected."""
    consumer = tmp_path / "configuration.py"
    command = [sys.executable, "-m", "mypy", "--cache-dir", str(tmp_path / "cache"), str(consumer)]
    valid = "from metta import config\nconfig.configure()\nconfig.configure(display_rows=3)\n"
    for source, refused in ((valid, False), (valid + 'config.configure(display_rows="wrong")\n', True)):
        consumer.write_text(source, encoding="utf-8")
        result = subprocess.run(command, cwd=SEAT, capture_output=True, text=True, check=False)
        assert result.returncode == int(refused), result.stdout + result.stderr
        if refused:
            assert "[arg-type]" in result.stdout, result.stdout


@pytest.fixture(scope="module")
def vocabulary_catalog():
    """Read real engine rows once; each fixture adds one valid vocabulary."""
    known = vocabgen.catalog()
    return known._replace(
        vocabularies=[*known.vocabularies, ("fixture-colour", ["layout-amber"])],
        colon=known.colon | {("FixtureColour", "Type"), ("layout-amber", "FixtureColour")},
    )


@pytest.fixture
def vocabulary_files(tmp_path, monkeypatch, vocabulary_catalog):
    """Give the actual checker two independent generated files."""
    monkeypatch.setattr(vocabgen, "ROOT", tmp_path)
    monkeypatch.setattr(vocabgen, "MODULE", tmp_path / "vocabulary.py")
    monkeypatch.setattr(vocabgen, "TS_MODULE", tmp_path / "vocabulary.ts")
    monkeypatch.setattr(vocabgen, "catalog", lambda: vocabulary_catalog)
    vocabgen.MODULE.write_text(vocabgen.module_text(vocabulary_catalog), encoding="utf-8")
    vocabgen.TS_MODULE.write_text(vocabgen.ts_text(vocabulary_catalog), encoding="utf-8")
    assert vocabgen.main([]) == 0
    return vocabgen.MODULE, vocabgen.TS_MODULE


@pytest.mark.parametrize("output", (0, 1), ids=("python", "node"))
def test_vocabulary_wrong_spelling_is_refused_independently(vocabulary_files, output, capsys):
    """Changing only one seat's value cannot agree with the catalog."""
    path = vocabulary_files[output]
    original = path.read_text(encoding="utf-8")
    path.write_text(original.replace('"layout-amber"', '"layout-violet"'), encoding="utf-8")
    assert path.read_text(encoding="utf-8") != original
    assert vocabgen.main([]) == 1
    assert path.name in capsys.readouterr().out


def test_vocabulary_new_member_and_stale_type_fact_are_distinct(vocabulary_files, vocabulary_catalog, monkeypatch, capsys):
    """Both seats must gain the value, and the engine must publish its type."""
    updated = vocabulary_catalog._replace(
        vocabularies=[(name, [*values, "layout-violet"] if name == "fixture-colour" else values)
                      for name, values in vocabulary_catalog.vocabularies],
        colon=vocabulary_catalog.colon | {("layout-violet", "FixtureColour")},
    )
    monkeypatch.setattr(vocabgen, "catalog", lambda: updated)
    assert vocabgen.main([]) == 1
    output = capsys.readouterr().out
    assert all(path.name in output for path in vocabulary_files)
    assert "type atoms disagree" not in output
    vocabulary_files[0].write_text(vocabgen.module_text(updated), encoding="utf-8")
    vocabulary_files[1].write_text(vocabgen.ts_text(updated), encoding="utf-8")
    assert vocabgen.main([]) == 0
    monkeypatch.setattr(vocabgen, "catalog", lambda: updated._replace(colon=vocabulary_catalog.colon))
    assert vocabgen.main([]) == 1
    assert "never wrote (: layout-violet FixtureColour)" in capsys.readouterr().out


def test_door_documents_build_each_atom_operator():
    """Every generated Python spelling constructs its complete documented term."""
    from metta import Symbol
    from metta._atoms.operators import OPERATOR_LOWERINGS

    table = [line for line in doorgen.atom_operator_table() if line.startswith("| `")]
    assert len(table) == len(OPERATOR_LOWERINGS)
    for line, entry in zip(table, OPERATOR_LOWERINGS, strict=True):
        syntax, expected = line.removeprefix("| `").removesuffix("` |").split("` | `")
        names = {f"x{index}": Symbol(f"x{index}") for index in range(1, entry.arity + 1)}
        built = eval(syntax.replace("\\|", "|"), {"builtins": builtins, "math": math, "operator": operator, **names})
        assert str(built) == expected.replace("\\|", "|"), entry


@pytest.mark.parametrize("defect", ("refusal", "longhand", "count", "atom-operator"))
def test_door_documents_reject_semantic_drift(defect, monkeypatch, capsys):
    """Changed refusals, fixed points, counts and operator images are refused."""
    rows = doorgen.all_rows()
    path = {"refusal": ROOT / "website/reference/python-door-contracts.md",
            "longhand": ROOT / "llms.txt", "count": ledger.PAGE,
            "atom-operator": ROOT / "website/guide/atoms-terms.md"}[defect]
    original = path.read_text(encoding="utf-8")
    if defect == "refusal":
        refusal = next(row.refuses[0] for row in rows if row.refuses)
        planted = original.replace(f"- `{refusal.kind}`: `{refusal.witness}`.\n", "", 1)
    elif defect == "longhand":
        row = next(row for row in rows if row.sugar_of and row.owner is doorgen.Owner.space)
        planted = original.replace(doorgen.sugar_longhand(row), "wrong-door(...)", 1)
    elif defect == "atom-operator":
        line = next(line for line in doorgen.atom_operator_table() if line.startswith("| `"))
        syntax, _image = line.removeprefix("| `").removesuffix("` |").split("` | `")
        planted = original.replace(line, f"| `{syntax}` | `(wrong-operator x1)` |", 1)
    else:
        count = sum(row.owner is doorgen.Owner.space and doorgen.Tier.sync in row.tiers for row in rows)
        planted = original.replace(f"declares {count} core doors", f"declares {count + 1} core doors", 1)
    assert planted != original
    read = Path.read_text
    checker = ledger.main if defect == "count" else doorgen.main
    assert checker([]) == 0
    with monkeypatch.context() as patch:
        patch.setattr(Path, "read_text", lambda candidate, *a, **kw: planted if candidate == path else read(candidate, *a, **kw))
        assert checker([]) == 1
    expected = "shrink ledger differs" if defect == "count" else f"stale projections: {path.relative_to(ROOT)}"
    assert expected in capsys.readouterr().out


def test_library_document_reads_changed_parameter_facts(tmp_path, monkeypatch):
    """An edited @param reaches the generated page and invalidates the old one."""
    library = tmp_path / "lib/lib_fixture"
    library.mkdir(parents=True)
    source = library / "lib_fixture.metta"
    source.write_text('(: fixture (-> Number Number))\n(@doc fixture (@params ((@param "width"))))\n', encoding="utf-8")
    page = tmp_path / "metta-libraries.md"
    monkeypatch.setattr(libdoc, "_REPO", tmp_path)
    monkeypatch.setattr(libdoc, "_PAGE", page)
    page.write_text(libdoc.page(), encoding="utf-8")
    assert "1. width" in page.read_text(encoding="utf-8")
    assert libdoc.main([]) == 0
    source.write_text(source.read_text(encoding="utf-8").replace('"width"', '"height"'), encoding="utf-8")
    assert "1. height" in libdoc.page()
    assert libdoc.main([]) == 1


def test_codec_document_rejects_a_valid_addition_missing_from_one_table(tmp_path, monkeypatch):
    """The symbol case remains valid when its identifier and value are new."""
    corpus = json.loads(codecdoc.CORPUS.read_text(encoding="utf-8"))
    current = codecdoc.document(codecdoc.DOCUMENT.read_text(encoding="utf-8"), corpus)
    corpus["cases"].append({"id": "layout-fixture", "tags": ["s"], "text": "layout-fixture",
                            "wire": ["s", "layout-fixture"], "written": "layout-fixture"})
    corpus_file, document = tmp_path / "corpus.json", tmp_path / "CODEC.md"
    corpus_file.write_text(json.dumps(corpus), encoding="utf-8")
    document.write_text(current, encoding="utf-8")
    monkeypatch.setattr(codecdoc, "CORPUS", corpus_file)
    monkeypatch.setattr(codecdoc, "DOCUMENT", document)
    wanted = codecdoc.document(current, corpus)
    before = {match.group("name"): match.group("body") for match in codecdoc.FENCE.finditer(current)}
    after = {match.group("name"): match.group("body") for match in codecdoc.FENCE.finditer(wanted)}
    assert {name for name in before if before[name] != after[name]} == {"cases"}
    assert codecdoc.main([]) == 1
    document.write_text(wanted, encoding="utf-8")
    assert codecdoc.main([]) == 0


@pytest.mark.parametrize("field", ("name", "match"), ids=("scope", "regex"))
def test_lexer_source_changes_reach_real_tokens_and_reject_drift(tmp_path, monkeypatch, field):
    """One accepted grammar rule changes the lexer behavior as well as its text."""
    rule = {"name": "keyword.control.metta", "match": "layout-needle"}
    grammar = {"patterns": [{"include": "#fixture"}], "repository": {"fixture": {"patterns": [rule]}}}
    old = pygmentsgen.module_text(grammar)
    rule[field] = "variable.other.metta" if field == "name" else "layout-other"
    wanted = pygmentsgen.module_text(grammar)
    old_scope, new_scope = {}, {}
    exec(compile(old, "original-lexer.py", "exec"), old_scope)
    exec(compile(wanted, "changed-lexer.py", "exec"), new_scope)
    assert list(old_scope["MettaLexer"]().get_tokens_unprocessed("layout-needle")) == [(0, Keyword, "layout-needle")]
    changed = list(new_scope["MettaLexer"]().get_tokens_unprocessed("layout-needle"))
    assert changed == ([(0, Name.Variable, "layout-needle")] if field == "name" else
                       [(index, Text, char) for index, char in enumerate("layout-needle")])
    source, module = tmp_path / "grammar.json", tmp_path / "lexer.py"
    source.write_text(json.dumps(grammar), encoding="utf-8")
    module.write_text(old, encoding="utf-8")
    monkeypatch.setattr(pygmentsgen, "ROOT", tmp_path)
    monkeypatch.setattr(pygmentsgen, "GRAMMAR", source)
    monkeypatch.setattr(pygmentsgen, "MODULE", module)
    assert pygmentsgen.main([]) == 1
    module.write_text(wanted, encoding="utf-8")
    assert pygmentsgen.main([]) == 0


@pytest.mark.parametrize("defect", ("orphan", "duplicate-owner"))
def test_example_origins_rejects_orphan_and_duplicate_owner(tmp_path, monkeypatch, defect):
    """Actual source comparison refuses a removed file or a second attribution."""
    root, upstream = tmp_path / "checkout", tmp_path / "upstream"
    for directory in (root / "examples", upstream / "examples"):
        directory.mkdir(parents=True)
        (directory / "fixture.metta").write_text("!(+ 1 2)\n", encoding="utf-8")
    manifest = root / "examples/ORIGINS.tsv"
    monkeypatch.setattr(example_origins, "REPO", root)
    monkeypatch.setattr(example_origins, "MANIFEST", manifest)
    monkeypatch.setattr(example_origins, "upstream_root", lambda: upstream)
    monkeypatch.setattr(example_origins, "authors", lambda *_: "Fixture Author")
    rows = example_origins.derived(upstream)
    assert rows == [("examples/fixture.metta", "examples/fixture.metta", 1.0, "Fixture Author")]
    manifest.write_text(example_origins.render(rows, 1), encoding="utf-8")
    assert example_origins.main([]) == 0
    if defect == "orphan":
        (root / "examples/fixture.metta").unlink()
    else:
        manifest.write_text(manifest.read_text(encoding="utf-8") +
                            "examples/fixture.metta\texamples/fixture.metta\t1.0\tSecond Owner\n", encoding="utf-8")
    assert example_origins.main([]) == 1
