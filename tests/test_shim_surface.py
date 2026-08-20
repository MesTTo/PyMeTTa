"""Purpose: the published host_service list is a ratchet toward the
transport floor. P4.23 published the 49 engine predicates the Python shim
calls; the shrink item moves the host-agnostic orchestration engine-side
under host-neutral names so every next binding stops re-paying it, and
each move deletes rows here. This pin makes the direction enforceable:
a NEW host_service row fails until the manifest below names it with a
reason, and a deleted row fails until it leaves the manifest, so the
scoreboard never drifts from the tree.

Assumes:
  - ext_point_kind rows in src/ext_points.pl are the one authority for a
    seam's kind [tested: every_seam_declares_one_kind in static_checks]
Guarantees:
  - the manifest and the tree hold the same host_service set, compared as
    sets with both differences named
    [tested: test_the_host_service_scoreboard_matches_the_tree]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import re

#: Every published host_service, exactly as declared. Deleting a row here
#: must accompany deleting its declaration (the shrink working as
#: intended); adding one means the shim grew a NEW dependency on the
#: engine, which is the direction the floor forbids without a recorded
#: reason beside the name.
HOST_SERVICES = {
    "catch_recover/2",
    "clear_foreign_atoms/1",
    "clear_native_atoms/1",
    "match_foreign/5",
    "metta_host_load_file/3",
    "metta_host_read_forms/2",
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
    "metta_host_fast_header/1",
    "metta_host_digest/2",
    "metta_host_substitute/3",
    "metta_add_atoms/2",
    "metta_atom_hook_clause/2",
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
    "petta_source_reset/1",
    "petta_transaction/1",
    "petta_transport_failure/1",
    "sread_with_names/3",
    "translate_expr/3",
    "unregister_metta_extension/1",
    "with_metta_module/2",
}

_ROW = re.compile(r"^ext_point_kind\(([a-zA-Z_'/0-9-]+/\d+),\s*host_service\)\.",
                  re.MULTILINE)


def test_the_host_service_scoreboard_matches_the_tree(repo_root):
    declared = set(
        _ROW.findall((repo_root / "src" / "ext_points.pl").read_text())
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
