"""Purpose: verify reachability through current native class fields at scope exit.

Guarantees: replacements, cycles and native edits retain only reachable scoped
  resources [tested: test_kept_native_field_graphs_preserve_exact_reachability;
  commit=bc30fbd0bbcbf535de217d5a9efad2910002f343].
Owns resources: each case releases its scopes, class program and context.
"""

from dataclasses import dataclass

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from metta import Atom, MeTTa, S, Space, convert
from metta._declare.classes import declaration


@pytest.mark.parametrize("grain", ["entity", "prototype"])
@pytest.mark.parametrize("native_edit", [False, True])
@pytest.mark.parametrize("kept_image", [False, True])
def test_kept_fields_follow_the_last_stored_value(grain, native_edit, kept_image):
    """Keeping a receiver retains the replacement and releases its old field."""
    with MeTTa() as context:
        home = context.self
        base = Space if grain == "prototype" else object

        @home.define
        @dataclass
        class ScopedFields(base):
            child: Space

        with home.scope():
            with home.scope() as inner:
                old = context.space()
                holder = ScopedFields(old)
                image = convert.project(holder).atom
                inner.keep(image if kept_image else holder)
                direct = inner.keep(context.space())
                replacement = context.space()
                replacement.add(S.payload(9))
                if native_edit:
                    storage = holder if grain == "prototype" else declaration(ScopedFields).space
                    prefix = () if grain == "prototype" else (image,)
                    storage.remove(S["_field-child"](*prefix, S[old.name]))
                    storage.add(S["_field-child"](*prefix, S[replacement.name]))
                else:
                    holder.child = replacement
                discarded_child = context.space()
                discarded = ScopedFields(discarded_child)
            assert old.dropped
            assert not replacement.dropped
            assert not direct.dropped
            assert holder.child.atoms() == [S.payload(9)]
            assert discarded_child.dropped
            with pytest.raises(ReferenceError):
                convert.project(discarded)
        assert replacement.dropped
        assert direct.dropped
        with pytest.raises(ReferenceError):
            convert.project(holder)


@pytest.mark.parametrize("grain", ["entity", "prototype"])
def test_an_ancestor_owned_receiver_can_keep_its_new_inner_field(grain):
    """The returned root can already belong to the enclosing scope."""
    with MeTTa() as context:
        home = context.self
        base = Space if grain == "prototype" else object

        @home.define
        @dataclass
        class AncestorFields(base):
            child: Space

        with home.scope():
            old = context.space()
            holder = AncestorFields(old)
            with home.scope() as inner:
                replacement = context.space()
                replacement.add(S.payload(12))
                holder.child = replacement
                inner.keep(holder)
            assert not replacement.dropped
            assert holder.child.atoms() == [S.payload(12)]
            assert not old.dropped
        assert old.dropped
        assert replacement.dropped


@settings(max_examples=20, deadline=None)
@given(
    grain=st.sampled_from(["entity", "prototype"]),
    edges=st.lists(st.sets(st.integers(0, 5)), max_size=6),
    roots=st.sets(st.integers(0, 5)),
)
def test_kept_native_field_graphs_preserve_exact_reachability(grain, edges, roots):
    """Arbitrary shared and cyclic field graphs retain their reachable nodes."""
    graph = [{child for child in row if child < len(edges)} for row in edges]
    reachable = {root for root in roots if root < len(edges)}
    pending = list(reachable)
    while pending:
        for child in graph[pending.pop()] - reachable:
            reachable.add(child)
            pending.append(child)
    with MeTTa() as context:
        home = context.self
        base = Space if grain == "prototype" else object

        @home.define
        @dataclass
        class ScopedGraphNode(base):
            links: Atom
            payload: Space

        with home.scope():
            with home.scope() as inner:
                payloads = [context.space() for _ in graph]
                nodes = [ScopedGraphNode(S.links(), payload) for payload in payloads]
                images = [convert.project(node).atom for node in nodes]
                for root in roots:
                    if root < len(nodes):
                        inner.keep(nodes[root])
                for node, children in zip(nodes, graph, strict=True):
                    node.links = S.links(*(images[child] for child in sorted(children)))
            for index, node in enumerate(nodes):
                assert payloads[index].dropped == (index not in reachable)
                if index in reachable:
                    assert convert.project(node).atom == images[index]
                    assert node.links == S.links(*(images[child] for child in sorted(graph[index])))
                else:
                    with pytest.raises(ReferenceError):
                        convert.project(node)
        assert all(payload.dropped for payload in payloads)
