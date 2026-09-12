"""Purpose: verify portable MeTTa programs after their original spaces close.

Guarantees: reference cycles, shared spaces, lexical bindings, entity classes,
source replacement and failed writes preserve their contracts
[tested: test_program_source.py; commit=9b0a084e534ddf7dd67980ad84c27c8279b877f1].
"""

import pytest

from metta import Expression, MeTTa, S, V, ground
from metta._errors.errors import EngineError, SourceNotFound
from metta._spaces.snapshot import program_space, save_program


def test_program_source_preserves_reference_cycles_and_lexical_bindings(tmp_path):
    """Two private namespaces keep their local reads and one shared node."""
    path = tmp_path / "graph.metta"
    with MeTTa() as donor:
        left, right, shared = (donor.space() for _ in range(3))
        donor.self.add(S.graph(left, right, shared))
        left.add(S.links(right, shared), S.seed(3))
        right.add(S.links(left, shared), S.seed(7))
        shared.add(S.shared_fact(S.ready))
        for node in (left, right):
            node.run("(internal pick) (= (pick) (match &self (seed $value) $value))")
        old = {left.name, right.name, shared.name}
        text = program_space(donor.runtime, donor.self.name)
        assert text == program_space(donor.runtime, donor.self.name)
        save_program(donor.runtime, donor.self.name, path)
        assert path.read_text() == text

    with MeTTa() as restored:
        assert restored.self.load(path) == [[True]]
        row, = restored.self.match(S.graph(V.left, V.right, V.shared))
        assert not old.intersection(map(str, (row.left, row.right, row.shared)))
        assert restored.run("!(evalc (pick) {left})", left=row.left) == [[3]]
        assert restored.run("!(evalc (pick) {right})", right=row.right) == [[7]]
        assert restored.run(
            "!(match {left} (links $next $shared) (== $shared {shared}))",
            left=row.left, shared=row.shared,
        ) == [[True]]
        assert restored.run(
            "!(match {right} (links $next $shared) (== $next {left}))",
            right=row.right, left=row.left,
        ) == [[True]]


def test_program_source_rebuilds_an_entity_class(tmp_path):
    """An exported entity still constructs, mutates and reads in native MeTTa."""
    path = tmp_path / "entity.metta"
    with MeTTa() as donor:
        @donor.self.define
        class ExportedCounter:
            value: int

        save_program(donor.runtime, donor.self.name, path)
    with MeTTa() as restored:
        assert restored.self.load(path) == [[True]]
        assert restored.run(
            "!(let $counter (make-ExportedCounter 4) "
            "(progn (ExportedCounter-value! $counter 9) "
            "(ExportedCounter-value $counter)))"
        ) == [[9]]


def test_program_reload_releases_its_previous_spaces(tmp_path):
    """Replacement retires allocations and failed replacement keeps the old graph."""
    path = tmp_path / "owned.metta"
    with MeTTa() as donor:
        child = donor.space()
        child.add(S.kept(17))
        donor.self.add(S.child(child))
        save_program(donor.runtime, donor.self.name, path)
        text = path.read_text()

    with MeTTa() as restored:
        restored.self.load(path)
        old, = restored.run("!(match &self (child $child) $child)")[0]
        restored.self.load(path)
        current, = restored.run("!(match &self (child $child) $child)")[0]
        assert old != current
        assert not restored.runtime.once(
            "spaces:metta_space_identity_live(Space)", Space=str(old)
        )
        before = restored.runtime.must(
            "findall(_Space, spaces:native_storage_module_cache(_Space, _), Spaces)"
        )["Spaces"]
        missing = tmp_path / "missing.metta"
        path.write_text(text + f'!(import! &self "{missing}")\n')
        with pytest.raises(SourceNotFound):
            restored.self.load(path)
        assert restored.run("!(match &self (child $child) $child)") == [[current]]
        after = restored.runtime.must(
            "findall(_Space, spaces:native_storage_module_cache(_Space, _), Spaces)"
        )["Spaces"]
        assert set(after) == set(before)


def test_program_source_refuses_a_live_object_before_replacing_a_file(tmp_path):
    """Validation reaches referenced children and preserves the destination."""
    path = tmp_path / "existing.metta"
    path.write_text("old source\n")
    with MeTTa() as donor:
        child = donor.space()
        child.add(S.payload(ground(object())))
        donor.self.add(S.child(child))
        with pytest.raises(ValueError, match="live Python object"):
            save_program(donor.runtime, donor.self.name, path)
    assert path.read_text() == "old source\n"
    assert list(tmp_path.glob(".metta-save-*")) == []


def test_program_source_restores_tokens_and_bidirectional_rules(tmp_path):
    """Aliases and inverse-rule ownership survive repeated text loads."""
    path = tmp_path / "registries.metta"
    with MeTTa() as donor:
        donor.run("!(bind! &portable-child (new-space))")
        donor.run("!(bind! &portable-alias &portable-child)")
        donor.run("!(add-atom &portable-child (kept 17))")
        donor.run("(= (portable-box $x) (noeval (portable-wrapped $x)))")
        donor.run("!(add-translator-rule! portable-box ((direction bidirectional)))")
        expected = donor.run("!(portable-box 3)")
        assert expected
        save_program(donor.runtime, donor.self.name, path)

    with MeTTa() as restored:
        for _ in range(2):
            assert restored.self.load(path) == [[True]]
            assert restored.run("!(== &portable-child &portable-alias)") == [[True]]
            assert restored.run("!(match &portable-child (kept $x) $x)") == [[17]]
            assert restored.run("!(portable-box 3)") == expected
            assert restored.run(
                "!(match &self (= (portable-wrapped $x) $body) True)"
            ) == [[True]]
        restored.run("!(remove-translator-rule! portable-box)")
        assert restored.run(
            "!(match &self (= (portable-wrapped $x) $body) True)"
        ) == [[]]


def test_program_source_refuses_an_incomplete_translator_rule(tmp_path):
    """Export names a missing derivative and preserves an existing file."""
    path = tmp_path / "incomplete-rule.metta"
    path.write_text("old source\n")
    with MeTTa() as context:
        context.run("(= (incomplete-box $x) (noeval (incomplete-wrapped $x)))")
        context.run("!(add-translator-rule! incomplete-box ((direction bidirectional)))")
        derived = next(atom for atom in context.self.atoms()
                       if isinstance(atom, Expression) and atom.head == S["="]
                       and atom.args[0].head == S["incomplete-wrapped"])
        assert context.self.remove(derived)
        with pytest.raises(EngineError, match=r"incomplete-box.*derived equation is missing"):
            save_program(context.runtime, context.self.name, path)
        assert path.read_text() == "old source\n"
        assert not list(tmp_path.glob(".metta-save-*"))
        context.run("!(remove-translator-rule! incomplete-box)")
        save_program(context.runtime, context.self.name, path)
        assert path.read_text() != "old source\n"


def test_a_failed_first_program_load_retires_its_token_bindings(tmp_path):
    """A failed import leaves neither a created child nor an alias to it."""
    path = tmp_path / "broken-registry.metta"
    with MeTTa() as donor:
        donor.run("!(bind! &portable-failed (new-space))")
        save_program(donor.runtime, donor.self.name, path)
    path.write_text(path.read_text() + f'!(import! &self "{tmp_path / "absent.metta"}")\n')
    with MeTTa() as restored:
        with pytest.raises(SourceNotFound):
            restored.self.load(path)
        assert not restored.runtime.once(
            "metta_engine:metta_token('&portable-failed', _)"
        )


def test_a_referenced_global_home_does_not_inherit_the_importing_program(tmp_path):
    """A class-style private space keeps the engine root as its equation base."""
    path = tmp_path / "base.metta"
    with MeTTa() as donor:
        @donor.self.define
        class GlobalHomeCounter:
            value: int

        save_program(donor.runtime, donor.self.name, path)
    with MeTTa() as restored:
        restored.self.load(path)
        home, = restored.run("!(match &self (from $home) $home)")[0]
        assert restored.runtime.once(
            "spaces:space_equation_home(Space, '&self')", Space=str(home)
        )


@pytest.mark.parametrize("order, answers", [((1, 0), (1, 0)), ((0, 1), (2, 0))])
def test_source_token_claims_withdraw_in_either_order(tmp_path, order, answers):
    """Source removal exposes the most recent binding whose owner still exists."""
    with MeTTa() as context:
        context.run('!(let $name (atom_concat "owned-source-token" "") (bind! $name 0))')
        paths = [tmp_path / f"claim-{index}.metta" for index in range(2)]
        for index, path in enumerate(paths):
            path.write_text(
                f'!(let $name (atom_concat "owned-source-token" "") (bind! $name {index + 1}))\n'
            )
            context.self.load(path)
        assert context.run("!(quote owned-source-token)") == [[2]]
        assert not context.runtime.once(
            "metta_engine:metta_token('owned-source-token', 1)"
        )
        for index, answer in zip(order, answers, strict=True):
            context.runtime.must(
                "filereader:withdraw_source_load(File, Space, _)",
                File=str(paths[index]), Space=context.self.name,
            )
            assert context.run("!(quote owned-source-token)") == [[answer]]


def test_a_later_explicit_token_binding_survives_source_withdrawal(tmp_path):
    """Withdrawing a file cannot erase a subsequent caller replacement."""
    path = tmp_path / "claim.metta"
    path.write_text('!(let $name (atom_concat "caller-source-token" "") (bind! $name 1))\n')
    with MeTTa() as context:
        context.self.load(path)
        context.run('!(let $name (atom_concat "caller-source-token" "") (bind! $name 2))')
        context.runtime.must(
            "filereader:withdraw_source_load(File, Space, _)",
            File=str(path), Space=context.self.name,
        )
        assert context.run("!(quote caller-source-token)") == [[2]]


def test_a_failed_source_token_binding_restores_the_previous_value(tmp_path):
    """A failed first load preserves the value it temporarily shadowed."""
    path = tmp_path / "claim-failed.metta"
    path.write_text(
        '!(let $name (atom_concat "failed-source-token" "") (bind! $name 1))\n'
        f'!(import! &self "{tmp_path / "missing.metta"}")\n'
    )
    with MeTTa() as context:
        context.run('!(let $name (atom_concat "failed-source-token" "") (bind! $name 0))')
        with pytest.raises(SourceNotFound):
            context.self.load(path)
        assert context.run("!(quote failed-source-token)") == [[0]]


@pytest.mark.parametrize("declarations", [
    "()",
    "((direction bidirectional))",
    "((left ((owned-rule $x) (seed $x))) (right (owned-result $x)))",
])
def test_a_failed_rule_registration_retires_only_its_source_artifacts(tmp_path, declarations):
    """A failed registration preserves the caller equation and removes its derivatives."""
    path = tmp_path / "failed-rule.metta"
    path.write_text(
        f"!(add-translator-rule! owned-rule {declarations})\n"
        f'!(import! &self "{tmp_path / "missing.metta"}")\n'
    )
    with MeTTa() as context:
        context.run("(= (owned-rule $x) (noeval (owned-result $x)))")
        before = context.self.source()
        with pytest.raises(SourceNotFound):
            context.self.load(path)
        assert not context.runtime.once(
            "translator_rules:translator_rule('owned-rule', _, _)"
        )
        assert not context.runtime.once(
            "translator_rules:translator_rule_derived('owned-rule', _, _)"
        )
        assert not context.runtime.once(
            "translator_rules:translator_rule('owned-result', _, _)"
        )
        assert context.self.source() == before


def test_source_withdrawal_keeps_a_later_registration_in_the_same_module(tmp_path):
    """An old source receipt cannot retire a subsequent registration of its name."""
    path = tmp_path / "replaced-rule.metta"
    path.write_text("!(add-translator-rule! later-rule)\n")
    with MeTTa() as context:
        context.run("(= (later-rule $x) (noeval (later-result $x)))")
        context.self.load(path)
        context.run("!(remove-translator-rule! later-rule)")
        context.run("!(add-translator-rule! later-rule ((cost 3)))")
        context.runtime.must(
            "filereader:withdraw_source_load(File, Space, _)",
            File=str(path), Space=context.self.name,
        )
        assert context.runtime.once(
            "translator_rules:translator_rule_declared_cost('later-rule', 3)"
        )


def test_a_program_releases_referenced_class_spaces_with_its_context(tmp_path):
    """Source-owned class homes retire even when their equation parent is global."""
    path = tmp_path / "released-program.metta"
    with MeTTa() as donor:
        @donor.self.define
        class ReleasedProgramCounter:
            value: int

        save_program(donor.runtime, donor.self.name, path)
    with MeTTa() as monitor:
        with MeTTa() as restored:
            restored.self.load(path)
            home, = restored.run("!(match &self (from $home) $home)")[0]
            assert monitor.runtime.once(
                "spaces:metta_space_identity_live(Space)", Space=str(home)
            )
        assert not monitor.runtime.once(
            "spaces:metta_space_identity_live(Space)", Space=str(home)
        )


@pytest.mark.parametrize("kept", [None, "child", "owner"])
def test_a_kept_program_space_retains_its_source_owner(tmp_path, kept):
    """The source owner and its allocated spaces remain live together."""
    path = tmp_path / "scoped-program.metta"
    path.write_text(
        '!(let $global (atom_concat "&self" "") '
        '(let $child (new-space $fresh (scoped $global)) '
        '(progn (add-atom $child (answer 17)) (add-atom &self (child $child)))))\n'
    )
    with MeTTa() as context:
        with context.self.scope() as scope:
            importing = context.space()
            importing.load(path)
            home, = importing.run("!(match &self (child $child) $child)")[0]
            if kept is not None:
                scope.keep(home if kept == "child" else importing)
        assert bool(context.runtime.once(
            "spaces:native_storage_module_cache(Space, _)", Space=str(home)
        )) is (kept is not None)
        if kept is not None:
            assert context.run("!(match {home} (answer $x) $x)", home=home) == [[17]]
            assert not importing.dropped
            importing.drop()


@pytest.mark.parametrize("operation", ["clear", "drop"])
def test_source_release_refuses_an_external_heir_before_removing_the_program(tmp_path, operation):
    """A source-owned base remains usable when an external child blocks release."""
    path = tmp_path / "base-program.metta"
    path.write_text(
        '!(let $global (atom_concat "&self" "") '
        '(let $child (new-space $fresh (scoped $global)) '
        '(progn (add-atom $child (answer 17)) (add-atom &self (child $child)))))\n'
    )
    with MeTTa() as context:
        importing = context.space()
        importing.load(path)
        home, = importing.run("!(match &self (child $child) $child)")[0]
        outside, = context.run("!(new-space $fresh (inherits {home}))", home=home)[0]
        before = importing.source()
        try:
            with pytest.raises(EngineError, match="live child"):
                getattr(importing, operation)()
            assert importing.source() == before
            assert context.run("!(match {home} (answer $x) $x)", home=home) == [[17]]
        finally:
            context.runtime.must("metta_release_space(Space)", Space=str(outside))
        importing.drop()


def test_source_release_orders_owned_heirs_across_files(tmp_path):
    """Separate source files can own a base and its heir in one program."""
    base, heir = tmp_path / "base.metta", tmp_path / "heir.metta"
    base.write_text('!(bind! &owned-release-base (new-space $fresh (inherits &self)))\n')
    heir.write_text(
        '!(bind! &owned-release-heir (new-space $fresh (inherits &owned-release-base)))\n'
    )
    with MeTTa() as context:
        importing = context.space()
        importing.load(base)
        importing.load(heir)
        spaces = context.runtime.must(
            "findall(_Space, (member(_Name, ['&owned-release-base', '&owned-release-heir']), "
            "metta_engine:metta_token(_Name, _Space)), Spaces)"
        )["Spaces"]
        assert len(spaces) == 2
        importing.drop()
        for space in spaces:
            assert not context.runtime.once(
                "spaces:native_storage_module_cache(Space, _)", Space=space
            )


def test_a_released_source_module_exposes_another_modules_token(tmp_path):
    """A module release removes only its source-owned claim on a shared token."""
    path = tmp_path / "other-module-token.metta"
    path.write_text('!(let $name (atom_concat "module-owned-token" "") (bind! $name 2))\n')
    with MeTTa() as original:
        original.run('!(bind! module-owned-token 1)')
        with MeTTa() as newer:
            newer.self.load(path)
            assert original.run("!(quote module-owned-token)") == [[2]]
        assert original.run("!(quote module-owned-token)") == [[1]]
