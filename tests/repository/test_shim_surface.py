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
    seam's kind [tested: static_checks:every_seam_declares_one_kind]
Guarantees:
  - host cursor services share transaction ownership and lifecycle across seats
    [tested: test_the_host_service_scoreboard_matches_the_tree,
    test_the_shim_surface_shrank_to_the_transport_floor; commit=ea2c1bde39a7b002b1e5948cf6c53bc469dac084]
  - metta_platform_absent/1 classifies the shim's existing platform census
    query as a host service [tested:
    test_the_host_service_scoreboard_matches_the_tree; commit=ede2ac57e213a0d4502c6bbbca6227f97015b720]
  - carrier membership and nonnumeric operations use engine-owned doors
    [tested: test_the_host_service_scoreboard_matches_the_tree; commit=90ba93eb8f6e98ebfefc55416859bf13de6a8427]
  - the manifest and the tree hold the same host_service set, compared as
    sets with both differences named
    [tested: test_the_host_service_scoreboard_matches_the_tree;
    commit=54cb2eee69c42c1ae685643cbe2578f8d617a265]
  - every remaining row carries a named floor reason, so the list is the
    transport floor rather than a smaller pile of orchestration
    [tested: test_the_shim_surface_shrank_to_the_transport_floor;
    commit=54cb2eee69c42c1ae685643cbe2578f8d617a265]
  - the host query door uses the engine's published pattern-modifier walk
    [tested: test_a_path_reaches_into_a_handle_without_converting_it;
    commit=a1b10566194f10c174101fdc05f956b33171613b]
  - operation-answer weights are composed through the engine's published
    annotation read and algebra extension rather than reimplemented by the
    transport [tested: test_the_host_service_scoreboard_matches_the_tree;
    commit=fc0f512887da08a19a0ec8422a3a8d5716262a64]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import re

import metta
import metta._declare.prelude

#: Every published host_service, exactly as declared. Deleting a row here
#: must accompany deleting its declaration (the shrink working as
#: intended); adding one means the shim grew a NEW dependency on the
#: engine, which is the direction the floor forbids without a recorded
#: reason beside the name.
HOST_SERVICES = {
    "catch_recover/2",
    # Actor inspection and occurrence blame are engine-owned identity reads.
    "metta_actor/1",
    "metta_host_blame/3",
    # The callable doors' cost read, beside the deprecation one below: a bound
    # function's docstring shows the class its (cost ...) row declares, and the
    # measure an unnamed row takes from the head's arrow is resolved by the
    # engine so the docstring and (explain ...) cannot answer differently.
    "metta_cost_declaration/4",
    # Head claims and origin ownership moved from the binding into the engine.
    # The batch, selected-property and occurrence reads share one claim source.
    "metta_head_claims/3",
    "metta_head_property/3",
    "metta_head_origins/3",
    # Which heads one MeTTa source REGISTERS, read from the source and never
    # run. The registration spellings are the engine's own, and a host reading
    # them itself would carry a table of engine forms that goes stale the day a
    # sixth is added: the generated library reference did exactly that by not
    # reading them at all, counting lib_memo at zero names while nine of its
    # heads were callable.
    "metta_string_registrations/2",
    # The callable doors' deprecation reads. The row lookup is the feature's
    # own consult, and the shim's apply-seam emptiness probe rides the same
    # published relation so an empty catalog costs one crossing per process
    # rather than one goal-string read per name [measured 2026-08-26: 1,311
    # inferences per name's first call through the goal-string read, double
    # digits through the apply seam].
    # Space ownership, and the one pair of rows this list GREW rather than
    # shed. The shim registers Python foreign spaces, and it used to record
    # that only in metta_py_foreign/1, a registry of its own that MORK's and
    # redis's equivalents could not see: two providers matching one name then
    # resolved by clause order and an atom landed in whichever store loaded
    # first. Taking the name through an engine door is what makes the second
    # claim a refusal, so these belong on the floor for the same reason
    # metta_release_space/1 does — a lifecycle transition the engine owns and
    # any host drives.
    "metta_claim_space/2",
    "metta_disclaim_space/2",
    "metta_space_claim/2",
    "metta_deprecation/3",
    # The modifier walk gained a fourth argument rather than a second walk:
    # it now also answers whether the pattern carries a sequence variable,
    # which the query door must know before it builds a candidate head, and
    # asking separately would cost a walk per query [measured 2026-08-24].
    "lift_pattern_modifiers/4",
    # Its companion, and the ONLY new row: the plan a gap pattern is asked
    # under. It is one call per gap query and none at all for a gap-free one,
    # and the alternative is the host reimplementing the fragment classifier
    # this engine already owns.
    "metta_seq_query_plan/2",
    # The query carrier is engine policy: the host enters one dynamic scope,
    # reads its effective declaration, and initializes annotations from that
    # declaration's one rather than rebuilding those rules in the transport.
    "metta_with_under/2",
    # Context transport and ranked-bound licensing are engine-owned policy.
    "metta_with_evaluation_context/2",
    "metta_evaluation_context/1",
    "metta_ordered_match_limit/6",
    "metta_effective_algebra/2",
    # current_algebra reads an engine-held per-call override before the host's
    # task scope and an explicit context declaration. The host cannot observe
    # that held override without this door.
    "metta_current_algebra/3",
    "metta_algebra_one/2",
    # Carrier membership is engine policy shared by declarations and native
    # annotations. The host decodes values and asks this same door instead
    # of implementing a second type and finite-domain checker.
    "metta_require_algebra_value/3",
    # Visibility's min/max use the carrier order rather than numeric arithmetic.
    # The transport invokes the engine's operation instead of duplicating it.
    "metta_apply_algebra_operation/5",
    "metta_annotation/2",
    "metta_k_extend/4",
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
    # The same bargain on the wall-clock axis, and it cannot be collapsed into
    # the row above: metta_host_inference_budget/3 is also used ALONE, once in
    # this shim and by the Node and CMeTTa bridges, so a single combined door
    # would not retire it and the floor would not shrink either way. The
    # sharper reason this one must be engine-side is that
    # call_with_time_limit/2 cannot interrupt a goal running inside an engine,
    # so a host wrapping its own pull loop waits for the current pull to
    # return before the alarm is ever seen.
    "metta_host_time_budget/3",
    # A suspended engine cannot join its creating thread's transaction. The
    # engine owns eager holding there, lazy engines elsewhere, thread access,
    # capture replies and cleanup; every seat uses the same opaque handle.
    "metta_host_hold/3",
    "metta_host_hold_next/2",
    "metta_host_hold_chunk/3",
    "metta_host_hold_post/3",
    "metta_host_hold_close/1",
    # Cache validation reads the function registry's engine-owned generation.
    "metta_host_function_generation/1",
    # The one row here that makes the floor SHRINK by being added. The engine
    # decides silent/1 from argv at load time, an embedded host has no argv,
    # and two seats had each written the same retract-then-assert privately
    # (metta_py_set_silent/1 here, metta_c_set_silent/1 in extensions/cmetta),
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
    # The rest of the refusal contract, which each seat used to hold its own
    # copy of. This shim's copies of the kind list, the reader-failure line
    # and the capability reading are GONE, replaced by these calls into the
    # one engine-side table both seats read; the two seats had already
    # drifted apart on which refusals had a class at all
    # [source: docs/journal/2026-09-07-two-seats-one-error-taxonomy.md].
    "metta_host_control_signal_info/3",
    "metta_host_control_signal_line/2",
    "metta_host_space_capability_error/4",
    # The same table as the aggregate reading and as enumerable rows, which
    # the Node bridge classifies with and both seats' suites read against
    # tests/data/error-kinds.json. This seat calls neither: its own wire asks
    # for the three above, one kind at a time.
    "metta_host_error_kind/3",
    "metta_host_error_kind_row/3",
    # The catalog's DECLARATION for whichever kind a ball is: the class name,
    # the ground and the remedy with its holes filled from that ball. This
    # seat calls the aggregate reading, metta_py_refusal/5 being one crossing
    # on a path that is already raising; the rows themselves it reads through
    # &metta like any other catalog data.
    "metta_host_refusal/6",
    "metta_host_refusal_row/4",
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
    "metta_space_operand/1",
    "metta_string_declarations/2",
    "metta_substitute_self/3",
    "metta_release_space/1",
    "metta_annotations/2",
    "metta_contract_fact/1",
    "metta_error_answer/3",
    "metta_handles_coherent/1",
    "metta_on_error_mode/3",
    "metta_name_pairs/2",
    "metta_source_reset/1",
    # Speculation and State fencing are engine-owned execution/store doors.
    # A host selects the boundary but does not reimplement snapshot rollback,
    # the non-backtrackable State guard, or live-cell identity.
    "metta_speculate/1",
    "metta_transaction/1",
    # Sagas need the durable transaction outcome before any post-commit
    # observer or foreign-provider failure is rethrown.
    "metta_transaction_notified/3",
    "metta_world_effect_coverage/2",
    "metta_effect_covered/2",
    "metta_compensation/2",
    "metta_transport_failure/1",
    "metta_with_state_write_fence/1",
    "metta_live_state_cell/1",
    # The platform census. Not shim orchestration moving host-side: it is a
    # fact about the running build that only the engine can answer, and a host
    # that cannot read it recovers the same knowledge by parsing SWI's boot
    # transcript, which is what extensions/node does today.
    "metta_platform/4",
    # The shim already asks which declared capability is absent when refusing
    # an unavailable spelling. Exporting the core makes that dependency explicit.
    "metta_platform_absent/1",
    # The recursion charge the translator writes in front of every recursive
    # equation's body, recognised in a clause body a host is WALKING rather
    # than running. It is engine-side for the shrink's own reason: every
    # binding that walks compiled clauses meets the charge, and a shape each
    # of them spells again drifts the moment the charge changes.
    "metta_host_stack_charge/3",
    # The reduction trace, and it answers the truncation flag beside the
    # events. Both transports moved from /4 to /5 together on 2026-09-03:
    # reaching the bound truncates rather than raising, and a prefix that
    # cannot say it is one is worse than the raise it replaced. The floor
    # SWAPPED rather than grew -- /4 is engine-internal now, reached only
    # by tests/prolog/suites/metatheory/tracer.plt. The function filter rides
    # inside its bound argument as a two-item request, which is why adding it
    # moved nothing here.
    "metta_trace_source/5",
    # The debugger's session trio: the two ends of a session and the goal that
    # goes inside the engine holding a suspended program. The transport creates
    # and steps that engine, as it does for a lazy cursor, because the policy a
    # scope names has to be part of the suspended goal rather than wrapped
    # around engine_next/2. What it cannot own is the WRAPPERS a breakpoint
    # needs: they are the tracer's, only one session may hold them, and
    # refusing a second is a decision no transport can make for the others.
    "metta_debug_begin/2",
    "metta_debug_run/3",
    "metta_debug_end/0",
    # Ask every library to forget what it derived earlier. Engine-side because
    # an event seam's clauses belong to the extensions and the TELLING belongs
    # to the engine, which is the same division every other event here keeps;
    # a host that fired the seam itself would be an extension calling the
    # handlers of every other extension. The host asks for it before replaying
    # a recorded run: the recording's digest pins the space's atoms and its
    # seed pins the draws, and the answers a memo or a table holds are the
    # third piece of the state that run started from.
    "metta_forget_derived/0",
    # The one question a refined type adds to the cast: which constraint the
    # value violates once the witness has declined it, so CastError names
    # `(Gt 0)` and the value rather than the value's types. The relation is the
    # engine's (engine/metta/refinements.pl) and the shim only asks it; the
    # orchestration, get-type then get-metatype then this, was already here.
    "metta_refinement_violation/3",
    # The per-space function catalogue: which registered heads ONE space can
    # call, fun_here/1's rule with the module explicit. The rule is the
    # engine's (engine/metta/registration.pl) and the shim only asks it, per
    # catalogue build and per attribute miss.
    "metta_host_function_callable_from/2",
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
    "metta_actor/1": "door",
    "metta_host_blame/3": "host-orchestration",
    "catch_recover/2": "host-choice",
    "metta_deprecation/3": "door",
    "metta_cost_declaration/4": "door",
    "metta_head_claims/3": "door",
    "metta_head_property/3": "door",
    "metta_head_origins/3": "door",
    "metta_string_registrations/2": "door",
    "lift_pattern_modifiers/4": "door",
    "metta_seq_query_plan/2": "door",
    "metta_with_under/2": "door",
    "metta_with_evaluation_context/2": "door",
    "metta_evaluation_context/1": "door",
    "metta_ordered_match_limit/6": "host-orchestration",
    "metta_effective_algebra/2": "door",
    "metta_current_algebra/3": "door",
    "metta_algebra_one/2": "door",
    "metta_require_algebra_value/3": "door",
    "metta_apply_algebra_operation/5": "door",
    "metta_annotation/2": "door",
    "metta_k_extend/4": "door",
    "metta_refinement_violation/3": "door",
    "metta_host_function_callable_from/2": "door",
    "match_foreign/5": "door",
    "metta_add_atoms/2": "door",
    "metta_assert_space_releasable/1": "door",
    "metta_claim_space/2": "door",
    "metta_disclaim_space/2": "door",
    "metta_space_claim/2": "door",
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
    "metta_host_control_signal_info/3": "error-vocabulary",
    "metta_host_control_signal_line/2": "error-vocabulary",
    "metta_host_space_capability_error/4": "error-vocabulary",
    "metta_host_error_kind/3": "error-vocabulary",
    "metta_host_error_kind_row/3": "error-vocabulary",
    "metta_host_refusal/6": "error-vocabulary",
    "metta_host_refusal_row/4": "error-vocabulary",
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
    "metta_host_stack_charge/3": "host-orchestration",
    "metta_host_save_fast/3": "host-orchestration",
    "metta_host_stored/2": "host-orchestration",
    "metta_host_time_budget/3": "host-orchestration",
    "metta_host_hold/3": "host-orchestration",
    "metta_host_hold_next/2": "host-orchestration",
    "metta_host_hold_chunk/3": "host-orchestration",
    "metta_host_hold_post/3": "host-orchestration",
    "metta_host_hold_close/1": "host-orchestration",
    "metta_host_substitute/3": "host-orchestration",
    "metta_host_unregister_reader_token/1": "door",
    "metta_reducible_head/2": "door",
    "metta_release_space/1": "door",
    "metta_typed_dispatch_applies/2": "door",
    "metta_source_declarations/2": "codec",
    "metta_space_names/1": "door",
    # The species decision behind the wire's p tag: an encoder asks what
    # metatype_of/2 asks, so get-metatype and the wire agree on every atom.
    "metta_space_operand/1": "codec",
    "metta_string_declarations/2": "codec",
    "metta_substitute_self/3": "door",
    "metta_trace_source/5": "door",
    "metta_debug_begin/2": "door",
    "metta_debug_run/3": "door",
    "metta_debug_end/0": "door",
    "metta_forget_derived/0": "door",
    "metta_annotations/2": "door",
    "metta_contract_fact/1": "door",
    "metta_error_answer/3": "error-vocabulary",
    "metta_handles_coherent/1": "door",
    "metta_on_error_mode/3": "host-choice",
    "metta_name_pairs/2": "codec",
    "metta_source_reset/1": "door",
    "metta_speculate/1": "door",
    "metta_transaction/1": "door",
    "metta_transaction_notified/3": "door",
    "metta_world_effect_coverage/2": "door",
    "metta_effect_covered/2": "door",
    "metta_compensation/2": "door",
    "metta_transport_failure/1": "error-vocabulary",
    "metta_with_state_write_fence/1": "door",
    "metta_live_state_cell/1": "door",
    "metta_platform/4": "census",
    "metta_platform_absent/1": "census",
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


def test_the_prelude_names_are_what_install_registers():
    """`_prelude.NAMES` and the table `install()` registers are one roster.

    The names are written twice by construction -- the tuple is read by the
    compiler before any engine exists, and the registration table pairs each
    with the closure that implements it -- so this is what holds the two
    together. A head added to one and not the other used to be found at run
    time, when a compiled body lowered to a name nothing had registered.
    """
    import ast
    from pathlib import Path

    from metta._declare.prelude import NAMES

    source = Path(metta._declare.prelude.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    install = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "install"
    )
    table = next(
        node.value
        for node in ast.walk(install)
        if isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
        and node.target.id == "prelude"
    )
    registered = [
        element.elts[1].value
        for element in table.elts
        if isinstance(element, ast.Tuple) and isinstance(element.elts[1], ast.Constant)
    ]
    assert registered == list(NAMES)


def test_the_binding_heads_are_heads_the_engine_knows(metta):
    """Every head `_lint_analysis` treats as binding is one the engine has.

    The set is a CHOICE -- which of the engine's heads bind a name in their
    body -- so it is not derived from the engine's roster; what is derived is
    that it cannot name a head the engine does not have, which is the way it
    could go stale without anything saying so. `bind!` is a FUNCTION rather
    than a special form and binds all the same, which is why the roster this
    reads is both.
    """
    from metta.lint._analysis import _BINDING_HEADS

    known = set(
        metta.runtime.must(
            "findall(_Head, (spaces:metta_special_form_head(_Head) ; fun(_Head)), Heads)"
        )["Heads"]
    )
    assert _BINDING_HEADS <= known, sorted(_BINDING_HEADS - known)


def test_the_metatypes_are_the_engines_own(metta):
    """`_lint_analysis._METATYPES` is what `get-metatype` can answer, plus two.

    The four `get-metatype` answers are the engine's. The three beside them
    are the ones no value ever IS: `Atom` is their supertype, `%Undefined%` is
    the wildcard a declaration writes for "anything", and `Type` is the type of
    a type. All three admit anything of their kind for the same reason the four
    do. A fifth metatype in the engine and not here would leave a declaration
    this lint could contradict.
    """
    from metta import G, S
    from metta.lint._analysis import _METATYPES

    answered = {
        str(metta.eval(S["get-metatype"](subject))[0])
        for subject in (S.a, S.a(S.b), G(1), metta.parse("$x"))
    }
    assert answered == {"Symbol", "Expression", "Grounded", "Variable"}
    assert answered <= _METATYPES, sorted(answered - _METATYPES)
    assert _METATYPES - answered == {"Atom", "%Undefined%", "Type"}
