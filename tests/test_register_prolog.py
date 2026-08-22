"""Purpose: MeTTa.register_prolog, the native-speed extension point for
libraries built on PyPeTTa.

register_op is the extension point people find first and it crosses the janus
boundary on every call. A library whose hot path is arithmetic or matching
should ship Prolog instead, and before this existed there was no way to do
that from Python at all.
Guarantees:
  - a predicate registered from inline source is callable from MeTTa
    [tested test_inline_source_becomes_a_metta_function]
  - a predicate registered from a file is callable from MeTTa
    [tested test_a_file_of_prolog_becomes_metta_functions]
  - a name with no predicate behind it is REFUSED, because registering it
    records no arity and then compiles every call into a partial application
    instead of failing [tested test_a_name_with_no_predicate_is_refused]
  - a Prolog-registered operation costs materially less per call than the
    same operation registered as Python [tested
    test_prolog_registration_is_cheaper_than_python_registration]
  - a builtin's name and a special form's name are both refused, before the
    source that would have replaced them loads [tested
    test_a_builtin_name_is_refused_and_the_builtin_still_works,
    test_a_special_form_name_is_refused]
  - two generated sources do not erase each other's clauses [tested
    test_generated_sources_do_not_erase_each_other]
  - a typo anywhere in the name list registers nothing [tested
    test_a_typo_in_the_list_registers_nothing]
  - a syntax error in the source raises a PettaError naming the line, where
    SWI would only have printed it [tested test_a_syntax_error_names_the_line]
  - one name has one owning tier, refused in both directions and leaving the
    incumbent usable [tested test_a_python_operation_is_not_silently_replaced,
    test_a_prolog_registration_is_not_silently_replaced]
  - an extension may add its own builtin type row without replacing the
    engine's table, and unload removes only that row [tested:
    test_a_library_types_its_own_blob_without_destroying_the_table;
    commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import contextlib
import subprocess
import sys
from pathlib import Path

import pytest

from petta import PettaError
from petta.errors import EngineError, SourceNotFound


@pytest.fixture()
def space(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    return metta._new_space()


def test_inline_source_becomes_a_metta_function(space):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    names = space.register_prolog(
        "'rp-square'(X, Y) :- Y is X * X.", names=["rp-square"]
    )
    assert names == ("rp-square",)
    assert space._one("(rp-square 7)") == 49


def test_a_file_of_prolog_becomes_metta_functions(space, tmp_path):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    source = tmp_path / "rp_lib.pl"
    source.write_text("'rp-triple'(X, Y) :- Y is X * 3.\n'rp-negate'(X, Y) :- Y is -X.\n")
    names = space.register_prolog(path=source, names=["rp-triple", "rp-negate"])
    assert names == ("rp-triple", "rp-negate")
    assert space._one("(rp-triple 14)") == 42
    assert space._one("(rp-negate 5)") == -5


# The failure this guards is the one engine/metta.pl documents: registering a name
# whose predicate is absent records no arity, and then every call to it
# compiles to a partial application rather than erroring, which is a silent
# wrong answer.
def test_a_name_with_no_predicate_is_refused(space):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with pytest.raises(EngineError, match="no predicate named"):
        space.register_prolog("'rp-present'(X, X).", names=["rp-absent"])


def test_names_must_be_given(space):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    # All three routes named, because pointing only at metta_export is a dead
    # end for a provider author, who has no functions to export.
    with pytest.raises(ValueError, match="metta_export") as caught:
        space.register_prolog("'rp-unnamed'(X, X).")
    assert "metta_extension" in str(caught.value)
    assert "the names to register" in str(caught.value)


def test_source_and_path_are_exclusive(space, tmp_path):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    source = tmp_path / "rp_either.pl"
    source.write_text("'rp-either'(X, X).\n")
    with pytest.raises(ValueError, match="exactly one"):
        space.register_prolog("'rp-either'(X, X).", path=source, names=["rp-either"])
    with pytest.raises(ValueError, match="exactly one"):
        space.register_prolog(names=["rp-either"])


# Both readings catch it: a caller reaching for a file writes
# `except FileNotFoundError` and a caller wrapping a whole registration writes
# `except PettaError`, and a plain FileNotFoundError silently escaped the
# second one.
def test_a_missing_file_is_named(space):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with pytest.raises(SourceNotFound, match="no Prolog source"):
        space.register_prolog(path="/nonexistent/petta/none.pl", names=["rp-x"])
    with pytest.raises(FileNotFoundError):
        space.register_prolog(path="/nonexistent/petta/none.pl", names=["rp-x"])
    with pytest.raises(PettaError):
        space.register_prolog(path="/nonexistent/petta/none.pl", names=["rp-x"])


def test_a_non_string_name_is_refused(space):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with pytest.raises(TypeError, match="name as a string"):
        space.register_prolog("'rp-ok'(X, X).", names=[42])


# A consulted predicate replaces the engine's static one for the whole
# process. Registering a predicate named + made (+ 1 2) answer whatever the
# library said, with SWI's redefinition warning on stderr the only sign and
# this call reporting success.
def test_a_builtin_name_is_refused_and_the_builtin_still_works(space):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with pytest.raises(EngineError, match="is a builtin"):
        space.register_prolog("'+'(_, _, R) :- R = shadowed.", names=["+"])
    assert space._one("(+ 1 2)") == 3
    with pytest.raises(EngineError, match="is a builtin"):
        space.register_prolog("'car-atom'(_, R) :- R = shadowed.", names=["car-atom"])
    assert space._one("(car-atom (1 2))") == 1


# Special forms are compiled by the translator before function dispatch, so a
# registration under one of their names is dead code the moment it lands.
def test_a_special_form_name_is_refused(space):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with pytest.raises(EngineError, match="is a special form"):
        space.register_prolog("'if'(_, _, _, R) :- R = shadowed.", names=["if"])
    assert space._one("(if True 1 2)") == 1


# The source is identified by a hash of its own content. It used to be
# id(source), an address CPython hands to the next string of the same size, so
# a library generating Prolog lost every predicate but the last: the reuse
# struck on the SECOND registration.
def test_generated_sources_do_not_erase_each_other(space):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    for i in range(4):
        generated = f"'rp-gen{i}'(X, Y) :- Y is X + {i}.\n"
        space.register_prolog(generated, names=[f"rp-gen{i}"])
        del generated
    assert [space._one(f"(rp-gen{i} 10)") for i in range(4)] == [10, 11, 12, 13]


def test_the_same_source_registered_twice_is_idempotent(space):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    source = "'rp-twice'(X, Y) :- Y is X + 1.\n"
    space.register_prolog(source, names=["rp-twice"])
    space.register_prolog(source, names=["rp-twice"])
    assert space.run("!(rp-twice 1)") == [[2]]


# Validating inside the registration loop left the first two names registered
# and callable when the third was a typo, and the list of what had taken died
# inside the exception.
def test_a_typo_in_the_list_registers_nothing(space):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with pytest.raises(EngineError, match="no predicate named"):
        space.register_prolog(
            "'rp-t1'(X, X).\n'rp-t2'(X, X).\n",
            names=["rp-t1", "rp-t2", "rp-typo"],
        )
    assert not space.is_function("rp-t1")
    assert not space.is_function("rp-t2")


# The registry used to keep claiming a name whose predicate register_prolog
# had replaced, so the operation could neither be unregistered (retractall on
# what was now a static procedure raised) nor re-registered.
def test_a_python_operation_is_not_silently_replaced(space):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    @space.op(name="rp-owned")
    def rp_owned(x):
        return ["python", x]

    with pytest.raises(EngineError, match="another extension tier"):
        space.register_prolog("'rp-owned'(X, R) :- R = [prolog, X].",
                              names=["rp-owned"])
    assert str(space._one("(rp-owned 1)")) == '("python" 1)'
    # And the registry is still usable, which is the half that used to wedge.
    space.unregister_op("rp-owned")
    assert not space.is_function("rp-owned")


def test_a_prolog_registration_is_not_silently_replaced(space):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    space.register_prolog("'rp-mine'(X, R) :- R = [prolog, X].", names=["rp-mine"])
    with pytest.raises(EngineError, match="another extension tier"):

        @space.op(name="rp-mine")
        def rp_mine(x):
            return ["python", x]

    assert str(space._one("(rp-mine 1)")) == "(prolog 1)"


# I29: the refusal was on the far side of the load, so it told the WRONG
# author. B heard "already registered from A", and A, which did nothing,
# answered B's implementation from then on:
#
#     A before B      : 20
#     B refused       : already registered from ...
#     A AFTER refusal : 30      <- A was clobbered anyway
#
# SWI prints "Redefined static procedure" and continues, so the incumbent's
# clauses are gone before any post-load check can speak. The names are in hand
# before the load on this route, so the refusal belongs there.
def test_a_rival_source_is_refused_before_it_can_clobber(space, tmp_path):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    first = tmp_path / "rp_norm_a.pl"
    first.write_text("'rp-rival-norm'(_, 20).\n")
    second = tmp_path / "rp_norm_b.pl"
    second.write_text("'rp-rival-norm'(_, 30).\n")

    space.register_prolog(path=first, names=["rp-rival-norm"])
    assert space._one("(rp-rival-norm 1)") == 20

    with pytest.raises(EngineError, match="already registered from"):
        space.register_prolog(path=second, names=["rp-rival-norm"])

    # The incumbent is intact, which is the whole point: B never loaded.
    assert space._one("(rp-rival-norm 1)") == 20


def test_a_rival_declaring_source_is_refused_before_it_can_clobber(space, tmp_path):
    """The same, for a library that declares its own exports.

    Here the names are not known until the file has run, so the engine reads
    the declaration out of the source WITHOUT running the source, the way
    PostgreSQL reads an extension's control file before its install script.
    """
    declaration = ':- metta_export("(: rp-declared-norm (-> Number Number))").\n'
    first = tmp_path / "rp_dnorm_a.pl"
    first.write_text(declaration + "'rp-declared-norm'(_, 20).\n")
    second = tmp_path / "rp_dnorm_b.pl"
    second.write_text(declaration + "'rp-declared-norm'(_, 30).\n")

    assert space.register_prolog(path=first) == ("rp-declared-norm",)
    assert space._one("(rp-declared-norm 1)") == 20

    with pytest.raises(EngineError, match="already registered from"):
        space.register_prolog(path=second)

    assert space._one("(rp-declared-norm 1)") == 20


# SWI prints a syntax error inside a consulted file and the load then succeeds
# with the predicate undefined, so this used to arrive as "no predicate named
# 'rp-syntax' was defined", naming the symptom rather than the cause, with the
# line and column only on stderr.
def test_a_syntax_error_names_the_line(space):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with pytest.raises(PettaError, match="Syntax error"):
        space.register_prolog("'rp-syntax'(X, Y) :- Y is X * .", names=["rp-syntax"])


# The whole point: gate on inferences, which are deterministic, rather than on
# wall clock, which is bimodal under load on this box.
def test_prolog_registration_is_cheaper_than_python_registration(space):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    space.register_prolog("'rp-fast'(X, Y) :- Y is X + 1.", names=["rp-fast"])

    @space.op(name="rp-slow")
    def rp_slow(x):
        return x + 1

    space.run("""
    (= (rp-drive $which $n)
       (if (> $n 0)
           (let $_ (case $which ((fast (rp-fast 1)) (slow (rp-slow 1))))
             (rp-drive $which (- $n 1)))
           done))
    """)
    calls = 500
    costs = {}
    for which in ("fast", "slow"):
        space._one(f"(rp-drive {which} 10)")
        with space.stats() as counted:
            space._one(f"(rp-drive {which} {calls})")
        costs[which] = counted.inferences / calls

    assert space._one("(rp-fast 41)") == space._one("(rp-slow 41)") == 42
    # Measured about 3.2x on 2026-08-15; assert the direction and a wide
    # margin rather than the exact ratio, which is engine-version specific.
    assert costs["slow"] > costs["fast"] * 1.5, costs


# X1 and X12: a library declares what it exports in the file that implements
# it, and the engine remembers that those names go together.
#
# Registering one predicate used to take three statements in two languages,
# with the arity DISCOVERED from whatever current_predicate/1 held rather than
# declared. A library shipping a public 'vec-dot'/3 and an internal helper
# 'vec-dot'/2 published both.
EXPORT_LIBRARY = """
:- metta_extension(rp_demo, [version('0.1.0')]).
:- metta_export("
    (: rp-demo-scale (-> Number Number))
    (: rp-demo-shape (-> Atom Atom))
    (export rp-demo-plain 1)
").

'rp-demo-scale'(X, Y) :- Y is X * 10.
'rp-demo-shape'(X, [shape, X]).
'rp-demo-plain'(X, X).
'rp-demo-helper'(_, _, hidden).
"""


@pytest.fixture()
def declared(space, tmp_path):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    source = tmp_path / "rp_demo.pl"
    source.write_text(EXPORT_LIBRARY)
    yield source
    with contextlib.suppress(PettaError):
        space.unregister_prolog("rp_demo")


def test_inline_source_declares_its_own_exports_too(space):
    """A declaration records itself under the name the LOAD runs under.

    For a file that is the path; for inline source it is the generated
    module name, and the Python side asked under a fixed "petta_inline"
    instead, which matched nothing. So a source declaring its own exports
    inline was told it had declared none, while the same text in a file
    worked.
    """
    inline = """
:- metta_extension(rp_inline, [version('0.1.0')]).
:- metta_export("
    (: rp-inline-scale (-> Number Number))
").
'rp-inline-scale'(X, Y) :- Y is X * 7.
"""
    try:
        assert space.register_prolog(inline) == ("rp-inline-scale",)
        assert space._one("(rp-inline-scale 3)") == 21
    finally:
        with contextlib.suppress(PettaError):
            space.unregister_prolog("rp_inline")


def test_a_file_declares_its_own_exports(space, declared):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    names = space.register_prolog(path=declared)
    assert set(names) == {"rp-demo-scale", "rp-demo-shape", "rp-demo-plain"}
    assert space._one("(rp-demo-scale 3)") == 30

    # The type travelled with the name, so there is no gap between registering
    # it and declaring it: the Atom parameter arrives as written from the
    # first call site ever compiled.
    assert str(space._one("(rp-demo-shape (+ 1 2))")) == "(shape (+ 1 2))"

    # And the helper that happens to share the library's prefix is not
    # published, because it was not declared.
    assert not space.is_function("rp-demo-helper")


def test_an_extension_unloads_whole(space, declared):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    space.register_prolog(path=declared)
    released = space.unregister_prolog("rp_demo")
    assert set(released) == {"rp-demo-scale", "rp-demo-shape", "rp-demo-plain"}
    assert not space.is_function("rp-demo-scale")
    assert str(space._one("(rp-demo-scale 3)")) == "(rp-demo-scale 3)"
    with pytest.raises(PettaError, match="does not exist"):
        space.unregister_prolog("rp_demo")


def test_a_library_types_its_own_blob_without_destroying_the_table(
    repo_root, tmp_path
):
    """A clause from another file extends the shared type register safely."""
    extension = tmp_path / "p5_blob_types.pl"
    extension.write_text(
        ":- metta_extension(p5_blob_types, [version('0.1.0')]).\n"
        "seam:builtin_type_declaration('p5-blob', 'P5Blob').\n"
    )
    script = """
import sys
from pathlib import Path

repo = Path(sys.argv[1])
sys.path.insert(0, str(repo / "bindings" / "python"))
from petta import MeTTa

m = MeTTa(petta_path=str(repo)).self
def types(form):
    return {str(atom) for row in m.run(form) for atom in row}

plus = {"(-> Number Number Number)"}
assert types("!(get-type +)") == plus
assert m.register_prolog(path=sys.argv[2]) == ()
assert types("!(get-type p5-blob)") == {"P5Blob"}
assert types("!(get-type +)") == plus
m.unregister_prolog("p5_blob_types")
assert types("!(get-type p5-blob)") == {"%Undefined%"}
assert types("!(get-type +)") == plus
print("P5_MULTIFILE_OK")
"""
    result = subprocess.run(
        [sys.executable, "-c", script, str(repo_root), str(extension)],
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert result.returncode == 0, result.stderr[-2000:]
    assert result.stdout.strip().endswith("P5_MULTIFILE_OK")


def test_a_declaration_without_an_extension_still_reports_its_names(space, tmp_path):
    """The single-file library shape: one declaration, no extension.

    An extension is optional on the Prolog side, and this is the shape that
    leaves it out. The Python side used to read back what a registration
    produced by walking extension MEMBERSHIP, so every name here registered,
    the function was callable, and the call still raised "register_prolog
    needs the names to register". Reading the per-file record answers the
    question the caller actually asked.
    """
    source = tmp_path / "rp_bare.pl"
    source.write_text(
        ':- metta_export("(: rp-bare-scale (-> Number Number))").\n'
        "'rp-bare-scale'(X, Y) :- Y is X * 10.\n"
    )
    assert space.register_prolog(path=source) == ("rp-bare-scale",)
    assert space.is_function("rp-bare-scale")
    assert space._one("(rp-bare-scale 4)") == 40

    # And registering the same file again reports the same names rather than
    # accumulating them.
    assert space.register_prolog(path=source) == ("rp-bare-scale",)


def test_an_unloaded_extension_does_not_leave_its_names_behind(space, declared):
    """Re-registering a file after unloading it reports what it has NOW.

    The per-file record is what register_prolog reads, so it has to go when
    the extension does, or the second registration answers names that were
    released between the two.
    """
    space.register_prolog(path=declared)
    space.unregister_prolog("rp_demo")
    names = space.register_prolog(path=declared)
    assert set(names) == {"rp-demo-scale", "rp-demo-shape", "rp-demo-plain"}
    assert space._one("(rp-demo-scale 3)") == 30


def test_a_source_with_neither_names_nor_a_declaration_is_refused(space):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with pytest.raises(ValueError, match="metta_export"):
        space.register_prolog("'rp-undeclared'(X, X).")


def test_a_provider_only_file_registers_no_functions_and_is_accepted(space, tmp_path):
    """A space provider exports nothing, and that is not an error.

    `metta_export` is for functions; a provider contributes clauses to a seam
    and has none. The message pointed only at `metta_export`, which for a
    provider author is a dead end, and the file was refused for lacking the
    one declaration it had no use for.
    """
    source = tmp_path / "rp_provider.pl"
    source.write_text(
        ":- metta_extension(rp_provider_demo, []).\n"
        ":- multifile seam:foreign_space/1.\n"
        ":- multifile seam:foreign_atoms/2.\n"
        "seam:foreign_space('&rp-provider-demo').\n"
        "seam:foreign_atoms('&rp-provider-demo', [fact, a]).\n"
    )
    try:
        assert space.register_prolog(path=source) == ()
        assert str(space._one("(collapse (get-atoms &rp-provider-demo))")) == "((fact a))"
    finally:
        with contextlib.suppress(PettaError):
            space.unregister_prolog("rp_provider_demo")


def test_a_file_that_declares_nothing_does_not_load_either(space, tmp_path):
    """It raised and installed the provider anyway.

    register_prolog consulted first and checked after, so an author who
    followed the provider chapter, shipped the file and got a ValueError would
    find that CATCHING it made everything work. That is the one outcome that
    teaches someone to ignore an error, and it breaks the hard-error rule from
    both directions at once: it raised where it should not and succeeded where
    it raised.
    """
    source = tmp_path / "rp_silent.pl"
    source.write_text(
        ":- multifile seam:foreign_space/1.\n"
        ":- multifile seam:foreign_atoms/2.\n"
        "seam:foreign_space('&rp-silent-demo').\n"
        "seam:foreign_atoms('&rp-silent-demo', [fact, a]).\n"
    )
    with pytest.raises(ValueError, match="metta_extension"):
        space.register_prolog(path=source)
    # Nothing of it loaded, so catching the error cannot make it work.
    assert str(space._one("(collapse (get-atoms &rp-silent-demo))")) == "()"


# X3: the one collision a name refusal cannot fix is two libraries that both
# export norm/2. Neither is wrong and neither can be asked to change, so SWI's
# renaming import list is what resolves it, as it has for thirty years.
_MODULE_A = ":- module(rp_liba, ['norm'/2]).\n'norm'(X, Y) :- Y is abs(X).\n"
_MODULE_B = ":- module(rp_libb, ['norm'/2]).\n'norm'(X, Y) :- Y is X * X.\n"


@pytest.fixture(scope="module")
def rival_modules(tmp_path_factory):
    """Two modules exporting the same name, written once for the module.

    Per-test copies at different paths would be different LIBRARIES claiming
    one MeTTa name, which the engine refuses by design.
    """
    directory = tmp_path_factory.mktemp("rival")
    (directory / "rp_liba.pl").write_text(_MODULE_A)
    (directory / "rp_libb.pl").write_text(_MODULE_B)
    return directory


def test_two_libraries_exporting_one_name_can_both_be_registered(space, rival_modules):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    assert space.register_prolog(
        path=rival_modules / "rp_liba.pl", names={"norm": "rp-liba-norm"}
    ) == ("rp-liba-norm",)
    assert space.register_prolog(
        path=rival_modules / "rp_libb.pl", names={"norm": "rp-libb-norm"}
    ) == ("rp-libb-norm",)
    # Neither is bound to the other's code, which is what SWI's own refusal
    # would have left: it declines the second import, prints, and continues.
    assert space._one("(rp-liba-norm -5)") == 5
    assert space._one("(rp-libb-norm -5)") == 25


def test_a_rename_of_something_not_exported_is_refused(space, rival_modules):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with pytest.raises(EngineError, match="does not export"):
        space.register_prolog(
            path=rival_modules / "rp_libb.pl", names={"absent": "rp-absent"}
        )


def test_renaming_needs_a_module_file(space):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with pytest.raises(ValueError, match="needs path="):
        space.register_prolog(source="'x'(1).", names={"x": "rp-x"})


def test_renaming_a_plain_file_says_it_is_not_a_module(space, tmp_path):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    plain = tmp_path / "rp_plain.pl"
    plain.write_text("'plainly'(1, 1).\n")
    with pytest.raises(EngineError, match="not a Prolog module"):
        space.register_prolog(path=plain, names={"plainly": "rp-plainly"})


# X5's determinism half. A leaked choice point is invisible to the inference
# counter and costs its callers about twice, so a library declares det and the
# failure moves to its own door.
_DET_LIBRARY = """
:- metta_extension(rp_det, [version('0.1.0')]).
:- metta_export("
    (: rp-det-clean (-> Number Number))
    (determinism rp-det-clean det)
    (: rp-det-leaky (-> Number Number))
    (determinism rp-det-leaky det)
    (: rp-det-many (-> Number Number))
    (determinism rp-det-many nondet)
").
'rp-det-clean'(X, Y) :- Y is X + 1.
'rp-det-leaky'(X, Y) :- member(Y, [X, X]).
'rp-det-many'(X, Y) :- member(Y, [X, X]).
"""


@pytest.fixture(scope="module")
def det_library(tmp_path_factory):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    source = tmp_path_factory.mktemp("rp_det") / "rp_det.pl"
    source.write_text(_DET_LIBRARY)
    return source


def test_a_declared_det_function_answers_normally(space, det_library):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    space.register_prolog(path=det_library)
    assert space._one("(rp-det-clean 1)") == 2


def test_a_declared_det_function_that_leaks_a_choice_point_raises(space, det_library):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    space.register_prolog(path=det_library)
    # SWI's own det/1 does this, at the library's door rather than the
    # caller's, and the counter cannot see the leak at all.
    with pytest.raises(EngineError, match="deterministic procedure"):
        space.eval("(rp-det-leaky 1)")


def test_a_declared_nondet_function_keeps_every_answer(space, det_library):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    space.register_prolog(path=det_library)
    assert space.eval("(rp-det-many 1)") == [1, 1]


def test_the_declaration_is_reported_beside_the_redos(space, det_library):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    space.register_prolog(path=det_library)
    _, costs = space.profile_extension("!(rp-det-clean 1)", extension="rp_det")
    declared = {cost.name: cost.determinism for cost in costs}
    assert declared["rp-det-clean"] == "det"
    assert declared["rp-det-many"] == "nondet"
    assert "declared det" in repr(next(c for c in costs if c.name == "rp-det-clean"))


def test_an_unknown_determinism_is_refused(space, tmp_path):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    source = tmp_path / "rp_det_bad.pl"
    source.write_text(
        ':- metta_export("(: rp-bad (-> Number Number))\\n'
        '(determinism rp-bad mostly)").\n'
        "'rp-bad'(X, X).\n"
    )
    with pytest.raises(EngineError, match="determinism"):
        space.register_prolog(path=source)


# D5.1: the C tier is the cheapest row on EXTENDING.md's table and reaching it
# meant hand-writing two Prolog directives with an absolute path computed from
# __file__. The path trap is the reason this exists rather than the typing.
_C_EXTENSION = Path(__file__).resolve().parents[3] / "examples" / "integration" / "c_extension"


@pytest.mark.skipif(
    not (_C_EXTENSION / "cbump.so").is_file(),
    reason="cbump.so is not built; a C toolchain is not an engine requirement",
)
def test_a_compiled_library_registers_from_python(space):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    assert space.register_foreign_library(
        _C_EXTENSION / "cbump.so", entry="install_cbump", names=["c-bump"]
    ) == ("c-bump",)
    assert space._one("(c-bump 41)") == 42


@pytest.mark.skipif(
    not (_C_EXTENSION / "handle.so").is_file(),
    reason="handle.so is not built; a C toolchain is not an engine requirement",
)
def test_an_opaque_handle_crosses_as_an_ordinary_value(space):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    space.register_foreign_library(
        _C_EXTENSION / "handle.so",
        entry="install_handle",
        names=["vector-new", "vector-length", "vector-nth"],
    )
    # The vector's contents never become text; only the handle crosses.
    assert space._one("(vector-length (vector-new 1000))") == 1000
    assert space._one("(vector-nth (vector-new 1000) 700)") == 700


def test_an_absent_compiled_library_is_refused_here(space):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with pytest.raises(SourceNotFound, match="no compiled library"):
        space.register_foreign_library("definitely-not-here.so", names=["nope"])
