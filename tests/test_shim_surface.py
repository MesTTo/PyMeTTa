"""Purpose: the published host_service list is a ratchet toward the
transport floor. P4.23 published the engine predicates the Python shim
calls; the shrink item moves the host-agnostic orchestration engine-side
under host-neutral names so every next binding stops re-paying it, and
each move deletes rows here. This pin makes the direction enforceable:
a NEW host_service row fails until the manifest below names it with a
reason, and a deleted row fails until it leaves the manifest, so the
scoreboard never drifts from the tree.

Assumes:
  - seam:kind rows in engine/ext_points.pl are the one authority for a
    seam's kind [tested: every_seam_declares_one_kind in static_checks]
Guarantees:
  - the manifest and the tree hold the same host_service set, compared as
    sets with both differences named
    [tested: test_the_host_service_scoreboard_matches_the_tree;
    commit=c7468b2789746bcf95c4bacc0e2d517ec4d972fa]
  - every remaining row carries a named floor reason, so the list is the
    transport floor rather than a smaller pile of orchestration
    [tested: test_the_shim_surface_shrank_to_the_transport_floor;
    commit=4c9a794750103e0a3a2e9d883adde337ffb501f0]
  - the host query door uses the engine's published pattern-modifier walk
    [tested: test_a_path_reaches_into_a_handle_without_converting_it;
    commit=a1b10566194f10c174101fdc05f956b33171613b]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import re

#: Every published host_service, exactly as declared. Deleting a row here
#: must accompany deleting its declaration (the shrink working as
#: intended); adding one means the shim grew a NEW dependency on the
#: engine, which is the direction the floor forbids without a recorded
#: reason beside the name.
HOST_SERVICES = {
    "catch_recover/2",
    # The callable doors' deprecation reads. The row lookup is the feature's
    # own consult, and the shim's apply-seam emptiness probe rides the same
    # published relation so an empty catalog costs one crossing per process
    # rather than one goal-string read per name [measured 2026-08-26: 1,311
    # inferences per name's first call through the goal-string read, double
    # digits through the apply seam].
    "petta_deprecation/3",
    # The modifier walk gained a fourth argument rather than a second walk:
    # it now also answers whether the pattern carries a sequence variable,
    # which the query door must know before it builds a candidate head, and
    # asking separately would cost a walk per query [measured 2026-08-24].
    "lift_pattern_modifiers/4",
    # Its companion, and the ONLY new row: the plan a gap pattern is asked
    # under. It is one call per gap query and none at all for a gap-free one,
    # and the alternative is the host reimplementing the fragment classifier
    # LeaTTa states and this engine already owns.
    "petta_seq_query_plan/2",
    # The query carrier is engine policy: the host enters one dynamic scope,
    # reads its effective declaration, and initializes annotations from that
    # declaration's one rather than rebuilding those rules in the transport.
    "petta_with_under/2",
    "petta_effective_algebra/2",
    "petta_algebra_one/2",
    "match_foreign/5",
    "metta_host_load_file/3",
    "metta_host_read_forms/2",
    # Reader-token mutation is an engine-owned door. The host contributes the
    # retained constructor but does not reimplement the registry lifecycle.
    "metta_host_register_reader_token/2",
    "metta_host_run_source/4",
    "metta_host_run_source_status/3",
    # The host scopes SWI's thread-local byte ceiling through one engine door.
    "metta_host_with_stack_limit/2",
    # An inference budget over a goal an engine will RESUME. A host cannot
    # place this bound correctly from outside: the engine counts its own
    # inferences and the host thread cannot see them, so a meter around
    # engine_next/2 charges the pull loop and reads as working. Two seats
    # wrote it independently and both made that mistake, and the Node seat
    # still has to grow one, so the wrapper is built engine-side and handed
    # back rather than described.
    "metta_host_inference_budget/3",
    # Cache validation reads the function registry's engine-owned generation.
    "metta_host_function_generation/1",
    # The one row here that makes the floor SHRINK by being added. The engine
    # decides silent/1 from argv at load time, an embedded host has no argv,
    # and two seats had each written the same retract-then-assert privately
    # (petta_py_set_silent/1 here, petta_c_set_silent/1 in bindings/cetta),
    # with engine/filereader.pl's own export comment naming the first. One
    # engine-side door replaces both copies and the engine stops depending on
    # a binding's internals.
    "metta_host_set_silent/1",
    # list() asks for a length hint before it pulls. The engine's shared
    # effect classifier decides whether that second evaluation is safe; the
    # host must not reconstruct its private queue protocol.
    "metta_host_goal_repeatable/2",
    # World admission asks the engine to walk the compiled target and compose
    # its canonical effect rows; reproducing that walk in a host is unsound.
    "metta_host_goal_effect_plan/4",
    # The same walk asked of a retained source term: what the target would do
    # before it is translated, what replaying a frozen image compiles, and
    # which operations one saga step can execute.
    "metta_host_source_effect_plan/4",
    "metta_host_source_compile_effect_plan/4",
    "metta_host_source_runtime_effect_plan/4",
    "metta_host_save_fast/3",
    "metta_host_load_fast/2",
    "metta_host_open_function/3",
    "metta_host_adopt_function/4",
    "metta_host_drop_function/2",
    "metta_host_forget_function/1",
    "metta_host_stored/2",
    "metta_host_remove_reported/3",
    "metta_host_native_fact/4",
    "metta_host_explain_match/3",
    "metta_host_operation_error/5",
    "metta_host_clear_space/1",
    "metta_host_clear_defined/1",
    "metta_host_fast_header/1",
    "metta_host_digest/2",
    "metta_host_dispatch_proof_step/6",
    "metta_host_substitute/3",
    "metta_host_unregister_reader_token/1",
    "metta_add_atoms/2",
    "metta_assert_space_releasable/1",
    "metta_declare_restricted_space/2",
    "metta_declare_space_parent/2",
    "metta_reducible_head/2",
    # The direct-call door's ownership question: a declared or translator-
    # rule-owned head declines the raw fast path (P14.32). Engine-owned as
    # one door rather than the two raw reads the shim briefly carried
    # (type_declaration_in/3 + the rule registry), the same shape
    # metta_host_dispatch_proof_step/6 took, so the walk and the registry
    # stay free to move.
    "metta_typed_dispatch_applies/2",
    "metta_source_declarations/2",
    "metta_space_names/1",
    "petta_space_operand/1",
    "metta_string_declarations/2",
    "metta_substitute_self/3",
    "metta_trace_source/4",
    "metta_release_space/1",
    "petta_annotations/2",
    "petta_contract_fact/1",
    "petta_error_answer/3",
    "petta_handles_coherent/1",
    "petta_on_error_mode/3",
    "petta_name_pairs/2",
    "petta_source_reset/1",
    # Speculation and State fencing are engine-owned execution/store doors.
    # A host selects the boundary but does not reimplement snapshot rollback,
    # the non-backtrackable State guard, or live-cell identity.
    "petta_speculate/1",
    "petta_transaction/1",
    # Sagas need the durable transaction outcome before any post-commit
    # observer or foreign-provider failure is rethrown.
    "petta_transaction_notified/3",
    "petta_world_effect_coverage/2",
    "petta_effect_covered/2",
    "petta_compensation/2",
    "petta_transport_failure/1",
    "petta_with_state_write_fence/1",
    "petta_live_state_cell/1",
    # The platform census. Not shim orchestration moving host-side: it is a
    # fact about the running build that only the engine can answer, and a host
    # that cannot read it recovers the same knowledge by parsing SWI's boot
    # transcript, which is what bindings/node does today.
    "petta_platform/4",
    "sread_with_names/3",
    "swrite_with_names/3",
    # Eval crosses through a cached translation template while source forms
    # retain translate_expr/3, so compile-once loading pays no cache tax.
    "translate_cached_expr/3",
    "translate_expr/3",
    "unregister_metta_extension/1",
    "with_metta_module/2",
}

_ROW = re.compile(r"^kind\(([a-zA-Z_'/0-9-]+/\d+),\s*host_service\)\.",
                  re.MULTILINE)


def test_the_host_service_scoreboard_matches_the_tree(repo_root):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    declared = set(
        _ROW.findall((repo_root / "engine" / "ext_points.pl").read_text())
    )
    grew = sorted(declared - HOST_SERVICES)
    shrank_untracked = sorted(HOST_SERVICES - declared)
    assert not grew, (
        "the shim grew new engine dependencies; the floor shrinks, it does "
        "not grow. Either move the orchestration engine-side under a "
        f"host-neutral name or record the reason beside the pin: {grew}"
    )
    assert not shrank_untracked, (
        "host_service rows left the tree without leaving this scoreboard; "
        f"delete them here too so the count stays the meter: {shrank_untracked}"
    )


#: The floor taxonomy: every row that MAY remain is one of these, and a row
#: none of them fits is orchestration that belongs engine-side. "door" is a
#: space or evaluation entry the engine owns and any host drives; "codec"
#: is a text or wire need of the transport itself; "host-orchestration" is
#: the engine-side surface the shrink moves BUILT (the metta_host_* rows);
#: "error-vocabulary" is the failure contract a transport classifies by;
#: "host-choice" is a consult whose answer only the host can make; "census"
#: is a fact about the running build that the engine alone observes and a
#: host would otherwise recover by parsing the boot transcript.
FLOOR_REASONS = {
    "catch_recover/2": "host-choice",
    "petta_deprecation/3": "door",
    "lift_pattern_modifiers/4": "door",
    "petta_seq_query_plan/2": "door",
    "petta_with_under/2": "door",
    "petta_effective_algebra/2": "door",
    "petta_algebra_one/2": "door",
    "match_foreign/5": "door",
    "metta_add_atoms/2": "door",
    "metta_assert_space_releasable/1": "door",
    "metta_declare_restricted_space/2": "door",
    "metta_declare_space_parent/2": "door",
    "metta_host_adopt_function/4": "host-orchestration",
    "metta_host_clear_defined/1": "host-orchestration",
    "metta_host_clear_space/1": "host-orchestration",
    "metta_host_digest/2": "host-orchestration",
    "metta_host_dispatch_proof_step/6": "host-orchestration",
    "metta_host_drop_function/2": "host-orchestration",
    "metta_host_explain_match/3": "host-orchestration",
    "metta_host_fast_header/1": "host-orchestration",
    "metta_host_forget_function/1": "host-orchestration",
    "metta_host_load_fast/2": "host-orchestration",
    "metta_host_load_file/3": "host-orchestration",
    "metta_host_native_fact/4": "host-orchestration",
    "metta_host_open_function/3": "host-orchestration",
    "metta_host_operation_error/5": "error-vocabulary",
    "metta_host_read_forms/2": "host-orchestration",
    "metta_host_register_reader_token/2": "door",
    "metta_host_remove_reported/3": "host-orchestration",
    "metta_host_run_source/4": "host-orchestration",
    "metta_host_run_source_status/3": "host-orchestration",
    "metta_host_with_stack_limit/2": "door",
    "metta_host_inference_budget/3": "host-orchestration",
    "metta_host_function_generation/1": "host-orchestration",
    "metta_host_set_silent/1": "door",
    "metta_host_goal_repeatable/2": "host-orchestration",
    "metta_host_goal_effect_plan/4": "host-orchestration",
    "metta_host_source_effect_plan/4": "host-orchestration",
    "metta_host_source_compile_effect_plan/4": "host-orchestration",
    "metta_host_source_runtime_effect_plan/4": "host-orchestration",
    "metta_host_save_fast/3": "host-orchestration",
    "metta_host_stored/2": "host-orchestration",
    "metta_host_substitute/3": "host-orchestration",
    "metta_host_unregister_reader_token/1": "door",
    "metta_reducible_head/2": "door",
    "metta_release_space/1": "door",
    "metta_typed_dispatch_applies/2": "door",
    "metta_source_declarations/2": "codec",
    "metta_space_names/1": "door",
    # The species decision behind the wire's p tag: an encoder asks what
    # metatype_of/2 asks, so get-metatype and the wire agree on every atom.
    "petta_space_operand/1": "codec",
    "metta_string_declarations/2": "codec",
    "metta_substitute_self/3": "door",
    "metta_trace_source/4": "door",
    "petta_annotations/2": "door",
    "petta_contract_fact/1": "door",
    "petta_error_answer/3": "error-vocabulary",
    "petta_handles_coherent/1": "door",
    "petta_on_error_mode/3": "host-choice",
    "petta_name_pairs/2": "codec",
    "petta_source_reset/1": "door",
    "petta_speculate/1": "door",
    "petta_transaction/1": "door",
    "petta_transaction_notified/3": "door",
    "petta_world_effect_coverage/2": "door",
    "petta_effect_covered/2": "door",
    "petta_compensation/2": "door",
    "petta_transport_failure/1": "error-vocabulary",
    "petta_with_state_write_fence/1": "door",
    "petta_live_state_cell/1": "door",
    "petta_platform/4": "census",
    "sread_with_names/3": "codec",
    "swrite_with_names/3": "codec",
    "translate_cached_expr/3": "codec",
    "translate_expr/3": "codec",
    "unregister_metta_extension/1": "door",
    "with_metta_module/2": "door",
}


def test_the_shim_surface_shrank_to_the_transport_floor():
    """Every published row carries a FLOOR reason, so the shrink is done.

    The scoreboard above pins the set; this pins its QUALITY: a row that
    is not a door the engine owns, a codec need of the transport, the
    engine-side host surface the shrink built, the failure contract, or a
    genuinely host-made choice, is orchestration a next binding would
    re-pay, and it fails here until it moves engine-side. The design moves
    keep run/load, registration lifecycle, remove-with-report, explanation,
    exception shaping, and bulk clearing at this classified floor.
    """
    unclassified = sorted(HOST_SERVICES - set(FLOOR_REASONS))
    over_classified = sorted(set(FLOOR_REASONS) - HOST_SERVICES)
    assert not unclassified, (
        "published host_service rows with no floor reason; move the "
        f"orchestration engine-side or classify them here: {unclassified}"
    )
    assert not over_classified, (
        "floor reasons for rows that no longer exist; delete them: "
        f"{over_classified}"
    )
    allowed = {"door", "codec", "host-orchestration", "error-vocabulary",
               "host-choice", "census"}
    stray = {name: why for name, why in FLOOR_REASONS.items()
             if why not in allowed}
    assert not stray, f"a reason outside the floor taxonomy: {stray}"
