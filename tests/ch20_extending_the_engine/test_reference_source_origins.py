"""Purpose: preserve explicit Atom values while FROM elaborates surrounding source.

Owns resources: context managers retire all program homes and the engine owner.
Guarantees: a supplied Atom keeps its head while the source around it elaborates,
a compiled supplied value survives withdrawal of its FROM row, and a resolved
import spec is never reinterpreted by a FROM alias
[tested: test_supplied_atoms_keep_their_heads_inside_fresh_source,
test_compiled_supplied_values_survive_reference_withdrawal,
test_python_import_rewriter_keeps_its_resolved_module_spec; commit=WORKTREE].
"""

import uuid

from metta import MeTTa, S, parse


def test_supplied_atoms_keep_their_heads_inside_fresh_source():
    """Source occurrences resolve locally while the supplied Atom stays literal."""
    with MeTTa() as m, m.space() as home, m.space() as target:
        home.run("(: OriginPythonCanonical (-> Number OriginPythonRecord))")
        target.from_(home, parse("(rename ((OriginPythonCanonical OriginPythonPoint)))"))
        supplied = S.OriginPythonPoint(9)
        assert target.run(
            "!(noeval (Pair (OriginPythonPoint 1) {value} ({head} 2)))",
            value=supplied,
            head=S.OriginPythonPoint,
        ) == [[S.Pair(S.OriginPythonCanonical(1), supplied, S.OriginPythonPoint(2))]]
        assert str(supplied) == "(OriginPythonPoint 9)"


def test_compiled_supplied_values_survive_reference_withdrawal():
    """The explicit value in an equation is never re-read as a source name."""
    with MeTTa() as m, m.space() as home, m.space() as target:
        home.run("(: OriginPythonCanonical (-> Number OriginPythonRecord))")
        mapping = parse("(rename ((OriginPythonCanonical OriginPythonPoint)))")
        target.from_(home, mapping)
        supplied = S.OriginPythonPoint(9)
        target.run("(= (origin-python-held) (noeval {value}))", value=supplied)
        assert target.eval(S.origin_python_held()) == [supplied]
        assert target.run("!(noeval (OriginPythonPoint 1))") == [[S.OriginPythonCanonical(1)]]
        target.remove(S["from"](home, mapping))
        assert target.eval(S.origin_python_held()) == [supplied]
        assert target.run("!(noeval (OriginPythonPoint 1))") == [[S.OriginPythonPoint(1)]]


def test_python_import_rewriter_keeps_its_resolved_module_spec(tmp_path):
    """A FROM name cannot reinterpret the private spec supplied by an import."""
    module_name = f"origin_rewriter_{uuid.uuid4().hex}"
    (tmp_path / f"{module_name}.py").write_text("def origin(): return 31\n")
    source = tmp_path / "origin.metta"
    source.write_text(f'!(import! &self "{module_name}.py")\n')
    with MeTTa() as m, m.space() as home, m.space() as target:
        target.load(str(source))
        private_module = m.runtime.must(
            "metta_py:python_import_alias(Name, Key)", Name=module_name,
        )["Key"]
        home.run("(: OriginSpecTrap Atom)")
        target.from_(home, parse(f"(rename ((OriginSpecTrap {private_module}.origin)))"))
        groups = target.run(f"!(py-call ({module_name}.origin))")
        assert [[str(value) for value in group] for group in groups] == [["31"]]
