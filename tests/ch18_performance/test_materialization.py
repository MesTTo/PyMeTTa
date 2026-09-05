"""Purpose: compare loaded function-free bags and retained proof trees.

Guarantees:
  - text and fast reloads preserve duplicate paths and replace old content
    [tested: test_reloading_a_materialized_program_preserves_its_bag;
    commit=WORKTREE]
  - later compiled callers retain the original bounded derivation tree
    [tested: test_a_later_retained_caller_preserves_bounded_derivations;
    commit=WORKTREE]
"""

from collections import Counter

import janus_swi
import pytest

from metta import MeTTa, S, Variable
from metta.errors import InferenceLimitError

_RULES = """
(= (materialized-reach $x $y) (match &self (materialized-edge $x $y) True))
(= (materialized-reach $x $y)
   (match &self (materialized-edge $x $z) (materialized-reach $z $y)))
"""


def _discard_relation(space):
    """The internal lifecycle door exposes the retained compiled oracle."""
    janus_swi.query_once("materialize:discard_space(S)", {"S": str(space.name)})


@pytest.mark.parametrize("file_format", ["metta", "fast"])
def test_reloading_a_materialized_program_preserves_its_bag(tmp_path, file_format):
    """Both loading doors replace a counted relation after a source edit."""
    path = tmp_path / f"materialized.{file_format}"
    with MeTTa() as m, m.space() as source, m.space() as restored:
        source.run(
            "(materialized-edge a b) (materialized-edge a b) "
            "(materialized-edge b c)" + _RULES
        )
        source.save(path, format=file_format)
        for _ in range(2):
            restored.load(path)
            assert Counter(map(str, restored.eval(S.materialized_reach(S.a, S.c)))) == {
                "True": 2
            }
        source.add(S.materialized_edge(S.a, S.c))
        source.save(path, format=file_format)
        restored.load(path)
        assert Counter(map(str, restored.eval(S.materialized_reach(S.a, S.c)))) == {
            "True": 3
        }


def test_a_later_retained_caller_preserves_bounded_derivations():
    """An eager caller must expose every original rule and fact to proof search."""
    source = (
        "(materialized-edge a b) (materialized-edge b c) "
        "(materialized-edge c d) (materialized-edge d e)" + _RULES
    )
    later = """
    (materialized-start a)
    (= (materialized-later $x $y)
       (match &self (materialized-start $x) (materialized-reach $x $y)))
    """
    summaries = []
    with MeTTa() as m:
        for use_relation in (True, False):
            with m.space() as space:
                space.run(source)
                if not use_relation:
                    _discard_relation(space)
                space.run(later)
                if not use_relation:
                    _discard_relation(space)
                summaries.append(
                    [
                        [
                            (
                                "$answer"
                                if isinstance(proof.answer, Variable)
                                else str(proof.answer),
                                proof.complete,
                                len(proof.rules),
                                len(proof.facts),
                                len(proof.truncations),
                            )
                            for proof in space.derivation(
                                S.materialized_later(S.a, S.e), depth=depth
                            )
                        ]
                        for depth in (2, 4, 20)
                    ]
                )
    assert summaries[0] == summaries[1]
    assert summaries[0][-1] == [("True", True, 5, 5, 0)]


def test_a_bounded_first_load_rolls_back_materialization_preprocessing(tmp_path):
    """An interrupted load removes source and derived rows before returning."""
    path = tmp_path / "bounded-materialization.metta"
    source = "\n".join(f"(materialized-edge n{i} n{i + 1})" for i in range(64))
    path.write_text(source + _RULES)
    with MeTTa() as m, m.space() as space:
        space.add(S.materialized_kept(S.value))
        with pytest.raises(InferenceLimitError):
            space.load(path, inferences=50_000)
        assert list(space.atoms()) == [S.materialized_kept(S.value)]
        assert not janus_swi.query_once(
            "materialize:materialized_snapshot(S,_M,_Token,_Stamp,_Functions)",
            {"S": str(space.name)},
        )["truth"]


def test_a_bounded_reload_restores_the_previous_materialized_bag(tmp_path):
    """A failed replacement restores the table with its original source."""
    path = tmp_path / "bounded-materialization-reload.metta"
    original = "(materialized-edge a b) (materialized-edge b c)" + _RULES
    path.write_text(original)
    with MeTTa() as m, m.space() as space:
        space.load(path)
        expected = space.source()
        path.write_text(
            original
            + "(materialized-edge a c) "
            "(= (materialized-load-spin $x) (materialized-load-spin $x)) "
            "!(materialized-load-spin 0)"
        )
        with pytest.raises(InferenceLimitError):
            space.load(path, inferences=50_000)
        assert space.source() == expected
        assert Counter(map(str, space.eval(S.materialized_reach(S.a, S.c)))) == {
            "True": 1
        }


def test_public_eval_reuses_the_loaded_ground_relation():
    """Direct expression evaluation shares the source runnable's indexed path."""
    costs = []
    with MeTTa() as m:
        for size in (32, 128, 512):
            with m.space() as space:
                source = "\n".join(
                    f"(materialized-edge n{i} n{i + 1})" for i in range(size)
                )
                space.run(source + _RULES)
                query = S.materialized_reach(S.n0, S[f"n{size}"])
                assert Counter(map(str, space.eval(query))) == {"True": 1}
                with space.stats() as spent:
                    assert Counter(map(str, space.eval(query))) == {"True": 1}
                costs.append(spent.inferences)
    assert costs[1] < costs[0] * 1.5
    assert costs[2] < costs[1] * 1.5


def test_public_transactions_prepare_and_roll_back_the_same_relation():
    """The public transaction owns preparation and nested rollback together."""
    with MeTTa() as m, m.space() as space:
        source = (
            "(materialized-edge a b) (materialized-edge a b) "
            "(materialized-edge b c)" + _RULES
        )
        space.transaction(lambda: space.run(source))
        assert janus_swi.query_once(
            "materialize:materialized_snapshot(S,_M,_Trie,_Stamp,_Functions)",
            {"S": str(space.name)},
        )["truth"]
        before = space.source()

        def fail_after_nested_source():
            space.transaction(lambda: space.run("(materialized-edge a c)"))
            assert Counter(map(str, space.eval(S.materialized_reach(S.a, S.c)))) == {
                "True": 3
            }
            msg = "roll back the prepared relation"
            raise RuntimeError(msg)

        with pytest.raises(RuntimeError, match="roll back the prepared relation"):
            space.transaction(fail_after_nested_source)
        assert space.source() == before
        assert Counter(map(str, space.eval(S.materialized_reach(S.a, S.c)))) == {
            "True": 2
        }


def _collected_trie_identities():
    """Separate host queries end transient Prolog roots before collecting."""
    janus_swi.query_once("garbage_collect_clauses,garbage_collect,garbage_collect_atoms")
    return janus_swi.query_once(
        "findall(_Text,(current_trie(_Trie),term_string(_Trie,_Text)),Identities)"
    )["Identities"]


def test_a_rolled_back_index_is_collected_while_the_live_index_answers():
    """A rolled-back image loses its root without destroying the restored one."""
    with MeTTa() as m, m.space() as space:
        space.run(
            "(materialized-edge a b) (materialized-edge a b) "
            "(materialized-edge b c)" + _RULES
        )
        live = janus_swi.query_once(
            "materialize:materialized_snapshot(S,_M,_Trie,_Stamp,_Functions),"
            "is_trie(_Trie),term_string(_Trie,Identity)",
            {"S": str(space.name)},
        )["Identity"]
        # A local nonbacktracking cell preserves only the printed identity
        # across rollback. Returning the blob itself would keep it alive.
        retired = janus_swi.query_once(
            r"_Box=image(none),\+materialize:materialization_transaction(("
            "materialize:discard_space(S),"
            "materialize:materialize_source(S),"
            "materialize:materialized_snapshot(S,_M,_Trie,_Stamp,_Functions),"
            "term_string(_Trie,_Text),nb_setarg(1,_Box,_Text),fail)),"
            "arg(1,_Box,Identity)",
            {"S": str(space.name)},
        )["Identity"]
        identities = _collected_trie_identities()
        assert live in identities
        assert retired not in identities
        assert Counter(map(str, space.eval(S.materialized_reach(S.a, S.c)))) == {
            "True": 2
        }


def test_a_released_index_is_collected_after_its_query_boundary():
    """A released snapshot leaves no index root in its lifetime registry."""
    with MeTTa() as m:
        with m.space() as space:
            space.run("(materialized-edge a b) (materialized-edge b c)" + _RULES)
            retired = janus_swi.query_once(
                "materialize:materialized_snapshot(S,_M,_Trie,_Stamp,_Functions),"
                "is_trie(_Trie),term_string(_Trie,Identity)",
                {"S": str(space.name)},
            )["Identity"]
            assert Counter(map(str, space.eval(S.materialized_reach(S.a, S.c)))) == {
                "True": 1
            }
        assert retired not in _collected_trie_identities()


def test_public_floating_keys_preserve_the_original_answer_bag():
    """Signed zeros, NaN, infinities and float/integer ties keep their identity."""
    values = (0, 0.0, -0.0, 1, 1.0, float("inf"), float("-inf"), float("nan"))
    rule = """
    (= (materialized-float-key $x)
       (match &self (materialized-float-value $x) True))
    """
    with MeTTa() as m, m.space() as fast, m.space() as reference:
        for space in (fast, reference):
            for count, value in enumerate(values, 1):
                for _ in range(count):
                    space.add(S.materialized_float_value(value))
        reference.run(rule)
        _discard_relation(reference)
        fast.run(rule)
        assert janus_swi.query_once(
            "materialize:materialized_snapshot(S,_M,_Trie,_Stamp,_Functions)",
            {"S": str(fast.name)},
        )["truth"]
        for value in values:
            query = S.materialized_float_key(value)
            expected = Counter(map(str, reference.eval(query)))
            assert expected
            assert Counter(map(str, fast.eval(query))) == expected
        query = S.materialized_float_key(Variable("x"))
        assert Counter(map(str, fast.eval(query))) == Counter(
            map(str, reference.eval(query))
        )
