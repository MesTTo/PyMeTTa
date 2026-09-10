% Purpose: Prolog side of the metta Python library. Adds tagged term encoding,
%   per-directive structured runs, space operations, Python-backed MeTTa
%   functions (deterministic and nondeterministic), evaluation, and proof-tree
%   derivations on top of an unmodified MeTTa engine. Consulted after
%   engine/main.pl; only adds predicates, never redefines engine ones.
% Guarantees:
%   - metta_py_space_untouched/1 rejects registered and revoked names before
%     probing their contents, including a free-name row restored by rollback
%     [tested: test_a_rolled_back_allocation_cannot_recycle_a_revoked_name;
%     commit=c6e1198c490a824b96f6fc6e1c0622a542917024].
%   - fresh decode frames index variable names while returning ordered pairs;
%     a prebound occurrence cannot change an earlier name's identity
%     [tested: shared_decode_index; commit=32650f9ff4d1c4aa0749d8eb8b153e5bb448ee5c].
%   - cursor and function work opened in a transaction belongs to it; capture
%     returns the eager enumeration's text once, and budgets bind that work
%     [tested: extensions/python/tests/ch15_writing_transactions_and_worlds/test_cursor_transaction.py,
%     host_hold; commit=ea2c1bde39a7b002b1e5948cf6c53bc469dac084].
%   - metta_py_mirror_bounds/0 turns the catalog's own watch point on for the
%     (limit ...) head, so a bound the seat mirrors is invalidated by whoever
%     writes the row, a MeTTa program's own add-atom included
%     [tested: extensions/python/tests/ch01_getting_started/test_config.py::test_a_bound_a_program_rewrites_reaches_the_next_read;
%     commit=c26b6a4d28ef8fb50742440feed2c0578ebb0f58]
%   - a Python provider's declared capability words are checked against the
%     catalog's (vocabulary provider-capability ...) row at the registration
%     door, and the encoder and decoder speak exactly the term tags the
%     (wire-tag ...) rows declare
%     [tested: catalog_vocabulary_words:an_unknown_capability_word_is_refused,
%     catalog_vocabulary_words:the_shim_speaks_the_declared_wire_tags;
%     commit=7f9c810e5f4a2023ad98de34e848667dd72bc4a7]
%   - metta_py_observe_begin/1 and metta_py_observe_end/1 hold ONE trace session
%     across the host's own calls and answer what it recorded, so a Python
%     with-block can instrument work it drives itself
%     [tested: extensions/python/ext/metta-otel/tests/test_otel.py::test_an_observed_block_hangs_its_reductions_under_one_span,
%     tracer:a_held_session_records_across_separate_evaluations; commit=0fb68d75871c57f2421c335e9faef3561f8dfdd5].
%   - metta_py_assert_answers/1 and metta_py_assert_includes/1 decide their
%     verdict with the same subtraction-atom their MeTTa twins use and then
%     report through the engine's own two assertion doors, so a Python
%     assertion over answer bags and a MeTTa one cannot hold different
%     relations or print different sentences [tested:
%     extensions/python/tests/ch12_testing/test_assert_answers.py;
%     commit=ef5b91d7950594a49e177d972a954841a6b8d6e0]
%   - a bound function's cost claim crosses as the class and the measure the
%     ENGINE resolved, never a second derivation on this side
%     [tested: test_the_measure_comes_from_the_arrow_at_the_holes_position;
%     commit=6b4dceb61ccc78e308e6678af58f8daf43c31523]
%   - internal and held evaluations install the same carrier and demand context
%     [tested: sh extensions/python/test.sh
%     tests/ch06_many_answers/test_evaluation_context.py -n 0; commit=54cb2eee69c42c1ae685643cbe2578f8d617a265].
%   - protocol type expressions use the atom wire and retain shared variables
%     [tested: test_computed_protocol_types_are_live_and_removable; commit=4eaefdd8d40e53b2613722287302a14b41704662]
%   - a profile row carries the predicate's own name and arity and the calls
%     SWI keeps on its '<recursive>' caller, so no host takes a quoted
%     module-qualified spelling back apart [tested:
%     test_a_profile_row_carries_its_predicate_name_and_arity_apart,
%     test_profile_extension_counts_a_compiled_head; commit=3287d4dd4928f09ce7c111d05a1c516808e226d5]
%   - tagged provider premises and direct matches share match/4, annotations,
%     and the controlled inference budget [tested:
%     test_tagged_premise_keeps_the_direct_provider_annotation,
%     test_provider_duplicate_premises_keep_four_proofs_and_one_source_bag;
%     commit=4f2d6c0f8eb293b73f8dde30a1c84e24834f7393].
%   - transport failure subclasses retain their outcome across error policies
%     [tested: test_protocol_errors_cannot_become_engine_answers; commit=089bc6036ae5039bce3963d8b4e80ecaf04dfb49]
%   - async Python operations answer a future space immediately, publish their
%     launch through the current observation frame, and publish landing only
%     from the later event-loop completion; a publication fault settles the
%     future as an error through its original token rather than stranding an
%     awaiter [tested:
%     test_an_async_operation_answers_a_future_space,
%     test_a_transaction_commits_async_launch_before_its_landing,
%     test_a_failed_landing_publication_settles_the_future_as_an_error;
%     commit=2f562bc5c051ee373cb7ab27ea6cae641f1df094].
%   - scheduler tasks dispatch Python callbacks under their copied ContextVars
%     and detach oracleIO calls onto transient offload threads [tested:
%     test_context_snapshot_crosses_every_spawn_door_including_thread_workers,
%     test_a_blocking_oracle_uses_the_dirty_lane_without_pinning_normal_work;
%     commit=39092863ae34184a9f955f185ff57c1ff177ec40].
%   - metta_py_evaluate/4 with answers=retained answers a cardinality and replay
%     cursor from ONE evaluation, so an effect-bearing goal fires once and a
%     length nobody turns into values encodes nothing [tested:
%     test_a_retained_count_replays_the_bag_the_cursor_would_have_answered;
%     commit=WORKTREE].
%   - ordered algebra cursors interrupt their deterministic collect-and-sort
%     phase at timeout without leaving an alarm armed across cursor suspension
%     [tested: test_an_ordered_algebra_view_is_bounded_by_its_timeout;
%     commit=51e719767e3dd322a9cf88bd096410bbc5647493].
%   - accounted eager evaluation returns its inference delta in the same
%     crossing so tagged Python fixpoints can pass only their remaining quota
%     to the next operation [tested:
%     test_tagged_algebra_debits_inferences_across_operations;
%     commit=51e719767e3dd322a9cf88bd096410bbc5647493].
%   - metta_py_origin/3 answers one row per compiled clause in clause order,
%     with the file from clause_property/2 or from the loader's ownership
%     journal and the line left to the position walk in
%     extensions/python/metta/_binding/positions.py [tested:
%     test_a_head_loaded_from_a_metta_file_names_that_file_and_line,
%     test_every_clause_of_a_multi_clause_head_answers_in_clause_order,
%     test_two_files_defining_one_head_keep_each_clause_with_its_own_file,
%     shim_observation_doors; commit=6375a7c8f3c035b04bc9d41c8f7f22e56b42fb41].
%   - the thread_message_hook/3 clause here delivers to metta_ops and then
%     FAILS, so SWI still prints, and it never reenters itself [tested:
%     test_the_engine_still_prints_its_own_message, shim_observation_doors;
%     commit=6375a7c8f3c035b04bc9d41c8f7f22e56b42fb41].
%   - a profile row carries its predicate's source and its ticks in seconds,
%     converted the way SWI's own report converts them [tested:
%     test_a_profile_is_the_same_table_every_other_door_answers,
%     test_a_profile_exports_as_pstats; commit=6375a7c8f3c035b04bc9d41c8f7f22e56b42fb41].
%   - atomic entry points publish atom hooks after commit, while speculative
%     and reified-world entry points discard their buffered event segments;
%     speculative and world execution also fence the non-backtrackable State
%     store [tested: test_events_publish_only_after_transaction_commit,
%     test_atomic_scope_commits_or_discards_one_event_segment,
%     test_speculative_execution_discards_its_event_segment,
%     test_world_eval_fences_state_and_emits_nothing; commit=3ded7552797b66d78e666141eb51f3bc14686bd2].
%   - the committed-segment boundary crosses to Python once per commit and only
%     while metta_py_segments(true) has installed its clause and the segment
%     touched a subscribed space [tested:
%     test_a_transaction_delivers_one_progress_after_its_deltas,
%     test_a_write_to_an_unwatched_space_costs_no_boundary_crossing;
%     commit=0de0dc08d2fc77bee9dd132c41f1de23cda1e6c2].
%   - held query and evaluation engines carry the same capture, atomic, or
%     speculative policy for their complete lifetime as eager execution;
%     speculation preserves every answer while discarding its writes
%     [tested: test_every_public_execution_door_honours_speculative_policy,
%     test_lazy_capture_collects_held_engine_output,
%     test_lazy_atomic_rolls_back_after_a_late_cursor_failure,
%     test_speculative_lazy_execution_preserves_every_answer;
%     commit=1262dd20ada9d5c799d9bdc4bdf5d2b859ca7a98].
%   - derivation search is collected inside the same execution-policy goal,
%     preserving every proof while speculative scopes discard meta-interpreter
%     writes [tested: test_every_public_execution_door_honours_speculative_policy,
%     test_derivation_speculation_fences_the_engine_global_self;
%     commit=cf6507cfe9c3d6512ac75039ae22f178140e0cbf].
%   - structured evaluation targets bind every &self occurrence to their
%     receiving space while decoding, including the executable handle produced
%     by parse, so Atom and source execution share one receiver law without a
%     second term walk [tested:
%     test_atom_eval_rebinds_nested_self_to_the_receiver,
%     test_parsed_atom_eval_rebinds_self_handle_to_the_receiver;
%     commit=f8453b013a603de9f9d4c7606c95ca7210229e78].
%   - successive annotated Python operation answers extend the current carrier
%     value instead of replacing it, while provider rows remain local inputs to
%     the engine's conjunction join [tested:
%     test_two_annotated_operation_calls_multiply_all_four_joint_weights;
%     commit=1208ea172e11560b2aaae238823514941aa5fe20].
%   - an empty direct eval answers NOTHING both for a guarded head with no
%     matching clause and for a matched empty body, which is one answer where
%     this door used to draw two: the guarded head was a not-reducible answer
%     until the NoMatchEnum default became NoMatchFail on 2026-08-30, and that
%     is upstream's own answer -- it has no policy layer, just
%     `Goal =.. [Fun|CallArgs]` and a call
%     [source: PeTTa@ae66fa8 src/translator.pl:363-370;
%     tested: test_the_no_match_policy_decides_between_empty_and_the_written_call,
%     which also pins NoMatchOriginal as the policy that asks for the written
%     call back]
%   - metta_py_world_effect_plan/4 translates and walks a target without
%     executing it, returning the engine's named effect plan and the world's
%     declared coverage before world scratch state exists; semantic special
%     forms remain visible when lowering erases their head [tested:
%     test_an_uncovered_world_refuses_before_creating_scratch_or_running_the_operation,
%     test_lowered_nondeterminism_remains_visible_to_world_admission;
%     commit=173eeed021beb360b5e5f9f8461889e27190affc]
%   - one saga step's receipt instrumentation is installed and retired as a
%     whole: a wrapper that cannot be installed unwinds the ones before it and
%     leaves no receipt sink, and a teardown whose first unwrap is already gone
%     still retires every later wrapper [tested:
%     test_a_refused_wrapper_installation_leaves_no_saga_instrumentation,
%     test_saga_teardown_retires_every_wrapper_past_a_missing_one;
%     commit=173eeed021beb360b5e5f9f8461889e27190affc]
%   - Python's non-direct eval paths use translate_cached_expr/3, so repeated
%     forms reuse the engine's invalidated translation templates
%     [tested: translation_cache, test_the_host_service_scoreboard_matches_the_tree; commit=d90a3c9620e56e42d3a2f5982b4353da8423e873]
%   - encoded generator tuple and sparse-dict rows are unified against the
%     operation's actual arguments, preserving one engine answer per matching
%     yielded occurrence [tested:
%     test_relational_tuple_candidates_unify_in_all_directions_without_changing_multiplicity,
%     test_sparse_relational_dict_candidates_bind_parameter_names;
%     commit=6917bef7ca902671999eafcae3a7a86db8f69723]
%   - the repeatability bridge fails closed on an ordinary classifier refusal
%     but preserves every engine control exception [tested:
%     python_repeatability_control:the_bridge_preserves_inference_limits;
%     commit=6917bef7ca902671999eafcae3a7a86db8f69723]
%   - metta_py_declare_handles/3 writes the declaration and checks the
%     context's critical pairs in one transaction, so a conflicting entry
%     rolls back and never becomes queryable
%     [tested test_declare_handles_rejects_a_conflict_eagerly]
%   - metta_py_raise/2 reserves one exact exception shape for Python-side
%     classification [tested test_reserved_exception_shape_maps_by_kind]
%   - a query pattern carrying a sequence variable is classified once at the ask
%     and handed to match/4 wrapped, from the same walk that lifts its
%     modifiers, so a gap-free query builds the goal it always built
%     [tested: test_ellipsis_is_an_anonymous_segment,
%     test_a_segment_binding_projects_as_an_expression_slice; commit=a3dff3abc83b9d82f3652093246e1d693d526cdb]
%   - metta_py_add_strict_declaration/2 refuses a declaration already owned by
%     source code before Python publishes an operation
%     [tested: test_a_duplicate_declaration_names_the_first_one;
%     commit=0d90e628b1f90c4b4464a2907efcb357d74b13d3]
%   - metta_py_declare_algebra/2 runs the engine's sole finite-carrier law
%     checker in the declaring space's equation module [tested:
%     test_a_law_is_checked_once_in_the_declaring_space; commit=2e627a593413191cda3170f2eb716835f7f62543]
%   - host algebra predicates receive symbols and expressions as atoms, not
%     Janus strings or lists [tested: test_carrier_preserves_text_and_symbol_types;
%     commit=074dc0a88b1605c54824de677d586b6f60998bcf].
%   - metta_py_check_algebra_values/4 decodes host values and checks them
%     through metta_require_algebra_value/3 in the declaring equation module
%     [source: engine/spaces/catalog.pl:metta_require_algebra_value/3;
%     commit=074dc0a88b1605c54824de677d586b6f60998bcf].
%   - metta_py_check_algebra_values_accounted/5 meters carrier predicates
%     inside the evaluation's resource guard [tested:
%     test_carrier_predicate_inferences_are_bounded_at_every_phase;
%     commit=074dc0a88b1605c54824de677d586b6f60998bcf].
%   - derivations descend through the default six-axis dispatch wrapper, so
%     recursive proof depth remains bounded and one equation yields one proof
%     [tested: test_depth_exhaustion_returns_a_partial_proof;
%     commit=0d90e628b1f90c4b4464a2907efcb357d74b13d3]
%   - a proof node is an equation, a stored atom or a goal the program called,
%     never the recursion charge metta_instrument_recursive_clause/3 writes in
%     front of a recursive equation's body
%     [tested: test_a_recursive_proof_omits_the_engine_stack_charge]
%   - metta_py_load/3 loads under the engine's own source-load lifecycle, so
%     the library's door and import! replace each other's loads of a file and
%     not only their own [tested 2026-08-19:
%     test_both_doors_replace_a_files_definitions,
%     test_loading_the_same_file_twice_leaves_one_copy]
%   - stack-bounded text and fast loads have explicit wrappable entries for
%     metta_py_limited/6 [tested:
%     test_stack_limit_is_carried_to_the_limited_six_seam; commit=b1de70215dd3f0c9d5437558c57c5911c13948b5]
%   - Engine atom hooks exist only while a Python space subscription exists
%     [tested test_subscription_hooks_follow_the_active_space_set]
%   - metta_py_new_modelled_space/3 and metta_py_release_space/1 keep
%     inherited-space declarations aligned with anonymous-name reuse [tested:
%     test_a_recycled_child_name_may_choose_a_different_parent;
%     commit=755330de329ece49eddcfb7d6db3061c3350a0ca]
%   - metta_py_new_space/1 answers a space that EXISTS with nothing written to
%     it, the property 'new-space'/1 has; the model-declaring doors take the
%     name alone because metta_declare_space_parent/2 and
%     metta_declare_restricted_space/2 create the storage themselves and refuse
%     a child already holding one [tested:
%     test_space_names_lists_the_registered_spaces,
%     test_space_handles_are_term_operands_and_round_trip,
%     test_a_recycled_child_name_may_choose_a_different_parent; commit=dee7dd651135f124376c183977b31320e1f9b3a1]
%   - metta_py_drop_space/1 ends a named space life without admitting that
%     public name to the anonymous pool [tested:
%     test_a_named_space_drop_never_enters_the_anonymous_pool;
%     commit=d843bb6d17a525c36afd21cab077d63b34447535]
%   - metta_py_open_atom_space/2 decodes and declares a ground expression
%     identity once for Python space handles [tested:
%     test_python_space_factory_accepts_atom_valued_names; commit=b1de70215dd3f0c9d5437558c57c5911c13948b5]
%   - metta_py_new_modelled_space/3 rolls a failed declaration back to the
%     anonymous-name pool [tested: test_restricted_constructor_validation_is_eager;
%     commit=6a08901f4125c2536f5b4032daac9937f793870f]
%   - metta_py_declare_space/3 declares a model on a name the CALLER chose, so
%     a named space can inherit, be restricted, or carry grants exactly as an
%     anonymous one can; metta_py_new_modelled_space/3 is that door with a
%     fresh name in front of it [tested:
%     test_a_named_space_takes_every_model_an_anonymous_one_takes]
%   - proof leaves recover a parametric space from its canonical storage
%     module and reserved functor [tested:
%     test_two_instances_of_a_parametric_space_answer_independently;
%     commit=3c7bcde6a0670ec5c563584b26977b41cc727580]
%   - metta_control_signal_info/3 returns the tagged reader detail without
%     parsing Janus's rendered exception [tested test_run_syntax_error_is_loud],
%     and metta_control_signal_line/2 answers WHERE a reader failure stopped
%     from the envelope's own context slot, failing where none was named
%     [tested: error_kinds:a_syntax_envelope_carries_its_line; commit=52e95b50cc5acdc0e41f97b444ab244ad1301433].
%     Both read the engine's one refusal table
%     (engine/metta/registration.pl, metta_host_error_kind_row/3), so this
%     seat and the Node seat classify the same kinds
%     [tested: extensions/python/tests/repository/test_error_kinds.py;
%     commit=52e95b50cc5acdc0e41f97b444ab244ad1301433]
%   - metta_py_refusal/6 puts that kind's catalog row on the wire, the ground
%     and the remedy encoded the way every other atom crosses, so the Python
%     side reads them back with Ground.from_atom/1 and Remedy.from_atom/1
%     [tested: extensions/python/tests/repository/test_refusal_rows.py;
%     commit=f33b7ab0200e6dc74c88fb4c7f827bf545a447ed]
%   - metta_py_infer_types/2 walks a space once and answers one
%     [Head, Arity, KindWires, ResultWire] row per (head, arity) the space
%     mentions and does not declare, naming the narrowest kind covering the
%     children observed at each position [tested: shim_type_inference;
%     commit=8d67307403c1e41ccf058bd3c8d4c079dd7cf7d5]
%   - metta_py_evaluate/4 with answers=status and metta_py_run_status/3 report which of
%     MeTTa's evaluation paths produced each answer, leaving the ordinary
%     entry points' output unchanged [tested:
%     test_eval_status_reports_the_four_outcomes; commit=WORKTREE]
%   - the held evaluation cursor is present at bridge boot, so the first lazy
%     answer pull performs no late consult [tested:
%     test_first_answer_pull_has_no_late_consult_floor; commit=18b1135167d60396c41e63e42ded2f66d0eb1900]
%   - metta_py_operation_error/5 reports a builtin refusal as its written
%     operation, formal functor, expected type and culprit, and every value it
%     yields is one Janus can carry [tested
%     test_operation_error_carries_its_parts]
%   - Every wire tag decodes to its term in both the atom and the string
%     spelling Janus may deliver, sharing a variable by name and never
%     sharing an anonymous one, and a malformed wire term fails rather than
%     decoding to something [tested 2026-08-16: shim_wire_decoding,
%     shim_wire_variable_sharing in tests/prolog/suites/host/shim.plt]
%   - A wire name is FIRST-OCCURRENCE POSITIONAL over the term being encoded,
%     so one cell spends one name however many times it occurs and two cells
%     never share one. It used to be the cell's printed form, which SWI
%     derives from a stack offset that moves under a collection and is reused
%     after one, so a term and a copy of it that differed only in where its
%     cells live crossed differently [tested 2026-08-31:
%     shim_wire_variable_sharing:a_variable_shared_by_a_parent_equation_and_a_child_goal_spends_one_name,
%     shim_wire_variable_sharing:one_variable_in_two_columns_crosses_under_one_name,
%     shim_wire_variable_sharing:two_crossings_do_not_share_a_name_between_distinct_variables]
%     Each of those goes red when the name minter is replaced by the printed
%     form this paragraph describes, and ten of that file's forty-nine tests
%     do; measured by planting it on 2026-08-31.
%   - A reply is decoded against the map its crossing was ENCODED under, never
%     against one rebuilt afterwards, so a returned variable is the caller's
%     variable whatever the stack did in between. One call's arguments encode
%     under one map, and an inverse's answered tuple decodes under one table
%     [tested 2026-08-31:
%     shim_answer_form:two_arguments_do_not_share_a_name_between_distinct_variables,
%     shim_answer_form:one_variable_in_two_arguments_crosses_under_one_name,
%     test_an_inverse_answers_one_variable_in_two_positions]
%   - A payload outside the class its tag names fails as a malformed shape
%     does, so a tag is a claim about its payload rather than a label
%     [tested 2026-08-20:
%     shim_wire_decoding:a_payload_outside_its_tags_class_fails]
%   - every atom metta_space_operand/1 calls a space crosses under the p tag
%     and every other atom under s, which is the species metatype_of/2 assigns,
%     so the tag carries the whole decision and Python restores nothing: the
%     two hardcoded names this used to tag sent a space !(new-space) had just
%     made across as a Symbol
%     [tested: test_space_handles_are_term_operands_and_round_trip,
%     test_a_space_the_engine_made_crosses_as_a_space,
%     test_the_ampersand_alone_does_not_make_a_space,
%     test_the_s_tag_stays_a_symbol_however_it_is_spelled; commit=dee7dd651135f124376c183977b31320e1f9b3a1]
%   - the n tag carries signed-i64 Number integers and wider BigInt integers
%     through Janus without changing their exact value
%     [tested 2026-08-20: test_janus_carries_bigint_losslessly]
%   - metta_py_run/3, metta_py_run_using/4 and metta_py_run_status/3 register a
%     source's whole signature set before processing any of its forms, through
%     the engine's own prepare_parsed_forms/1, so a ! may NAME a function the
%     same source defines lower down and run() and load() answer what the
%     engine's file reader answers. What is registered is the signature, not
%     the clauses, so a ! that CALLS one still cannot answer, in either
%     configuration [tested 2026-08-18:
%     test_a_source_registers_every_signature_before_any_form_runs,
%     test_run_using_registers_signatures_over_the_forms_that_will_run,
%     test_run_status_registers_signatures_before_any_form_runs,
%     test_load_memoizes_a_function_the_same_file_defines_lower_down,
%     test_a_declaration_that_cannot_type_what_the_source_defines_is_refused]
%   - metta_py_read_forms/2 is the exception and stays one: it neither compiles
%     nor stores nor runs, so it parses without preparing
%     [tested test_a_manifest_neither_runs_nor_defines]
%   - the library-description doors read and never run: metta_py_registrations/2
%     parses a source for the heads its registration forms claim,
%     metta_py_source_declarations/2 scans a Prolog half's directives, and
%     metta_py_head_claims/2 answers the engine's own effect, cost and
%     deprecation resolutions for a whole roster in one crossing
%     [tested: test_a_card_reads_a_library_without_running_it,
%     test_a_card_carries_the_engines_own_effect_and_cost_answers,
%     test_a_card_names_what_the_library_needs_from_the_platform;
%     commit=ff4257005f562786e3ef7a5a37ce94b7d80e782d]
%   - metta_py_source_loads/2 reads the load table inside one transaction and
%     answers `loading` with no rows while a load is in flight, so a lock
%     cannot record a program that is only half loaded
%     [tested: test_a_lock_refuses_while_a_load_is_in_flight,
%     test_a_lock_round_trips_through_its_file; commit=ff4257005f562786e3ef7a5a37ce94b7d80e782d]
%   - grouped runnable answers use their carried reader map when encoding free
%     variables, so the public run surface retains source names
%     [tested: test_variable_names_survive_to_the_printer; commit=916def0562c211143bb91cd0bd8b2c9dac7ab4fa]
%   - metta_py_symbol_writable/2 exposes the engine grammar's single symbol
%     decision to Python consumers without reproducing delimiters there
%     [tested: test_every_delimiter_check_derives_from_one_grammar_rule;
%     commit=3ae4e6b08bc82d8b9cbdf934afc92ada7cf7a19e]
%   - metta_py_symbol_refusal/2 derives its refusal from
%     metta_symbol_writable/1 and identifies a whole-name custom token before
%     looking for a reserved character, so register_op rejects unreadable
%     names before any registry state changes and explains the grammar that
%     claimed them [tested: test_register_op_refuses_a_name_metta_cannot_read,
%     test_a_registered_token_class_parses_like_a_shipped_one;
%     commit=2c741dda928a30d0ce1c7e1fcf0b263b4d1bb97b]
%   - metta_py_builtins/1 answers the sorted union of every fun/1 name and
%     every translate_special_dl/5 head, so host tooling sees the language
%     rather than only its callable registry [tested:
%     test_builtins_equals_the_union_of_functions_and_special_forms;
%     commit=bcf80e727923cce0e034f716d7eef01f9395c490]
%   - metta_py_builtins/2 answers that union narrowed to the functions ONE
%     space can call (fun_here/1's rule with the module explicit), so a
%     space's namespace never lists or resolves a head whose equations live
%     in a module it cannot see, and its directory stays inside the 750
%     candidates CPython's suggestion machinery accepts
%     [tested: test_a_namespace_lists_and_resolves_only_what_its_space_can_call;
%     commit=1f32a7c85d5c3bcbd8797218694ae5550c362e9a]
%   - metta_py_catalogue_member/2 answers membership in exactly that union
%     as a point probe, so the bound namespace resolves an attribute
%     without rebuilding the catalogue after a definition [tested:
%     test_catalogue_membership_answers_the_builtins_union;
%     commit=d70c8de55092a0ee9b61668810e2f2b906fc1371]
%   - py-eq and py-truthy are decided without a host crossing for variables,
%     booleans, numbers, strings, symbols, and recursively for expressions;
%     opaque grounded objects, including None and objects with __eq__ or
%     __bool__, retain the Python dispatch fallback [tested:
%     shim_python_scalar_semantics,
%     test_wire_scalars_match_the_python_host_oracle; commit=551f6236be947d5c52f5243e3d56f0009a000071]
%   - native comparison classifies a decoded expression by its outer cell and
%     never walks the whole operand before comparing it [tested:
%     comparing_against_the_empty_expression_does_not_walk_the_other_operand;
%     commit=fddb28afcb066271d1f0c78fad8b578b2ab65ccd]
%   - metta_py_limited/6 adds a negative-sentinel stack byte ceiling to the
%     existing time and inference bounds and restores it on every exit path
%     [tested: test_janus_stack_scope_restores_on_all_exits; commit=81c50d3ae4c03ddfd70ed3f1ff70e085cfee3978]
%   - metta_py_function_generation/1 exposes the engine's process-global
%     fun/1-set generation without reproducing catalogue policy in the host
%     [tested: test_generation_tracks_definitions_but_not_evaluation;
%     commit=4c9a794750103e0a3a2e9d883adde337ffb501f0]
%   - metta_py_register_token/2 retains a Python constructor in the engine's
%     reader table and seam:host_reader_token_construct/3 returns its encoded
%     Atom through the shared decoder [tested:
%     test_a_registered_token_class_parses_like_a_shipped_one;
%     commit=2c741dda928a30d0ce1c7e1fcf0b263b4d1bb97b]
%   - query decoding and projection use one name index once a row reaches 64
%     columns, while eager, limited, guarded, prepared, and cursor answer doors
%     preserve first-appearance column order and variable sharing [tested:
%     test_wide_query_projection_is_identical_through_every_answer_door;
%     commit=d843bb6d17a525c36afd21cab077d63b34447535]
%   - a converted Python tuple encodes as its structural MeTTa expression,
%     while an explicitly Grounded tuple remains an object reference
%     [tested: test_a_python_tuple_answers_the_same_through_both_doors;
%     commit=89374a7ed8eec75e26ea595f2c6e55665f80d6fc]
%   - seam:pattern_modifier/3 lifts lazy paths out of stored-pattern position and
%     resolves them only after the root handle has matched [tested:
%     test_a_path_reaches_into_a_handle_without_converting_it;
%     commit=b54ecaaa1224eabb90f808275003cd9abeef8065]
%   - a modifier-free query decides that case before its nondeterministic match,
%     so path support adds 22 fixed inferences per one-pattern query instead of
%     one call per answer [measured: query-2k-rows minimum of 561469, 561467,
%     561467, 440 over 20 queries on 2026-08-21; command=python bench.py query-2k-rows
%     --counter-only; fixture=2000-row native space;
%     commit=b54ecaaa1224eabb90f808275003cd9abeef8065]
%   - metta_py_query_count/6 counts a query inside the engine for an untouched
%     lazy Python answer view [tested:
%     test_query_answers_complete_the_lazy_projection_protocol;
%     commit=b1de70215dd3f0c9d5437558c57c5911c13948b5]
%   - metta_py_query_count_if_repeatable/6 fails closed for foreign spaces,
%     pattern modifiers, and effect-bearing guards, so a Python length hint
%     cannot execute a query effect twice [tested:
%     test_a_guarded_query_length_hint_executes_its_write_once;
%     commit=1262dd20ada9d5c799d9bdc4bdf5d2b859ca7a98]
%   - evaluation emits one undefined-truth frame and never a flag-selected
%     residual-program shape [tested:
%     test_a_not_reducible_answer_is_the_unreduced_term_with_no_flag;
%     commit=affc981bd744563f65f595259b8a3564b9d84ba9]
% Open Obligations:
%   To Do: None
%   Hacks: None
%   Future Enhancements: None

:- use_module(library(janus)).
% Janus resolves maplist/2 lazily on its first failed text query. The native
% file-search cache expires after ten seconds, making that import vary by
% exactly 229 inferences under concurrent startup. Resolve this required
% failure-path dependency while loading the binding.
% [tested: test_first_failed_text_query_has_no_deferred_dependency_cost;
% commit=WORKTREE]
% Workaround: swi-file-search-cache-autoload - import Janus's failed-query dependency once at binding boot.
:- janus:use_module(library(apply), [maplist/2]).
% These predicates are called directly by binding units. Declare their host
% imports here instead of making the first count, variable, or bounded cursor
% load the missing import through Prolog's global autoloader.
% [tested: test_binding_boot_resolves_its_direct_standard_library_dependencies;
% commit=WORKTREE]
:- use_module(library(aggregate), [aggregate_all/3]).
:- use_module(library(gensym), [gensym/2]).
:- use_module(library(solution_sequences), [limit/2]).
:- use_module(library(lists)).
:- use_module(library(apply)).
:- use_module(library(pairs)).  % group_pairs_by_key/2, pairs_values/2
:- use_module(library(hashtable), [ht_get/3, ht_new/1, ht_put/3]).
:- use_module(library(time)).
:- use_module(library(prolog_profile)).
:- use_module(library(prolog_wrap), [wrap_predicate/4, unwrap_predicate/2]).
:- use_module(library(wfs)).

% Resolve the name index's dependencies during bridge loading. Its first
% insertion otherwise autoloads code during the caller's first decode
% [tested: shared_decode_index:the_first_decode_does_not_pay_for_dependency_loading;
% commit=32650f9ff4d1c4aa0749d8eb8b153e5bb448ee5c]. The temporary backtrackable table retains no shared state.
:- ht_new(Index), ht_put(Index, '', _).

%translated_from/2 is engine/filereader.pl's, declared dynamic and exported
%there, so a read before the first equation finds nothing rather than raising.
%A `:- dynamic translated_from/2.` here used to supply that guarantee and now
%creates a SECOND, local predicate that shadows the engine's: SWI reports
%"Local definition of user:translated_from/2 overrides weak import from
%filereader" and every read in this file answers about a table nothing writes.

:- use_module('options.pl', [binding_options_expansion/2]).
:- use_module('evaluation_policy.pl', [binding_evaluation_expansion/2]).
:- use_module('source_macros.pl', [binding_source_expansion/2]).
:- use_module('services.pl', [binding_forward_expansion/2]).
:- include('provides_host_user.pl').
:- include('wire.pl').
:- include('errors.pl').
:- include('source.pl').
:- include('control.pl').
:- include('cursors.pl').
:- include('profiling.pl').
:- include('handles.pl').
:- include('json.pl').
:- include('reader.pl').
:- include('worlds.pl').
:- include('printer.pl').
:- include('store.pl').
:- include('trace.pl').
:- include('debug.pl').
:- include('reflection.pl').
:- include('transport_errors.pl').
:- use_module('bounds.pl', [metta_py_mirror_bounds/0]).
:- include('lifecycle.pl').
:- include('query.pl').
:- include('modules.pl').
:- include('evaluation.pl').
:- include('operations.pl').
:- include('library.pl').
:- include('inference.pl').
:- include('positions.pl').
:- include('derivation.pl').
:- include('foreign.pl').
:- include('messages.pl').
:- include('subscriptions.pl').
:- include('protocol.pl').
:- include('persistence.pl').
