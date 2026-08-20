"""Purpose: the published host_service list is a ratchet toward the
transport floor. P4.23 published the 49 engine predicates the Python shim
calls; the shrink item moves the host-agnostic orchestration engine-side
under host-neutral names so every next binding stops re-paying it, and
each move deletes rows here. This pin makes the direction enforceable:
a NEW host_service row fails until the manifest below names it with a
reason, and a deleted row fails until it leaves the manifest, so the
scoreboard never drifts from the tree.

Assumes:
  - ext_point_kind rows in engine/ext_points.pl are the one authority for a
    seam's kind [tested: every_seam_declares_one_kind in static_checks]
Guarantees:
  - the manifest and the tree hold the same host_service set, compared as
    sets with both differences named
    [tested: test_the_host_service_scoreboard_matches_the_tree;
    commit=WORKTREE]
  - every remaining row carries a named floor reason, so the list is the
    transport floor rather than a smaller pile of orchestration
    [tested: test_the_shim_surface_shrank_to_the_transport_floor]
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
    "match_foreign/5",
    "metta_host_load_file/3",
    "metta_host_read_forms/2",
    # Reader-token mutation is an engine-owned door. The host contributes the
    # retained constructor but does not reimplement the registry lifecycle.
    "metta_host_register_reader_token/2",
    "metta_host_run_source/4",
    "metta_host_run_source_status/3",
    "metta_host_save_fast/3",
    "metta_host_load_fast/2",
    "metta_host_open_function/3",
    "metta_host_adopt_function/4",
    "metta_host_drop_function/2",
    "metta_host_forget_function/1",
    "metta_host_stored/2",
    "metta_host_remove_reported/3",
    "metta_host_explain_match/3",
    "metta_host_operation_error/5",
    "metta_host_clear_space/1",
    "metta_host_clear_defined/1",
    "metta_host_fast_header/1",
    "metta_host_digest/2",
    "metta_host_substitute/3",
    "metta_host_unregister_reader_token/1",
    "metta_add_atoms/2",
    "metta_reducible_head/2",
    "metta_source_declarations/2",
    "metta_space_names/1",
    "metta_string_declarations/2",
    "metta_substitute_self/3",
    "metta_trace_source/4",
    "petta_annotations/2",
    "petta_contract_fact/1",
    "petta_error_answer/3",
    "petta_handles_coherent/1",
    "petta_on_error_mode/3",
    "petta_name_pairs/2",
    "petta_source_reset/1",
    "petta_transaction/1",
    "petta_transport_failure/1",
    "sread_with_names/3",
    "swrite_with_names/3",
    # Eval crosses through a cached translation template while source forms
    # retain translate_expr/3, so compile-once loading pays no cache tax.
    "translate_cached_expr/3",
    "translate_expr/3",
    "unregister_metta_extension/1",
    "with_metta_module/2",
}

_ROW = re.compile(r"^ext_point_kind\(([a-zA-Z_'/0-9-]+/\d+),\s*host_service\)\.",
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
#: "host-choice" is a consult whose answer only the host can make.
FLOOR_REASONS = {
    "catch_recover/2": "host-choice",
    "match_foreign/5": "door",
    "metta_add_atoms/2": "door",
    "metta_host_adopt_function/4": "host-orchestration",
    "metta_host_clear_defined/1": "host-orchestration",
    "metta_host_clear_space/1": "host-orchestration",
    "metta_host_digest/2": "host-orchestration",
    "metta_host_drop_function/2": "host-orchestration",
    "metta_host_explain_match/3": "host-orchestration",
    "metta_host_fast_header/1": "host-orchestration",
    "metta_host_forget_function/1": "host-orchestration",
    "metta_host_load_fast/2": "host-orchestration",
    "metta_host_load_file/3": "host-orchestration",
    "metta_host_open_function/3": "host-orchestration",
    "metta_host_operation_error/5": "error-vocabulary",
    "metta_host_read_forms/2": "host-orchestration",
    "metta_host_register_reader_token/2": "door",
    "metta_host_remove_reported/3": "host-orchestration",
    "metta_host_run_source/4": "host-orchestration",
    "metta_host_run_source_status/3": "host-orchestration",
    "metta_host_save_fast/3": "host-orchestration",
    "metta_host_stored/2": "host-orchestration",
    "metta_host_substitute/3": "host-orchestration",
    "metta_host_unregister_reader_token/1": "door",
    "metta_reducible_head/2": "door",
    "metta_source_declarations/2": "codec",
    "metta_space_names/1": "door",
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
    "petta_transaction/1": "door",
    "petta_transport_failure/1": "error-vocabulary",
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
    re-pay, and it fails here until it moves engine-side. The six design
    moves (run/load, registration lifecycle, remove-with-report, the
    explain mirror, exception shaping, the bulk clears) took the list
    from 49 published rows to this classified floor.
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
               "host-choice"}
    stray = {name: why for name, why in FLOOR_REASONS.items()
             if why not in allowed}
    assert not stray, f"a reason outside the floor taxonomy: {stray}"
