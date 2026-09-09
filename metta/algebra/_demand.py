"""Purpose: transform certified tagged rules into query-directed demands.

Assumes:
  - algebra._derive_rule_steps remains the shared directional bag evaluator.
Guarantees:
  - demand control facts are unique while every source occurrence and proof
    combination remains in each cached answer bag [tested:
    test_demand_preserves_complete_derivation_bags,
    test_demand_preserves_all_four_duplicate_combinations; commit=3c64e2e24787362a5a5081513bc24b880711a1d7]
  - cycles, insufficient fixpoint bounds, custom operations, linear evidence,
    and unsupported atoms retain full evaluation [tested:
    test_demand_preserves_global_cycle_and_round_failures,
    test_demand_retains_custom_operation_effects; commit=3c64e2e24787362a5a5081513bc24b880711a1d7]
  - the readers certification makes total say so themselves: an atom that
    reached the evaluator without shaping is refused by name instead of being
    read as though it had a relation and arguments [tested:
    test_an_atom_the_certifier_would_decline_is_refused_by_name;
    commit=60d6ca9089f50521bba869c3b7a87c92fd6a990f]
Owns resources:
  - indexes, completed demands, and suspended rule generators belong to one
    evaluation; the generator stack closes on success and every exception
    [tested: test_demand_closes_suspended_rules_on_failure;
    commit=3c64e2e24787362a5a5081513bc24b880711a1d7]
"""

from __future__ import annotations

import sys
from collections import defaultdict, deque
from collections.abc import Generator, Sequence
from dataclasses import dataclass, field

from metta._atoms.factories import Atom, Expression, Grounded, Symbol, Variable, _decode
from metta._faces.space import Space
from metta.algebra import (
    AlgebraEvaluationError,
    DeclaredAlgebra,
    TaggedAnswer,
    _derive_rule_steps,
    _EvaluationBudget,
    _Rule,
    _signature,
)

# Tekle and Liu's positive demand transformation keeps original predicates and
# represents each bound-argument pattern as a separate demand control fact:
# https://arxiv.org/html/1909.08246v1#S3.SS2
# Here its acyclic demand graph is evaluated by an explicit stack. Only control
# demands are sets; cached relation values retain their original proof bags.
# This bag discipline is the multiset magic transformation of Mumick, Pirahesh
# and Ramakrishnan: erasing unique magic guards preserves each original proof.
# https://www.vldb.org/conf/1990/P264.PDF
# [source: VLDB 1990, section 2.3.2 and theorem 2.5; commit=3c64e2e24787362a5a5081513bc24b880711a1d7]
type _Relation = tuple[bool, str, int]
type _Shape = tuple[_Relation, tuple[Atom, ...]]
type _Bindings = tuple[tuple[int, Atom], ...]
type _Derivation = Generator[Atom, Sequence[TaggedAnswer], list[TaggedAnswer]]
type _Rank = tuple[int, int, tuple[_Rank, ...]]


def _shape(atom: Atom) -> _Shape | None:
    if type(atom) is Symbol:
        return (False, atom.name, 0), ()
    if type(atom) is not Expression or not atom.children:
        return None
    head, *arguments = atom.children
    if type(head) is not Symbol:
        return None
    for value in arguments:
        if type(value) in (Symbol, Variable):
            continue
        if type(value) is not Grounded or type(_decode(value)) not in (bool, int, float, str):
            return None
        if type(_decode(value)) is int and not _printable_bits(_decode(value).bit_length()):
            return None
    return (True, head.name, len(arguments)), tuple(arguments)


def _certified_shape(atom: Atom) -> _Shape:
    """The shape of an atom `_certify` has already accepted.

    Certification is what makes this total: it declines the whole algebra
    unless every fact, head and premise shapes, and the evaluator runs only on
    what it admitted. So a None here is not a program this transformation
    declines, it is an atom that reached the evaluator without passing the
    gate, and saying so beats reading a position off nothing.
    """
    shape = _shape(atom)
    if shape is None:
        msg = f"algebra_demand_uncertified_atom({atom})"
        raise AlgebraEvaluationError(msg)
    return shape


def _printable_bits(bits: int) -> bool:
    # _signature renders tags as decimal text. Python's integer conversion limit
    # can therefore make an irrelevant arithmetic rule fail. Three bits per
    # allowed decimal digit is a conservative bound; zero disables the limit.
    digits = sys.get_int_max_str_digits()
    return digits == 0 or bits < digits * 3


def _integer_bits(tag: Atom) -> int | None:
    if type(tag) is not Grounded or type(_decode(tag)) is not int:
        return None
    bits = max(1, _decode(tag).bit_length())
    return bits if _printable_bits(bits) else None


def _certify(
    declaration: DeclaredAlgebra,
    facts: Sequence[TaggedAnswer],
    rules: Sequence[_Rule],
    *,
    goal: Atom,
    max_rounds: int,
    budget: _EvaluationBudget,
) -> tuple[dict[_Relation, list[TaggedAnswer]], dict[_Relation, list[_Rule]]] | None:
    # These are exactly DeclaredAlgebra.operation's direct integer operations.
    # No user operation can execute and an integer carrier never changes kind.
    direct = {"+", "*", "min", "max"}
    # What the transformation asks of the DECLARATION, named apart from what it
    # asks of this call below.
    declared_directly = (
        declaration.extend in direct
        and declaration.combine in direct
        and "linear" not in declaration.requires
    )
    if (
        not declared_directly
        or not rules
        or not isinstance(max_rounds, int)
        or _shape(goal) is None
    ):
        return None
    fact_rows: dict[_Relation, list[TaggedAnswer]] = defaultdict(list)
    rule_rows: dict[_Relation, list[_Rule]] = defaultdict(list)
    dependencies: dict[_Relation, set[_Relation]] = defaultdict(set)
    bounds: dict[_Relation, int] = defaultdict(lambda: 1)
    rule_bits: dict[int, int] = {}
    rule_relations: dict[int, list[_Relation]] = {}
    for answer in facts:
        budget.checkpoint()
        shape = _shape(answer.value)
        bits = _integer_bits(answer.tag)
        if shape is None or bits is None or any(isinstance(arg, Variable) for arg in shape[1]):
            return None
        key, _ = shape
        fact_rows[key].append(answer)
        bounds[key] = max(bounds[key], bits)
        dependencies.setdefault(key, set())
    for rule in rules:
        budget.checkpoint()
        head = _shape(rule.head)
        bits = _integer_bits(rule.tag)
        if head is None or bits is None:
            return None
        key, arguments = head
        head_vars = {arg.name for arg in arguments if isinstance(arg, Variable)}
        body_vars: set[str] = set()
        dependencies.setdefault(key, set())
        # In premise order and keeping repeats: the walk below charges one
        # bound per premise, where `dependencies` is a set and cannot say how
        # many times a relation was named.
        relations: list[_Relation] = []
        for premise in rule.premises:
            premise_shape = _shape(premise)
            if premise_shape is None:
                return None
            relation, args = premise_shape
            relations.append(relation)
            dependencies[key].add(relation)
            dependencies.setdefault(relation, set())
            body_vars.update(arg.name for arg in args if isinstance(arg, Variable))
        if "_" in head_vars or not head_vars <= body_vars:
            return None
        rule_rows[key].append(rule)
        rule_bits[rule.order] = bits
        rule_relations[rule.order] = relations

    # Certify the entire graph: full evaluation can fail on a cycle or depth
    # outside the query's slice, and pruning must not conceal that failure.
    dependents: dict[_Relation, list[_Relation]] = defaultdict(list)
    pending = {key: len(needs) for key, needs in dependencies.items()}
    for key, needs in dependencies.items():
        for needed in needs:
            dependents[needed].append(key)
    ready = deque(key for key, count in pending.items() if count == 0)
    depth: dict[_Relation, int] = {}
    while ready:
        budget.checkpoint()
        key = ready.popleft()
        depth[key] = 0
        for rule in rule_rows[key]:
            bits = rule_bits[rule.order]
            height = 1
            # The relations the pass above already read off this rule's
            # premises, rather than shaping every premise a second time.
            for relation in rule_relations[rule.order]:
                height = max(height, depth[relation] + 1)
                if declaration.extend == "*":
                    bits += bounds[relation]
                elif declaration.extend == "+":
                    bits = max(bits, bounds[relation]) + 1
                else:
                    bits = max(bits, bounds[relation])
            bounds[key] = max(bounds[key], bits)
            depth[key] = max(depth[key], height)
        if depth[key] >= max_rounds or not _printable_bits(bounds[key]):
            return None
        for dependent in dependents[key]:
            pending[dependent] -= 1
            if pending[dependent] == 0:
                ready.append(dependent)
    if len(depth) != len(dependencies):
        return None
    return fact_rows, rule_rows


@dataclass(frozen=True, slots=True)
class _Demand:
    relation: _Relation
    bindings: _Bindings

    @classmethod
    def from_pattern(cls, pattern: Atom) -> _Demand:
        relation, args = _certified_shape(pattern)
        return cls(relation, tuple((i, arg) for i, arg in enumerate(args) if not isinstance(arg, Variable)))


def _head_bindings(rule: _Rule, demand: _Demand) -> dict[str, Atom] | None:
    shape = _certified_shape(rule.head)
    result: dict[str, Atom] = {}
    for position, value in demand.bindings:
        head = shape[1][position]
        if isinstance(head, Variable):
            previous = result.setdefault(head.name, value)
            if previous != value:
                return None
        elif head != value:
            return None
    return result


@dataclass(slots=True)
class _DemandEvaluator:
    metta: Space
    declaration: DeclaredAlgebra
    budget: _EvaluationBudget
    facts: dict[_Relation, list[TaggedAnswer]]
    rules: dict[_Relation, list[_Rule]]
    indexes: dict[tuple[_Relation, tuple[int, ...]], dict[tuple[Atom, ...], list[TaggedAnswer]]] = field(default_factory=dict)
    cache: dict[_Demand, list[TaggedAnswer]] = field(default_factory=dict)
    ranks: dict[int, _Rank] = field(default_factory=dict)

    def _facts(self, demand: _Demand) -> Sequence[TaggedAnswer]:
        if not demand.bindings:
            return self.facts.get(demand.relation, ())
        positions = tuple(position for position, _ in demand.bindings)
        index_key = demand.relation, positions
        index = self.indexes.get(index_key)
        if index is None:
            index = defaultdict(list)
            for answer in self.facts.get(demand.relation, ()):
                self.budget.checkpoint()
                shape = _certified_shape(answer.value)
                index[tuple(shape[1][position] for position in positions)].append(answer)
            self.indexes[index_key] = index
        return index.get(tuple(value for _, value in demand.bindings), ())

    def _rank(self, answer: TaggedAnswer) -> _Rank:
        # Full closure appends facts, then increasing proof heights; within a
        # height it follows source rule order and each premise's available order.
        root = answer._derivations[0]
        stack = [(root, False)]
        while stack:
            self.budget.checkpoint()
            trace, expanded = stack.pop()
            if id(trace) in self.ranks:
                continue
            if trace.children and not expanded:
                stack.append((trace, True))
                stack.extend((child, False) for child in trace.children)
                continue
            children = tuple(self.ranks[id(child)] for child in trace.children)
            height = 1 + max((child[0] for child in children), default=0) if trace.is_rule else 0
            self.ranks[id(trace)] = height, trace.source, children
        return self.ranks[id(root)]

    def _solve(self, demand: _Demand) -> _Derivation:
        answers = list(self._facts(demand))
        for rule in self.rules.get(demand.relation, ()):
            self.budget.checkpoint()
            bindings = _head_bindings(rule, demand)
            if bindings is None:
                continue
            # Prefix bindings generate the next demand, like Souffle's magic
            # clauses constrained by the preceding body atoms. Unlike Souffle's
            # set relations, the shared generator consumes complete proof bags.
            # https://github.com/souffle-lang/souffle/blob/a1303be3c0166400dee3d1f36f0d96abe03e6901/src/ast/transform/MagicSet.cpp#L1135-L1167
            derived = yield from _derive_rule_steps(
                self.metta, self.declaration, rule, self.budget, bindings
            )
            answers.extend(derived)
        unique = {_signature(answer): answer for answer in answers}
        return sorted(unique.values(), key=self._rank)

    def evaluate(self, goal: Atom) -> list[TaggedAnswer]:
        """Run suspended demand rules without using the Python call stack."""
        demand = _Demand.from_pattern(goal)
        stack = [(demand, self._solve(demand))]
        reply: Sequence[TaggedAnswer] | None = None
        try:
            while stack:
                self.budget.checkpoint()
                current, derivation = stack[-1]
                try:
                    requested = next(derivation) if reply is None else derivation.send(reply)
                except StopIteration as completed:
                    self.cache[current] = completed.value
                    stack.pop()
                    reply = completed.value
                    continue
                next_demand = _Demand.from_pattern(requested)
                reply = self.cache.get(next_demand)
                if reply is None:
                    stack.append((next_demand, self._solve(next_demand)))
            return self.cache[demand]
        finally:
            for _, derivation in stack:
                derivation.close()


def evaluate_demand(
    metta: Space,
    declaration: DeclaredAlgebra,
    facts: Sequence[TaggedAnswer],
    rules: Sequence[_Rule],
    *,
    goal: Atom,
    max_rounds: int,
    budget: _EvaluationBudget,
) -> list[TaggedAnswer] | None:
    """Return a complete demanded bag, or decline without running any rule."""
    certified = _certify(
        declaration, facts, rules, goal=goal, max_rounds=max_rounds, budget=budget
    )
    if certified is None:
        return None
    fact_rows, rule_rows = certified
    return _DemandEvaluator(metta, declaration, budget, fact_rows, rule_rows).evaluate(goal)
