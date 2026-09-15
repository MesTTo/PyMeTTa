"""Purpose: keep compiled argument collectors visible to native rewriting.

Guarantees:
  - native method and constructor heads match positional and ordered keyword
    terms [tested: test_compiled_collectors_match_native_equation_heads;
    test_constructor_keyword_terms_reach_native_initializers; commit=WORKTREE]
  - every answer of one activation shares its fresh keyword dictionary
    [tested: test_compiled_generator_answers_share_one_keyword_dictionary;
    commit=WORKTREE]
  - Atom result syntax remains held after dictionary allocation [tested:
    test_compiled_collector_entry_preserves_held_result_syntax; commit=WORKTREE]
  - refused method bodies receive the same native collector values as compiled
    bodies [tested: test_refused_method_collectors_enter_the_host_body; commit=WORKTREE]
Owns resources: each context releases its program and collected dictionaries.
"""

import inspect
from dataclasses import dataclass

import pytest

from metta import Atom, Expression, G, MeTTa, S, Space, V
from metta._catalog.call_values import apply_sources
from metta._declare.classes import declaration
from metta._declare.define import compile_function
from metta._errors.errors import EngineError


def test_compiled_collectors_match_native_equation_heads():
    """A native rule can distinguish keyword order before dictionary creation."""
    with MeTTa() as context:
        home = context.self

        @home.define
        @dataclass(frozen=True)
        class RewriteCollector:
            def collect(self, *values: int, flag: int = 3, **options: int) -> int:
                return sum(values) + flag + sum(options.values())

        value = RewriteCollector()
        owner = declaration(RewriteCollector)
        head = S["RewriteCollector-collect"]
        owner.space.remove(S["="](head(V.self, V.values, V.flag, V.options), V.body))
        keywords = Expression([Expression([G("right"), V.right]), Expression([G("left"), V.left])])
        owner.space.add(S["="](head(V.self, Expression([V.first, V.second]), V.flag, keywords),
                                S["+"](S["+"](V.first, V.second), S["+"](V.flag, V.right))))
        assert value.collect(2, 3, right=5, left=7) == 13
        with pytest.raises(EngineError, match="expected exactly one answer, got 0"):
            value.collect(2, 3, left=7, right=5)


def test_constructor_keyword_terms_reach_native_initializers():
    """The constructor grammar reaches a structural native initialization rule."""
    with MeTTa() as context:
        home = context.self

        @home.define
        class RewriteConstructor:
            value: int

            def __init__(self, **options: int):
                self.value = options["left"]

        owner = declaration(RewriteConstructor)
        head = S["_initialize-RewriteConstructor"]
        owner.space.remove(S["="](head(V.self, V.options), V.body))
        keywords = Expression([Expression([G("left"), V.left])])
        body = S.chain(owner.accessor("value", write=True)(V.self, V.left), V.written, V.self)
        owner.space.add(S["="](head(V.self, keywords), body))
        assert RewriteConstructor(left=9).value == 9


def _collector_answers(**options):
    yield options
    yield options


def test_compiled_generator_answers_share_one_keyword_dictionary():
    """Flat yields share one entry allocation; separate calls get fresh spaces."""
    compiled = compile_function(_collector_answers, lambda _name: False,
                                signature=inspect.signature(_collector_answers),
                                metta_name="collector-answers")
    with MeTTa() as context:
        home = context.self
        home.run("!(import! &self (library lib_dict))")
        head = S["collector-answers"]
        home.add(S[":"](head, S["->"](S.Expression, S["%Undefined%"])))
        home.add(*(S["="](head(V.options), body) for body in compiled.equation_bodies))
        keywords = Expression([Expression([G("held"), S["+"](1, 2)])])
        previous = None
        for _ in range(2):
            before = set(home.space_names())
            result = home.eval(apply_sources(head, (S.noeval(keywords),)))
            assert len(result) == 2
            spaces = [Space(value) for value in result]
            assert spaces[0] == spaces[1]
            assert spaces[0] != previous
            assert Expression(spaces[0].atoms()) == keywords
            assert len(set(home.space_names()) - before) == 1
            previous = spaces[0]


def test_compiled_collector_entry_preserves_held_result_syntax():
    """An Atom result retains its body syntax after the dictionary is bound."""
    with MeTTa() as context:
        home = context.self

        @home.define
        @dataclass(frozen=True)
        class QuotedCollector:
            def syntax(self, **options: Atom) -> Atom:
                return S.pair(options, S["+"](1, 2))

        result = QuotedCollector().syntax(code=S["+"](4, 5))
        assert result.head == S.pair
        assert result.args[1] == S["+"](1, 2)
        assert Space(result.args[0]).atoms() == [Expression([G("code"), S["+"](4, 5)])]


def test_refused_method_collectors_enter_the_host_body(capsys):
    """The explicit host island sees tuple and dictionary collector values."""
    with MeTTa() as context:
        home = context.self

        @home.define
        @dataclass(frozen=True)
        class RefusedCollector:
            def collect(self, *values: int, **options: int) -> int:
                try:
                    total = sum(values) + options["left"]
                except* ValueError:
                    total = 0
                return total

        value = RefusedCollector()
        assert "except*" in capsys.readouterr().err
        assert value.collect(2, 3, left=7) == value.collect.py(2, 3, left=7) == 12
        assert "_host-" in value.collect.source()
