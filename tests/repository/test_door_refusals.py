"""Purpose: plant the invalid inputs and replies declared by door contracts.

Guarantees: each witness reaches a public door and asserts its declared refusal
  class [tested: this file; commit=b615b5a33b43252ef9826e5387da7c9bd7f6b543].
Owns resources: each test borrows the context fixture; answer sources close
  through their context managers and patched engine replies restore on exit.
"""

from __future__ import annotations

import pytest

from metta import G, MeTTa, S, V, lib
from metta._errors.errors import EngineError, SourceNotFound
from metta._spaces.results import Answers, Rows


@pytest.fixture
def context():
    """Own every space allocated by one refusal witness."""
    with MeTTa() as held:
        yield held


def _two_argument_judge(atom, _other):
    return atom


@pytest.mark.parametrize("invoke", [
    pytest.param(lambda m: m.self.bind({1: 2}), id="space:bind"),
    pytest.param(lambda m: m.self.register_token("door-token", None), id="space:register-token"),
    pytest.param(lambda m: m.self.add(lib.he, S.fact), id="space:add"),
    pytest.param(lambda m: m.self.__ior__(1), id="space:__ior__"),
    pytest.param(lambda m: m.self[:1], id="space:__getitem__"),
    pytest.param(lambda m: m.self.stream(S.fact(V.x), under="counting"), id="space:stream"),
    pytest.param(lambda m: m.self.saga(None), id="space:saga"),
    pytest.param(lambda m: m.self.subscribe(S.fact, where=object()), id="space:subscribe"),
    pytest.param(lambda m: m.self.define(), id="space:define"),
    pytest.param(lambda m: m.self.pre_add(_two_argument_judge), id="space:pre-add"),
    pytest.param(lambda m: m.self.reacts(S.fact, S.fact, priority=True), id="space:reacts"),
    pytest.param(lambda m: m.self.args, id="space:args"),
    pytest.param(lambda m: m.self.children, id="space:children"),
    pytest.param(lambda m: m.self.head, id="space:head"),
    pytest.param(lambda m: m.space(sync="always"), id="context:space"),
    pytest.param(lambda _m: Rows((), ()).why(), id="rows:why"),
    pytest.param(lambda _m: Rows((), ()).build("not-a-class"), id="rows:build"),
    pytest.param(lambda _m: Rows((), ()).to("door-unregistered-frame"), id="rows:to"),
])
def test_door_type_refusals(context, invoke):
    """A malformed caller shape raises the engine table's Python type class."""
    with pytest.raises(TypeError):
        invoke(context)


def test_answer_rows_refuses_an_answer_without_bindings():
    """A plain term cannot be presented as a caller-variable row."""
    with Answers(iter((S.fact,))) as answers, answers.rows as rows:
        with pytest.raises(TypeError, match="carries no variable row"):
            list(rows)


@pytest.mark.parametrize("invoke", [
    pytest.param(lambda m: m.self.profile_extension("!(+ 1 2)"), id="space:profile-extension"),
    pytest.param(lambda m: m.self.solve(1, 2), id="space:solve"),
    pytest.param(lambda m: m.self.register_prolog(), id="space:register-prolog"),
    pytest.param(lambda m: m.self.agenda("user"), id="space:agenda"),
    pytest.param(lambda m: m.self.capacity(0), id="space:capacity"),
    pytest.param(lambda _m: Rows(("x",), ((G(1),),)).why(), id="rows:why"),
    pytest.param(lambda _m: Rows((), ((),)).table(), id="rows:table"),
])
def test_door_value_refusals(context, invoke):
    """An invalid value raises the refusal table's host value class."""
    with pytest.raises(ValueError):
        invoke(context)


def test_bind_refuses_the_reserved_template_namespace(context):
    """Caller bindings cannot replace symbols allocated for template holes."""
    from metta._spaces.handle import _HOLE_PREFIX

    with pytest.raises(ValueError, match="cannot be bound"):
        context.self.bind({_HOLE_PREFIX + "0": 1})


def test_digest_refuses_live_host_identity(context):
    """A live host object has no portable content digest."""
    context.self.add(S.holds(G(object())))
    with pytest.raises(ValueError, match="cross-process identity"):
        context.self.digest()


@pytest.mark.parametrize("door", ("first", "one"))
def test_empty_rows_refuse_an_asserted_scalar(door):
    """Absence without an explicit default cannot satisfy a scalar request."""
    with pytest.raises(EngineError):
        getattr(Rows((), ()), door)()


@pytest.mark.parametrize("door", ("first", "one"))
def test_empty_answers_refuse_an_asserted_scalar(door):
    """The lazy result enforces the same scalar absence rule."""
    with Answers(iter(())) as answers:
        with pytest.raises(EngineError):
            getattr(answers, door)()


@pytest.mark.parametrize("door", ("type", "doc"))
def test_door_refuses_a_missing_engine_answer(context, monkeypatch, door):
    """A failed engine reply is reported before indexing its missing answer."""
    monkeypatch.setattr(type(context.self), "eval", lambda *_args, **_kwargs: [])
    with pytest.raises(EngineError):
        getattr(context.self, door)(S.subject)


def test_digest_refuses_an_invalid_engine_reply(context, monkeypatch):
    """A malformed digest reply cannot become a plausible digest string."""
    monkeypatch.setattr(type(context.runtime), "apply_must", lambda *_args, **_kwargs: None)
    with pytest.raises(EngineError, match="invalid result"):
        context.self.digest()


def test_transaction_refuses_an_unreported_engine_failure(context, monkeypatch):
    """A transaction cannot report success if its engine goal silently fails."""
    monkeypatch.setattr(type(context.runtime), "once", lambda *_args, **_kwargs: None)
    with pytest.raises(EngineError, match="transaction goal failed"):
        context.self.transaction(lambda: None)


def test_info_refuses_an_unreported_engine_version(context, monkeypatch):
    """Version reflection rejects a reply without the version it promises."""
    import metta._spaces.handle as _space

    with monkeypatch.context() as patch:
        patch.setattr(_space.bridge(), "query_once", lambda *_args, **_kwargs: None)
        with pytest.raises(EngineError, match="did not report"):
            context.info()


def test_foreign_library_refuses_a_missing_source(context, tmp_path):
    """A missing library is refused before any engine registration changes."""
    with pytest.raises(SourceNotFound, match="no compiled library"):
        context.self.register_foreign_library(tmp_path / "missing-door-library.so")
