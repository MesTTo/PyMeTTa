% Purpose: Prolog side of the metta Python library. Adds tagged term encoding,
%   per-directive structured runs, space operations, Python-backed MeTTa
%   functions (deterministic and nondeterministic), evaluation, and proof-tree
%   derivations on top of an unmodified MeTTa engine. Consulted after
%   engine/main.pl; only adds predicates, never redefines engine ones.
% Guarantees:
%   - async Python operations answer a future space immediately, publish their
%     launch through the current observation frame, and publish landing only
%     from the later event-loop completion [tested:
%     test_an_async_operation_answers_a_future_space,
%     test_a_transaction_commits_async_launch_before_its_landing;
%     commit=39092863ae34184a9f955f185ff57c1ff177ec40].
%   - scheduler tasks dispatch Python callbacks under their copied ContextVars
%     and detach oracleIO calls onto transient offload threads [tested:
%     test_context_snapshot_crosses_every_spawn_door_including_thread_workers,
%     test_a_blocking_oracle_uses_the_dirty_lane_without_pinning_normal_work;
%     commit=39092863ae34184a9f955f185ff57c1ff177ec40].
%   - metta_py_eval_count_retaining/6 answers a cardinality and a replay
%     cursor from ONE evaluation, so an effect-bearing goal fires once and a
%     length nobody turns into values encodes nothing [tested:
%     test_a_retained_count_replays_the_bag_the_cursor_would_have_answered;
%     commit=00a30179a1acd55aa969b44a977fb9a38e2e2df2].
%   - atomic entry points publish atom hooks after commit, while speculative
%     and reified-world entry points discard their buffered event segments;
%     speculative and world execution also fence the non-backtrackable State
%     store [tested: test_events_publish_only_after_transaction_commit,
%     test_atomic_scope_commits_or_discards_one_event_segment,
%     test_speculative_execution_discards_its_event_segment,
%     test_world_eval_fences_state_and_emits_nothing; commit=3ded7552797b66d78e666141eb51f3bc14686bd2].
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
%   - structured evaluation targets bind every symbolic &self occurrence to
%     their receiving space while decoding, so Atom and source execution share
%     one receiver law without a second term walk [tested:
%     test_atom_eval_rebinds_nested_self_to_the_receiver;
%     commit=a408160adee022dffb72fbde405efc8f229c0b6e].
%   - successive annotated Python operation answers extend the current carrier
%     value instead of replacing it, while provider rows remain local inputs to
%     the engine's conjunction join [tested:
%     test_two_annotated_operation_calls_multiply_all_four_joint_weights;
%     commit=WORKTREE].
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
%     parsing Janus's rendered exception [tested test_run_syntax_error_is_loud]
%   - metta_py_eval_status_all/3, metta_py_eval_status_using_all/4, and
%     metta_py_run_status/3 report which of
%     MeTTa's evaluation paths produced each answer, leaving the ordinary
%     entry points' output unchanged [tested:
%     test_eval_status_reports_the_four_outcomes; commit=b1de70215dd3f0c9d5437558c57c5911c13948b5]
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
%   - metta_py_catalogue_member/1 answers membership in exactly that union
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
:- use_module(library(lists)).
:- use_module(library(apply)).
:- use_module(library(hashtable), [ht_get/3, ht_new/1, ht_put/3]).
:- use_module(library(time)).
:- use_module(library(prolog_profile)).
:- use_module(library(prolog_wrap), [wrap_predicate/4, unwrap_predicate/2]).
:- use_module(library(wfs)).

%translated_from/2 is engine/filereader.pl's, declared dynamic and exported
%there, so a read before the first equation finds nothing rather than raising.
%A `:- dynamic translated_from/2.` here used to supply that guarantee and now
%creates a SECOND, local predicate that shadows the engine's: SWI reports
%"Local definition of user:translated_from/2 overrides weak import from
%filereader" and every read in this file answers about a table nothing writes.

%%%%%%%%%% Wire encoding %%%%%%%%%%
%
% janus maps both a Prolog atom and a Prolog string to a Python str, and maps
% the booleans to strings too, so a bare term crossing the boundary loses its
% metatype. Every term crosses tagged instead: ["s",Name] symbol, ["g",Text]
% string, ["n",N] Number or BigInt, ["b",true|false] boolean,
% ["v",Name] variable, ["e",[...]] expression, ["p",Name] space reference,
% ["o",Ref] Python object reference. The tag list itself is nested lists, which janus converts
% natively in both directions.

%Encode a Prolog term as a tagged wire term:
%The clauses are mutually exclusive and every one of them cuts, so their order
%is a pure COST decision, and py_is_object/1 was in the wrong place: it is a
%foreign call into janus and it ran on every argument, and on every ELEMENT of
%every list, before anything asked whether the value was a number. It costs 915
%instructions where number/1 and string/1 are VM instructions costing nothing
%measurable [measured 2026-08-17, 3,000,000 iterations, min of 3: 1,765,021,710
%for the bare loop, 4,510,067,594 with py_is_object/1, 2,914,057,131 with
%blob/2]. Moving it behind the free tests is worth most on exactly the argument
%shape the encoded path is worst at, since a 64-item list paid it 64 times.
%
%Sound because a janus reference satisfies NONE of the tests now in front of
%it: it is atomic and not atom, number, string, is_list, compound or callable
%[measured 2026-08-17 against py_call(builtins:object(), Obj), blob type py].
%That is the same fact get_type_candidate/2 relies on where it writes
%`atomic(X), \+ atom(X), python_object_blob(X)` to keep ordinary values out of
%janus. Nothing else about the encoding moves; the relative order of every
%other clause is unchanged.
%The wire name is an IDENTITY, never a display name: the same cell must
%encode the same on every crossing, and two different cells must never
%collide, so the source-name attribute (metta_var_name) deliberately does
%NOT reach here. Sending it was measured breaking round-trip identity
%(a variable through a registered op stopped unifying home) and aliasing
%distinct answer variables that shared a spelling.
%A wire name is FIRST-OCCURRENCE POSITIONAL, the numbering engine/writer.c
%and numbervars/3 already give a term's variables. It used to be the printed
%form, and SWI prints an unbound variable as its STACK OFFSET:
%  if (p > (Word) lBase) iref = ((Word)p - (Word)lBase)*2+1;
%  else                  iref = ((Word)p - (Word)gBase)*2;
%  Ssprintf(name, "_%lld", (int64_t)iref);
%[source: swipl-9.3.33/src/pl-write.c:127-140, var_name_ptr()]. An offset
%moves when the cell moves and is handed to whatever lands there next, so the
%spelling broke this contract in both directions: one cell answered _9162
%before a collection and _32 after [measured 2026-08-31], which crossed one
%variable under two names, and a reused offset gives two variables one name.
%A five-deep (fact 5) proof crossed as
%  (= (fact $_17642) (if (> $_17642 0) (* $_17642 (fact (- $_2528 1))) 1))
%whose free $_2528 is not the variable the head binds.
%
%The map is THREADED rather than pre-built, so a term holding no variable
%pays only for passing it and a name is minted the first time its cell is
%met. metta_py_encode/2 remains the door every caller uses.
metta_py_encode(Term, Wire) :- metta_py_encode(Term, [], _, Wire).

metta_py_encode(T, N0, N, ["v", Name]) :- var(T), !, metta_py_wire_name(T, N0, N, Name).
metta_py_encode(T, N, N, ["n", T])    :- number(T), !.
metta_py_encode(T, N, N, ["g", T])    :- string(T), !.
metta_py_encode(T, N, N, ["b", T])    :- ( T == true ; T == false ), !.
%WHICH QUESTION THE `p` TAG ASKS, asked of the engine rather than answered
%here. `p` is a SPECIES tag: what it decodes into is a Space where `s` decodes
%into a Symbol, so the question is the one the engine's own species classifier
%asks, and metatype_of/2 asks metta_space_operand/1
%[source: engine/metta/types.pl, metatype_of(X, 'Grounded') :- atom(X),
%metta_space_operand(X)]. Asking it here is what makes get-metatype and the
%wire agree on every atom.
%
%The pair '&self' and '&metta' used to be written out here, which tagged
%exactly two names, so a space !(new-space) had just made crossed as an
%ordinary symbol and Python could not use it as a space
%[measured 2026-08-27: &metta-space-1 encoded ["s", "&metta-space-1"] while
%being listed by metta_space_names/1 and answering Grounded to get-metatype].
%
%NOT metta_space_name/1, the WIDER test that is-space/2 answers. That one is
%about operand admissibility, not species: it accepts any ampersand name
%because a space is created on demand, so it calls '&bar' a space where
%get-metatype answers Symbol, and it calls a State cell a space too
%[measured 2026-08-27: metta_space_name('&state-#0') is true and
%get-metatype answers Grounded through metta_state_cell/1, not through the
%space clause]. Tagging either as `p` would make the wire disagree with the
%language in the one dimension the tag encodes.
%
%NOT metta_space_names/1 either, which is the same set as a sorted LIST:
%two findalls, an append and a sort per call where this is one indexed lookup.
%
%atom(T) first because the wire's `p` payload is TEXT (CODEC.md), while
%metta_space_operand/1 also accepts a PARAMETRIC space, which is a compound
%and crosses as the expression it is. The order is this file's cost rule: the
%test costs 6 inferences on an ordinary symbol and 5 on '&self'
%[measured 2026-08-27, 100,000 iterations against a bare loop of 100,002:
%700,002 for a non-space atom, 600,002 for '&self'].
metta_py_encode(T, N, N, ["p", S]) :- atom(T), metta_space_operand(T), !, atom_string(T, S).
metta_py_encode(T, N, N, ["s", S])    :- atom(T), !, atom_string(T, S).
metta_py_encode(T, N, N, ["o", T])    :- py_is_object(T), !.
metta_py_encode(T, N0, N, ["e", Es])  :- is_list(T), !, metta_py_encode_each(T, N0, N, Es).
metta_py_encode([H|T], N0, N, ["e", [["s", "cons"], EH, ET]]) :- !,
    metta_py_encode(H, N0, N1, EH),
    metta_py_encode(T, N1, N, ET).
%Janus's default tuple translation is -/N. It is the carrier for a structural
%MeTTa expression here, not a callable named `-`; a Grounded tuple never
%reaches this clause because its Python reference is claimed above.
metta_py_encode(T, N0, N, ["e", Es]) :-
    metta_py_tuple_arguments(T, Raw), !,
    maplist(metta_py_result, Raw, Elements),
    metta_py_encode_each(Elements, N0, N, Es).
%A non-list compound encodes as (f a b). compound_name_arguments/3 rather
%than =../2, because =.. RAISES on a ZERO-ARITY compound and janus hands us
%one for every empty Python tuple: py_call(builtins:tuple(), X) binds X to
%-() [measured 2026-08-18]. That reached here as
%`Domain error: compound_non_zero_arity expected, found -()` out of an
%ordinary Python return value, ''.split() of an empty string among them,
%and only through the LIBRARY: the engine has its own writer and never ran
%this clause [tested: test_wire_round_trip].
%
metta_py_encode(T, N0, N, ["e", [["s", FS] | Es]]) :-
    compound(T),
    compound_name_arguments(T, F, Args),
    atom(F), !,
    atom_string(F, FS),
    metta_py_encode_each(Args, N0, N, Es).
%Anything else (a blob, a dict) is carried as text, the printer's last resort:
%A native handle (a C blob) crosses as a registry reference plus its own
%printed text, so Python holds it opaquely and can hand back the very
%same blob: identity, not a serialisation. It used to fall through to
%the term_string clause below, which silently stringified it and made
%the round trip impossible: 'vector-length' on what came back saw a
%string [measured 2026-08-17]. The clause sits HERE, at the tail, so
%only a term every other clause refused pays the blob/2 probe: placed
%before the list clauses it taxed every encoded list node, and SWI's []
%is itself a reserved non-text blob, so it also registered every () as
%a handle, caught by the wire round-trip property over Expr('()'). A
%blob is atomic, so nothing above claims one: atom/1 is false for
%non-text blobs, and the compound clause needs compound/1.
metta_py_encode(T, N, N, ["h", Id, S]) :- blob(T, Type), Type \== text, T \== [], !,
    metta_py_handle_keep(T, Id),
    term_string(T, S).
metta_py_encode(T, N, N, ["g", S]) :- term_string(T, S).

metta_py_encode_each([], N, N, []).
metta_py_encode_each([T|Ts], N0, N, [E|Es]) :-
    metta_py_encode(T, N0, N1, E),
    metta_py_encode_each(Ts, N1, N, Es).

%The name this cell already has, or a fresh one. Compared by ==, because
%identity of a Prolog variable is only answerable by comparison
%[source: engine/writer.c, METTA_WRITER_VARS], which is why this scan and
%writer.c's are both linear in the count of DISTINCT variables a term holds.
metta_py_wire_name(Variable, Names0, Names, Name) :-
    (   metta_py_var_name(Names0, Variable, Found)
    ->  Names = Names0,
        atom_string(Found, Name)
    ;   metta_py_fresh_name(Names0, Fresh),
        Names = [Fresh-Variable|Names0],
        atom_string(Fresh, Name)
    ).

%A fresh name comes from a SESSION counter, not from this term's own count.
%Both halves of the contract have to hold at once and they pull apart:
%  - within a crossing, one cell is one name, which is what the MAP gives and
%    what the printed form could not, because a collection moves the offset it
%    is made of;
%  - across crossings, two cells are never one name, which is what the COUNTER
%    gives. A host atom compares by spelling, so two variables answered by two
%    separate matches and then put in one expression would be one variable if
%    each crossing had started its own numbering at _0 [measured 2026-08-31:
%    `(p (f $x))` and `(p (g $y))` answered `(f $_0)` and `(g $_0)`].
%Numbering per term satisfies the first and breaks the second; the address did
%the reverse. gensym/2 is the counter the cut barriers below already use.
%
%The seeded names are stepped over: a caller may seed the map with the
%reader's own spellings, and $_3 is one a program is allowed to write.
metta_py_fresh_name(Names, Name) :-
    gensym('_', Candidate),
    (   memberchk(Candidate-_, Names)
    ->  metta_py_fresh_name(Names, Name)
    ;   Name = Candidate
    ).

%Encode with an explicit Name-Var list, so parsed variables keep their names.
%The list SEEDS the same map every encode threads, so a variable the seed
%does not name is minted beside the named ones rather than through a second
%naming rule that could disagree with them.
metta_py_encode_named(T, Pairs, W) :- metta_py_encode(T, Pairs, _, W).

%Every argument of one call under ONE map, and the map itself, because the
%reply is decoded against it. Encoding argument by argument would restart the
%numbering at each one, so two DISTINCT variables in two arguments would both
%be named _0 and the decoder would share them into one.
metta_py_encode_arguments(Arguments, Encoded, Names) :-
    metta_py_encode_each(Arguments, [], Names, Encoded).

metta_py_var_name([N-V|_], T, N) :- V == T, !.
metta_py_var_name([_|Pairs], T, N) :- metta_py_var_name(Pairs, T, N).

%A tag arrives back as an atom or a string depending on the sender; accept both:
metta_py_tag(T, T) :- atom(T), !.
metta_py_tag(T, A) :- string(T), atom_string(A, T).

%A HOST ANSWER read as a boolean: a Python predicate answers whatever it
%answers and everything that is not one of the true spellings is false, the
%truthiness reading. This is for a RETURN VALUE, not for a wire payload; the
%b tag has its own strict reader below, because a payload the grammar does
%not admit is a malformed term and turning it into `false` would answer a
%question nobody asked.
metta_py_bool(B, true)  :- B == true, !.
metta_py_bool(B, false) :- B == false, !.
metta_py_bool(B, true)  :- B == '@'(true), !.
metta_py_bool(B, false) :- B == '@'(false), !.
metta_py_bool(B, true)  :- B == "true", !.
metta_py_bool(_, false).

%The b tag's payload, and nothing else. Facts rather than a chain of ==/2
%with cuts, so first-argument indexing decides in one step and an
%inadmissible payload has no clause to fall into.
metta_py_wire_bool(true,       true).
metta_py_wire_bool(false,      false).
metta_py_wire_bool('@'(true),  true).
metta_py_wire_bool('@'(false), false).
metta_py_wire_bool("true",     true).
metta_py_wire_bool("false",    false).

%Decode a tagged wire term; every v tag becomes its own fresh variable.
%
%The tag decides the clause, so it is normalised once and dispatched on.
%Asking metta_py_tag/2 whether the tag is o, then s, then g, then n, walks
%that list of alternatives and re-runs atom/1 and string/1 at every step,
%which is how deciding that ['n',1] holds a number came to cost nine
%inferences. Every Python term crossing into the engine is decoded this way,
%so the walk was on the query path, the run path and the eval path alike
%[measured 2026-08-16: (m6f 1) evaluated from Python, 72.00 inferences to
%63.00 and 5.45us to 4.98us, of which the wire term's own decode fell 22.00
%to 13.00 and a single number leaf 9.00 to 4.00].
metta_py_decode([T0|Rest], Term) :-
    ( atom(T0) -> T = T0 ; string(T0) -> atom_string(T, T0) ),
    metta_py_decode_(T, Rest, Term).

metta_py_decode_(o, [Obj], Obj).
%A handle reference resolves to the registered blob itself. A stale id
%is an existence error naming it, never a fresh or empty value: the
%handle's release is explicit on the Python side, so reaching a released
%one is the caller's bug and silence would turn it into a wrong answer.
metta_py_decode_(h, [Id|_], Blob) :-
    (   metta_py_handle_store(Id, Blob)
    ->  true
    ;   throw(error(existence_error(metta_native_handle, Id),
                    context(metta_py_decode_/3,
                            'the handle was released or never issued')))
    ).
%Each payload is checked against the class its tag names, and a payload of
%another class has no decoding: the term is malformed and the decode fails,
%which is what every malformed shape above already did. Without the checks
%the tag was a label rather than a claim, and six payloads decoded to
%something instead: ["s",1] to the symbol '1', ["g",1] to "1", ["n","1/3"]
%to a string wearing the number tag, ["v",1] to a fresh variable, and
%["b",<anything>] to FALSE, which is the one that answers rather than fails
%[measured 2026-08-20, both spellings, against extensions/python/metta/_atom_wire.py,
%which refuses all six]. A wire term is written by an encoder, so nothing
%conforming loses a shape here; what changes is that a boundary bug now
%reports as one [tested: shim_wire_decoding:a_payload_outside_its_tags_class_fails].
%Every check is a TYPE TEST WRITTEN OUT, never a call to a shared one, and
%that is a measurement rather than a preference: number/1, atom/1 and
%string/1 compile to VM instructions costing no inference, while a call to
%a predicate wrapping them costs one on a path that runs per leaf of every
%answer. Per-leaf inferences, before against after, as the atom payload /
%as the string payload, both being spellings janus delivers
%[measured 2026-08-20, 10,000 decodes each, three runs identical]:
%
%  s        4.00/5.00  ->  3.00/5.00     g   4.00/4.00  ->  4.00/4.00
%  v        3.00/4.00  ->  3.00/4.00     n   4.00       ->  4.00
%  v shared 8.00/10.00 ->  8.00/10.00    b   4.00/8.00  ->  4.00/5.00
%
%Faster or equal on every tag and every spelling: the boolean payload
%replaced a chain of ==/2 with indexed facts, and the symbol payload stopped
%calling atom_string/2 on an atom that already is the symbol.
%
%A shared metta_py_wire_text/1 helper was written first and cost +1.00 on s
%and on v, which the alpha-unique benchmark saw as +1.54% and the counter
%gate refused. The A/B behind it had measured zero and was wrong: its
%synthetic term held 1000 s, 500 v and 500 b leaves, whose +1000 +500 -1500
%cancels exactly. A per-tag change needs a per-tag measurement.
metta_py_decode_(s, [S], A)     :- ( atom(S) -> A = S ; string(S), atom_string(A, S) ).
metta_py_decode_(g, [S], Str)   :- ( string(S) -> Str = S ; atom(S), atom_string(S, Str) ).
metta_py_decode_(n, [N], N)     :- number(N).
metta_py_decode_(b, [B], A)     :- metta_py_wire_bool(B, A).
metta_py_decode_(v, [Name], _)  :- ( atom(Name) -> true ; string(Name) ).
metta_py_decode_(e, [Es], Term) :- maplist(metta_py_decode, Es, Term).
metta_py_decode_(p, [S], Space) :-
    ( atom(S) -> Space = S ; string(S), atom_string(Space, S) ),
    sub_atom(Space, 0, 1, _, '&').

%Decode sharing variables by name, so the $x in a head and in a body unify.
%Bindings comes back as Name-Var pairs for reading answers off a query:
metta_py_decode_shared(Tagged, Term, Bindings) :-
    metta_py_decode_shared_(Tagged, Term, [], Bindings).

metta_py_decode_shared_([T0|Rest], Term, B0, B) :-
    ( atom(T0) -> T = T0 ; string(T0) -> atom_string(T, T0) ),
    metta_py_decode_shared_tagged(T, Rest, Term, B0, B).

%Only v and e differ from the plain decode: one shares a variable by name and
%the other has to thread the bindings through its elements. Every leaf below
%them carries no bindings, so it is the plain decode with B unchanged.
metta_py_decode_shared_tagged(v, [Name0], Var,
                              indexed(B0, Index), indexed(B, Index)) :- !,
    ( string(Name0) -> atom_string(Name, Name0) ; atom(Name0), Name = Name0 ),
    ( Name == '_' -> Var = _, B = B0
    ; ht_get(Index, Name, Shared) -> Var = Shared, B = B0
    ; ht_put(Index, Name, Var), B = [Name-Var|B0] ).
metta_py_decode_shared_tagged(v, [Name0], Var, Table, B) :- !,
    %The atom branch carries the payload check with it: a name arriving as
    %anything but text has no identity to share by, and testing it here
    %rather than ahead of the table keeps the check on a branch that was
    %already being taken.
    ( string(Name0) -> atom_string(Name, Name0) ; atom(Name0), Name = Name0 ),
    %The anonymous variable is fresh at every occurrence and never binds,
    %exactly as the reader treats $_ in source; recording it would make two
    %underscores constrain each other.
    ( Name == '_' -> Var = _, B = Table
    ; memberchk(Name-Var, Table) -> B = Table
    ; B = [Name-Var|Table] ).
metta_py_decode_shared_tagged(e, [Es], Term, B0, B) :- !,
    foldl_decode(Es, Term, B0, B).
metta_py_decode_shared_tagged(T, Rest, Term, B, B) :-
    metta_py_decode_(T, Rest, Term).

foldl_decode([], [], B, B).
foldl_decode([E|Es], [T|Ts], B0, B) :-
    metta_py_decode_shared_(E, T, B0, B1),
    foldl_decode(Es, Ts, B1, B).

%Decode an evaluation target in its receiver context. The ordinary &self
%receiver takes the exact hot decoder above. A named receiver uses the same
%single decode walk but replaces a symbolic ["s","&self"] leaf as it is met;
%a ["p","&self"] is a carried Space handle and stays the handle it names.
%Doing the replacement during decode avoids the second O(n) term walk that
%formerly cost alpha-unique about 400k inferences, while still preserving the
%shared variable table [source:
%extensions/python/benchmarks/target_self_decode.py;
%commit=a408160adee022dffb72fbde405efc8f229c0b6e]. The
%current and target complexity are both O(n); this removes the duplicate
%traversal rather than changing the class.
metta_py_decode_target('&self', Tagged, Term, Bindings) :- !,
    metta_py_decode_shared(Tagged, Term, Bindings).
metta_py_decode_target(Space, Tagged, Term, Bindings) :-
    metta_py_decode_target_(Tagged, Space, Term, [], Bindings).

metta_py_decode_target_([T0|Rest], Space, Term, B0, B) :-
    ( atom(T0) -> T = T0 ; string(T0) -> atom_string(T, T0) ),
    metta_py_decode_target_tagged(T, Rest, Space, Term, B0, B).

metta_py_decode_target_tagged(e, [Es], Space, Term, B0, B) :- !,
    foldl_decode_target(Es, Space, Term, B0, B).
metta_py_decode_target_tagged(s, ['&self'], Space, Space, B, B) :- !.
metta_py_decode_target_tagged(s, ["&self"], Space, Space, B, B) :- !.
metta_py_decode_target_tagged(T, Rest, _, Term, B0, B) :-
    metta_py_decode_shared_tagged(T, Rest, Term, B0, B).

foldl_decode_target([], _, [], B, B).
foldl_decode_target([E|Es], Space, [T|Ts], B0, B) :-
    metta_py_decode_target_(E, Space, T, B0, B1),
    foldl_decode_target(Es, Space, Ts, B1, B).

%THE SEED TABLE IS GONE, and with it the reason a decode had to be handed
%something to expand. It rebuilt the argument variables' names AFTER the
%crossing, while the names Python was given had been written BEFORE it, and a
%name was the cell's stack offset: a collection anywhere in encode-call-decode
%renamed the very variables the table existed to find, so a returned variable
%stopped resolving to the caller's. metta_py_encode_arguments/3 hands back the
%map it wrote and the decode is given that map, so the two sides cannot name
%one cell differently and nothing is built a second time. The laziness this
%replaces was worth one inference on a thirteen-inference call
%[measured 2026-08-17]; threading costs a call with no variable nothing at
%all, because the map stays [] and no name is ever minted.

% A wide query retains first-appearance pairs for acyclicity and answer
% semantics while using a backtrackable hash table for variable identity and
% projection lookup.
metta_py_decode_indexed(Tagged, Term, Bindings) :-
    ht_new(Index),
    metta_py_decode_shared_(Tagged, Term, indexed([], Index), Bindings).

%%%%%%%%%% The explicit answer form %%%%%%%%%%
%
%["a", Theta, Residue, K] and ["a", Theta, Residue, K, Value]: bindings
%for the query's variables, crossing beside plain atom wires in one
%stream. Theta pairs are [Name, ValueWire]; the names are the ones
%metta_py_encode/2 wrote for the query's variables, so binding by name is
%binding the caller's own variable. This is Hyperon's execute_bindings,
%LeaTTa's ReduceResult.okBind: an answer atom together with the bindings
%it is returned under, each set merged into the current frame. The wire
%is transport-agnostic; janus is one carrier of it, and a Prolog-side
%provider needs none of it because unification already binds.
%
%The head asks for four elements before it looks at the tag, so every
%plain two-element wire falls through on the list spine without reaching
%the comparison; the explicit form stays off the hot path's price.
metta_py_answer_form([Tag, Theta, Residue, K], Theta, Residue, K, none) :-
    ( Tag == "a" -> true ; Tag == a ).
metta_py_answer_form([Tag, Theta, Residue, K, Value], Theta, Residue, K,
                     value(Value)) :-
    ( Tag == "a" -> true ; Tag == a ).

%The annotation slot: the degenerate point is the carrier's one and costs
%nothing; a real k is admitted exactly when its context declared a non-Boolean
%algebra. Provider rows REPLACE the cell because match_foreign_routed/6 captures
%each row locally and extends the conjuncts itself. Operation answers EXTEND the
%cell because sequential evaluation is the join: replacing there made the last
%call's weight win. An undeclared k is refused loudly because silently dropping
%it would misweigh the answer and silently keeping it would smuggle a carrier
%the context never declared.
metta_py_answer_kappa('@'(none), _) :- !.
metta_py_answer_kappa(K0, Ctx) :-
    metta_py_answer_kappa_value(K0, Ctx, K),
    b_setval('$metta_answer_k', K).

metta_py_answer_compose_kappa('@'(none), _) :- !.
metta_py_answer_compose_kappa(K0, Ctx) :-
    metta_py_answer_kappa_value(K0, Ctx, K),
    metta_annotation(Ctx, Previous),
    metta_k_extend(Ctx, Previous, K, Joint),
    b_setval('$metta_answer_k', Joint).

metta_py_answer_kappa_value(K0, Ctx, K) :-
    (   metta_effective_algebra(Ctx, Algebra),
        Algebra \== bool
    ->  ( K0 = [_|_] -> metta_py_decode_shared(K0, K, _) ; K = K0 )
    ;   throw(error(metta_answer_annotation_undeclared(Ctx, K0), none))
    ).

%Close an answer's residue: the part of the query the provider did not
%discharge, evaluated by the engine under the bindings already made. The
%residue decodes against the same name table, so its variables ARE the
%query's, and each evaluation result that is not false contributes one
%closure, composing bindings by ordinary sharing; false contributes
%nothing. That rule is the language's own: a condition like (> $y 3)
%reduces to a boolean and false drops the answer, a match form inside the
%residue contributes one closure per solution, and a term with no
%equation answers itself, exactly as !(edge a b) does at the top level.
%This residue is only the part a provider did not discharge. Constraint goals
%remain language-internal through residual-goals/2, and a WFS answer carries
%its delay condition; neither creates a second Python return shape.
metta_py_answer_close('@'(true), _) :- !.
metta_py_answer_close(ResidueW, Table) :-
    metta_py_decode_shared_(ResidueW, Residue, Table, _),
    eval(Residue, Out),
    Out \== false.

%A conditional answer under a pushed bound under-answers: the provider
%truncated at the caller's k, and a residue can still drop answers after
%that, so fewer than k arrive while more existed. Exact licensed the
%bound; a residue is exactly what Exact rules out.
metta_py_answer_bounded('@'(true), _, _) :- !.
metta_py_answer_bounded(_, '@'(none), _) :- !.
metta_py_answer_bounded(Residue, _, Pattern) :-
    throw(error(metta_answer_conditional_under_bound(Pattern, Residue),
                none)).

%Merge Theta into the query frame: seed the name table with the query's
%own variables, decode each bound value against it, so values may
%reference the query's variables and each other while unknown names stay
%fresh, and unify. A failing unification drops the ANSWER, exactly as a
%candidate that does not unify is dropped, and is equally sound.
%Table0 is the map the encoder wrote for the term this answer replies to,
%so theta's bindings extend the caller's own variables rather than a second
%naming of them.
metta_py_answer_theta(Pairs, Table0, Table) :-
    foldl(metta_py_answer_binding, Pairs, Table0, Table).

metta_py_answer_binding([NameW, ValueW], Table0, Table) :-
    ( atom(NameW) -> Name = NameW ; atom_string(Name, NameW) ),
    metta_py_decode_shared_(ValueW, Value, Table0, Table1),
    ( memberchk(Name-Variable, Table1) -> Table = Table1
    ; Table = [Name-Variable|Table1] ),
    Variable = Value.

%One item of a provider's match stream against the query pattern. The
%explicit form applies theta to the pattern's variables; its value, when
%present, is the candidate-with-bindings reading and unifies under them,
%and its residue closes through the engine, one answer per closure.
metta_py_answer_match(Item, Pattern, Table0, Ctx) :-
    metta_py_answer_match(Item, Pattern, '@'(none), Table0, Ctx).
metta_py_answer_match(Item, Pattern, Limit, Table0, Ctx) :-
    (   metta_py_answer_form(Item, Theta, Residue, K, ValueW)
    ->  metta_py_answer_kappa(K, Ctx),
        metta_py_answer_bounded(Residue, Limit, Pattern),
        metta_py_answer_theta(Theta, Table0, Table),
        (   ValueW = value(VW)
        ->  metta_py_decode_shared_(VW, Value, Table, _),
            Pattern = Value
        ;   true
        ),
        metta_py_answer_close(Residue, Table)
    ;   %The crossing's own map, so a reply's names mean one thing on both
        %branches rather than the map here and a fresh table there. It changes
        %no answer, and that is a measurement rather than an expectation: a
        %candidate that repeats the crossing's own name, one that invents a
        %name, a ground one and one that echoes the variable it was handed all
        %answer identically either way [measured 2026-08-31, four providers
        %against (match &probe (edge a $y) $y)]. The unification below is why:
        %a plain candidate is unified with the pattern immediately, which
        %aliases exactly what resolving the names would have. Unlike the theta
        %branch, where the value is returned rather than unified and the map is
        %the only link, this branch cannot go wrong either way.
        metta_py_decode_shared_(Item, Candidate, Table0, _),
        Pattern = Candidate
    ).

%One result of an operation dispatch: the explicit form binds the CALL's
%variables and reduces to its value, () when none, the relational
%reading; a plain wire is the value itself, decoded with the lazy seed.
metta_py_answer_result(Item, Name, Table0, Result) :-
    (   metta_py_answer_form(Item, Theta, Residue, K, ValueW)
    ->  metta_py_answer_compose_kappa(K, Name),
        metta_py_answer_theta(Theta, Table0, Table),
        (   ValueW = value(VW)
        ->  metta_py_decode_shared_(VW, Result, Table, _)
        ;   Result = []
        ),
        metta_py_answer_close(Residue, Table)
    ;   metta_py_decode_shared_(Item, Result, Table0, _)
    ).

:- multifile prolog:error_message//1.
prolog:error_message(metta_answer_conditional_under_bound(Pattern, Residue)) -->
    [ 'an answer for ~q carries a residue (~q) while the caller\'s bound \c
       was pushed to the provider. A conditional answer can still drop \c
       after the provider truncated, which under-answers; a residue is \c
       exactly what an Exact claim rules out, so declare this shape \c
       Sound instead'-[Pattern, Residue] ].
prolog:error_message(metta_answer_annotation_undeclared(Ctx, K)) -->
    [ 'this answer carries an annotation (~q) and ~w declares no \c
       semiring for it. Declare (annotations ~w ranked) to admit ordered \c
       annotations there; silently dropping k would misweigh the answer \c
       and silently keeping it would smuggle an order the context never \c
       declared'-[K, Ctx, Ctx] ].

%%%%%%%%%% Errors %%%%%%%%%%
%
% Some exceptions are control signals rather than errors; converting one into a
% value would swallow the very signal its thrower waits for.
metta_py_raise(Kind, Detail) :-
    throw(error(metta_control_signal(Kind, Detail), context(metta, Kind))).

metta_control_signal_info(
    error(metta_control_signal(Kind, Detail), context(metta, _)), Kind, Detail) :-
    % policy-inventory-exempt: mechanism-internal; reason=these are the reserved control-envelope classifier tags shared with the Python exception bridge; evidence=extensions/python/metta/shim.pl:metta_control_signal_info/3
    memberchk(Kind, [syntax, time_limit, inference_limit, interrupted,
                     value, type]).

metta_control_signal_kind(Error, Kind) :-
    metta_control_signal_info(Error, Kind, _).

%The classification is the engine's metta_host_operation_error/5; this side
%maps its neutral absence, an unbound part, onto janus's None.
metta_py_operation_error(Error, Operation, Kind, Expected, Culprit) :-
    metta_host_operation_error(Error, Operation, Kind, Expected0, Culprit0),
    metta_py_operation_part(Expected0, Expected),
    metta_py_operation_part(Culprit0, Culprit).

metta_py_operation_part(Part, @none) :- var(Part), !.
metta_py_operation_part(Part, Part).

metta_py_space_capability_error(
    error(metta_space_capability_required(Space, Operation, Capability), _),
    Space, Operation, Capability).

%The Python side's contributions to the engine's control-signal seam. There
%was a metta_py_control_exception/1 here holding a SECOND copy of the list,
%and nothing ever called it: it had drifted from the engine's, missing
%metta_host_interrupted and both of this side's limit errors, so anyone who found it
%and used it would have swallowed exactly the signals this side raises.
:- multifile control_exception/1.
control_exception(error(metta_control_signal(_, _), context(metta, _))).

%%%%%%%%%% Run and load %%%%%%%%%%
%
% The grouping walk, the using-substitution, the load lifecycle and the
% status vocabulary live ENGINE-SIDE now, in engine/filereader.pl's host run
% and load surface, where every binding shares one copy; this side decodes
% the host values in, maps the codec over the term groups coming out, and
% nothing else. Reader failures arrive as the engine's reserved
% metta_control_signal envelope, which the Python side already classifies
% by shape. The grouping is one answer list per ! directive, in source
% order [tested test_run_status_reports_each_directive,
% test_both_doors_replace_a_files_definitions].

metta_py_run(Source, Space, Groups) :-
    metta_host_run_source(Source, Space, [], TermGroups),
    maplist(metta_py_encode_group, TermGroups, Groups).

metta_py_encode_group(Terms, Encoded) :-
    maplist(metta_py_encode_answer, Terms, Encoded).

%A binding may be a rational tree under the petta alignment, since
%unification binds raw, and the tagged-array wire has no finite form for
%one: the encoder's recursion would diverge (measured: 6.7 million frames
%to the stack limit). The ANSWER and ROW sites are the only places a
%cyclic term can reach the wire, so they test first and refuse loudly
%with the remedy named; stored atoms, events and parses are finite by
%construction and pay nothing
%[tested: test_a_rational_tree_binding_refuses_its_row_loudly].
%Inlined at the row clauses as ( acyclic_term(B) -> true ; refuse ), the
%exact shape and price the silent gate had (+2 inferences per row through
%a helper call measured on foreign-match and run-source); the cold branch
%alone is a predicate.
metta_py_wire_refuse :-
    throw(error(metta_rational_tree_wire,
                context(metta_py_encode/2,
                        'a rational-tree binding has no finite wire \c
                         form; match with the stored atom as the \c
                         template to read the atoms themselves'))).

metta_py_wire_acyclic(Term) :-
    (   acyclic_term(Term)
    ->  true
    ;   metta_py_wire_refuse
    ).

prolog:error_message(metta_rational_tree_wire) -->
    [ 'a rational-tree binding has no finite wire form; match with the \c
       stored atom as the template to read the atoms themselves' ].

metta_py_encode_answer('$metta_answer'(Term, NameState), Encoded) :- !,
    metta_py_wire_acyclic(Term),
    metta_name_pairs(NameState, Names),
    metta_py_encode_named(Term, Names, Encoded).
metta_py_encode_answer(Term, Encoded) :-
    metta_py_wire_acyclic(Term),
    metta_py_encode(Term, Encoded).

%Run with named host values: each Name-Value pair substitutes the bare
%symbol Name throughout the parsed forms before anything runs, the local-
%variable reading a dataframe gets in embedded SQL. Values arrive on the
%wire, objects boxed, so identity crosses whole; the decode is this side's
%half, the substitution walk is the engine's.
metta_py_run_using(Source, Space, Pairs, Groups) :-
    maplist(metta_py_using_pair, Pairs, Bindings),
    metta_host_run_source(Source, Space, Bindings, TermGroups),
    maplist(metta_py_encode_group, TermGroups, Groups).

metta_py_using_pair([Name0, Wire], Name-Value) :-
    ( atom(Name0) -> Name = Name0 ; atom_string(Name, Name0) ),
    metta_py_decode_shared(Wire, Value, _).

metta_py_run_status(Source, Space, Groups) :-
    metta_host_run_source_status(Source, Space, TermGroups),
    maplist(metta_py_status_group, TermGroups, Groups).

metta_py_status_group(Rows, Encoded) :-
    maplist(metta_py_status_row, Rows, Encoded).

metta_py_status_row([empty, none], [empty, none]) :- !.
metta_py_status_row([Status, Term], [Status, Encoded]) :-
    metta_py_encode_answer(Term, Encoded).

metta_py_load(File, Space, Groups) :-
    metta_host_load_file(File, Space, TermGroups),
    maplist(metta_py_encode_group, TermGroups, Groups).

%Read every form in Source without processing any, the boot-manifest door
%[tested test_a_manifest_neither_runs_nor_defines].
metta_py_read_forms(Source, Forms) :-
    metta_host_read_forms(Source, Pairs),
    maplist(metta_py_form_pair, Pairs, Forms).

metta_py_form_pair([Kind, Text], [KindStr, TextStr]) :-
    atom_string(Kind, KindStr),
    ( string(Text) -> TextStr = Text ; atom_string(Text, TextStr) ).

%%%%%%%%%% Guarded and captured calls %%%%%%%%%%
%
% Two meta entry points wrap the run, query and eval entry points without
% changing them. metta_py_limited applies the engine's own per-call guards,
% call_with_time_limit (seconds) and call_with_inference_limit (steps);
% metta_py_captured collects everything the wrapped goal prints to the
% current output. Both name their target as data, a listed entry point plus
% its input list and one output, so they compose by listing
% metta_py_captured as itself wrappable: limited over captured is a capture
% inside a limit. Exceeding a guard throws the reserved exception envelope;
% the Python side classifies its exact shape, never its rendered text.
% A guard that stops a goal stops it mid-way, so writes it already made
% stand, the honest semantics of every timeout.

metta_py_wrappable(metta_py_run).
metta_py_wrappable(metta_py_run_using).
metta_py_wrappable(metta_py_query_all).
metta_py_wrappable(metta_py_query_guarded_all).
metta_py_wrappable(metta_py_query_limit_all).
metta_py_wrappable(metta_py_query_count).
metta_py_wrappable(metta_py_query_count_if_repeatable).
metta_py_wrappable(metta_py_eval_all).
metta_py_wrappable(metta_py_eval_using_all).
metta_py_wrappable(metta_py_eval_many_all).
metta_py_wrappable(metta_py_eval_many_using_all).
metta_py_wrappable(metta_py_eval_status_all).
metta_py_wrappable(metta_py_reducible).
metta_py_wrappable(metta_py_eval_status_using_all).
metta_py_wrappable(metta_py_run_status).
metta_py_wrappable(metta_py_captured).
metta_py_wrappable(metta_py_atomic).
metta_py_wrappable(metta_py_speculative).
metta_py_wrappable(metta_py_profiled).
metta_py_wrappable(metta_py_trace).
metta_py_wrappable(metta_py_function_shape).
metta_py_wrappable(metta_py_cursor_next).
metta_py_wrappable(metta_py_cursor_chunk).
metta_py_wrappable(metta_py_cursor_next_controlled).
metta_py_wrappable(metta_py_cursor_chunk_controlled).
metta_py_wrappable(metta_py_cursor_open_controlled).
metta_py_wrappable(metta_py_cursor_open_under_controlled).
metta_py_wrappable(metta_py_eval_cursor_open_controlled).
metta_py_wrappable(metta_py_eval_cursor_open_under_controlled).
metta_py_wrappable(metta_py_eval_count).
metta_py_wrappable(metta_py_eval_count_under).
metta_py_wrappable(metta_py_eval_count_if_repeatable).
metta_py_wrappable(metta_py_eval_count_under_if_repeatable).
metta_py_wrappable(metta_py_eval_count_retaining).
metta_py_wrappable(metta_py_tagged_count).
metta_py_wrappable(metta_py_derivation).
metta_py_wrappable(metta_py_derivations).
metta_py_wrappable(metta_py_load).
metta_py_wrappable(metta_py_fast_load_unit).
%A save is linear in the space in all three of its parts, so all three are
%bounded: the enumeration, the unwritable-atom scan the validator runs, and
%the fast writer. Loading was already bounded and saving was not, which left
%the one door on this surface that does unbounded engine work with no guard.
metta_py_wrappable(metta_py_atoms).
metta_py_wrappable(metta_py_fast_save).
metta_py_wrappable(metta_py_world_eval).

metta_py_fast_load_unit(File, Space, []) :-
    metta_py_fast_load(File, Space).

metta_py_wrapped_goal(Pred0, Ins, Out, Goal) :-
    ( atom(Pred0) -> Pred = Pred0 ; atom_string(Pred, Pred0) ),
    ( metta_py_wrappable(Pred) -> true
    ; throw(error(domain_error(metta_py_wrappable, Pred), none)) ),
    append(Ins, [Out], Args),
    Goal =.. [Pred | Args].

%TimeS and Inf use -1 for "no bound"; both bounds may apply at once, the
%inference wrapper outermost so a time signal thrown inside it passes out.
metta_py_limited(TimeS, Inf, Pred, Ins, Out) :-
    metta_py_wrapped_goal(Pred, Ins, Out, Goal),
    metta_py_guarded(TimeS, Inf, Goal).

%The six-argument seam extends rather than changes metta_py_limited/5. A
%negative StackBytes is the same no-bound sentinel the older limits use.
metta_py_limited(TimeS, Inf, StackBytes, Pred, Ins, Out) :-
    metta_py_wrapped_goal(Pred, Ins, Out, Goal),
    metta_py_guarded(TimeS, Inf, StackBytes, Goal).

metta_py_guarded(TimeS, Inf, StackBytes, Goal) :-
    (   StackBytes < 0
    ->  metta_py_guarded(TimeS, Inf, Goal)
    ;   metta_host_with_stack_limit(
            StackBytes, metta_py_guarded(TimeS, Inf, Goal))
    ).

metta_py_guarded(TimeS, Inf, Goal) :-
    ( TimeS < 0 -> Timed = Goal
    ; Timed = catch(call_with_time_limit(TimeS, Goal),
                    time_limit_exceeded,
                    metta_py_raise(time_limit, TimeS)) ),
    ( Inf < 0 -> call(Timed)
    ; call_with_inference_limit(Timed, Inf, Result),
      ( Result == inference_limit_exceeded
        -> metta_py_raise(inference_limit, Inf)
      ; true ) ).

metta_py_captured(Pred, Ins, [Out, Text]) :-
    metta_py_wrapped_goal(Pred, Ins, Out, Goal),
    with_output_to(string(Text), call(Goal)).

%One crossing for the engine's own counters: statistics/2 inferences and
%cputime, the garbage_collection triple (collections, bytes freed,
%milliseconds spent), and the thread's answer-table bytes, which the
%tabling review found reachable only through the lower-level runtime.
%The Python side reads deltas around a with-block.
metta_py_stats([Inferences, CpuTime, GcCount, GcFreed, GcTimeMs, TableBytes]) :-
    statistics(inferences, Inferences),
    statistics(cputime, CpuTime),
    statistics(garbage_collection, [GcCount, GcFreed, GcTimeMs|_]),
    statistics(table_space_used, TableBytes).

%Run the wrapped call through the engine's user-transaction coordinator:
%dynamic state and enlisted providers finish first, then the buffered atom
%event segment is published. A failure or throw discards that segment with
%the rolled-back writes.
metta_py_atomic(Pred, Ins, Out) :-
    metta_py_wrapped_goal(Pred, Ins, Out, Goal),
    metta_py_execution_policy_goal(atomic, Goal, Scoped),
    call(Scoped).

%Run against a frozen view and discard every change: snapshot/1, the
%what-if reading. The answers return; the space stays as it was. Atom events
%and process-shared State writes are effects a snapshot cannot roll back, so
%the former stay in a discarded observation frame and the latter refuse.
metta_py_speculative(Pred, Ins, Out) :-
    metta_py_wrapped_goal(Pred, Ins, Out, Goal),
    metta_py_execution_policy_goal(speculative, Goal, Scoped),
    call(Scoped).

%The policy constructor is also used by held engines. Wrapping engine_next/2
%on the caller cannot roll back work performed by the engine it resumes; the
%transaction must be part of the engine's suspended Goal so it spans every
%pull and closes with that one execution.
metta_py_execution_policy_goal(none, Goal, Goal) :- !.
metta_py_execution_policy_goal(atomic, Goal, metta_transaction(Goal)) :- !.
metta_py_execution_policy_goal(
    speculative,
    Goal,
    metta_speculate(metta_with_state_write_fence(Goal))) :- !.
metta_py_execution_policy_goal(Mode, _, _) :-
    throw(error(domain_error(metta_py_execution_policy, Mode), none)).

%snapshot/1 is semidet, while a held evaluation is nondeterministic. Collect
%inside the snapshot and replay outside it so speculation preserves every
%answer while all writes still belong to one discarded execution.
metta_py_execution_cursor_goal(speculative, Template, Goal, Controlled) :- !,
    Controlled =
        ( metta_speculate(
              metta_with_state_write_fence(findall(Template, Goal, Bag))),
          member(Template, Bag) ).
metta_py_execution_cursor_goal(Mode, _, Goal, Controlled) :-
    metta_py_execution_policy_goal(Mode, Goal, Controlled).

%A held engine has its own current_output, so redirecting engine_next/2 in the
%caller cannot capture it. The captured engine asks for a fresh memory stream
%before each resume, yields one answer, and asks again before backtracking.
%The caller can then close and read an unbounded memory file without a pipe's
%finite-buffer deadlock.
metta_py_captured_engine(Template, Goal) :-
    setup_call_cleanup(
        current_output(Old),
        ( engine_fetch(Stream0),
          set_output(Stream0),
          call(Goal),
          flush_output,
          engine_yield(Template),
          engine_fetch(Stream),
          set_output(Stream),
          fail ),
        set_output(Old)).

metta_py_open_controlled_cursor([Mode, Capture], Template, Goal, Handle) :-
    metta_py_execution_cursor_goal(Mode, Template, Goal, Controlled),
    (   Capture == @(true)
    ->  engine_create(_, metta_py_captured_engine(Template, Controlled), Engine),
        Handle = metta_py_captured_cursor(Engine)
    ;   engine_create(Template, Controlled, Handle)
    ).

%%%%%%%%%% Lazy cursors %%%%%%%%%%
%
% A query held open as an SWI engine: engine_next pulls one answer per
% call, the goal's join state stays alive inside the engine between
% pulls, and unrelated calls interleave freely, which a raw janus cursor
% forbids (its frames nest LIFO and it dies crossing threads; probed).
% The handle crosses to Python opaquely inside prolog/1, and both
% stepping and destroying work from any thread (probed). The engine runs
% under the logical update view: a fact added after the first pull is not
% seen by this cursor, the snapshot-like enumeration contract.

%Inf bounds the cursor's WHOLE engine work, cumulatively across pulls, and the
%engine publishes the wrapper because a host cannot place this bound correctly
%from outside: an engine counts its own inferences and this thread cannot see
%them, so a limiter around one pull charges the pull loop rather than the
%engine. This file used to read that measurement the other way round and wrap
%each pull, which left the budget inert; metta_host_inference_budget/3 in
%engine/metta/control.pl carries the numbers and the reasoning. Wall bounds
%stay outside, per pull, where idle time between pulls cannot count.
metta_py_cursor_open(Space, PatternsTagged, GuardTagged, VarNames, Limit, Inf,
                     prolog(Engine)) :-
    metta_py_cursor_open_controlled(
        Space, PatternsTagged, GuardTagged, VarNames, Limit, Inf, none,
        prolog(Engine)).

metta_py_cursor_open_controlled(
        Space, PatternsTagged, GuardTagged, VarNames, Limit, Inf, Policy,
        prolog(Engine)) :-
    metta_py_cursor_goal(Space, PatternsTagged, GuardTagged, VarNames, Limit,
                         Row, Goal),
    metta_host_inference_budget(Goal, Inf, Bounded),
    metta_py_open_controlled_cursor(Policy, Row, Bounded, Engine).

metta_py_cursor_goal(Space, PatternsTagged, GuardTagged, VarNames, Limit,
                     Row, Goal) :-
    (   GuardTagged == [], Limit > 0,
        PatternsTagged = [PatternTagged], seam:foreign_space(Space)
    ->  Goal0 = metta_py_bounded_query(Space, PatternTagged, VarNames,
                                       Limit, Row)
    ;   GuardTagged == []
    ->  Goal0 = metta_py_query(Space, PatternsTagged, VarNames, Row)
    ;   Goal0 = metta_py_query_guarded(Space, PatternsTagged, GuardTagged,
                                       VarNames, Row)
    ),
    ( Limit > 0 -> Goal = limit(Limit, Goal0) ; Goal = Goal0 ).

%The annotation-returning cursor is a separate wire so the ordinary hot path
%keeps its one Row. The override lives INSIDE the held engine goal, because
%engine_create defers execution until the first pull. Ordered carriers collect
%and stably sort in the engine; Answers slicing then reads a genuine best
%prefix rather than sorting a Python materialisation [tested:
%extensions/python/tests/ch06_many_answers/test_under_algebra.py;
%commit=c7468b2789746bcf95c4bacc0e2d517ec4d972fa].
metta_py_cursor_open_under(Space, PatternsTagged, GuardTagged, VarNames,
                           Limit, Inf, Algebra, Direction, prolog(Engine)) :-
    metta_py_cursor_open_under_controlled(
        Space, PatternsTagged, GuardTagged, VarNames, Limit, Inf, Algebra,
        Direction, none, prolog(Engine)).

metta_py_cursor_open_under_controlled(
        Space, PatternsTagged, GuardTagged, VarNames, Limit, Inf, Algebra,
        Direction, Policy, prolog(Engine)) :-
    (   Direction \== none
    ->  metta_py_cursor_goal(Space, PatternsTagged, GuardTagged, VarNames, 0,
                             Row, Producer),
        Core = metta_py_ordered_under_query(Space, Direction, Producer, Row, K),
        ( Limit > 0 -> Goal = limit(Limit, Core) ; Goal = Core )
    ;   metta_py_cursor_goal(Space, PatternsTagged, GuardTagged, VarNames,
                             Limit, Row, Producer),
        Goal = metta_py_under_query(Space, Producer, K)
    ),
    Scoped = metta_with_under(Algebra, Goal),
    Encoded = ( Scoped, metta_py_encode(K, KWire) ),
    metta_host_inference_budget(Encoded, Inf, Bounded),
    metta_py_open_controlled_cursor(Policy, [Row, KWire], Bounded, Engine).

metta_py_under_query(Space, Producer, K) :-
    metta_algebra_one(Space, One),
    b_setval('$metta_answer_k', One),
    call(Producer),
    b_getval('$metta_answer_k', K).

metta_py_ordered_under_query(Space, Direction, Producer, Row, K) :-
    findall(K0-Row,
            metta_py_under_query(Space, Producer, K0),
            Pairs),
    metta_py_ordered_pairs(Direction, Pairs, Ordered),
    member(K-Row, Ordered).

metta_py_ordered_pairs(ascending, Pairs, Ordered) :- !,
    sort(1, @=<, Pairs, Ordered).
metta_py_ordered_pairs(_, Pairs, Ordered) :-
    sort(1, @>=, Pairs, Ordered).

%[] is exhaustion, [Row] one answer, so Python needs no sentinel value.
metta_py_cursor_next(Engine, Answer) :-
    ( engine_next(Engine, Row) -> Answer = [Row] ; Answer = [] ).

metta_py_captured_cursor_next(Engine, Answer, Text) :-
    setup_call_cleanup(
        new_memory_file(Memory),
        ( setup_call_cleanup(
              open_memory_file(
                  Memory, write, Stream,
                  [free_on_close(false), encoding(utf8)]),
              ( engine_post(Engine, Stream),
                ( engine_next(Engine, Row)
                -> Answer = [Row]
                ;  Answer = [] ),
                flush_output(Stream) ),
              close(Stream)),
          memory_file_to_string(Memory, Text) ),
        free_memory_file(Memory)).

%The controlled variants normalize both handle kinds to [payload, text]. A
%retained-count replay cursor has no captured engine because its target output
%was already collected during the retaining call; it therefore contributes an
%empty text chunk here.
metta_py_cursor_next_controlled(
        metta_py_captured_cursor(Engine), [Answer, Text]) :- !,
    metta_py_captured_cursor_next(Engine, Answer, Text).
metta_py_cursor_next_controlled(Engine, [Answer, ""]) :-
    metta_py_cursor_next(Engine, Answer).

%Up to Count answers in ONE crossing, which is the whole of the optimisation:
%a pull costs 2.55us of janus crossing against 2.55us of engine work, so a
%cursor that crosses per answer spends half its time in the boundary
%[measured 2026-08-31, extensions/python/tests/ch18_performance/test_cursor_chunking.py].
%A SHORT list is the whole of the exhaustion signal, the same reading the
%remote seat's _pull/2 takes, so nothing here looks ahead: the answer after
%the last one asked for is never computed. Count is what Python asked for and
%Python is what decides it may ask for more than one; see _Chunk in
%_space_objects.py for when that is sound.
metta_py_cursor_chunk(_, Count, []) :-
    Count =< 0, !.
metta_py_cursor_chunk(Engine, Count, Answers) :-
    (   engine_next(Engine, Row)
    ->  Answers = [Row|Rest],
        Left is Count - 1,
        metta_py_cursor_chunk(Engine, Left, Rest)
    ;   Answers = []
    ).

metta_py_captured_cursor_chunk(_, Count, [], []) :-
    Count =< 0, !.
metta_py_captured_cursor_chunk(Engine, Count, Answers, Texts) :-
    metta_py_captured_cursor_next(Engine, Answer, Text),
    (   Answer = [Row]
    ->  Answers = [Row|Rest],
        Texts = [Text|MoreText],
        Left is Count - 1,
        metta_py_captured_cursor_chunk(Engine, Left, Rest, MoreText)
    ;   Answers = [],
        Texts = [Text]
    ).

metta_py_cursor_chunk_controlled(
        metta_py_captured_cursor(Engine), Count, [Answers, Text]) :- !,
    metta_py_captured_cursor_chunk(Engine, Count, Answers, Texts),
    atomics_to_string(Texts, "", Text).
metta_py_cursor_chunk_controlled(Engine, Count, [Answers, ""]) :-
    metta_py_cursor_chunk(Engine, Count, Answers).

%Idempotent close: a second destroy finds no engine and is at peace.
metta_py_cursor_close(metta_py_captured_cursor(Engine)) :- !,
    metta_py_cursor_close(Engine).
metta_py_cursor_close(Engine) :-
    catch(engine_destroy(Engine), error(existence_error(_, _), _), true).

%%%%%%%%%% Profiling %%%%%%%%%%
%
% The statistical profiler around one wrapped call, its terminal report
% swallowed and its data projected to plain values: the summary counters
% and one row per predicate, self-ticks-descending. Sampling is
% statistical, so a short program may carry few samples.
metta_py_profiled(Pred, Ins, [Out, Samples, Ticks, Nodes]) :-
    metta_py_wrapped_goal(Pred, Ins, Out, Goal),
    with_output_to(string(_), profile(Goal, [top(0)])),
    profile_data(Data),
    get_dict(summary, Data, Summary),
    get_dict(samples, Summary, Samples),
    get_dict(ticks, Summary, Ticks),
    get_dict(nodes, Data, NodeDicts),
    %sort/4 keys index compounds, not lists, so the self-ticks ride in
    %front as the key of a pair and are stripped after the sort.
    findall(Self-[PredName, Calls, Redos, Self, Siblings],
            ( member(Node, NodeDicts),
              get_dict(predicate, Node, P), term_string(P, PredName),
              get_dict(call, Node, Calls), get_dict(redo, Node, Redos),
              get_dict(ticks_self, Node, Self),
              get_dict(ticks_siblings, Node, Siblings) ),
            Keyed),
    sort(1, @>=, Keyed, SortedKeyed),
    findall(Row, member(_-Row, SortedKeyed), Nodes).

%What the profiler cannot say about a registered function: which tier put it
%there, and whether the clause index its callers rely on actually exists.
%
%Index quality is read from predicate_property/2 rather than
%library(prolog_jiti)'s jiti_list/1, which prints its table instead of
%answering it. `speedup` is the ratio SWI itself computes for the index it
%chose, so 1.0 means the argument does not discriminate and every call walks
%the clause list. `realised` matters as much: SWI builds an index on first
%need, so an unrealised index is one no call has asked for yet rather than a
%bad one.
%The tier comes from the two engine facts lib_reflect.pl's 'engine-origin'/2
%reads, not from that predicate, which lives in a library the profiler cannot
%require to be loaded. Its builtin and special-form branches are absent here
%on purpose: a profiled name is one an extension registered, and neither of
%those can be.
metta_py_function_shape(Name0, [Tier, Detail, Arities, Determinism]) :-
    ( atom(Name0) -> Name = Name0 ; atom_string(Name, Name0) ),
    (   catch(metta_function_determinism(Name, Mode), _, fail)
    ->  atom_string(Mode, Determinism)
    ;   Determinism = ""
    ),
    (   metta_function_origin(Name, Tier0, Detail0)
    ->  atom_string(Tier0, Tier), metta_py_origin_part(Detail0, Detail)
    ;   fun(Name)
    ->  Tier = "equation",
        ( fun_in(Module, Name) -> atom_string(Module, Detail) ; Detail = "" )
    ;   Tier = "absent", Detail = ""
    ),
    ( fun_in(Home, Name) -> true ; metta_py_module('&self', Home) ),
    spaces:metta_ensure_compiled(Name),
    findall([Arity, Speedup, Realised],
            ( arity(Name, Arity),
              metta_py_index_quality(Home, Name, Arity, Speedup, Realised) ),
            Arities).

metta_py_origin_part(Part, String) :-
    ( atom(Part) -> atom_string(Part, String)
    ; string(Part) -> String = Part
    ; term_string(Part, String) ).

%The best index SWI has for this predicate, or 1.0 for none, which is the
%same number a useless index scores and reads the same way: no discrimination.
metta_py_index_quality(Module, Name, Arity, Speedup, Realised) :-
    functor(Head, Name, Arity),
    (   predicate_property(Module:Head, indexed(Indexes)),
        Indexes \== []
    ->  findall(S-R, ( member(Index, Indexes),
                       get_dict(speedup, Index, S),
                       get_dict(realised, Index, R0),
                       ( R0 == true -> R = @(true) ; R = @(false) ) ), Pairs),
        sort(1, @>=, Pairs, [Speedup-Realised|_])
    ;   Speedup = 1.0, Realised = @(false)
    ).

%%%%%%%%%% Native handles %%%%%%%%%%
%
%The registry that keeps a blob alive while Python holds its reference.
%A dynamic clause referencing the blob is what pins it: SWI's atom
%garbage collector respects clause references, so the blob lives exactly
%as long as its registry entry and release is one retract. Each crossing
%issues a fresh id (two crossings of one blob resolve to the same blob
%either way); flag/3 makes the counter atomic across threads.

:- dynamic metta_py_handle_store/2.

metta_py_handle_keep(Blob, Id) :-
    flag(metta_py_handle_counter, Id, Id + 1),
    assertz(metta_py_handle_store(Id, Blob)).

metta_py_handle_release(Id) :-
    retractall(metta_py_handle_store(Id, _)).

%%%%%%%%%% JSON %%%%%%%%%%
%
%The JSON codec is the engine's own, through the one JSON door in
%engine/json_codec.pl, which is library(json) with a C fast path beside
%it. What this file adds is the janus value conventions: @(true),
%@(false) and @(none) are what janus makes of Python True, False and
%None, and naming them here teaches the reader and writer that exact
%vocabulary, so a Python value crosses, serializes and comes back with
%no Python-side JSON implementation existing anywhere. SWI integers are
%unbounded, which is what makes wide integers exact in both directions
%without any guard.

%Found from THIS file's own directory rather than by counting levels, because
%the two ship at different depths: the shim is extensions/python/metta/shim.pl
%three levels under the engine in a checkout, and metta/shim.pl one level OVER
%it, at metta/_runtime/engine/, in an installed wheel. The old directive spelled
%the checkout's depth, and a use_module that resolves to nothing only WARNS, so
%the wheel loaded, booted, answered arithmetic, and failed every metta._json
%call with Unknown procedure: json_codec_write/3 [measured 2026-08-29 against a
%wheel installed into a fresh venv outside the checkout].
%
%Resolved here rather than through an alias the ENGINE publishes, because this
%file loads engine-free by contract: tests/prolog/suites/host/shim.plt consults
%it and nothing else, so an alias registered by engine/metta.pl does not exist
%in that session and the directive raised
%`source_sink metta_engine(json_codec) does not exist`
%[tested: test_the_shim_reaches_the_engine_by_alias_rather_than_by_depth].
:- prolog_load_context(directory, Here),
   % policy-inventory-exempt: mechanism-internal; reason=the two entries are the only layouts this package ships in, a checkout and an installed wheel, rather than a choice an operator makes; evidence=extensions/python/tests/ch01_getting_started/test_packaging.py:test_the_shim_reaches_the_engine_by_alias_rather_than_by_depth
   (   member(Relative, ['../../../engine/json_codec.pl',
                         '_runtime/engine/json_codec.pl']),
       absolute_file_name(Relative, Codec,
                          [relative_to(Here), access(read), file_errors(fail)])
   ->  use_module(Codec, [ json_codec_read/3, json_codec_write/3 ])
   ;   throw(error(existence_error(source_sink, json_codec),
                   context(shim, 'no engine/json_codec.pl beside this shim')))
   ).

metta_py_json_options([shape(dicts), true(@(true)), false(@(false)),
                       null(@(none))]).

%Encode one janus-shaped value to JSON text. Errors leave through the
%reserved envelope so the Python side raises ValueError and TypeError by
%kind rather than by message text; the refusals themselves, of a
%non-finite number and of a term JSON cannot carry, belong to the codec.
metta_py_json_encode(Value, Text) :-
    catch(metta_py_json_encode_(Value, Text), Error,
          metta_py_json_rethrow(Error)).

metta_py_json_encode_(Value, Text) :-
    metta_py_json_options(Options),
    json_codec_write(Value, Text, Options).

%Decode JSON text to a janus-shaped value. The codec stops after one
%value and refuses a remainder that is not layout, so a second value in
%the same text is an error rather than silently dropped.
%
%This used to pass tag(py) to json_read_dict/3, which does not do what
%its comment claimed. tag/1 names the object KEY whose value becomes the
%dict's tag, so a document with a "py" key lost it: '{"py": "x", "a": 1}'
%decoded to {'a': 1} [measured 2026-08-28]. Nothing needed the option --
%an ordinary object never has that key, so the tag stayed unbound either
%way, and janus makes a Python dict of a tagged and an untagged dict
%alike [tested: test_json_codec_keeps_a_key_named_py].
metta_py_json_decode(Text, Value) :-
    catch(metta_py_json_decode_(Text, Value), Error,
          metta_py_json_rethrow(Error)).

metta_py_json_decode_(Text, Value) :-
    metta_py_json_options(Options),
    json_codec_read(Text, Value, Options).

%Each error class keeps its own clause, so Python raises by kind: a
%value that JSON cannot carry is a ValueError, a term that is not JSON
%data at all is a TypeError, and anything unrecognized stays a raw
%engine error rather than being dressed as one of those.
metta_py_json_rethrow(error(domain_error(finite_number, Culprit), _)) :-
    format(string(Message),
           "JSON cannot carry the non-finite number ~w", [Culprit]),
    metta_py_raise(value, Message).
metta_py_json_rethrow(error(type_error(Type, Culprit), _)) :-
    format(string(Message),
           "JSON cannot carry ~p, which is not a ~w", [Culprit, Type]),
    metta_py_raise(type, Message).
metta_py_json_rethrow(error(domain_error(Domain, Culprit), _)) :-
    format(string(Message),
           "JSON cannot carry ~p, which is not a ~w", [Culprit, Domain]),
    metta_py_raise(type, Message).
metta_py_json_rethrow(error(syntax_error(What), _)) :-
    format(string(Message), "not valid JSON: ~w", [What]),
    metta_py_raise(value, Message).
metta_py_json_rethrow(error(duplicate_key(Key), _)) :-
    format(string(Message), "JSON object repeats the key ~w", [Key]),
    metta_py_raise(value, Message).
metta_py_json_rethrow(Error) :-
    throw(Error).

%%%%%%%%%% Parse and print %%%%%%%%%%

%Read one form into a tagged term, keeping variable names. sread/2 discards the
%name map its own DCG builds; calling sexpr//3 directly keeps it:
metta_py_parse(Source, Tagged) :-
    metta_py_read_form(Source, Term, VarMap),
    metta_py_encode_named(Term, VarMap, Tagged).

%The reader half of metta_py_parse/2, on its own. An evaluation handed source
%text needs the TERM, and reaching it through the wire form costs an encode
%and a decode of a term that never left the engine, on top of the second janus
%crossing Python makes to parse before it evaluates [measured 2026-08-16:
%(structured (pair a b)) cost 516.00 inferences as parse-then-evaluate and
%449.00 read straight to a term].
metta_py_read_form(Source, Term, VarMap) :-
    ( string(Source) -> S = Source ; atom_string(Source, S) ),
    ( sread_with_names(S, Term, VarMap)
      -> true
    ; format(atom(Msg), 'Parse error in form: ~w', [S]),
      metta_py_raise(syntax, Msg) ).

%Registering a token stores the callable itself in the engine's mapping. The
%dynamic clause's Janus blob owns its Python reference, so there is no Python
%registry to synchronize; Prolog's normal clause and blob reclamation owns a
%retired constructor's lifetime.
metta_py_register_token(Pattern, Constructor) :-
    seam:host_object(Constructor),
    metta_host_register_reader_token(Pattern, Constructor).

metta_py_unregister_token(Pattern) :-
    metta_host_unregister_reader_token(Pattern).

%Ownership is established by the live Python object before the cut implicit in
%the caller's first-success seam. Constructors receive the complete lexeme and
%return an Atom wire; shared decoding preserves repeated variables if a custom
%class deliberately constructs them.
seam:host_reader_token_construct(Constructor, Text, Term) :-
    seam:host_object(Constructor),
    catch(py_call(metta_ops:construct_token(Constructor, Text), Wire),
          Error, metta_py_failure(['reader-token', Text], Error)),
    metta_py_decode_shared(Wire, Term, _).

%An evaluation target arrives either as a wire term or, when the caller passed
%source text, as that text. The test is whether it is a wire term, not what
%type the text has: Janus hands a Python str over as an ATOM, so asking
%string/1 sent every source evaluation down the decoder, where it failed and
%findall/3 turned that into an empty answer list indistinguishable from a
%query that truly answered nothing. Reading it here also keeps the variables
%the reader shared by name, which is what the wire round trip was rebuilding.
%Every wire term is exactly two elements, so the shape is decided here in O(1)
%and the decode below is NOT wrapped in the test. Wrapping it, as an earlier
%version did to turn a failed decode into a refusal, left a choice point over
%the whole recursive walk and cost 11% of alpha-unique, whose operation
%decodes one large term: 3,699,768,516 instructions became 4,106,476,179
%[measured 2026-08-16]. That is the same last-call optimisation the plunit
%gate's own choicepoint check exists to catch.
%&self resolves to the evaluation receiver at both input doors. Text uses the
%reader rewrite, gated by a C substring probe so text without &self pays two
%inferences rather than a term walk. A wire target is decoded through the
%receiver-aware decoder above, which substitutes in the decode walk rather than
%walking the complete term again. metta_py_parse/2 has no receiver and still
%reads unpinned, as does stored data: this policy belongs only to execution
%targets.
metta_py_target_term(Space, Target, Term) :-
    metta_py_target_term_bindings(Space, Target, Term, _).

metta_py_target_term_bindings(Space, Target, Term, Bindings) :-
    (   Target = [_, _]
    ->  metta_py_decode_target(Space, Target, Term, Bindings)
    ;   \+ is_list(Target)
    ->  metta_py_read_form(Target, Term0, Bindings),
        (   Space == '&self'
        ->  Term = Term0
        ;   atom(Target), sub_atom(Target, _, _, _, '&self')
        ->  metta_substitute_self(Space, Term0, Term)
        ;   string(Target), sub_string(Target, _, _, _, "&self")
        ->  metta_substitute_self(Space, Term0, Term)
        ;   Term = Term0
        )
    ;   throw(error(domain_error(metta_py_wire_term, Target), none))
    ).

%Plan the same direct or translated goal metta_py_eval/3 will call. Translation
%may populate its ordinary invalidated template cache, but this seam creates no
%space and executes no target goal; ReifiedWorld.eval calls it before allocating
%the discarded receiver. Coverage remains catalog data keyed by the originating
%world context.
metta_py_world_effect_plan(Space, Origin, Target,
                           [Operations, Effect, Coverage]) :-
    metta_py_target_term(Space, Target, Term0),
    metta_py_world_rebase(Term0, Origin, Space, Term),
    metta_py_module(Space, Module),
    metta_world_effect_coverage(Origin, Coverage),
    metta_host_source_effect_plan(
        Module, Term, SourceOperations, SourceEffect),
    (   metta_effect_covered(SourceEffect, Coverage)
    ->  (   metta_py_direct_goal(Module, Term, Goal, _)
        ->  Body0 = Goal
        ;   metta_py_in_module(
                Module,
                ( translator:translate_cached_expr(Term, Goals, _),
                  translator:goals_list_to_conj(Goals, Body0) ))
        ),
        Body = (metta_effect_source_term(Term), Body0),
        metta_host_goal_effect_plan(Module, Body, Operations, Effect)
    ;   Operations = SourceOperations,
        Effect = SourceEffect
    ).

%Replay the immutable program image once and retain the native space. The
%observation segment is discarded and State writes are fenced, just like a
%world evaluation, but the stored clauses remain so every later admission
%question is asked of the frozen program rather than the mutable origin.
metta_py_world_prepare(Space, Origin, AtomWires) :-
    setup_call_cleanup(
        seam:observation_begin,
        metta_with_state_write_fence(
            maplist(metta_py_world_add(Origin, Space), AtomWires)),
        seam:observation_discard).

%The raw image is immutable world data, but materialising its equations may run
%translator rules. Compute that compilation-only join against the module whose
%complete compiled image supplied the atoms. The walk itself never translates.
metta_py_world_image_effect_plan(Space, Origin, AtomWires,
                                 [Operations, Effect, Coverage]) :-
    metta_py_module(Space, Module),
    findall(Row,
            ( member(Wire, AtomWires),
              metta_py_decode_shared(Wire, Term0, _),
              metta_py_world_rebase(Term0, Origin, Space, Term),
              metta_host_source_compile_effect_plan(
                  Module, Term, TermOperations, _),
              member(Row, TermOperations) ),
            RawOperations),
    sort(RawOperations, Operations),
    findall(Class, member([_, Class], Operations), Classes),
    metta_effect_compose(Classes, Effect),
    metta_world_effect_coverage(Origin, Coverage).

%The catalog checks a compensation when its row is written. Recovery checks
%again against the execution space because either callable can be unregistered
%or hidden after that write, and preflight must detect the stale plan before an
%earlier handler changes anything.
metta_py_saga_compensation_callable(Space, Name) :-
    atom(Name),
    metta_py_module(Space, Module),
    metta_ensure_compiled(Name),
    functor(Goal, Name, 2),
    current_predicate(Module:Name/2),
    predicate_property(Module:Goal, visible),
    (   metta_contract_fact([op, Name, 1, _])
    ;   arity(Name, 2)
    ).

%The saga's Python callback is run through the engine transaction owner. The
%two zero-argument notifications happen after the database outcome is known
%but before a post-commit failure is rethrown, so bookkeeping never guesses
%durability from the exception's class.
metta_py_saga_transaction(F, Committed, RolledBack, R) :-
    metta_transaction_notified(
        py_call(F:'__call__'(), R),
        py_call(Committed:'__call__'(), _),
        py_call(RolledBack:'__call__'(), _)).

%A non-host operation may still publish an (effect ...) row. Wrap only those
%reachable predicates for the duration of one saga evaluation. Registered
%Python operations keep their earlier capture point inside dispatch, where an
%effect has already fired even if a later relation candidate is rejected.
metta_py_saga_eval_all(Space, Tagged, SelectHost, ReceiptSink, Answers) :-
    with_mutex('$metta_saga_wrappers',
        ( metta_py_saga_prepare_target(
              Space, Tagged, NativeOperations, HostOperations),
          py_call(SelectHost:'__call__'(HostOperations), _),
          setup_call_cleanup(
              metta_py_saga_capture_begin(
                  Space, NativeOperations, ReceiptSink, Wrapped),
              metta_py_eval_all(Space, Tagged, Answers),
              metta_py_saga_capture_end(Wrapped)) )).

%Compilation can call effect-classified engine predicates such as include/3 to
%publish function metadata. Those are implementation work, not operations the
%forward target performed, and wrapping before the first translation produced
%a spurious `(did include ...)` recovery obligation. Populate the ordinary
%translation cache before installing wrappers, but keep the preparation inside
%the step transaction and the wrapper mutex. Python host calls made by a custom
%translator rule remain captured by the active Python ContextVar.
metta_py_saga_prepare_target(Space, Tagged,
                             NativeOperations, HostOperations) :-
    metta_py_target_term(Space, Tagged, Term),
    metta_py_module(Space, Module),
    metta_host_source_runtime_effect_plan(Module, Term, RuntimeRows, _),
    (   member(['<dynamic-operation>', _], RuntimeRows)
    ->  throw(error(metta_saga_dynamic_operation(Term), none))
    ;   true
    ),
    (   member(['<catalog-policy-mutation>', _], RuntimeRows)
    ->  throw(error(metta_saga_catalog_policy_mutation(Term), none))
    ;   true
    ),
    metta_effect_rank(writesState, Threshold),
    findall(Name,
            ( member([Name, Effect], RuntimeRows),
              metta_effect_rank(Effect, Rank),
              Rank >= Threshold ),
            Names),
    sort(Names, NativeOperations),
    findall(Name,
            ( metta_contract_fact([op, Name, _, _]),
              metta_operation_effect(Name, Effect),
              metta_effect_rank(Effect, Rank),
              Rank >= Threshold ),
            HostNames),
    sort(HostNames, HostOperations),
    (   metta_py_direct_goal(Module, Term, _, _, _)
    ->  true
    ;   metta_py_in_module(Module,
                           translate_cached_expr(Term, _, _))
    ).

:- multifile prolog:error_message//1.
prolog:error_message(metta_saga_dynamic_operation(Term)) -->
    [ 'Saga.run cannot journal dynamic-head target ~p; use a static operation \c
       head so the effect and compensation boundary is known before execution'-
      [Term] ].
prolog:error_message(metta_saga_catalog_policy_mutation(Term)) -->
    [ 'Saga.run refuses target ~p because it mutates &metta policy while \c
       receipt eligibility is frozen; declare effects and compensations \c
       before entering the saga'-[Term] ].

%Install the whole wrapper set or none of it. setup_call_cleanup/3 runs no
%cleanup when its setup raises or fails, so a half-installed set would outlive
%the step that began it and publish `(did ...)` receipts for later work the
%saga never planned. Choosing the predicates before the sink exists keeps a
%module or selection failure from leaving the sink behind either.
metta_py_saga_capture_begin(Space, Operations, ReceiptSink, Wrapped) :-
    metta_py_module(Space, Module),
    findall(Owner:Name/Arity,
            metta_py_saga_effect_predicate(Module, Operations,
                                           Owner, Name, Arity),
            Predicates0),
    sort(Predicates0, Predicates),
    nb_setval('$metta_saga_receipt_sink', ReceiptSink),
    metta_py_saga_wrap_all(Predicates, [], Wrapped).

%Each step's own catch covers only its own installation, so the unwind runs
%exactly once: the levels below have already left their catch when the throw
%passes them. A wrap that merely fails is reported as an error rather than a
%silent failure, because the caller's setup would otherwise fail with the
%earlier predicates still wrapped.
metta_py_saga_wrap_all([], Wrapped, Wrapped).
metta_py_saga_wrap_all([Predicate|Rest], Installed, Wrapped) :-
    catch(( metta_py_saga_wrap(Predicate, One)
          -> true
          ;  throw(error(metta_saga_wrap_failed(Predicate), none))
          ),
          Error,
          ( metta_py_saga_capture_end(Installed), throw(Error) )),
    metta_py_saga_wrap_all(Rest, [One|Installed], Wrapped).

prolog:error_message(metta_saga_wrap_failed(Predicate)) -->
    [ 'Saga.run could not instrument ~p for receipt capture; no wrapper was \c
       left installed'-[Predicate] ].

metta_py_saga_effect_predicate(Module, Operations, Owner, Name, Arity) :-
    memberchk(Name, Operations),
    (   builtin_fun(Name)
    ;   metta_contract_fact([effect, Name, _])
    ),
    metta_operation_effect(Name, Effect),
    metta_effect_rank(Effect, Rank),
    metta_effect_rank(writesState, Threshold),
    Rank >= Threshold,
    \+ metta_contract_fact([op, Name, _, _]),
    (   current_predicate(Module:Name/Arity)
    ;   current_predicate(Name/Arity),
        functor(Visible, Name, Arity),
        predicate_property(Module:Visible, visible)
    ),
    Arity > 0,
    functor(Head, Name, Arity),
    (   predicate_property(Module:Head, imported_from(Imported))
    ->  Owner = Imported
    ;   Owner = Module
    ).

metta_py_saga_wrap(Owner:Name/Arity, Owner:Name/Arity) :-
    functor(Head, Name, Arity),
    Head =.. [_|All],
    append(Args, [Result], All),
    wrap_predicate(Owner:Head, metta_saga_receipt, Wrapped,
                   metta_py_saga_wrapped_call(Name, Args, Result, Wrapped)).

metta_py_saga_wrapped_call(Name, Args, Result, Wrapped) :-
    call(Wrapped),
    (   nb_current('$metta_saga_receipt_sink', Sink)
    ->  metta_py_encode([did, Name, Args, Result], Wire),
        py_call(Sink:'__call__'(Wire), _)
    ;   true
    ).

%Teardown is total. setup_call_cleanup/3 IGNORES a failing cleanup goal
%[measured 2026-08-26: setup_call_cleanup(true, true, fail) succeeds], so a
%forall/2 that stopped at the first predicate somebody else already unwrapped
%would silently leave every later wrapper installed. Retire each one on its
%own and always release the sink.
metta_py_saga_capture_end(Wrapped) :-
    forall(member(Predicate, Wrapped),
           ignore(catch(unwrap_predicate(Predicate, metta_saga_receipt),
                        _, true))),
    (   nb_current('$metta_saga_receipt_sink', _)
    ->  nb_delete('$metta_saga_receipt_sink')
    ;   true
    ).

%Evaluate one already-prepared frozen image. Admission is repeated inside the
%same engine call immediately before execution, closing the replacement race
%between the Python-side before-allocation check and the actual operation.
%Success retains Space as the successor world's exact compiled image; Python
%drops it on refusal or exception.
metta_py_world_eval(Space, Origin, AtomWires, Target,
                    Operations, Effect, Result) :-
    metta_world_effect_coverage(Origin, Coverage),
    (   metta_effect_covered(Effect, Coverage)
    ->  setup_call_cleanup(
            seam:observation_begin,
            metta_with_state_write_fence(
                ( maplist(metta_py_world_add(Origin, Space), AtomWires),
                  metta_py_target_term(Space, Target, Term0),
                  metta_py_world_rebase(Term0, Origin, Space, Term),
                  metta_py_world_eval_answers(Space, Term, Answers),
                  metta_py_world_atoms(Space, Origin, Stored),
                  metta_py_world_image_effect_plan(
                      Space, Origin, Stored,
                      [ImageOperations, ImageEffect, _]),
                  Result = [admitted, Answers, Stored,
                            ImageOperations, ImageEffect] )),
            seam:observation_discard)
    ;   Result = [refused, Operations, Effect, Coverage]
    ).

metta_py_world_add(Origin, Space, Wire) :-
    metta_py_decode_shared(Wire, Term0, _),
    metta_py_world_rebase(Term0, Origin, Space, Term),
    'add-atom'(Space, Term, _).

metta_py_world_eval_answers(Space, Term, Answers) :-
    findall(E, metta_py_eval_term_bounded(Space, Term, E), Found),
    (   Found == [], metta_py_preserve_unmatched(Space, Term, Original)
    ->  Answers = [Original]
    ;   Answers = Found
    ).

metta_py_world_atoms(Space, Origin, Encoded) :-
    findall(Wire,
            ( 'get-atoms'(Space, Atom0),
              metta_py_world_rebase(Atom0, Space, Origin, Atom),
              metta_py_encode(Atom, Wire) ),
            Encoded).

%A provider-owned world commit has already landed and journaled its durable
%delta. Decode the complete report before opening an observation frame, then
%publish remove-before-add in the same ordering as the native commit door.
%Callbacks therefore see the complete provider state, and a callback failure
%is post-commit just as it is for a native transaction.
metta_py_publish_world_diff(Space, RemovedWires, AddedWires) :-
    maplist(metta_py_decode_world_atom, RemovedWires, Removed),
    maplist(metta_py_decode_world_atom, AddedWires, Added),
    seam:observation_begin,
    maplist(metta_py_world_observe(removed, Space), Removed),
    maplist(metta_py_world_observe(added, Space), Added),
    seam:observation_commit.

metta_py_decode_world_atom(Wire, Atom) :-
    metta_py_decode_shared(Wire, Atom, _).

metta_py_world_observe(Action, Space, Atom) :-
    seam:observe(Action, Space, Atom).

metta_py_world_rebase(Term0, From, To, Term) :-
    (   Term0 == From
    ->  Term = To
    ;   Term0 == '&self'
    ->  Term = To
    ;   var(Term0)
    ->  Term = Term0
    ;   atomic(Term0)
    ->  Term = Term0
    ;   is_list(Term0)
    ->  maplist(metta_py_world_rebase_(From, To), Term0, Term)
    ;   Term = Term0
    ).

metta_py_world_rebase_(From, To, Term0, Term) :-
    metta_py_world_rebase(Term0, From, To, Term).

%Print a tagged term the way MeTTa prints it:
%A symbol spelled like a boolean has no faithful text form: the engine's
%term for it IS the boolean (Prolog true/false), so only the wire tag still
%knows the caller meant a symbol, and text written here would read back as
%the boolean. Refuse at this door, where the tag is visible, with the
%writer's own refusal shape; the engine-side writer cannot make this
%distinction because both kinds are one atom there.
metta_py_swrite(Tagged, String) :-
    (   metta_py_wire_boolean_symbol(Tagged, Bad)
    ->  throw(error(metta_unwritable_text(Bad),
                    context(swrite/2,
                            'printed form would read back as a different value')))
    ;   metta_py_decode_shared(Tagged, Term, _),
        swrite(Term, String)
    ).

%Janus hands the wire's leaves over as atoms while Prolog-built wrappers use
%strings, so both spellings of a tag are accepted here.
metta_py_wire_boolean_symbol([Tag, Name], Bad) :-
    metta_py_wire_tag(Tag, s),
    (   atom(Name) -> Bad = Name ; string(Name), atom_string(Bad, Name) ),
    % policy-inventory-exempt: codec-version-identity; reason=these four spellings are how the wire encodes a boolean, so a symbol carrying one would print as text that reads back as a boolean rather than as itself; evidence=extensions/python/metta/shim.pl:metta_py_wire_boolean_symbol/2
    memberchk(Bad, [true, false, 'True', 'False']).
metta_py_wire_boolean_symbol([Tag, Items], Bad) :-
    metta_py_wire_tag(Tag, e),
    is_list(Items),
    member(Item, Items),
    metta_py_wire_boolean_symbol(Item, Bad),
    !.

metta_py_wire_tag(Tag, Wanted) :-
    (   atom(Tag) -> Tag == Wanted
    ;   string(Tag), atom_string(Wanted, Tag)
    ).

%%%%%%%%%% Space operations %%%%%%%%%%
%
% Writes go through MeTTa's own 'add-atom'/3 and 'remove-atom'/3, so an
% equation takes the engine's function path (register_fun, arity,
% translate_clause, invalidation) exactly as one read from a file does, and
% removal keeps the engine's own semantics (a plain atom removal is retractall).

metta_py_add(Space, Tagged) :-
    metta_py_decode_shared(Tagged, Term, _),
    'add-atom'(Space, Term, _).

%Python operation registration owns the declaration it retains. Ordinary
%source loading deliberately treats an identical declaration as an idempotent
%warning, but adopting somebody else's row here would let unregister remove
%that source-owned declaration. Probe and add through this shim's public doors
%so the ownership distinction does not leak into the engine's general add API.
metta_py_add_strict_declaration(Space, Tagged) :-
    (   metta_py_contains(Space, Tagged)
    ->  metta_py_decode_shared(Tagged, Term, _),
        throw(error(metta_duplicate_declaration(Space, Term, Term), none))
    ;   metta_py_add(Space, Tagged)
    ).

metta_py_decode_for_add(Tagged, Term) :-
    metta_py_decode_shared(Tagged, Term, _).

%The engine decides how a batch crosses. This chose for MORK itself and so
%bypassed metta_add_atoms/2 entirely, which is where the rule that a batch may
%not skip per-atom work lives: an equation added to a MORK space alongside any
%other atom was stored inert [measured 2026-08-16].
metta_py_add_many(Space, TaggedList) :-
    maplist(metta_py_decode_for_add, TaggedList, Terms),
    metta_add_atoms(Space, Terms).

%ONE LAW, ONE IMPLEMENTATION. Every one-occurrence door in this seat asks the
%engine's own 'subtract-atom'/3 rather than the private service beneath it, so
%the unbound-term guard is written once and remove(), its variadic face, the
%`-=` operator and transfer cannot disagree about what one occurrence means.
%Reaching past the head is what made them disagree: remove(V.x) read the
%variable as the whole space and DRAINED it while answering True, and
%transfer(V.x, to=b) died on an opaque instantiation error, its transaction
%rolling the source back [measured 2026-09-01].
metta_py_subtract(Space, Term, Verdict) :-
    'subtract-atom'(Space, Term, Result),
    (   Result == true
    ->  Verdict = true
    ;   Result == false
    ->  Verdict = false
    ;   metta_py_subtract_refusal(Result)
    ).

%A refusal is the engine's error DATA, and a Python door must not answer it as
%if it were a verdict: a caller testing `if space.remove(x)` would read the
%(Error ...) atom as truthy and conclude the removal happened.
metta_py_subtract_refusal(['Error', _, Reason]) :-
    !,
    metta_py_raise(value, Reason).
metta_py_subtract_refusal(Result) :-
    format(string(Message),
           "subtract-atom answered ~p, which is neither a verdict nor a refusal",
           [Result]),
    metta_py_raise(value, Message).

metta_py_remove(Space, Tagged, Removed) :-
    metta_py_decode_shared(Tagged, Term, _),
    metta_py_subtract(Space, Term, Verdict),
    metta_py_encode(Verdict, Removed).

%The OTHER documented mode of the same door, named rather than hidden behind a
%var check three layers down: remove() given a bare variable takes everything,
%the reading a multiset space gives an atom that unifies with all of them, each
%leaving by its own proper path so equations and their compiled clauses go too.
%It is a different operation from subtracting one occurrence, so it is a
%different predicate, and 'subtract-atom' can keep refusing the unbound term
%that would otherwise mean two opposite things in one head.
metta_py_remove_everything(Space, Removed) :-
    metta_host_remove_reported(Space, _Anything, Verdict),
    metta_py_encode(Verdict, Removed).

%One crossing MOVES a batch: each wire removes one reported occurrence from
%the source and, when found, lands in the target, all inside one engine
%transaction, so a mid-move failure rolls every side back and an atom is
%never lost between spaces. The count answers how many moved; an absent
%member moves nothing and counts nothing, the found-reporting grain of the
%one-occurrence remove door.
metta_py_transfer(From, To, Wires, Count) :-
    metta_transaction(metta_py_transfer_each(Wires, From, To, 0, Count)).

metta_py_transfer_each([], _, _, Count, Count).
metta_py_transfer_each([Wire|Wires], From, To, Count0, Count) :-
    metta_py_decode_shared(Wire, Term, _),
    metta_py_subtract(From, Term, Verdict),
    (   Verdict == true
    ->  'add-atom'(To, Term, _),
        Count1 is Count0 + 1
    ;   Count1 = Count0
    ),
    metta_py_transfer_each(Wires, From, To, Count1, Count).

%One crossing evaluates a BATCH of targets, answering one encoded group per
%target in order: run()'s own grouping carried to the eval door, which is
%how evaluation batches. The using form applies ONE binding scope to every
%target, the call-level reading a bind() block already has.
metta_py_eval_many_all(Space, Targets, Groups) :-
    findall(Group,
            ( member(Tagged, Targets),
              findall(E, metta_py_eval(Space, Tagged, E), Group) ),
            Groups).

metta_py_eval_many_using_all(Space, Targets, Pairs, Groups) :-
    findall(Group,
            ( member(Tagged, Targets),
              metta_py_eval_using_all(Space, Tagged, Pairs, Group) ),
            Groups).

%One crossing REMOVES a batch, one reported occurrence each, inside one
%transaction; the count answers how many were found, remove's own grain.
metta_py_remove_many(Space, Wires, Count) :-
    metta_transaction(metta_py_remove_each(Wires, Space, 0, Count)).

metta_py_remove_each([], _, Count, Count).
metta_py_remove_each([Wire|Wires], Space, Count0, Count) :-
    metta_py_decode_shared(Wire, Term, _),
    metta_py_subtract(Space, Term, Verdict),
    ( Verdict == true -> Count1 is Count0 + 1 ; Count1 = Count0 ),
    metta_py_remove_each(Wires, Space, Count1, Count).

%The `del space[pattern]` door: remove-atom drains EVERY unifying occurrence
%in ONE crossing, upstream's law, and the verdict says whether anything was
%there so the caller can raise KeyError the way `del d[k]` does. The door used
%to drain by repeating remove(), one crossing per removed atom; asking the
%engine's own drain makes it one crossing for the whole pattern.
metta_py_drain(Space, Wire, Removed) :-
    metta_py_decode_shared(Wire, Term, _),
    %The ask runs on a COPY for the reason the engine's own removal does: a
    %probe that instantiated the caller's pattern would turn the drain that
    %follows into a search for the probe's answer, taking one stored atom and
    %leaving its siblings.
    copy_term(Term, Probe),
    (   match_stored(Space, Probe, Probe, _)
    ->  Existed = true
    ;   Existed = false
    ),
    'remove-atom'(Space, Term, _),
    metta_py_encode(Existed, Removed).

metta_py_atoms(Space, Encoded) :-
    findall(E, ('get-atoms'(Space, P), metta_py_encode(P, E)), Encoded).

%The tracer answers terms; putting them on the wire is the shim's job, as
%it is for every other atom leaving the engine. A call event has no answer
%field at all, rather than a value standing in for its absence.
metta_py_trace(Source, Space, Max, Encoded) :-
    metta_trace_source(Source, Space, Max, Events),
    maplist(metta_py_trace_event, Events, Encoded).

metta_py_trace_event(event(Depth, call, Term, _, Names),
                     [Depth, "call", EncodedTerm]) :- !,
    metta_py_encode_named(Term, Names, EncodedTerm).
metta_py_trace_event(event(Depth, exit, Term, Answer, Names),
                     [Depth, "exit", EncodedTerm, EncodedAnswer]) :-
    metta_py_encode_named(Term, Names, EncodedTerm),
    metta_py_encode_named(Answer, Names, EncodedAnswer).

%Bulk cleanup of the reflection facts describing one space: every
%(defined <Space> _) atom in &metta goes through the engine's own removal
%funnel (hooks fire per fact), but in ONE crossing from Python; the
%per-fact crossing measured 10,000 calls and 64ms for 10,000 defines.
metta_py_reflect_clear_defined(SpaceName) :-
    ( atom(SpaceName) -> S = SpaceName ; atom_string(S, SpaceName) ),
    metta_host_clear_defined(S).

metta_py_count(Space, Count) :-
    aggregate_all(count, 'get-atoms'(Space, _), Count).

metta_py_space_names(Names) :-
    metta_space_names(Names).

%The live Python exception object inside a python_error term, so the
%boundary can re-raise the ORIGINAL, structured fields intact, instead of
%a flattened transcript of it. Handing Obj back through janus converts
%the blob to the very object the callback raised.
metta_py_original_exception(error(python_error(_, Obj), _), Obj) :-
    py_is_object(Obj).

%Run a Python callable inside one engine transaction: the same
%metta_transaction/1 the MeTTa (transaction ...) form compiles to, so
%foreign-space enlistment and nesting behave identically from both
%languages. py_call re-enters Python on the calling thread; an exception
%there aborts the transaction, every dynamic change rolls back, and the
%Python side re-raises the original.
metta_py_transaction(F, R) :-
    metta_transaction(py_call(F:'__call__'(), R)).

metta_py_contains(Space, Tagged) :-
    metta_py_decode_shared(Tagged, Pattern, _),
    match(Space, Pattern, found, found), !.

%Clear a space: a Python provider owns its storage, so it clears (or
%refuses, loudly, when it cannot); everything else, Prolog providers and
%native spaces with their announce-when-watched and tabling-death rules,
%is the engine's metta_host_clear_space/1.
metta_py_clear_for_release(Space) :-
    (   metta_py_foreign(Space)
    ->  atom_string(Space, SpaceStr),
        py_call(metta_ops:foreign_clear(SpaceStr), _)
    ;   metta_clear_space_for_release(Space)
    ).

metta_py_clear(Space) :-
    metta_py_foreign(Space), !,
    atom_string(Space, SpaceStr),
    py_call(metta_ops:foreign_clear(SpaceStr), _).
metta_py_clear(Space) :-
    metta_host_clear_space(Space).

%The host's clause of the hooks-idle ownership seams: the engine hands the
%handler census in as clause references, and this side answers from the one
%reference it installed, the subscription bridge, without consulting any
%engine internals. Idle means this unwatched space's only handler is the
%bridge itself.
:- multifile seam:host_add_hooks_idle/2.
seam:host_add_hooks_idle(Space, [OnlyRef]) :-
    \+ metta_py_subscribed_space(Space),
    metta_py_subscription_hook_ref(added, OnlyRef).

:- multifile seam:host_remove_hooks_idle/2.
seam:host_remove_hooks_idle(Space, [OnlyRef]) :-
    \+ metta_py_subscribed_space(Space),
    metta_py_subscription_hook_ref(removed, OnlyRef).

%Fresh space names for callers that want an anonymous space. The & prefix is
%load-bearing: 'is-space' recognises it, and a $ name would read as a variable.
%A released name goes back into a pool and is handed out again, because a
%space's module cannot be destroyed (SWI keeps modules for the process), so
%reuse is what keeps a churn of short-lived spaces from growing the module
%table forever. A candidate that already holds anything, foreign
%registrations included, is skipped: fresh means fresh.
:- dynamic metta_py_space_counter/1.
:- dynamic metta_py_free_space/1.
metta_py_space_counter(0).

%A SPACE THIS DOOR HANDS OUT IS ONE, with nothing written to it, which is the
%property 'new-space'/1 has and the arbiter requires: (chain (new-space) $s
%(get-type $s)) is SpaceType [source: engine/metta/control.pl, 'new-space'/1
%and its LeaTTa citation]. Minting only the NAME left metta.space() answering
%a handle whose get-type was %Undefined% and whose metatype was Symbol, so it
%crossed the wire as an ordinary symbol and came home as one [measured
%2026-08-27].
metta_py_new_space(Name) :-
    metta_py_fresh_space_name(Name),
    ensure_native_storage_module(Name, _).

%A pooled name is a name that WAS free, not one that still is: a handle that
%outlives its context writes to the released name again and revives it, so the
%pool is scanned rather than trusted and a revived entry is dropped from it.
%The owner that revived it pools it again when it releases it
%[tested test_a_second_context_does_not_reuse_a_revived_space_name].
metta_py_fresh_space_name(Name) :-
    (   retract(metta_py_free_space(Candidate)),
        metta_py_space_untouched(Candidate)
    ->  Name = Candidate
    ;   metta_py_next_space(Name) ).

%The three model declarations create the storage THEMSELVES and refuse a child
%that has been used already (space_parent_child_used/1 reads exactly the
%storage cache ensure_native_storage_module/2 writes), so these take the name
%and let the declaration create it.
%
%Each is written ONCE, taking the name, and the anonymous door below is "mint a
%fresh name, then declare". The engine never required the name to be anonymous:
%metta_declare_restricted_space/2 and metta_declare_space_parent/2 validate
%with metta_require_space_name/2 and accept any space name. Only the Python
%door required it, and only because the mint and the declaration were written
%as one predicate per model with no way to supply the name
%[engine/spaces/lifecycle.pl:764,870].
%ONE declaration door, with the model as its first argument, because the three
%models differ only in which engine declaration they reach: the name check, the
%argument decoding and the failure handling are identical for all of them.
%Three mint predicates and three declare predicates for that is five copies of
%one shape.
metta_py_declare_space(inherits, Name0, Parent0) :-
    metta_py_space_atom(Name0, Name),
    metta_py_space_atom(Parent0, Parent),
    metta_declare_space_parent(Name, Parent).
%A context's sibling space: the home supplies its EQUATION tier only, the
%narrow relation engine/spaces/lifecycle.pl documents, so the space's atoms
%stay its own and conjunctive matching keeps the direct native path.
metta_py_declare_space(scoped, Name0, Home0) :-
    metta_py_space_atom(Name0, Name),
    metta_py_space_atom(Home0, Home),
    metta_declare_space_equation_home(Name, Home).
metta_py_declare_space(restricted, Name0, Grants0) :-
    metta_py_space_atom(Name0, Name),
    maplist(metta_py_space_capability, Grants0, Grants),
    metta_declare_restricted_space(Name, Grants).

metta_py_space_atom(Space0, Space) :-
    ( atom(Space0) -> Space = Space0 ; atom_string(Space, Space0) ).

%The anonymous door is that door with a fresh name in front of it. A refusal
%returns the name to the anonymous pool, so a rejected request leaks no
%allocation [tested: test_restricted_constructor_validation_is_eager].
metta_py_new_modelled_space(Model, Argument, Name) :-
    metta_py_fresh_space_name(Name),
    catch(metta_py_declare_space(Model, Name, Argument), Error,
          ( metta_py_pool_space(Name), throw(Error) )).

metta_py_open_atom_space(NameWire, Space) :-
    metta_py_decode_shared(NameWire, Space, _),
    metta_declare_parametric_space(Space).

metta_py_space_capability(Capability, Capability) :- atom(Capability), !.
metta_py_space_capability(Capability0, Capability) :-
    atom_string(Capability, Capability0).

metta_py_next_space(Name) :-
    retract(metta_py_space_counter(N)),
    N1 is N + 1,
    assertz(metta_py_space_counter(N1)),
    atom_concat('&pyspace_', N1, Candidate),
    ( metta_py_space_untouched(Candidate)
      -> Name = Candidate
    ; metta_py_next_space(Name) ).

%The same question engine/spaces/lifecycle.pl asks before it declares a
%parent or a restriction, asked of the one authority rather than restated:
%a space with an execution module and no atom is used, and handing out its
%name raises metta_space_parent_after_use at the declaration instead
%[tested test_a_second_context_does_not_reuse_a_revived_space_name,
%test_a_recycled_space_name_inherits_no_clauses_from_its_past_life].
metta_py_space_untouched(Name) :-
    \+ metta_py_foreign(Name),
    \+ metta_host_stored(Name, _),
    \+ spaces:space_parent_child_used(Name).

metta_py_pool_space(Name) :-
    ( metta_py_free_space(Name) -> true ; assertz(metta_py_free_space(Name)) ).

metta_py_space_releasable(Name0) :-
    ( atom(Name0) -> Name = Name0
    ; string(Name0) -> atom_string(Name, Name0)
    ; Name = Name0 ),
    metta_assert_space_releasable(Name).

% Drop a named life without putting its public name in the anonymous pool.
metta_py_drop_space(Name0) :-
    ( atom(Name0) -> Name = Name0
    ; string(Name0) -> atom_string(Name, Name0)
    ; Name = Name0 ),
    metta_release_space(Name).

% Release an anonymous life: drop first, then pool the minted atom name.
metta_py_release_space(Name0) :-
    ( atom(Name0) -> Name = Name0
    ; string(Name0) -> atom_string(Name, Name0)
    ; Name = Name0 ),
    metta_py_drop_space(Name),
    ( atom(Name) -> metta_py_pool_space(Name) ; true ).

%%%%%%%%%% Query %%%%%%%%%%
%
% A query is a list of patterns run as one conjunction through the engine's own
% match/4, its native [','|Patterns] form, so joins are the matcher's joins.
% VarNames selects which variables come back, as one row per answer.

metta_py_query(Space, PatternsTagged, VarNames, Row) :-
    VarNames = [
        _, _, _, _, _, _, _, _,
        _, _, _, _, _, _, _, _,
        _, _, _, _, _, _, _, _,
        _, _, _, _, _, _, _, _,
        _, _, _, _, _, _, _, _,
        _, _, _, _, _, _, _, _,
        _, _, _, _, _, _, _, _,
        _, _, _, _, _, _, _, _ | _
    ],
    !,
    metta_py_decode_indexed(["e", PatternsTagged], Patterns, Bindings),
    metta_py_prepare_patterns(Patterns, PlainPatterns, Modifiers, Segments),
    metta_py_match_goal(Segments, Space, PlainPatterns, Goal),
    (   Modifiers == []
    ->  call(Goal)
    ;   call(Goal), metta_py_call_modifiers(Modifiers)
    ),
    metta_py_row(VarNames, Bindings, Row).

metta_py_query(Space, PatternsTagged, VarNames, Row) :-
    metta_py_query_match(Space, PatternsTagged, Bindings),
    metta_py_row(VarNames, Bindings, Row).

metta_py_query_match(Space, PatternsTagged, Bindings) :-
    metta_py_decode_shared(["e", PatternsTagged], Patterns, Bindings),
    metta_py_prepare_patterns(Patterns, PlainPatterns, Modifiers, Segments),
    metta_py_match_goal(Segments, Space, PlainPatterns, Goal),
    %Choose before the nondeterministic match. Calling the empty modifier
    %walker after Goal would call it once for every answer row.
    (   Modifiers == []
    ->  call(Goal)
    ;   call(Goal), metta_py_call_modifiers(Modifiers)
    ).

%A path marker occupies the root handle's position while Python builds the
%pattern. Before matching, it becomes one fresh variable and its structural
%work becomes a post-match goal. The engine therefore joins the opaque handle
%like any stored value and Python sees only the named segments, never an eager
%projection of the object graph.
:- multifile seam:pattern_modifier/3.
seam:pattern_modifier([PathAt, [SegmentsHead|Segments], Target], Root,
                 metta_py_path_guard(Root, Segments, Target)) :-
    %Both markers are read nonvar-then-==, the same reading colon_expression/1
    %uses, because a LITERAL in the head unifies with an unbound head instead
    %of rejecting it: an ordinary three-element pattern whose head is a
    %variable was compiled as a lazy path and raised `invalid lazy path
    %segment` out of paths.py [measured 2026-08-21, hypothesis
    %SpaceStateMachine].
    nonvar(PathAt), PathAt == 'path-at',
    nonvar(SegmentsHead), SegmentsHead == segments,
    !.

metta_py_prepare_patterns(Patterns, PlainPatterns, Modifiers, Segments) :-
    lift_pattern_modifiers(Patterns, PlainPatterns, Modifiers, Segments).

metta_py_call_modifiers([]).
metta_py_call_modifiers([Modifier|Modifiers]) :-
    call(Modifier),
    metta_py_call_modifiers(Modifiers).

metta_py_path_guard(Root, Segments, Target) :-
    nonvar(Root),
    py_call(metta_ops:path_begin(Root), Cursor),
    metta_py_path_steps(Cursor, Segments),
    py_call(metta_ops:path_value(Cursor), ValueWire),
    metta_py_decode_shared(ValueWire, Value, _),
    unify_with_occurs_check(Target, Value).

metta_py_path_steps(_, []).
metta_py_path_steps(Cursor, [Segment|Segments]) :-
    metta_py_encode(Segment, SegmentWire),
    py_call(metta_ops:path_step(Cursor, SegmentWire), Answer),
    Answer == @(true),
    metta_py_path_steps(Cursor, Segments).

%The gap-pattern decision arrives from the walk that already lifted the
%modifiers, so the question costs no inference of its own, and the answer sits
%in the FIRST argument, where SWI's clause index decides it: a query with no
%sequence variable resolves to the same one goal construction it always did
%[measured 2026-08-24: query-2k-rows unchanged at its pinned count]. A gap
%pattern is parsed and classified at the ask instead of at compile time,
%because a host built it rather than wrote it.
metta_py_match_goal(false, Space, [P], match(Space, P, answered, answered)) :- !.
metta_py_match_goal(false, Space, Ps,
                    match(Space, [','|Ps], answered, answered)).
metta_py_match_goal(true, Space, [P],
                    match(Space, Asked, answered, answered)) :- !,
    metta_seq_query_plan(P, Asked).
metta_py_match_goal(true, Space, Ps, match(Space, Asked, answered, answered)) :-
    metta_seq_query_plan([','|Ps], Asked).

metta_py_query_all(Space, PatternsTagged, VarNames, Rows) :-
    findall(Row, metta_py_query(Space, PatternsTagged, VarNames, Row), Rows).

%Count without constructing, encoding, or crossing caller rows. The count-only
%match cores retain shared pattern/guard bindings but skip metta_py_row/3, so
%answers whose terms grow with input depth stay linear instead of paying to
%walk every bound term again [tested:
%test_counting_inference_growth_is_linear_when_answers_grow_in_depth;
%commit=c7468b2789746bcf95c4bacc0e2d517ec4d972fa]. GuardTagged=[] selects the unguarded query, and Limit=0
%means unbounded, matching the eager query doors.
metta_py_query_count(Space, PatternsTagged, GuardTagged, _VarNames, Limit, Count) :-
    (   GuardTagged == [], Limit > 0,
        PatternsTagged = [PatternTagged], seam:foreign_space(Space)
    ->  Query = metta_py_bounded_match(Space, PatternTagged, Limit, _)
    ;   GuardTagged == []
    ->  Query = metta_py_query_match(Space, PatternsTagged, _)
    ;   Query = metta_py_query_guarded_match(Space, PatternsTagged,
                                             GuardTagged, _)
    ),
    (   Limit > 0
    ->  aggregate_all(count, limit(Limit, Query), Count)
    ;   aggregate_all(count, Query, Count)
    ).

%Answers may ask for a length hint before it opens its row cursor. Repeating a
%foreign provider, a path modifier, or an effect-bearing guard would make that
%hint observable, so the engine's shared effect walk admits only the ordinary
%native match with no modifier and a repeatable guard. [] tells Python to
%materialize its one existing cursor instead.
metta_py_query_count_if_repeatable(
        Space, PatternsTagged, GuardTagged, VarNames, Limit, Answer) :-
    (   metta_py_query_repeatable(Space, PatternsTagged, GuardTagged)
    ->  metta_py_query_count(
            Space, PatternsTagged, GuardTagged, VarNames, Limit, Count),
        Answer = [Count]
    ;   Answer = []
    ).

metta_py_query_repeatable(Space, PatternsTagged, GuardTagged) :-
    catch_recover(
        (   \+ seam:foreign_space(Space),
            (   GuardTagged == []
            ->  metta_py_decode_shared(
                    ["e", PatternsTagged], Patterns, _),
                Guard = true
            ;   metta_py_decode_shared(
                    ["e", [GuardTagged | PatternsTagged]],
                    [Guard | Patterns], _)
            ),
            metta_py_prepare_patterns(Patterns, _, Modifiers, _),
            Modifiers == [],
            (   GuardTagged == []
            ->  true
            ;   metta_py_module(Space, Module),
                metta_py_in_module(
                    Module,
                    ( translate_expr(Guard, Goals, _),
                      goals_list_to_conj(Goals, Body) )),
                metta_host_goal_repeatable(Module, Body)
            )
        ),
        fail).

metta_py_query_count_under(Space, PatternsTagged, GuardTagged, VarNames,
                           Limit, Algebra, Count) :-
    metta_with_under(
        Algebra,
        metta_py_query_count(Space, PatternsTagged, GuardTagged, VarNames,
                             Limit, Count)).

%The generic tagged facts and rules remain ordinary atoms. Counting is their
%semiring homomorphism that maps every source and rule coefficient to one, so
%the engine enumerates proof trees and aggregate_all/3 keeps the bag cardinality
%without returning any tree or row to Python [tested:
%test_tagged_derivations_flow_through_match_and_reinterpret_without_requery;
%commit=c7468b2789746bcf95c4bacc0e2d517ec4d972fa].
metta_py_has_tagged_program(Space, Target, Has) :-
    metta_py_eval_target(Space, Target, [], Query, _),
    (   once(( 'get-atoms'(Space, Atom),
               copy_term(Atom, Stored),
               metta_py_tagged_conclusion(Stored, Conclusion),
               unifiable(Query, Conclusion, _) ))
    ->  Has = true
    ;   Has = false
    ).

metta_py_tagged_conclusion([fact, _Tag, Proposition], Proposition).
metta_py_tagged_conclusion([rule, _Tag, Head, [premises|_]], Head).

metta_py_tagged_count(Space, Target, MaxDepth, Limit, Count) :-
    metta_py_eval_target(Space, Target, [], Query, _),
    findall(Atom, 'get-atoms'(Space, Atom), Atoms),
    Goal = metta_py_tagged_prove(Atoms, Query, MaxDepth),
    (   Limit > 0
    ->  aggregate_all(count, limit(Limit, Goal), Count)
    ;   aggregate_all(count, Goal, Count)
    ).

metta_py_tagged_prove(Atoms, Query, _) :-
    member(Stored, Atoms),
    copy_term(Stored, [fact, _Tag, Proposition]),
    unify_with_occurs_check(Query, Proposition).
metta_py_tagged_prove(Atoms, Query, Depth) :-
    Depth > 0,
    member(Stored, Atoms),
    copy_term(Stored, [rule, _Tag, Head, [premises|Premises]]),
    unify_with_occurs_check(Query, Head),
    NextDepth is Depth - 1,
    metta_py_tagged_premises(Premises, Atoms, NextDepth),
    ground(Head).

metta_py_tagged_premises([], _, _).
metta_py_tagged_premises([Premise|Premises], Atoms, Depth) :-
    metta_py_tagged_prove(Atoms, Premise, Depth),
    metta_py_tagged_premises(Premises, Atoms, Depth).

%The seam's own decision for this query, shown without running it, is the
%engine's metta_host_explain_match/3; this renders its term report as the
%wire shape, classes to strings and origin terms to prose
%[tested test_explain_reflects_the_plan].
metta_py_explain(Space, PatternsTagged, Report) :-
    metta_py_decode_shared(["e", PatternsTagged], Patterns, _),
    metta_host_explain_match(Space, Patterns, Explained),
    metta_py_render_explain(Explained, Report).

metta_py_render_explain(explain(stored, _, _, _), ["stored", [], [], []]).
metta_py_render_explain(explain(refused, [Entry], _, _),
                        ["refused", [EText], [], []]) :-
    swrite(Entry, EText).
metta_py_render_explain(explain(foreign, Classes, ClaimedIdx, RestIdx),
                        ["foreign", Rendered, ClaimedIdx, RestIdx]) :-
    maplist(metta_py_render_class, Classes, Rendered).

metta_py_render_class(class(ClassAtom, Origin), [Class, OriginText]) :-
    atom_string(ClassAtom, Class),
    metta_py_render_origin(Origin, OriginText).

metta_py_render_origin(declared(Entry, Fidelity, Det), Text) :-
    swrite(Entry, EText),
    ( var(Det) -> DetText = unstated ; DetText = Det ),
    format(string(Text), "declared: (handles ~w ~w ~w)",
           [EText, Fidelity, DetText]).
metta_py_render_origin(provider, "the provider's own pushdown method").
metta_py_render_origin(unclaimed,
                       "unclaimed; silence is inexact and candidates re-unify").
metta_py_render_origin(refused(Refusing), Text) :-
    swrite(Refusing, RText),
    format(string(Text), "the declared entry ~w answers Refuse", [RText]).

%A query with a guard and a bound: the guard decodes IN THE SAME variable
%scope as the patterns, so $age in both is one variable; after the match
%joins, the guard evaluates in the space's module and must answer true.
%Limit 0 means every answer.
%The guard translates ONCE, before the match enumerates: its variables are
%the same Prolog variables the patterns bind, so each answer runs the
%already-compiled goals against its own bindings, and backtracking retracts
%them. Translating inside the enumeration would recompile per candidate
%row, which measured at ~500ms per 2000-row guarded query.
metta_py_query_guarded(Space, PatternsTagged, GuardTagged, VarNames, Row) :-
    VarNames = [
        _, _, _, _, _, _, _, _,
        _, _, _, _, _, _, _, _,
        _, _, _, _, _, _, _, _,
        _, _, _, _, _, _, _, _,
        _, _, _, _, _, _, _, _,
        _, _, _, _, _, _, _, _,
        _, _, _, _, _, _, _, _,
        _, _, _, _, _, _, _, _ | _
    ],
    !,
    metta_py_decode_indexed(["e", [GuardTagged | PatternsTagged]],
                            [Guard | Patterns], Bindings),
    metta_py_prepare_patterns(Patterns, PlainPatterns, Modifiers, Segments),
    metta_py_match_goal(Segments, Space, PlainPatterns, Goal),
    metta_py_module(Space, Module),
    metta_py_in_module(Module, translate_expr(Guard, Goals, Out)),
    (   Modifiers == []
    ->  call(Goal)
    ;   call(Goal), metta_py_call_modifiers(Modifiers)
    ),
    metta_py_call_goals(Module, Goals),
    Out == true,
    metta_py_row(VarNames, Bindings, Row).

metta_py_query_guarded(Space, PatternsTagged, GuardTagged, VarNames, Row) :-
    metta_py_query_guarded_match(Space, PatternsTagged, GuardTagged, Bindings),
    metta_py_row(VarNames, Bindings, Row).

metta_py_query_guarded_match(Space, PatternsTagged, GuardTagged, Bindings) :-
    metta_py_decode_shared(["e", [GuardTagged | PatternsTagged]], [Guard | Patterns], Bindings),
    metta_py_prepare_patterns(Patterns, PlainPatterns, Modifiers, Segments),
    metta_py_match_goal(Segments, Space, PlainPatterns, Goal),
    metta_py_module(Space, Module),
    metta_py_in_module(Module, translate_expr(Guard, Goals, Out)),
    (   Modifiers == []
    ->  call(Goal)
    ;   call(Goal), metta_py_call_modifiers(Modifiers)
    ),
    metta_py_call_goals(Module, Goals),
    Out == true.

metta_py_query_guarded_all(Space, PatternsTagged, GuardTagged, VarNames, Limit, Rows) :-
    Query = metta_py_query_guarded(Space, PatternsTagged, GuardTagged, VarNames, Row),
    ( Limit > 0
      -> findall(Row, limit(Limit, Query), Rows)
    ; findall(Row, Query, Rows) ).

%The bound is applied here whatever happens below, so pushing it down cannot
%change an answer. It is pushed only for ONE pattern against a foreign space:
%across a join the bound belongs to the joined rows, and an outer match
%truncated at N would lose the rows its later candidates would have joined
%to. A guarded query keeps the bound here too, since the guard decides how
%many candidates become answers.
metta_py_query_limit_all(Space, PatternsTagged, VarNames, Limit, Rows) :-
    (   PatternsTagged = [PatternTagged],
        seam:foreign_space(Space)
    ->  findall(Row,
                limit(Limit,
                      metta_py_bounded_query(Space, PatternTagged, VarNames,
                                             Limit, Row)),
                Rows)
    ;   findall(Row,
                limit(Limit, metta_py_query(Space, PatternsTagged, VarNames, Row)),
                Rows)
    ).

metta_py_bounded_query(Space, PatternTagged, VarNames, Limit, Row) :-
    VarNames = [
        _, _, _, _, _, _, _, _,
        _, _, _, _, _, _, _, _,
        _, _, _, _, _, _, _, _,
        _, _, _, _, _, _, _, _,
        _, _, _, _, _, _, _, _,
        _, _, _, _, _, _, _, _,
        _, _, _, _, _, _, _, _,
        _, _, _, _, _, _, _, _ | _
    ],
    !,
    metta_py_decode_indexed(["e", [PatternTagged]], [Pattern], Bindings),
    metta_py_prepare_patterns([Pattern], [PlainPattern], Modifiers, Segments),
    (   Segments == true
    ->  metta_seq_query_plan(PlainPattern, Asked),
        match(Space, Asked, answered, answered),
        ( Modifiers == [] -> true ; metta_py_call_modifiers(Modifiers) )
    ;   Modifiers == []
    ->  match_foreign(Space, PlainPattern, [limit(Limit)], answered, answered)
    ;   match_foreign(Space, PlainPattern, [limit(Limit)], answered, answered),
        metta_py_call_modifiers(Modifiers)
    ),
    metta_py_row(VarNames, Bindings, Row).

metta_py_bounded_query(Space, PatternTagged, VarNames, Limit, Row) :-
    metta_py_bounded_match(Space, PatternTagged, Limit, Bindings),
    metta_py_row(VarNames, Bindings, Row).

metta_py_bounded_match(Space, PatternTagged, Limit, Bindings) :-
    metta_py_decode_shared(["e", [PatternTagged]], [Pattern], Bindings),
    metta_py_prepare_patterns([Pattern], [PlainPattern], Modifiers, Segments),
    %A gap pattern is not a shape a provider was handed a bound for: its arity
    %is what the gap decides, so the engine enumerates candidates and the
    %caller's own limit/2 still cuts the stream. The test is == on an atom,
    %which SWI compiles inline, so the pushdown path keeps its per-row cost.
    (   Segments == true
    ->  metta_seq_query_plan(PlainPattern, Asked),
        match(Space, Asked, answered, answered),
        ( Modifiers == [] -> true ; metta_py_call_modifiers(Modifiers) )
    ;   Modifiers == []
    ->  match_foreign(Space, PlainPattern, [limit(Limit)], answered, answered)
    ;   match_foreign(Space, PlainPattern, [limit(Limit)], answered, answered),
        metta_py_call_modifiers(Modifiers)
    ).

%A row holds one encoded value per requested name; a variable the answer left
%unbound comes back as itself:
%The acyclicity guard is the engine's own semantics, not a transport
%limit: match_native guards every OUT template with acyclic_term/1, so a
%rational-tree instantiation is not an answer there, and the engine's
%matching is unify_with_occurs_check throughout (spaces.pl
%metta_match_atoms, the arbiter's variable cases). The query lanes keep
%their bindings OUTSIDE the out template, so without this guard a cyclic
%join sailed past match_native's check and the row encode walked it to a
%stack overflow. Same semantics as match/4: the cyclic candidate FAILS
%this row and enumeration continues. Guarded once per row, not per
%column.
%Loud, not a silent row drop: this gate used to FAIL a cyclic row, which
%made the engine-side len disagree with the rows a caller could read.
metta_py_row(Names, indexed(Bindings, Index), Row) :- !,
    ( acyclic_term(Bindings) -> true ; metta_py_wire_refuse ),
    metta_py_row_indexed(Names, Index, Row).
metta_py_row(Names, Bindings, Row) :-
    ( acyclic_term(Bindings) -> true ; metta_py_wire_refuse ),
    metta_py_row_columns(Names, Bindings, Row).

%A ROW IS ONE CROSSING, so its columns share one name map: a variable in two
%columns has to come back as one variable, and two variables must never come
%back as one. Encoding column by column restarted the numbering at each, which
%named the first variable of every column alike; (= $head $body) then answered
%a head and a body whose distinct variables had collided, and the equation read
%back with its head variable merged into a let* binder
%[tested: test_a_twin_stores_the_equations_its_comments_claim].
%
%The map is NOT seeded with the query's variable names. Seeding it reads
%well and is wrong: a column bound to a VARIABLE would then cross under the
%caller's spelling, which is the same spelling in every row, so two rows'
%distinct variables would arrive as one [measured 2026-08-31: two separately
%sealed rules both answered $x]. A caller's name says which column, not which
%cell. Only a column the match did not bind at all keeps it, below, and that
%names no cell to collide with.
metta_py_row_columns(Names, Bindings, Row) :-
    metta_py_row_columns(Names, Bindings, [], Row).

metta_py_row_columns([], _, _, []).
metta_py_row_columns([Name0|Names], Bindings, N0, [Value|Values]) :-
    ( atom(Name0) -> Name = Name0 ; atom_string(Name, Name0) ),
    ( memberchk(Name-V, Bindings) -> metta_py_encode(V, N0, N1, Value)
    ; Value = ["v", Name0], N1 = N0 ),
    metta_py_row_columns(Names, Bindings, N1, Values).

metta_py_row_indexed(Names, Index, Row) :-
    metta_py_row_indexed(Names, Index, [], Row).

metta_py_row_indexed([], _, _, []).
metta_py_row_indexed([Name0|Names], Index, N0, [Value|Values]) :-
    ( atom(Name0) -> Name = Name0 ; atom_string(Name, Name0) ),
    ( ht_get(Index, Name, V) -> metta_py_encode(V, N0, N1, Value)
    ; Value = ["v", Name0], N1 = N0 ),
    metta_py_row_indexed(Names, Index, N1, Values).


%%%%%%%%%% Space modules %%%%%%%%%%
%
% On an engine carrying the per-space-equation patch, a space's compiled
% clauses live in a module named after it and space_module/2 says which; a
% stock engine keeps everything in user. Asking rather than assuming keeps
% this shim loadable on both.

metta_py_module(Space, Module) :-
    ( current_predicate(space_module/2) -> space_module(Space, Module)
    ; Module = user ).

metta_py_in_module(Module, Goal) :-
    ( current_predicate(with_metta_module/2) -> with_metta_module(Module, Goal)
    ; call(Goal) ).

%The translator's own acceptance for one typed argument position,
%exposed to Python: Value admits Type when ('get-type' *-> true ;
%'get-metatype') succeeds with Type bound, the exact check a typed call
%compiles, run in Space's module so its ':' declarations and &self's
%both answer, protocol types included. Both terms decode with shared
%variables, so a repeated variable in the target ((Pair $t $t))
%constrains. Refusal answers the value's own type candidates for the
%message; 'get-type' always answers at least '%Undefined%'.
metta_py_cast(Space, ValueW, TypeW, Out) :-
    metta_py_decode_shared(ValueW, Value, _),
    metta_py_decode_shared(TypeW, Type, _),
    metta_py_module(Space, Module),
    ( metta_py_in_module(Module,
          ( 'get-type'(Value, Type) *-> true ; 'get-metatype'(Value, Type) ))
      -> Out = ["s", "ok"]
    ; metta_py_in_module(Module, findall(T, 'get-type'(Value, T), Ts)),
      maplist(metta_py_encode, Ts, TsW),
      Out = ["e", TsW] ).

%%%%%%%%%% Evaluation %%%%%%%%%%
%
% Evaluation is the engine's own translate_expr/3 over the term, then its
% goals, exactly what a ! directive runs: compiled and called in the space's
% module, so the space's own equations answer. Answers enumerate on
% backtracking.

%Every answer carries its Well Founded Semantics truth: call_delays is
%one '$wfs_call' around the goal, answering true for an unconditional
%derivation and the conjunction of unknown tabled goals otherwise, per
%answer, INSIDE the enumeration, which is the only place the condition
%exists (findall erases it). An unconditional answer encodes exactly as
%before; an undefined one crosses under the u tag so the third truth
%value reaches Python instead of masquerading as an ordinary answer.
%The wrapper is unconditional on purpose: every gate on "tabling in use"
%has a first-tabled-call window that would answer silently wrong exactly
%once, and callees make per-predicate checks unsound. Measured cost on
%the trivial-eval crossing: five to ten percent (interleaved A/B against
%a plain twin, 222-236k against 248-249k calls per second); real
%evaluations amortize it below that.
%One module wrap for resolution AND execution. Resolution went through
%metta_py_direct_goal/4, whose own metta_py_in_module made this door pay the
%context switch twice per eval; the compiled call sites resolve_dispatch
%serves pay it zero times, because they are already in their module. Folding
%resolution inside the execution wrap keeps the seam offer and the module
%context identical and returns ~10 of the +18 inferences the seam routing
%added [measured 2026-09-01: eval-arith 292,604 -> see baseline comment].
metta_py_eval(Space, Tagged, Encoded) :-
    metta_py_target_term(Space, Tagged, Term),
    metta_py_module(Space, Module),
    metta_py_in_module(Module,
        (   metta_py_direct_goal(Module, Term, F, Args, Produced)
        ->  translator:resolve_dispatch(F, Args, Produced, Goal),
            call_delays(call(Module:Goal), Delays)
        ;   translate_cached_expr(Term, Goals, Produced),
            call_delays(metta_py_call_goals(Module, Goals), Delays)
        )),
    translator:metta_boundary_result(Term, Produced, Out),
    metta_py_encode_truth(Out, Delays, Encoded).

metta_py_encode_truth(Out, Delays, Encoded) :-
    metta_py_wire_acyclic(Out),
    ( Delays == true
      -> metta_py_encode(Out, Encoded)
    ; metta_py_encode(Out, Inner),
      term_string(Delays, Why),
      Encoded = ["u", Inner, Why] ).

%The fast path: a flat call of a compiled function whose arguments are all
%plain data needs no translation, just the call. translate_expr costs two
%orders more than the call itself on such terms, and they are what an API
%client evaluates all day. Anything with structure or evaluable arguments
%(a special form, a nested call, a symbol that names a function) takes the
%translator, whose judgment stays authoritative.
%Every head translate_expr treats structurally (its HV == chain and the
%stream rewrites): these must always take the translator, whatever their
%arguments look like.
%The translator's own registry, MATERIALIZED at load. The hand table this
%replaces lagged the engine: 'not-provable' gained a translate_special_dl
%clause and a bare same-name predicate, the stale table let the direct path
%claim the predicate, and the Python eval door answered [] where the
%engine's own directive answered True [measured 2026-09-01,
%examples/ch22-.../03-constructive_negation]. Consulting the registry per
%ask fixed that but taxed every eval crossing +2 inferences (+4,002 on the
%2,000-operation eval-arith lane, +4,000 on op-encoded), so the rows are
%asserted once here from metta_special_form_head/1, the enumerable face
%published for exactly this kind of reader: the ask stays one indexed
%lookup at the hand table's own cost (both lanes back on their pins under
%a plant/restore control [measured 2026-09-01]), and a form added to the
%engine's table is covered at the next boot, which is the table's own
%grain because translate_special_dl/5 is static engine source. The second
%forall is the RESIDUE the registry does not carry: rewrites owned by
%other dispatchers (the and-then/or-else pair and the stream set), and the
%trace! directive form. The findall completes the whole enumeration, the
%fallible part, before the retractall, so a reconsult swaps the set
%exactly (a form removed from the engine source leaves on the same
%reload that would have added one) and a failed enumeration leaves the
%previous set standing rather than an empty one. The current_predicate
%guard keeps the shim's engine-free consult (shim.plt's contract) loading
%clean: without the engine only the residue rows exist, and nothing
%engine-free can reach a special form anyway.
:- dynamic metta_py_special/1.
:- findall(F,
           ( current_predicate(translator:metta_special_form_head/1),
             translator:metta_special_form_head(F)
% policy-inventory-exempt: mechanism-internal; reason=the residue rows are the dispatch table's own content, heads owned by other rewrite dispatchers, not an operator choice; evidence=examples/ch06-many-answers/09-streamops.metta:1
           ; member(F, ['and-then', 'or-else', 'trace!', unique,
                        'alpha-unique', union, intersection, subtraction]) ),
           Forms),
   retractall(metta_py_special(_)),
   forall(member(F, Forms), assertz(metta_py_special(F))).

%The resolved goal, for every caller that wants one. Resolution goes through
%the engine's OWN resolve_dispatch so a compiled call site and this one make
%the same decision: seam:dispatch_call/4 is offered the call first, which is
%where lib_memo binds a cache lookup. Building the goal here instead was a
%second copy of resolve_dispatch's else-branch and skipped the seam entirely.
metta_py_direct_goal(Module, Term, Goal, Out) :-
    metta_py_direct_goal(Module, Term, F, Args, Out),
    metta_py_in_module(Module, translator:resolve_dispatch(F, Args, Out, Goal)).

%Whether the fast path applies at all, and the parts a resolution needs.
metta_py_direct_goal(Module, [F|Args], F, Args, _Out) :-
    atom(F),
    fun(F),
    \+ metta_py_special(F),
    %A declared callee, any installed USER typing rule, or a translator
    %rule means call-site machinery owns this call: the raw compiled clause
    %carries no argument checks, so the direct goal would skip a refusal
    %the same call written as a ! form makes -- (typing-rule-demo
    %unknown-demo) answered (seen unknown-demo) here while the runnable
    %answered the declared BadArgType with its TypingRuleRefusal. Shipped
    %rules ride the clause-compile route and need no per-call gate. The
    %question is the engine's (metta/types.pl documents both owners and
    %the measured cost); the shim used to carry its own copy of the
    %disjunction, and a three-state A/B on the eval-arith lane measured
    %the declaration walk and a raw &self read within two inferences per
    %LANE, so there is nothing to buy by narrowing the walk. The gate runs
    %OUTSIDE metta_py_in_module, which is why the module-parameterized
    %door is the right one: an ambient read like type_declaration/2 would
    %inspect the wrong module.
    \+ metta_typed_dispatch_applies(Module, F),
    metta_py_plain_args(Args),
    length(Args, N),
    Arity is N + 1,
    %The direct-goal guard reads the registry, so a deferred function fell
    %to the slow path until something else forced it.
    spaces:metta_ensure_compiled(F),
    arity(F, Arity),
    current_predicate(Module:F/Arity).

metta_py_plain_args([]).
metta_py_plain_args([A|As]) :-
    ( number(A) -> true
    ; string(A) -> true
    ; A == true -> true
    ; A == false -> true
    ; atom(A), \+ fun(A) -> true
    ; py_is_object(A) ),
    metta_py_plain_args(As).

metta_py_call_goals(_, []).
metta_py_call_goals(Module, [G|Gs]) :-
    call(Module:G),
    metta_py_call_goals(Module, Gs).

%%%%%%%%%% Every evaluation door opens a fuel scope %%%%%%%%%%
%
%m.eval's own docstring says it is "what !(...) runs, minus the printing", and
%a runnable form runs inside the fuel scope engine/translator.pl wraps its
%conjunction in [source: engine/translator.pl, translate_runnable_expr/4's
%metta_run_with_fuel/3 call]. This door opened none, so `max-stack-depth` did
%not apply through it: the same two equations that answer
%`[120, (Error -3 StackOverflow)]` through `!` instead ran until SWI's stack
%gave out, 28.7 million inferences deep, and took the process with them
%[measured 2026-08-22 on identical string-loaded equations, both doors in one
%process each]. A bound the language offers has to hold at every door that
%claims to run the same thing
%[tested: test_the_same_source_answers_the_same_error_through_both_doors].
%
%The wrapper is metta_run_with_fuel/3's own contract: it answers the Value it
%was given for each ordinary solution, and then replays each branch that ran
%out of fuel as `(Error <culprit> StackOverflow)`. So an ordinary answer
%arrives inside metta_py_answer/1 and is unwrapped, and anything else is a
%fuel error atom that still has to cross as an encoded answer. Reentry is
%free: metta_run_with_fuel/3 calls the goal directly when a scope is already
%open, so m.eval from inside a runnable spends the runnable's fuel rather than
%opening a second budget.
metta_py_eval_all(Space, Tagged, Encoded) :-
    findall(E, metta_py_eval_bounded(Space, Tagged, E), Answers),
    ( Answers == [],
      metta_py_target_term(Space, Tagged, Term),
      metta_py_preserve_unmatched(Space, Term, Original)
      -> Encoded = [Original]
      ;  Encoded = Answers ).

metta_py_eval_bounded(Space, Tagged, Encoded) :-
    metta_run_with_fuel(metta_py_answer(Raw), Answer,
                        metta_py_eval(Space, Tagged, Raw)),
    metta_py_fuel_encoded(Answer, Encoded).

metta_py_fuel_encoded(metta_py_answer(Encoded), Encoded) :- !.
metta_py_fuel_encoded(Overflow, Encoded) :- metta_py_encode(Overflow, Encoded).

%eval with named host values, the same door metta_py_run_using opens for
%run: each Name-Value pair substitutes the bare symbol Name throughout the
%target before it evaluates, so a tensor or any other object reaches a
%rule by name and by IDENTITY rather than through a printed form. The
%target is read first, because substitution is over the term
%[tested test_run_using_carries_identity].
metta_py_eval_using_all(Space, Target, Pairs, Encoded) :-
    metta_py_target_term(Space, Target, Term0),
    maplist(metta_py_using_pair, Pairs, Bindings),
    metta_host_substitute(Bindings, Term0, Term),
    %The substituted TERM evaluates directly. Re-encoding it to a wire and
    %handing that back to the ordinary entry point looks tidier and is
    %wrong: a substituted host value is a boxed reference, and a round
    %trip through the encoder is exactly the copy `using` exists to
    %avoid.
    findall(E, metta_py_eval_term_bounded(Space, Term, E), Answers),
    ( Answers == [], metta_py_preserve_unmatched(Space, Term, Original)
      -> Encoded = [Original]
      ;  Encoded = Answers ).

%The lazy Answers door shares target decoding with eager eval, then holds one
%SWI engine so each Python pull resumes the producer rather than materializing
%it. These predicates live in the boot-consulted shim: consulting them on the
%first pull charged every fresh process for loading infrastructure rather than
%for its query.
metta_py_eval_target(Space, Target, Pairs, Term, Bindings) :-
    metta_py_target_term_bindings(Space, Target, Term0, Bindings),
    (   Pairs == []
    ->  Term = Term0
    ;   maplist(metta_py_using_pair, Pairs, Substitutions),
        metta_host_substitute(Substitutions, Term0, Term)
    ).

metta_py_eval_cursor_open(Space, Target, Pairs, VarNames, Inf, prolog(Engine)) :-
    metta_py_eval_cursor_open_controlled(
        Space, Target, Pairs, VarNames, Inf, none, prolog(Engine)).

metta_py_eval_cursor_open_controlled(
        Space, Target, Pairs, VarNames, Inf, Policy, prolog(Engine)) :-
    metta_py_eval_target(Space, Target, Pairs, Term, Bindings),
    Goal = ( statistics(inferences, Before),
             metta_py_eval_term_bounded(Space, Term, Encoded),
             metta_py_row(VarNames, Bindings, Row),
             statistics(inferences, Now), Used is Now - Before ),
    metta_host_inference_budget(Goal, Inf, Bounded),
    metta_py_open_controlled_cursor(
        Policy, [Encoded, Row, Used], Bounded, Engine).

metta_py_eval_cursor_open_under(Space, Target, Pairs, VarNames, Inf, Algebra,
                                Direction, prolog(Engine)) :-
    metta_py_eval_cursor_open_under_controlled(
        Space, Target, Pairs, VarNames, Inf, Algebra, Direction, none,
        prolog(Engine)).

metta_py_eval_cursor_open_under_controlled(
        Space, Target, Pairs, VarNames, Inf, Algebra, Direction, Policy,
        prolog(Engine)) :-
    metta_py_eval_target(Space, Target, Pairs, Term, Bindings),
    (   Direction \== none
    ->  Core = metta_py_ordered_eval_under(Space, Term, VarNames, Direction,
                                            Bindings, Encoded, Row, K, Used)
    ;   Core = ( statistics(inferences, Before),
                 metta_algebra_one(Space, One),
                 b_setval('$metta_answer_k', One),
                 metta_py_eval_term_bounded(Space, Term, Encoded),
                 metta_py_row(VarNames, Bindings, Row),
                 b_getval('$metta_answer_k', K),
                 statistics(inferences, Now), Used is Now - Before )
    ),
    Goal = ( metta_with_under(Algebra, Core), metta_py_encode(K, KWire) ),
    metta_host_inference_budget(Goal, Inf, Bounded),
    metta_py_open_controlled_cursor(
        Policy, [Encoded, Row, KWire, Used], Bounded, Engine).

metta_py_ordered_eval_under(Space, Term, VarNames, Direction, Bindings, Encoded,
                            Row, K, Used) :-
    statistics(inferences, Before),
    metta_algebra_one(Space, One),
    findall(K0-[Encoded0, Row0],
            ( b_setval('$metta_answer_k', One),
              metta_py_eval_term_bounded(Space, Term, Encoded0),
              metta_py_row(VarNames, Bindings, Row0),
              b_getval('$metta_answer_k', K0) ),
            Pairs),
    statistics(inferences, Now),
    Used is Now - Before,
    metta_py_ordered_pairs(Direction, Pairs, Ordered),
    member(K-[Encoded, Row], Ordered).

metta_py_eval_count(Space, Target, Pairs, Count) :-
    metta_py_eval_target(Space, Target, Pairs, Term, _),
    metta_py_eval_count_term(Space, Term, Count).

%A count is a second evaluation. It is a free cardinality probe for an
%effect-safe goal, but executing an effectful operation here and then opening
%the held answer cursor fires the operation twice. Reuse the engine's table /
%memo admission walk as the decision: it follows user definitions, recognizes
%host operation declarations, and fails closed on an unknown effect. Unsafe
%answers return [] so Answers.__len__ materializes its one cursor instead.
metta_py_eval_count_if_repeatable(Space, Target, Pairs, Answer) :-
    metta_py_eval_target(Space, Target, Pairs, Term, _),
    (   metta_py_eval_repeatable(Space, Term)
    ->  metta_py_eval_count_term(Space, Term, Count), Answer = [Count]
    ;   Answer = []
    ).

metta_py_eval_repeatable(Space, Term) :-
    metta_py_module(Space, Module),
    catch_recover(
        (   (   metta_py_direct_goal(Module, Term, Goal, _)
            ->  Body = Goal
            ;   metta_py_in_module(
                    Module,
                    ( translate_cached_expr(Term, Goals, _),
                      goals_list_to_conj(Goals, Body) ))
            ),
            metta_host_goal_repeatable(Module, Body)
        ),
        fail).

metta_py_eval_count_term(Space, Term, Count) :-
    aggregate_all(
        count,
        metta_run_with_fuel(metta_py_answer(Out), _,
                            metta_py_eval_solution(Space, Term, Out, _)),
        Count).

%A count is a second evaluation, which an effect-bearing goal must not pay.
%Evaluate ONCE instead: hold every answer one step short of the wire, answer
%the count, and hand back a cursor that replays what was held. A count nobody
%turns into values then crosses one integer, where the materializing pass it
%replaces encoded and crossed every answer to reach that number; a later value
%demand encodes exactly the answers it pulls. Encoding is the whole per-answer
%cost here, measured on examples/ch07-control-flow/07-05-recursion/06-peano.metta's 301 answers: 2029719
%inferences counting without it, 2392138 counting with it, and 2393864 for the
%full materializing pass, so deferring the encode recovers 99.5% of the gap
%while the boundary walk it keeps costs one inference per answer.
%This is the held-portal shape a SQL engine uses to answer a count over an
%open cursor without re-running the query: PostgreSQL materializes a SCROLL
%cursor once and MOVE FORWARD ALL reports the row count with no row reaching
%the client [source: PostgreSQL 17 manual, SQL-DECLARE and SQL-MOVE].
%
%This is the one budget site that does NOT run in an engine: findall/3 drives
%the whole enumeration here, on the calling thread, so the counter it reads
%has been growing since the process started. That is why
%metta_host_inference_budget/3 takes a base when the goal starts rather than
%comparing the raw counter, and why the base cannot be dropped as dead weight
%on the grounds that an engine's counter starts near zero.
metta_py_eval_count_retaining(Space, Target, Pairs, VarNames, Inf,
                              [Count, prolog(Engine)]) :-
    metta_py_eval_target(Space, Target, Pairs, Term, Bindings),
    Collect = ( metta_py_eval_retained(Space, Term, Retained),
                metta_py_row(VarNames, Bindings, Row) ),
    metta_host_inference_budget(Collect, Inf, Bounded),
    findall(Retained-Row, Bounded, Bag),
    length(Bag, Count),
    %Same cumulative-inference report the evaluating cursor makes, so a
    %replayed view still tells its enclosing stats block what the held engine
    %spent. The evaluation's own inferences were spent on the caller's engine
    %and are already in that thread's counter.
    Replay = ( statistics(inferences, Before),
               member(Held-HeldRow, Bag),
               metta_py_retained_encoded(Held, Encoded),
               statistics(inferences, Now), Used is Now - Before ),
    engine_create([Encoded, HeldRow, Used], Replay, Engine).

%One held answer: the fuel-scope result before its wire form exists.
metta_py_eval_retained(Space, Term, Retained) :-
    metta_run_with_fuel(metta_py_answer(Out-Delays), Retained,
                        metta_py_eval_solution(Space, Term, Out, Delays)).

%The encoding metta_py_eval_term_bounded/3 does eagerly, deferred to the pull
%that wants the answer. Mirrors metta_py_fuel_encoded/2: a fuel overflow
%answer is its own term rather than a held value-and-delays pair.
metta_py_retained_encoded(metta_py_answer(Out-Delays), Encoded) :- !,
    metta_py_encode_truth(Out, Delays, Encoded).
metta_py_retained_encoded(Overflow, Encoded) :- metta_py_encode(Overflow, Encoded).

metta_py_eval_count_under(Space, Target, Pairs, Algebra, Count) :-
    metta_with_under(
        Algebra,
        metta_py_eval_count(Space, Target, Pairs, Count)).

%The carrier count keeps the repeatability guard: counting is a second
%evaluation whatever algebra tags it, so an effect-unsafe goal answers []
%and the Python side counts through its one materializing pass.
metta_py_eval_count_under_if_repeatable(Space, Target, Pairs, Algebra, Answer) :-
    metta_with_under(
        Algebra,
        metta_py_eval_count_if_repeatable(Space, Target, Pairs, Answer)).

%metta_py_eval_term/3 is this dispatch plus metta_py_encode_truth/3, written
%out there rather than calling here so the eager answer path pays no extra
%frame. The two are held in step by
%test_a_retained_count_replays_the_bag_the_cursor_would_have_answered, which
%runs the same programs through both and compares the answer bags.
metta_py_eval_solution(Space, Term, Out, Delays) :-
    metta_py_module(Space, Module),
    ( metta_py_direct_goal(Module, Term, Goal, Produced)
      -> metta_py_in_module(Module, call_delays(call(Module:Goal), Delays))
    ; metta_py_in_module(Module, ( translate_cached_expr(Term, Goals, Produced),
                                   call_delays(metta_py_call_goals(Module, Goals),
                                               Delays) )) ),
    translator:metta_boundary_result(Term, Produced, Out).

%A direct compiled predicate that fails can mean either that its written head
%did not match or that a matching body's answer set was empty. Only the first
%is an unreduced original. Classify after an empty aggregate so the successful
%hot path retains the old direct goal and its exact inference cost.
metta_py_preserve_unmatched(Space, [F|Args], Encoded) :-
    atom(F),
    metta_py_module(Space, Module),
    translator:fun_meta_module(Module, F, _),
    \+ translator:dispatch_any_head_matches(Module, F, Args),
    translator:dispatch_no_match_result(F, Args, Produced),
    translator:metta_boundary_result([F|Args], Produced, Out),
    metta_py_encode(Out, Encoded).

metta_py_eval_term_bounded(Space, Term, Encoded) :-
    metta_run_with_fuel(metta_py_answer(Raw), Answer,
                        metta_py_eval_term(Space, Term, Raw)),
    metta_py_fuel_encoded(Answer, Encoded).

metta_py_eval_term(Space, Term, Encoded) :-
    metta_py_module(Space, Module),
    ( metta_py_direct_goal(Module, Term, Goal, Produced)
      -> metta_py_in_module(Module, call_delays(call(Module:Goal), Delays))
    ; metta_py_in_module(Module, ( translate_cached_expr(Term, Goals, Produced),
                                   call_delays(metta_py_call_goals(Module, Goals),
                                               Delays) )) ),
    translator:metta_boundary_result(Term, Produced, Out),
    metta_py_encode_truth(Out, Delays, Encoded).

%Which of MeTTa's own evaluation paths produced each answer, reported without
%changing what the ordinary entry points return:
%
%  value           an equation, builtin or special form applied
%  not-reducible   no rule applied, so the answer is the written term itself,
%                  which is what MeTTa does with any head it cannot call
%  empty           the goal produced no answer at all, which is what (empty)
%                  and a match with no candidates do
%
%MeTTa had no name for these, so the taxonomy was taken from the mechanised
%Hyperon specification, which is the only part borrowed
%[source: LeaTTa checkout, MettaHyperonFull/Core/Result.lean, EvalStatus].
%The distinction that matters is the one that surface behaviour hides: empty
%is a pruned branch and not-reducible is an unevaluated term, and reading
%both as "nothing happened" is what made an earlier strict mode fire on
%(empty) and on a match with no candidates. An error is the fourth outcome
%there and is not reported here, because the caller already receives it as
%an exception.
%
%The head decides between value and not-reducible, using the same test the
%translator uses when it chooses between emitting a call and building data,
%so this reports the branch the engine actually took rather than guessing
%from the answer [tested test_eval_status_reports_the_four_outcomes].
%The reducibility question ASKED rather than answered by evaluating. It is
%the same head test eval_status uses, published on its own because a caller
%who wants to decide about an unreduced term should not have to run the term
%to find out. The Node seat has had m.reducible since it existed and this
%seat had only eval_status, which evaluates to tell you
%[measured 2026-08-31].
metta_py_reducible(Space, Tagged, Reducible) :-
    metta_py_target_term(Space, Tagged, Term),
    metta_py_module(Space, Module),
    %Status is asked UNBOUND, the way eval_status asks it: binding it to
    %`value` first skips the clause that reports a function whose heads do
    %not match, and every such term came back reducible.
    metta_py_eval_status(Module, Term, Status),
    (   Status == value
    ->  Reducible = true
    ;   Reducible = false
    ).

metta_py_eval_status_all(Space, Tagged, Results) :-
    metta_py_target_term(Space, Tagged, Term),
    metta_py_eval_status_term(Space, Term, Results).

metta_py_eval_status_using_all(Space, Tagged, Pairs, Results) :-
    metta_py_target_term(Space, Tagged, Term0),
    maplist(metta_py_using_pair, Pairs, Bindings),
    metta_host_substitute(Bindings, Term0, Term),
    metta_py_eval_status_term(Space, Term, Results).

metta_py_eval_status_term(Space, Term, Results) :-
    metta_py_module(Space, Module),
    metta_py_eval_status(Module, Term, Status),
    findall([Status, E], metta_py_eval_term_bounded(Space, Term, E), Answers),
    ( Answers == []
      -> ( Status == 'not-reducible',
           metta_py_preserve_unmatched(Space, Term, Original)
           -> Results = [[Status, Original]]
           ;  Results = [[empty, none]] )
      ;  Results = Answers ).

metta_py_eval_status(Module, [F|Args], 'not-reducible') :-
    atom(F),
    %A deferred function has no fun_meta rows until its equations
    %translate, and this door's whole question is about those rows.
    spaces:metta_ensure_compiled(F),
    translator:fun_meta_module(Module, F, _),
    \+ translator:dispatch_any_head_matches(Module, F, Args),
    !.
metta_py_eval_status(Module, Term, Status) :-
    ( metta_reducible_head(Module, Term) -> Status = value
                                          ; Status = 'not-reducible' ).

%%%%%%%%%% Python-backed MeTTa functions %%%%%%%%%%
%
% A registered operation is an ordinary MeTTa function whose body lives in
% Python. Arguments cross encoded so Python sees real atoms; results cross
% back encoded. kind det calls once; kind many enumerates a Python iterator
% through py_iter/2, which is genuine nondeterminism. The raw kinds skip the
% encoding for speed and receive janus's default conversion instead, which
% suits operations over object references such as tensors.

:- dynamic metta_py_op_spec/3.

%An operation that answers nothing sends the declined sentinel, which turns
%into failure here: the semidet reading of a Python None or a raised Decline.
metta_py_declined(TR) :- TR = [T, D], metta_py_tag(T, x), metta_py_tag(D, declined).

%A variable that crosses and comes back is the CALLER'S variable, not a fresh
%one with the same name. Without this the boundary silently broke variable
%identity, which is the whole of why no relational use of a Python operation
%worked: a native (= (mcons $h $t) ($h 2 3)) answers an expression whose head
%IS $x, so binding the result to (9 2 3) binds $x to 9, while the same shape
%through a registered operation answered a fresh $_34678 that binding did
%nothing to [tested: test_a_variable_crossing_python_comes_back_the_same_variable].
%
%The decoder already shares by name WITHIN one term, which is what makes an
%answer mentioning $x twice mention one variable. It just started from an
%empty table. Seeding it with the arguments is the whole fix, and the seed is
%now the very map metta_py_encode_arguments/3 wrote for those arguments
%rather than one rebuilt from them afterwards: rebuilding read the cells'
%addresses a whole Python crossing later, by which time a collection could
%have moved them. A call whose arguments hold no variable seeds an empty map
%and mints nothing, so it still pays nothing at all for this.
%metta_py_failure/2 is extensions/python/bridge.pl's, and a registered operation was the one
%Python caller not reaching it. That is not a cosmetic gap: without it janus's
%own error term reaches MeTTa carrying the live exception OBJECT and a live
%TRACEBACK object, which is the defect metta_py_failure/2 was written to fix
%for py-call and py-atom, and it names a Python file and line and no MeTTa
%call at all. What a program gets instead is
%(Error (python_error ZeroDivisionError "division by zero") (context (op 1) ...)),
%which it can branch on, compare and print after the failure
%[tested: test_an_operation_failure_names_the_metta_call].
%
%The catch is written out here rather than going through metta_py_guard/2, its
%three other callers' spelling, because the wrapper is a predicate call and
%this is the hot path: guard plus catch cost two inferences per call where the
%catch alone costs one [measured 2026-08-17: the encoded operation at 14.01
%through the wrapper, 13.01 written out]. Same catcher, same recovery.
%Python's equality and truth protocols are richer than Prolog term identity,
%but the wire's structural classes have exact local answers. Keep this pair
%ahead of the generic dispatch so a compiled Python body does not cross the
%host once per comparison. Failure means an opaque grounded value is present;
%its Python class may implement __eq__ or __bool__, so only the retained host
%route may decide it [source: Python 3.14 data model, object.__eq__ and
%object.__bool__, https://docs.python.org/3/reference/datamodel.html;
%commit=551f6236be947d5c52f5243e3d56f0009a000071].
%Numbers lead because compiled arithmetic comparisons are the loop case. The
%two guards and arithmetic comparison are in this clause so that case pays no
%classification or helper calls.
metta_py_dispatch_eq(Left, Right, Result) :-
    number(Left), number(Right),
    !,
    ( Left =:= Right -> Result = true ; Result = false ).
%The railway rows, the same law the host table's guard carries: a compiled
%strict position propagates error DATA instead of computing over it, so a
%comparison meeting an (Error ...) answers the error rather than reading
%it as an expression. The native lanes decide without crossing, so they
%need their own rows; they sit after the number clause, which cannot meet
%an error, so the compiled loop case pays nothing.
metta_py_dispatch_eq(Left, _Right, Left) :-
    nonvar(Left), Left = ['Error'|_], !.
metta_py_dispatch_eq(_Left, Right, Right) :-
    nonvar(Right), Right = ['Error'|_], !.
metta_py_dispatch_eq(Left, Right, Result) :-
    metta_py_native_eq(Left, Right, Result),
    !.
metta_py_dispatch_eq(Left, Right, Result) :-
    metta_py_dispatch_det('py-eq', [Left, Right], Result).

metta_py_dispatch_truthy(Value, Result) :-
    number(Value),
    !,
    ( Value =:= 0 -> Result = false ; Result = true ).
metta_py_dispatch_truthy(Value, Value) :-
    nonvar(Value), Value = ['Error'|_], !.
metta_py_dispatch_truthy(Value, Result) :-
    metta_py_native_truthy(Value, Result),
    !.
metta_py_dispatch_truthy(Value, Result) :-
    metta_py_dispatch_det('py-truthy', [Value], Result).

metta_py_dispatch_det(Name, Args, Result) :-
    metta_py_encode_arguments(Args, TA, Table),
    catch(metta_py_host_call(Name, metta_py_call_det(Name, TA, TR)),
          Error, TR = '$metta_op_error'(Error)),
    (   TR = '$metta_op_error'(DetError)
    ->  metta_py_op_erring(Name, Args, DetError, Result)
    ;   \+ metta_py_declined(TR),
        %The shape test and this whole branch are written out because
        %this is the hot path: a plain wire is two elements, the explicit
        %answer four or five, the inlined unification costs no inference,
        %and even one helper call showed up as +1 per call on the extcost
        %gate [measured 2026-08-17: encoded 57248 against its 54248
        %baseline through a metta_py_dispatch_det_result/4 helper, and
        %54248 written out].
        (   TR = [_, _, _, _|_]
        ->  metta_py_answer_result(TR, Name, Table, Result)
        ;   metta_py_decode_shared_(TR, Result, Table, _)
        )
    ).

%A scheduler engine owns one retained Python Context token. Direct host calls
%have none and keep their old callback path. Context selection is outside the
%Python registry's hot dispatch so unscheduled calls pay one b-value probe and
%no copied Context.
metta_py_call_det(Name, Args, Result) :-
    (   nb_current('$metta_python_context', Context), integer(Context)
    ->  py_call(metta_ops:dispatch_context(Context, Name, Args), Result)
    ;   py_call(metta_ops:dispatch(Name, Args), Result)
    ).

metta_py_call_many(Name, Args, Mode, Result) :-
    (   nb_current('$metta_python_context', Context), integer(Context)
    ->  py_iter(metta_ops:dispatch_many_context(Context, Name, Args, Mode),
                Result)
    ;   py_iter(metta_ops:dispatch_many(Name, Args, Mode), Result)
    ).

metta_py_call_raw_det(Name, Args, Result) :-
    (   nb_current('$metta_python_context', Context), integer(Context)
    ->  py_call(metta_ops:dispatch_raw_context(Context, Name, Args), Result)
    ;   py_call(metta_ops:dispatch_raw(Name, Args), Result)
    ).

metta_py_call_raw_many(Name, Args, Result) :-
    (   nb_current('$metta_python_context', Context), integer(Context)
    ->  py_iter(metta_ops:dispatch_raw_many_context(Context, Name, Args),
                Result)
    ;   py_iter(metta_ops:dispatch_raw_many(Name, Args), Result)
    ).

%Go's blocking-syscall handoff applied at the five-rank admission boundary:
%oracleIO yields before entering Python; the scheduler detaches that engine
%onto a transient worker and keeps every bounded normal carrier available.
%writesState stays on normal carriers and serializes at the store write door;
%the three read ranks remain eligible on every normal carrier. A deterministic
%call reifies success, failure, or error and hands back to normal explicitly.
%A nondeterministic call runs in a nested SWI engine: each pull happens after
%a dirty handoff and each answer returns after a normal handoff, avoiding both
%carrier pinning and a cleanup-time yield (SWI forbids engine_yield/1 from a
%cleanup handler) [source:
%https://github.com/golang/go/blob/c19862e5f8415b4f24b189d065ed739517c548ba/src/runtime/proc.go#L4781-L4831,
%Go 1.26.5 entersyscallblock; tested:
%test_a_blocking_oracle_uses_the_dirty_lane_without_pinning_normal_work;
%commit=39092863ae34184a9f955f185ff57c1ff177ec40].
metta_py_host_call(Name, Goal) :-
    (   nb_current('$metta_scheduler_task', _),
        metta_operation_effect(Name, oracleIO)
    ->  (   metta_py_host_many(Name)
        ->  metta_py_dirty_many(Goal)
        ;   metta_py_dirty_once(Goal)
        )
    ;   call(Goal)
    ).

metta_py_host_many(Name) :-
    once(metta_contract_fact([op, Name, _, Kind])),
    % policy-inventory-exempt: mechanism-internal; reason=the two op kinds whose answers stream nondeterministically, a projection of the catalog's declared op-kind vocabulary rather than a second list; evidence=engine/spaces/catalog.pl:metta_catalog_preset/1
    memberchk(Kind, [many, raw_many]).

metta_py_dirty_once(Goal) :-
    engine_yield('$metta_scheduler_lane'(dirty)),
    catch(( once(call(Goal)) -> Outcome = success ; Outcome = failure ),
          Error,
          Outcome = error(Error)),
    engine_yield('$metta_scheduler_lane'(normal)),
    metta_py_dirty_outcome(Outcome).

metta_py_dirty_outcome(success).
metta_py_dirty_outcome(failure) :- fail.
metta_py_dirty_outcome(error(Error)) :- throw(Error).

metta_py_dirty_many(Goal) :-
    term_variables(Goal, Variables),
    (   nb_current('$metta_python_context', Context0)
    ->  Context = Context0
    ;   Context = none
    ),
    setup_call_cleanup(
        engine_create(Variables,
                      metta_py_dirty_inner(Context, Goal, Variables),
                      HostEngine),
        metta_py_dirty_many_next(HostEngine, Variables),
        engine_destroy(HostEngine)).

metta_py_dirty_inner(none, Goal, _) :- !,
    call(Goal).
metta_py_dirty_inner(Context, Goal, _) :-
    b_setval('$metta_python_context', Context),
    call(Goal).

metta_py_dirty_many_next(HostEngine, Variables) :-
    engine_yield('$metta_scheduler_lane'(dirty)),
    engine_next_reified(HostEngine, Event),
    metta_py_dirty_many_event(Event, HostEngine, Variables).

metta_py_dirty_many_event(the(Values), HostEngine, Variables) :-
    engine_yield('$metta_scheduler_lane'(normal)),
    (   Variables = Values
    ;   metta_py_dirty_many_next(HostEngine, Variables)
    ).
metta_py_dirty_many_event(no, _, _) :-
    engine_yield('$metta_scheduler_lane'(normal)),
    fail.
metta_py_dirty_many_event(throw(Error), _, _) :-
    engine_yield('$metta_scheduler_lane'(normal)),
    throw(Error).

%The coroutine itself is not created here. async_prepare retains decoded
%arguments and a copied Context; observation_defer starts it only after the
%outer transaction has committed and discards it on rollback. The launch atom
%therefore rides the transaction's ordinary buffered event segment, while the
%landing atom below is a later write from the event-loop thread.
metta_py_dispatch_async(Name, Args, Space) :-
    metta_py_encode_arguments(Args, Tagged, _),
    metta_async_future_new(Space, Done),
    (   catch(metta_py_async_prepare(Name, Tagged, Space, Done, Token),
              Error,
              ( metta_async_future_abandon(Space, Done), throw(Error) ))
    ->  true
    ;   metta_async_future_abandon(Space, Done),
        fail
    ),
    metta_py_async_publish_launch(Name, Space, Token, Done).

%A local observation frame makes the event and deferred start one ordered
%segment even outside a user transaction. Nested commit merges the pair into
%an outer frame; a direct commit publishes launch and then starts. If the
%launch watcher fails after the write committed, observation_commit/0 still
%runs the later deferred start before rethrowing.
metta_py_async_publish_launch(Name, Space, Token, Done) :-
    seam:observation_begin,
    catch((   'add-atom'('&metta', ['async-op', Name, Space, launch], _),
              seam:observation_defer(
                  metta_py_async_start(Token),
                  metta_py_async_discard(Token, Space, Done))
          ->  Outcome = commit
          ;   Outcome = discard
          ),
          Error,
          Outcome = error(Error)),
    metta_py_async_finish_launch(Outcome, Token, Space, Done).

metta_py_async_finish_launch(commit, _, _, _) :- !,
    seam:observation_commit.
metta_py_async_finish_launch(discard, Token, Space, Done) :- !,
    seam:observation_discard,
    metta_py_async_discard(Token, Space, Done),
    fail.
metta_py_async_finish_launch(error(Error), Token, Space, Done) :-
    seam:observation_discard,
    metta_py_async_discard(Token, Space, Done),
    throw(Error).

metta_py_async_prepare(Name, Tagged, Space, Done, Token) :-
    (   nb_current('$metta_python_context', Context), integer(Context)
    ->  Parent = Context
    ;   Parent = @(none)
    ),
    metta_py_host_call(
        Name,
        py_call(metta_ops:async_prepare(Name, Tagged, Parent), Token)),
    metta_async_future_bind(Token, Name, Space, Done).

metta_py_async_start(Token) :-
    py_call(metta_ops:async_start(Token), Started),
    metta_py_bool(Started, true), !.
metta_py_async_start(Token) :-
    throw(error(metta_async_start_failed(Token),
                context(metta_py_async_start/1,
                        'the prepared coroutine was absent at commit'))).

metta_py_async_discard(Token) :-
    catch(py_call(metta_ops:async_discard(Token), _), _, true),
    metta_async_future_discard(Token).

metta_py_async_discard(Token, Space, Done) :-
    catch(py_call(metta_ops:async_discard(Token), _), _, true),
    metta_async_future_discard(Token, Space, Done).

metta_py_async_land(Token, Status0, Payload) :-
    metta_py_tag(Status0, Status),
    metta_async_future(Token, Name, Space, _),
    catch(metta_py_async_outcome(Status, Payload, Space, Outcome),
          Error,
          Outcome = error(Error)),
    %Terminal state precedes the landing notification: a synchronous landing
    %observer may await the future it was told has landed without deadlocking
    %the callback that still needs to settle it.
    metta_async_future_settle(Token, Outcome, Name, Space),
    metta_py_async_publish_landing(Name, Space).

%A watcher failure is raised to the background publisher and logged there; it
%cannot rewrite an operation outcome that was already committed to its future.
metta_py_async_publish_landing(Name, Space) :-
    (   'add-atom'('&metta', ['async-op', Name, Space, landing], _)
    ->  true
    ;   throw(error(metta_async_landing_publish_failed(Name, Space),
                    context(metta_py_async_land/3,
                            'the lifecycle write answered no result')))
    ).

metta_py_async_outcome(ok, Tagged, Space, done) :-
    (   metta_py_declined(Tagged)
    ->  true
    ;   metta_py_decode_shared(Tagged, Result, _),
        'add-atom'(Space, Result, _)
    ).
metta_py_async_outcome(cancelled, _, _, cancelled).
metta_py_async_outcome(error, [Class0, Exception], _,
                       error(error(python_error(Class, Exception), none))) :-
    metta_py_tag(Class0, Class).

:- multifile prolog:error_message//1.
prolog:error_message(metta_async_start_failed(Token)) -->
    [ 'async operation ~w was prepared but absent when its transaction committed'-[Token] ].
prolog:error_message(metta_async_landing_publish_failed(Name, Space)) -->
    [ 'async operation ~w could not publish its landing for ~w'-[Name, Space] ].

%A differential-only name for the retained host route. Production generic
%operations call metta_py_dispatch_det/3 directly, preserving their original
%one-clause path; native operations use this route only for opaque values.
metta_py_dispatch_det_host(Name, Args, Result) :-
    metta_py_dispatch_det(Name, Args, Result).

metta_py_native_eq(Left, Right, Result) :-
    metta_py_native_class(Left, LeftClass),
    metta_py_native_class(Right, RightClass),
    metta_py_native_eq_classes(LeftClass, Left, RightClass, Right, Result).

%Order matters: true and false are atoms in Prolog but bool is a numeric
%subclass in Python, and an unbound variable must never bind to either while
%being classified.
metta_py_native_class(Value, variable) :- var(Value), !.
metta_py_native_class(true, boolean) :- !.
metta_py_native_class(false, boolean) :- !.
metta_py_native_class(Value, number) :- number(Value), !.
metta_py_native_class(Value, string) :- string(Value), !.
metta_py_native_class(Value, symbol) :- atom(Value), !.
%The decoder has already proved an expression wire is a proper list. Inspect
%only its outer cell here: is_list/1 would walk the whole operand before the
%recursive comparison and would make repeated end-of-list comparisons
%quadratic in a traversal.
metta_py_native_class([], expression) :- !.
metta_py_native_class([_|_], expression).

metta_py_native_eq_classes(boolean, Left, boolean, Right, Result) :-
    metta_py_boolean_number(Left, LeftNumber),
    metta_py_boolean_number(Right, RightNumber),
    metta_py_numeric_eq(LeftNumber, RightNumber, Result).
metta_py_native_eq_classes(boolean, Left, number, Right, Result) :-
    metta_py_boolean_number(Left, LeftNumber),
    metta_py_numeric_eq(LeftNumber, Right, Result).
metta_py_native_eq_classes(number, Left, boolean, Right, Result) :-
    metta_py_boolean_number(Right, RightNumber),
    metta_py_numeric_eq(Left, RightNumber, Result).
metta_py_native_eq_classes(number, Left, number, Right, Result) :-
    metta_py_numeric_eq(Left, Right, Result).
metta_py_native_eq_classes(string, Left, string, Right, Result) :-
    ( Left == Right -> Result = true ; Result = false ).
metta_py_native_eq_classes(symbol, Left, symbol, Right, Result) :-
    ( Left == Right -> Result = true ; Result = false ).
metta_py_native_eq_classes(variable, Left, variable, Right, Result) :-
    ( Left == Right -> Result = true ; Result = false ).
metta_py_native_eq_classes(expression, Left, expression, Right, Result) :-
    metta_py_native_expression_eq(Left, Right, Result).
metta_py_native_eq_classes(_, _, _, _, false).

metta_py_boolean_number(true, 1).
metta_py_boolean_number(false, 0).

%Arithmetic comparison gives Python's numeric widening, signed-zero equality,
%and NaN inequality directly.
metta_py_numeric_eq(Left, Right, Result) :-
    ( Left =:= Right -> Result = true ; Result = false ).

metta_py_native_expression_eq([], [], true).
metta_py_native_expression_eq([], [_|_], false).
metta_py_native_expression_eq([_|_], [], false).
metta_py_native_expression_eq([Left|Lefts], [Right|Rights], Result) :-
    metta_py_native_eq(Left, Right, HeadResult),
    (   HeadResult == false
    ->  Result = false
    ;   metta_py_native_expression_eq(Lefts, Rights, Result)
    ).

metta_py_native_truthy(Value, Result) :-
    metta_py_native_class(Value, Class),
    metta_py_native_truth_class(Class, Value, Result).

metta_py_native_truth_class(variable, _, true).
metta_py_native_truth_class(boolean, Value, Value).
metta_py_native_truth_class(number, Value, Result) :-
    ( Value =:= 0 -> Result = false ; Result = true ).
metta_py_native_truth_class(string, Value, Result) :-
    ( Value == "" -> Result = false ; Result = true ).
metta_py_native_truth_class(symbol, _, true).
metta_py_native_truth_class(expression, Value, Result) :-
    ( Value == [] -> Result = false ; Result = true ).

%The guard wraps the whole enumeration and that is safe in both directions:
%catch/3 keeps Goal's choice points and re-establishes the catcher on
%backtracking, so a generator yielding two values and then raising is caught
%on the third [measured 2026-08-17: catch/3 over member/2 gives all three
%solutions, and a throw on the last one is caught].
metta_py_dispatch_many(Name, Args, Result) :-
    metta_py_encode_arguments(Args, TA, Table),
    (   metta_on_error_mode(Name, [Name|Args], DeclaredMode),
        DeclaredMode \== abort
    ->  Mode = DeclaredMode
    ;   Mode = abort
    ),
    catch(( metta_py_host_call(Name,
                              metta_py_call_many(Name, TA, Mode, TR0)),
            TR = TR0 ),
          Error, TR = '$metta_op_error'(Error)),
    (   TR = '$metta_op_error'(ManyError)
    ->  metta_py_op_erring(Name, Args, ManyError, Result)
    ;   metta_py_stream_error(TR, StreamError)
    ->  metta_py_failure([Name|Args], StreamError)
    ;   metta_py_relation_form(TR, Fields)
    ->  metta_py_relation_result(Fields, Args, Table, Result)
    ;   TR = [_, _, _, _|_]
    ->  metta_py_answer_result(TR, Name, Table, Result)
    ;   metta_py_decode_shared_(TR, Result, Table, _)
    ).

%Python cannot raise from inside py_iter/2 without Janus replacing the real
%exception with a bare SystemError. A generator therefore yields this reserved
%terminal frame; reconstruct the ordinary Janus error term and pass it through
%the same structured failure boundary as a deterministic operation.
metta_py_stream_error([Tag, Raise, Class0, Exception],
                      error(python_error(Class, Exception), none)) :-
    metta_py_tag(Tag, x),
    metta_py_tag(Raise, raise),
    metta_py_tag(Class0, Class).

%An encoded generator's exact tuple/dict yield is a relation row, tagged away
%from the atom wire. Python has already mapped sparse parameter names to their
%argument positions and checked the row shape. Decode every field against the
%call's shared variable table, then use the engine matcher itself: custom
%grounded matching, numeric promotion, space operands and the occurs check all
%remain one law. Failure filters the candidate; success binds the call and
%answers unit. py_iter contributes one choice point per yielded occurrence, so
%duplicates remain duplicates.
metta_py_relation_form([Tag, Fields], Fields) :-
    metta_py_tag(Tag, r).

metta_py_relation_result(Fields, Args, Table, []) :-
    metta_py_relation_fields(Fields, Args, Table, _).

metta_py_relation_fields(Fields, Args, Table0, Table) :-
    metta_py_relation_fields(Fields, Args, 0, Table0, Table).

metta_py_relation_fields([], _, _, Table, Table).
metta_py_relation_fields([[Index, Wire]|Fields], Args0, Offset, Table0, Table) :-
    integer(Index),
    Index >= Offset,
    Skip is Index - Offset,
    metta_py_relation_argument(Skip, Args0, Actual, Args),
    metta_py_decode_shared_(Wire, Candidate, Table0, Table1),
    metta_match_atoms(Candidate, Actual),
    Next is Index + 1,
    metta_py_relation_fields(Fields, Args, Next, Table1, Table).

metta_py_relation_argument(0, [Actual|Args], Actual, Args).
metta_py_relation_argument(Skip, [_|Args0], Actual, Args) :-
    Skip > 0,
    Next is Skip - 1,
    metta_py_relation_argument(Next, Args0, Actual, Args).

%An operation's declared error mode, consulted only in the recovery, so
%the success path pays one functor test. keep reduces the failed call to
%its (Error ...) atom; empty answers nothing, the semidet reading;
%control signals and transport failures always pass to the thrower.
metta_py_op_erring(Name, Args, Error, Result) :-
    (   control_exception(Error)
    ->  metta_py_failure([Name|Args], Error)
    ;   metta_transport_failure(Error)
    ->  metta_py_failure([Name|Args], Error)
    ;   metta_on_error_mode(Name, [Name|Args], Mode)
    ->  (   Mode == keep
        ->  metta_error_answer([Name|Args], Error, Result)
        ;   Mode == empty
        ->  fail
        ;   metta_py_failure([Name|Args], Error)
        )
    ;   metta_py_failure([Name|Args], Error)
    ).

%Raw results skip the wire encoding, so a Python boolean arrives as janus's
%@(true)/@(false); normalize to the language booleans exactly as 'py-call'
%does, so raw operations compose with if, and, or:
metta_py_raw_norm('@'(true), true) :- !.
metta_py_raw_norm('@'(false), false) :- !.
metta_py_raw_norm(R, R).

%A raw None is janus's @(none); it reads as no answer, the same semidet rule
%the encoded path applies, since MeTTa has no None value to hand back:
%The same catcher the encoded paths carry, and for the same reason: without it
%a raw operation's failure reaches MeTTa as janus's own term, holding the live
%exception OBJECT, a live TRACEBACK and an unbound context, so `(catch (op 1))`
%answered
%(Error (python_error ZeroDivisionError <ZeroDivisionError>)
%       (context $_26320 (python_stack <traceback>)))
%which names an address, cannot be compared and says nothing about which MeTTa
%call failed. Skipping the wire encoding is a speed decision about ARGUMENTS
%and results; it was never a decision to report failures differently
%[tested: test_a_raw_operation_fails_like_an_encoded_one].
%
%It costs one inference, and that is the floor rather than a choice: "the
%overhead of calling a goal through catch/3 is comparable to call/1"
%[source: SWI-Prolog manual, catch/3]. The zero-cost alternative was looked
%for and rejected. prolog:prolog_exception_hook/5 fires only on an actual
%exception, and it is a process-global singleton `library(prolog_stack)`,
%trap/1 and the GUI debugger already use, it "is never called recursively",
%and converting this error means calling back into Python to render the
%message, which is exactly what a non-reentrant hook must not do.
%
%Against the crossing it guards, one inference is not the number that matters:
%a raw operation costs 0.87 microseconds where a MeTTa function costs 0.09
%[measured 2026-08-17], so janus dominates it by an order of magnitude.
metta_py_dispatch_raw_det(Name, Args, Result) :-
    catch(metta_py_host_call(Name, metta_py_call_raw_det(Name, Args, R0)),
          Error, metta_py_failure([Name|Args], Error)),
    R0 \== '@'(none),
    metta_py_raw_norm(R0, Result).

metta_py_dispatch_raw_many(Name, Args, Result) :-
    catch(metta_py_host_call(Name, metta_py_call_raw_many(Name, Args, R0)),
          Error, metta_py_failure([Name|Args], Error)),
    (   metta_py_stream_error(R0, StreamError)
    ->  metta_py_failure([Name|Args], StreamError)
    ;   true
    ),
    R0 \== '@'(none),
    metta_py_raw_norm(R0, Result).

%Register every arity of a Python-backed function in one step, checked
%before anything mutates: a name whose compiled predicate would collide
%with a static procedure ((+)/3, say) throws HERE, with no state touched,
%and every previously registered arity of the name is replaced rather than
%left behind for calls the new callable no longer serves.
%The dogfood route: registration parameters read from the contract atoms in
%&metta rather than passed. The Python keywords are sugar that asserts the
%atoms ((op Name Arity Kind) per arity, (inverse Name) when a backwards
%direction exists), and this compiles the predicate FROM them, through
%exactly the builders the passed-parameter route uses, so the clause is
%identical by construction and the cube gate proves it stays that way.
metta_py_compile_op(Name0) :-
    ( atom(Name0) -> Name = Name0 ; atom_string(Name, Name0) ),
    findall(Arity-Kind, metta_contract_fact([op, Name, Arity, Kind]), Pairs),
    (   Pairs == []
    ->  throw(error(metta_contract_missing_op(Name), none))
    ;   true
    ),
    pairs_keys(Pairs, Arities),
    Pairs = [_-Kind|_],
    (   forall(member(_-K, Pairs), K == Kind)
    ->  true
    ;   throw(error(metta_contract_conflict(Name, Pairs), none))
    ),
    (   metta_contract_fact([inverse, Name])
    ->  Invertible = true
    ;   Invertible = false
    ),
    metta_py_register_op_set(Name, Arities, Kind, Invertible).

%A (handles ...) declaration, written and coherence-checked in one
%transaction: the new entry is asserted, every critical pair over the
%context is routed, and a disagreeing tie throws metta_contract_conflict,
%which rolls the assert back. The overlap is caught at declaration time
%naming both entries, not on the first query that falls into it.
metta_py_declare_handles(Space, Tagged, Ctx0) :-
    ( atom(Ctx0) -> Ctx = Ctx0 ; atom_string(Ctx, Ctx0) ),
    transaction(( metta_py_add(Space, Tagged),
                  metta_handles_coherent(Ctx) )).

:- multifile prolog:error_message//1.
prolog:error_message(metta_contract_missing_op(Name)) -->
    [ 'compiling ~w from the contract found no (op ~w Arity Kind) atom in \c
       &metta; the registration sugar asserts them before compiling, so \c
       reaching this means the atoms and the compile call got out of \c
       order'-[Name, Name] ].
prolog:error_message(metta_contract_conflict(Name, Pairs)) -->
    [ 'the contract atoms for ~w disagree on its kind across arities: ~w. \c
       One operation has one kind'-[Name, Pairs] ].

metta_py_register_op_set(Name0, Arities, Kind, Invertible) :-
    ( atom(Name0) -> Name = Name0 ; atom_string(Name, Name0) ),
    metta_py_set_invertible(Name, Invertible),
    %OPEN before any mutation: the tier refusal and the name probe both run
    %while there is still nothing to undo, and each one's diagnostic names
    %what to do about it. The unregister of prior arities may release the
    %name; the adopt below claims it again, so the set's final state is
    %claimed whatever order the arities land in.
    forall(member(A, Arities),
           (   metta_py_op_spec(Name, A, _)
           ->  true
           ;   PredArity is A + 1,
               metta_host_open_function(Name, python, PredArity)
           )),
    forall(metta_py_op_spec(Name, Old, _), metta_py_unregister_op(Name, Old)),
    forall(member(A, Arities), metta_py_register_op(Name, A, Kind)).

%The name probe, its owner-naming refusal and the metta_op_name_taken
%message live in the engine now (metta_host_open_function/3): the protocol
%was host-agnostic bookkeeping every binding restated in order. The one
%shortcut kept here is the caller's: an arity this file already registered
%occupies its own functor, so re-opening it proves nothing.

%Register a Python-backed function of the given MeTTa arity. The compiled
%predicate carries one extra output argument, the engine's own convention:
metta_py_register_op(Name0, Arity, Kind) :-
    ( atom(Name0) -> Name = Name0 ; atom_string(Name, Name0) ),
    metta_py_unregister_op(Name, Arity),
    length(Args, Arity),
    append(Args, [Result], HeadArgs),
    Head =.. [Name | HeadArgs],
    metta_py_op_body(Kind, Name, Args, Result, Forward),
    metta_py_directed_body(Name, Kind, Args, Result, Forward, Body),
    %Into &self's module, which every other space inherits, so the operation is
    %callable from all of them and its name is free: asserting into the module
    %the ENGINE resolves in is what made 217 ordinary names unusable at MeTTa
    %arity 1.
    metta_py_module('&self', Base),
    assertz(Base:(Head :- Body)),
    assertz(metta_py_op_spec(Name, Arity, Kind)),
    %Adopt AFTER the dispatch clause is in place: the engine marks the name a
    %function of the BASE tier (which every space inherits, so the operation
    %stays callable after a named space defines an equation of the same
    %name), refreshes dependents against the clause that already exists, and
    %claims the name for python.
    PredArity is Arity + 1,
    metta_host_adopt_function(Name, python, Kind, PredArity).

%The engine asks who a dispatch goal really is, so a purity refusal names the
%operation rather than this file's dispatcher. The name is the goal's first
%argument in all four kinds, which is why it is recoverable exactly.
:- multifile seam:effect_operation_name/3.
seam:effect_operation_name(metta_py_dispatch_det(Name, Args, _), Name, Arity) :-
    metta_py_dispatch_arity(Args, Arity).
seam:effect_operation_name(metta_py_dispatch_eq(_, _, _), 'py-eq', 2).
seam:effect_operation_name(metta_py_dispatch_truthy(_, _), 'py-truthy', 1).
seam:effect_operation_name(metta_py_dispatch_many(Name, Args, _), Name, Arity) :-
    metta_py_dispatch_arity(Args, Arity).
seam:effect_operation_name(metta_py_dispatch_async(Name, Args, _), Name, Arity) :-
    metta_py_dispatch_arity(Args, Arity).
seam:effect_operation_name(metta_py_dispatch_raw_det(Name, Args, _), Name, Arity) :-
    metta_py_dispatch_arity(Args, Arity).
seam:effect_operation_name(metta_py_dispatch_raw_many(Name, Args, _), Name, Arity) :-
    metta_py_dispatch_arity(Args, Arity).
seam:effect_operation_name(metta_py_dispatch_inverse(Name, _, Args), Name, Arity) :-
    metta_py_dispatch_arity(Args, Arity).
seam:effect_operation_name(metta_py_dispatch_inverse_raw(Name, _, Args), Name, Arity) :-
    metta_py_dispatch_arity(Args, Arity).

%The MeTTa arity, which is the argument list's length: the engine's extra
%output slot is the dispatch goal's third argument and not one of these.
metta_py_dispatch_arity(Args, Arity) :- is_list(Args), !, length(Args, Arity).
metta_py_dispatch_arity(_, unknown).

metta_py_op_body(det,      'py-eq', [Left, Right], R,
                 metta_py_dispatch_eq(Left, Right, R)) :- !.
metta_py_op_body(det,      'py-truthy', [Value], R,
                 metta_py_dispatch_truthy(Value, R)) :- !.
metta_py_op_body(det,      Name, Args, R, metta_py_dispatch_det(Name, Args, R)).
metta_py_op_body(many,     Name, Args, R, metta_py_dispatch_many(Name, Args, R)).
metta_py_op_body(async,    Name, Args, R, metta_py_dispatch_async(Name, Args, R)).
metta_py_op_body(raw_det,  Name, Args, R, metta_py_dispatch_raw_det(Name, Args, R)).
metta_py_op_body(raw_many, Name, Args, R, metta_py_dispatch_raw_many(Name, Args, R)).

:- dynamic metta_py_op_invertible/1.

metta_py_set_invertible(Name, Invertible) :-
    retractall(metta_py_op_invertible(Name)),
    ( ( Invertible == true ; Invertible == "true" )
      -> assertz(metta_py_op_invertible(Name)) ; true ).

%An operation that declared an inverse compiles a MODE TEST into its clause,
%and one that did not compiles exactly the body it compiled before. That is
%the point of deciding it here rather than in the dispatch: a direction almost
%no operation can serve must not cost every operation a check per call.
%
%The three modes read in the order a reader would ask them. Ground arguments
%are an ordinary forward call whatever the result slot holds, so a forward
%call never reaches the inverse even when the caller left the result unbound.
%Otherwise a bound result with unbound arguments is the relational position,
%which is what (let (f $h $t) (1 2 3) ...) compiles to. Anything else is
%forwards, and fails the way it always did, because an operation cannot
%invent a result from nothing.
%
%This is Curry's mode-directed reading of a function as a relation, done by
%hand because a foreign function cannot be narrowed: Curry does not invert its
%own `external` functions either, so an explicit backwards direction is the
%same answer Prolog's plus/3 and succ/2 give for their non-narrowable
%builtins [tested: test_a_registered_operation_runs_backwards].
metta_py_directed_body(Name, Kind, Args, Result, Forward, Body) :-
    (   metta_py_op_invertible(Name)
    ->  metta_py_inverse_goal(Kind, Name, Result, Args, Backward),
        Body = (   ground(Args)
               ->  Forward
               ;   nonvar(Result)
               ->  Backward
               ;   Forward
               )
    ;   Body = Forward
    ).

%The inverse crosses the way the operation's FORWARD direction crosses. An
%author writes one function pair, and a raw operation whose inverse went
%through the wire encoding saw `str` for a symbol going forwards and `Sym`
%coming back, which is one pair and two value conventions
%[tested: test_a_raw_operations_inverse_crosses_raw_too].
metta_py_inverse_goal(Kind, Name, Result, Args, Goal) :-
    (   metta_py_raw_kind(Kind)
    ->  Goal = metta_py_dispatch_inverse_raw(Name, Result, Args)
    ;   Goal = metta_py_dispatch_inverse(Name, Result, Args)
    ).

metta_py_raw_kind(raw_det).
metta_py_raw_kind(raw_many).

%One result in, argument tuples out. It enumerates, because an inverse is a
%relation: a result with two preimages answers twice, and one with none fails,
%which is failure rather than an error exactly as it is forwards.
%
%The arity is checked here rather than trusted, because the inverse is the
%author's own Python and a tuple of the wrong width would otherwise unify
%against nothing and read as "no solution" rather than as the mistake it is.
metta_py_dispatch_inverse(Name, Result, Args) :-
    metta_py_encode(Result, [], Table, TR),
    catch(metta_py_host_call(
              Name,
              metta_py_call_inverse(Name, TR, TArgs)),
          Error, metta_py_failure([Name, Result], Error)),
    metta_py_inverse_width(Name, Args, TArgs),
    metta_py_decode_arguments(TArgs, Table, Args).

metta_py_dispatch_inverse_raw(Name, Result, Args) :-
    catch(metta_py_host_call(
              Name,
              metta_py_call_inverse_raw(Name, Result, RawArgs)),
          Error, metta_py_failure([Name, Result], Error)),
    metta_py_inverse_width(Name, Args, RawArgs),
    maplist(metta_py_raw_norm, RawArgs, Args).

metta_py_call_inverse(Name, Result, Args) :-
    (   nb_current('$metta_python_context', Context), integer(Context)
    ->  py_iter(metta_ops:dispatch_inverse_context(Context, Name, Result), Args)
    ;   py_iter(metta_ops:dispatch_inverse(Name, Result), Args)
    ).

metta_py_call_inverse_raw(Name, Result, Args) :-
    (   nb_current('$metta_python_context', Context), integer(Context)
    ->  py_iter(metta_ops:dispatch_inverse_raw_context(Context, Name, Result),
                Args)
    ;   py_iter(metta_ops:dispatch_inverse_raw(Name, Result), Args)
    ).

metta_py_inverse_width(Name, Args, Answered) :-
    length(Args, Arity),
    (   is_list(Answered), length(Answered, Arity)
    ->  true
    ;   metta_py_inverse_arity_error(Name, Arity, Answered)
    ).

%ONE table across the answered tuple, seeded with the map the result was
%encoded under. Decoding argument by argument started an empty table at each
%one, so a variable an inverse put in two positions came back as two
%variables, and a variable it took from the RESULT came back as neither the
%result's nor its own. Nothing unifies these afterwards the way a match
%candidate is unified with its pattern: Args is bound from the decode and
%that is the answer.
metta_py_decode_arguments([], _, []).
metta_py_decode_arguments([Tagged|Rest], Table0, [Term|Terms]) :-
    metta_py_decode_shared_(Tagged, Term, Table0, Table),
    metta_py_decode_arguments(Rest, Table, Terms).

metta_py_inverse_arity_error(Name, Arity, TArgs) :-
    ( is_list(TArgs) -> length(TArgs, Got) ; Got = 1 ),
    throw(error(metta_py_inverse_arity(Name, Arity, Got),
                context(metta, 'the inverse answered the wrong number of arguments'))).

:- multifile prolog:error_message//1.

%A tuple of the wrong width would otherwise unify against nothing and read as
%"this result has no preimage", which is the one answer an inverse is entitled
%to give and the one that hides the mistake.
prolog:error_message(metta_py_inverse_arity(Name, Wanted, Got)) -->
    [ 'the inverse of ~w answered an argument tuple of width ~d, and the \c
       operation takes ~d'-[Name, Got, Wanted], nl,
      '  an inverse returns the arguments as a tuple of that width, or the \c
       bare value at arity one' ].

%Remove one registered arity of an operation, leaving other arities alone.
%When nothing defines the name any more, forget the function entirely, the
%same forgetting 'remove-atom'/3 does when a last equation goes: fun/1 and
%arity/2 retract, so the next compile treats the name as data again:
metta_py_unregister_op(Name0, Arity) :-
    ( atom(Name0) -> Name = Name0 ; atom_string(Name, Name0) ),
    %The drop is guarded by this file's own bookkeeping, so only arities this
    %file registered are dropped; the engine's drop then retracts the base
    %tier's clauses and the arity row generically.
    ( metta_py_op_spec(Name, Arity, _)
      -> PredArity is Arity + 1,
         metta_host_drop_function(Name, PredArity),
         retractall(metta_py_op_spec(Name, Arity, _))
    ; true ),
    %"does anything still define this name at any arity" is a question about
    %OUR clauses, and clause/3 raises permission_error(access,
    %private_procedure, _) on a protected system predicate rather than
    %answering it, so unregistering an operation named print or format threw
    %from here instead of unregistering. A builtin is never a clause of ours
    %[tested test_unregistering_a_name_a_system_predicate_shares_does_not_throw].
    ( \+ metta_py_name_still_defined(Name)
      -> metta_host_forget_function(Name)
    ; true ).

%Does anything still define this name at any arity? Two tiers are asked by
%name because ONE of them cannot be reached by generating: current_predicate/1
%with the arity unbound enumerates a module's own predicates and the ones
%explicitly imported into it, and NOT the ones it reaches through its base
%chain. A registered operation's clauses are in the base tier's module and a
%Prolog function's are in the host's, so asking either alone released a name
%the other still defined: registering an operation over a Prolog registration
%was refused, correctly, and dropped the Prolog one's arity/2 and fun/1 on the
%way out, so the call it had been answering came back unreduced
%[tested test_a_prolog_registration_is_not_silently_replaced].
metta_py_name_still_defined(Name) :-
    spaces:metta_ensure_compiled(Name),
    ( metta_py_module('&self', Module) ; metta_engine_module(Module) ),
    current_predicate(Module:Name/A),
    functor(Head, Name, A),
    \+ predicate_property(Module:Head, built_in),
    clause(Module:Head, _, _),
    !.

%The names a source declared for itself, so register_prolog can answer what it
%registered without being told. The membership record is the engine's, not the
%library's, which is what makes the extension a unit rather than a list the
%library has to keep: it registers, and the engine remembers
%[source: PostgreSQL, "the objects of the extension go together"].
%The file is compared after resolving both sides, because the engine records
%SWI's canonical absolute path and a caller passes whatever they typed.
%Read off the FILE record rather than off extension membership. An extension
%is optional on the Prolog side, so asking through one made a file with
%`metta_export` and no `metta_extension` look like a failed registration when
%every name in it had registered.
%What a source declares, read WITHOUT running it, so register_prolog can
%refuse a file that declares nothing before consulting it. It used to consult
%first and check after, so a provider file with no declaration raised and
%installed the provider anyway: catching the error made everything work, which
%is the one outcome that teaches an author to ignore an error.
metta_py_source_declares(Source0, Declares) :-
    ( atom(Source0) -> Source = Source0 ; atom_string(Source, Source0) ),
    metta_source_declarations(Source, Declarations),
    metta_py_classify_declarations(Declarations, Declares).

%The same question of source held in memory, which has no file to open.
metta_py_string_declares(Text, Declares) :-
    metta_string_declarations(Text, Declarations),
    metta_py_classify_declarations(Declarations, Declares).

metta_py_classify_declarations(Declarations, Declares) :-
    ( memberchk(export(_), Declarations) -> Exports = true ; Exports = false ),
    ( memberchk(extension(_), Declarations) -> Extension = true
    ; Extension = false ),
    metta_py_declares(Exports, Extension, Declares).

metta_py_declares(true, true, "both").
metta_py_declares(true, false, "exports").
metta_py_declares(false, true, "extension").
metta_py_declares(false, false, "nothing").

metta_py_declared_exports(Source0, Names) :-
    ( atom(Source0) -> Source = Source0 ; atom_string(Source, Source0) ),
    ( absolute_file_name(Source, Resolved, [file_errors(fail)]) -> true
    ; Resolved = Source ),
    findall(S,
            ( metta_file_export(Recorded, Name),
              ( Recorded == Resolved -> true ; Recorded == Source ),
              atom_string(Name, S) ),
            Names0),
    sort(Names0, Names).

%The names one extension installed, asked before releasing them so the caller
%can be told what went.
metta_py_extension_members(Name0, Names) :-
    ( atom(Name0) -> Name = Name0 ; atom_string(Name, Name0) ),
    findall(S, ( metta_extension_member(Name, Member), atom_string(Member, S) ), Names).

%Everything one extension installed, released together.
metta_py_unregister_extension(Name0) :-
    ( atom(Name0) -> Name = Name0 ; atom_string(Name, Name0) ),
    unregister_metta_extension(Name).

%Every function or translator special-form name the language knows, for
%completion and docs. The special forms come from the translator's published
%service rather than from its clause table: this used to read
%clause(Engine:translate_special_dl(...), _) directly, and the moment the
%compiler's clauses moved into a module of their own the read matched nothing
%and m.builtins() quietly answered 31 names short, with no error anywhere
%[measured 2026-08-22: 268 names before the translator became a module, 237
%after, 268 again through the service].
metta_py_builtins(Names) :-
    findall(N, fun(N), Functions),
    metta_py_special_form_names(SpecialForms),
    append(Functions, SpecialForms, Language0),
    sort(Language0, Language),
    maplist(atom_string, Language, Names).

metta_py_function_generation(Generation) :-
    metta_host_function_generation(Generation).

%Whether ANY deprecation declaration exists, as 1/0 through the apply seam.
%The catalog is almost always empty, and the callable doors' first-call
%deprecation read through a fresh once/1 goal string measured 1,311
%inferences where this apply-seam probe is double digits, the same
%once-versus-apply gap metta_py_catalogue_member/1 documents below
%[tested: test_an_empty_deprecation_catalog_costs_one_cheap_probe].
metta_py_deprecation_declared(Flag) :-
    ( metta_deprecation(_, _, _) -> Flag = 1 ; Flag = 0 ).

metta_py_special_form_names(Names) :-
    findall(Name, metta_special_form_head(Name), Names0),
    sort(Names0, Names).

metta_py_is_function(Name0) :-
    ( atom(Name0) -> Name = Name0 ; atom_string(Name, Name0) ),
    fun(Name).

%Point membership in the catalogue metta_py_builtins/1 lists: one indexed
%fun/1 probe, then the special-form heads, instead of materializing and
%string-converting the whole catalogue. The bound namespace asks this on
%every attribute resolution, and the full read it replaces measured 1,347
%inferences on the first access after any definition where this probe is
%double digits [measured 2026-08-24; consumer _FunctionNamespace._known].
metta_py_catalogue_member(Name0) :-
    ( atom(Name0) -> Name = Name0 ; atom_string(Name, Name0) ),
    ( fun(Name) -> true
    ; once(metta_special_form_head(Name))
    ).

%Whether a function ANSWERS from this space: it has clauses its module can
%see, its own or inherited from user. Another space's equations live in that
%space's module and are invisible here, so they do not count.
metta_py_function_visible(Space0, Name0) :-
    ( atom(Space0) -> Space = Space0 ; atom_string(Space, Space0) ),
    ( atom(Name0) -> Name = Name0 ; atom_string(Name, Name0) ),
    fun(Name),
    %The question is about clauses, and a deferred function has none until
    %its equations translate; the clause probe below is a read the
    %undefined-predicate net never fires for.
    spaces:metta_ensure_compiled(Name),
    metta_py_module(Space, Module),
    catch_recover(( current_predicate(Module:Name/Arity),
                    functor(Head, Name, Arity),
                    clause(Module:Head, _, _) ),
                  fail), !.

metta_py_arities(Name0, As) :-
    ( atom(Name0) -> Name = Name0 ; atom_string(Name, Name0) ),
    %Compiled arities are registered at translation, so the read forces.
    spaces:metta_ensure_compiled(Name),
    findall(A, arity(Name, A), As).

%Every stored equation for a name, live from the space. Pattern-directed:
%a native space answers by first-argument index on '=', a foreign space
%enumerates and unifies, and the open tail in the head pattern is Prolog
%unification against stored lists, not the MeTTa matcher.
metta_py_equations(Space, Name0, Encoded) :-
    ( atom(Name0) -> Name = Name0 ; atom_string(Name, Name0) ),
    Pattern = [=, [Name|_], _],
    findall(E, ( metta_host_stored(Space, Pattern),
                 metta_py_encode(Pattern, E) ), Encoded).

%The Prolog clauses a name compiled to, dis for the translator: one
%listing per registered arity, resolved in this space's module so a named
%space shows the clauses it would run. Fails on a name the engine never
%compiled, and the Python side turns that into its own refusal.
metta_py_disassemble(Space, Name0, Text) :-
    ( atom(Name0) -> Name = Name0 ; atom_string(Name, Name0) ),
    %The listing below is a read, so a deferred function would show nothing
    %and register no arity; the disassembly IS the demand.
    spaces:metta_ensure_compiled(Name),
    findall(A, arity(Name, A), As0),
    As0 \== [],
    sort(As0, As),
    space_module(Space, Module),
    with_output_to(string(Text),
                   forall(member(A, As),
                          (   current_predicate(Module:Name/A)
                          ->  listing(Module:Name/A)
                          ;   true ))).

%%%%%%%%%% Derivation trees %%%%%%%%%%
%
% The classic proof-tree meta-interpreter, rendered in MeTTa terms: every
% compiled clause remembers its source equation through translated_from/2,
% so each node names the equation that fired, a stored atom is a leaf, and a
% builtin call is an opaque leaf. Control constructs recurse into the branch
% they execute. A finite depth emits a truncated node rather than claiming no
% proof. Negative depth means unbounded; Python puts that search behind the
% same time and inference guards as evaluation.

metta_py_derivations(Space, Tagged, Depth, Trees) :-
    findall(Tree, metta_py_derivation(Space, Tagged, Depth, Tree), Trees).

metta_py_derivation(Space, Tagged, Depth, TreeTagged) :-
    metta_py_decode_shared(Tagged, Term, _),
    Term = [F|Args],
    atom(F),
    append(Args, [Out], FullArgs),
    Goal =.. [F|FullArgs],
    metta_py_module(Space, Module),
    metta_py_in_module(Module, metta_py_solve(Module, Goal, Depth, Tree)),
    metta_py_encode_tree(Tree, [F|Args], Out, TreeTagged).

metta_py_solve(M, Goal, D, Tree) :-
    metta_py_solve_barrier(M, Goal, D, Tree, _).

%A cut prunes the clauses that follow it and the choicepoints that precede
%it in the same body. Recorded as a leaf and simply called, it pruned
%neither, so the tree proved conclusions the program cannot reach: two
%equations for one head, the first cutting, proved both while run answered
%only the first.
%
%That is the naive incorporation the literature names and rejects: "A naive
%incorporation of cuts treats them as a builtin predicate, effectively
%adding a clause solve(!) <- !. This clause does not achieve the correct
%behavior of cut. The cut in the clause commits to the current solve clause
%rather than pruning the search tree." What has to be modelled instead is
%the cut's SCOPE, the clause in which the cut is a goal
%[source: Sterling and Shapiro, The Art of Prolog, 2nd ed., p327, ch17].
%That page states the problem and refers the solution out, so the technique
%below is this engine's own.
%
%Passing a cut signal upward prunes the later clauses but not the earlier
%goals, so the cut throws instead. Every construct that is a cut barrier in
%Prolog, a clause body, call/1, once/1, \+/1, findall/3 and an if-then-else
%condition, catches its own throw and turns it into failure, which discards
%the goals inside it and the clauses beside it together. That is what a cut
%does [tested: test_derivation_honours_a_cut].
metta_py_solve_barrier(M, Goal, D, Tree, Status) :-
    gensym('$metta_py_cut_', Barrier),
    catch(metta_py_solve_(M, Goal, D, Tree, Status, Barrier),
          metta_py_cut(Barrier),
          fail).

metta_py_solve_(_, Goal, 0, [truncated(Goal)], truncated, _) :- !.
metta_py_solve_(_, true, _, [], complete, _) :- !.
metta_py_solve_(_, '!', _, [builtin(!)], complete, Barrier) :- !,
    ( true ; throw(metta_py_cut(Barrier)) ).
metta_py_solve_(M, (If -> Then ; Else), D, Tree, Status, Barrier) :- !,
    ( metta_py_solve_barrier(M, If, D, IfTree, IfStatus)
      -> ( IfStatus == truncated
           -> Tree = IfTree, Status = truncated
         ; metta_py_solve_(M, Then, D, ThenTree, Status, Barrier),
           append(IfTree, ThenTree, Tree) )
    ; metta_py_solve_(M, Else, D, Tree, Status, Barrier) ).
metta_py_solve_(M, (If -> Then), D, Tree, Status, Barrier) :- !,
    ( metta_py_solve_barrier(M, If, D, IfTree, IfStatus)
      -> ( IfStatus == truncated
           -> Tree = IfTree, Status = truncated
         ; metta_py_solve_(M, Then, D, ThenTree, Status, Barrier),
           append(IfTree, ThenTree, Tree) )
    ; fail ).
%The SOFT cut, which the engine writes wherever a call must keep every answer
%and still have an else arm: the typed-dispatch fallback is
%`( <branches> *-> true ; dispatch_mismatch_result(...) )` and the error
%short circuit is `( <call> *-> true ; <recovery> )`. Without these two clauses
%the pair below reads the whole construct as one opaque builtin, so a proof
%stopped at the wrapper instead of descending into the call it wraps: the
%recursive branch of a conditional equation showed one rule where three fired
%[tested: test_conditional_derivation_exposes_the_recursive_branch]. They sit
%ABOVE the plain disjunction because `( If *-> Then ; Else )` IS a disjunction
%whose left side is the soft cut, and that reading loses the else arm's
%condition.
metta_py_solve_(M, (If *-> Then ; Else), D, Tree, Status, Barrier) :- !,
    (   metta_py_solve_barrier(M, If, D, IfTree, IfStatus)
    *-> ( IfStatus == truncated
          -> Tree = IfTree, Status = truncated
        ; metta_py_solve_(M, Then, D, ThenTree, Status, Barrier),
          append(IfTree, ThenTree, Tree) )
    ;   metta_py_solve_(M, Else, D, Tree, Status, Barrier) ).
metta_py_solve_(M, (If *-> Then), D, Tree, Status, Barrier) :- !,
    metta_py_solve_barrier(M, If, D, IfTree, IfStatus),
    ( IfStatus == truncated
      -> Tree = IfTree, Status = truncated
    ; metta_py_solve_(M, Then, D, ThenTree, Status, Barrier),
      append(IfTree, ThenTree, Tree) ).
metta_py_solve_(M, (A ; B), D, Tree, Status, Barrier) :- !,
    ( metta_py_solve_(M, A, D, Tree, Status, Barrier)
    ; metta_py_solve_(M, B, D, Tree, Status, Barrier) ).
metta_py_solve_(M, (A, B), D, Tree, Status, Barrier) :- !,
    metta_py_solve_(M, A, D, TA, SA, Barrier),
    ( SA == truncated
      -> Tree = TA, Status = truncated
    ; metta_py_solve_(M, B, D, TB, Status, Barrier),
      append(TA, TB, Tree) ).
metta_py_solve_(M, call(A), D, Tree, Status, _) :- !,
    metta_py_solve_barrier(M, A, D, Tree, Status).
metta_py_solve_(M, once(A), D, Tree, Status, _) :- !,
    once(metta_py_solve_barrier(M, A, D, Tree, Status)).
metta_py_solve_(M, \+ A, D, Tree, Status, _) :- !,
    ( once(metta_py_solve_barrier(M, A, D, TA, SA))
      -> ( SA == truncated
           -> Tree = TA, Status = truncated
         ; fail )
    ; Tree = [builtin(\+ A)], Status = complete ).
metta_py_solve_(M, findall(Template, Goal, List), D, Tree, Status, _) :- !,
    findall([Template, SubTree, SubStatus],
            metta_py_solve_barrier(M, Goal, D, SubTree, SubStatus),
            Results),
    metta_py_findall_results(Results, Values, Tree, Status),
    ( Status == complete -> List = Values ; true ).

%The P3 dispatcher is engine machinery, but its shipped fast path wraps an
%ordinary generated goal. Treating the wrapper as a generic Prolog predicate
%enumerated its implementation clauses as separate proofs and ran the wrapped
%recursion through call/1, outside the derivation depth counter. Open the fast
%path and keep its direct goal inside this interpreter. A non-default policy is
%still executed by the authoritative dispatcher and recorded as one opaque
%builtin; duplicating its retained-clause interpreter here would let proofs and
%evaluation drift on the six policy axes.
metta_py_solve_(_,
                dispatch_policy_execute(Module, Fun, Args, Goal, Out),
                D, Tree, Status, Barrier) :-
    !,
    metta_host_dispatch_proof_step(Module, Fun, Args, Goal, Out, Route),
    (   Route == direct
    ->  metta_py_solve_(Module, Goal, D, Tree, Status, Barrier)
    ;   Route == opaque,
        Tree = [builtin(dispatch_policy_execute(Module, Fun, Args, Goal, Out))],
        Status = complete
    ).

%Application/result protocol helpers only classify the value the preceding
%goal produced.  They are transparent proof steps: retaining a call or exposing
%NotReducible is not another premise and must not turn a recursive MeTTa call
%into an opaque builtin leaf.
metta_py_solve_(M, metta_application_result(Written, Produced, Out), _,
                [], complete, _) :- !,
    call(M:metta_application_result(Written, Produced, Out)).
metta_py_solve_(M,
                metta_application_result(Source, Runtime, Produced, Out), _,
                [], complete, _) :- !,
    call(M:metta_application_result(Source, Runtime, Produced, Out)).
metta_py_solve_(M, metta_boundary_result(Written, Produced, Out), _,
                [], complete, _) :- !,
    call(M:metta_boundary_result(Written, Produced, Out)).

%A clause compiled from a MeTTa equation is a step worth showing, and its body
%is walked further. Everything else, engine machinery and space facts alike, is
%called whole and appears as one leaf, so the tree stays in MeTTa terms. The
%lookup is module-qualified: a named space's equations live in its module, and
%clause/3 falls back to user through module inheritance for the rest. Only the
%clause INSPECTION is guarded (an uninspectable goal is an opaque leaf); a
%body or builtin that ERRS propagates, because (+ $x $y) failing into "no
%proof" would be a lie about why (integer zero division is Error data):
%One barrier serves every clause of the goal, because a cut in the body of
%one clause discards the clauses after it as well as its own alternatives.
metta_py_solve_(M, Goal, D, Tree, Status, _) :-
    \+ predicate_property(M:Goal, built_in),
    gensym('$metta_py_cut_', Barrier),
    catch(metta_py_solve_clause(M, Goal, D, Tree, Status, Barrier),
          metta_py_cut(Barrier),
          fail).
metta_py_solve_(M, Goal, _, [builtin(Goal)], complete, _) :-
    predicate_property(M:Goal, built_in), !,
    call(M:Goal).

%A clause's body runs in the module that DEFINES the clause, which is the
%space's module for a MeTTa equation and an engine subsystem's for engine
%machinery. Running it in the caller's module worked only while the whole
%engine shared one namespace: once engine/spaces.pl became a module of its own,
%descending into match/4 and calling its body under the space gave
%existence_error(procedure, '$metta_exec:&self':match_native/5), because
%match_native/5 is spaces' own and a base module lends only what it exports
%[measured 2026-08-22, on every test in tests/test_derivation.py].
metta_py_solve_clause(M, Goal, D, Tree, Status, Barrier) :-
    %clause/2 is a read, not a call, so the undefined-predicate net never
    %fires for a deferred callee and the proof walk saw zero clauses where
    %evaluation answers. Force the name at every step: the tree descends
    %into callees the running program may never have reached.
    (   Goal =.. [Predicate|_],
        translator:compiled_function_name(Fun, Predicate)
    ->  spaces:metta_ensure_compiled(Fun)
    ;   true
    ),
    metta_py_clause_owner(M, Goal, Owner),
    catch_recover(clause(Owner:Goal, Body, Ref), fail),
    ( translated_from(Ref, Source)
      -> metta_py_next_depth(D, D1),
         metta_py_body_after_stack_charge(Owner, Body, Premises),
         metta_py_solve_(Owner, Premises, D1, Sub, Status, Barrier),
         Tree = [step(Goal, Source, Sub)]
    ; call(Owner:Body),
      %The LEAF keeps the caller's module, because what it names is the space
      %the fact came from and not the subsystem that ran the goal.
      metta_py_leaf(M, Goal, Tree),
      Status = complete ).

%catch_recover/2 rather than catch/3, because this runs once per level of a
%derivation and a blanket catch swallows the very signals that stop an
%unbounded one: inference_limit_exceeded arriving inside predicate_property/2
%was caught here and the loop ran on to a stack overflow at depth 9,673,261
%instead of raising at 2,000 inferences
%[measured 2026-08-22; tested: test_unbounded_derivation_obeys_resource_guards].
metta_py_clause_owner(M, Goal, Owner) :-
    (   catch_recover(predicate_property(M:Goal,
                                         implementation_module(Definer)),
                      fail)
    ->  Owner = Definer
    ;   Owner = M
    ).

%A recursive equation's clause opens with the stack charge that
%engine/spaces/foreign.pl's metta_instrument_recursive_clause/3 writes in front
%of the translated body, built by engine/metta/control.pl's
%metta_fuel_step_goal/3. That charge is the engine counting its own recursion
%depth, not a premise of the program being proved, so it contributes no node.
%Walked as ordinary goals it put `builtin
%system:b_getval('$metta_fuel_remaining',off)` and `builtin off==off` in front
%of every premise of every recursive equation
%[tested: test_a_recursive_proof_omits_the_engine_stack_charge].
%
%RECOGNISED by the engine, not by a shape spelled again here. Every binding
%that walks compiled clauses meets this charge, so the recogniser is
%metta_host_stack_charge/3 beside the generator that writes it and the next
%seat does not re-pay it. It hands the charge back rather than running it,
%because a clause body runs in the module that DEFINES the clause and only this
%caller knows which that is.
%
%CALLED rather than skipped, at the point the body would have run it. A proof
%walk opens no fuel scope of its own, so the balance reads `off` and the charge
%decides nothing today; derivation bounds its search with the timeout and
%inference guards instead [tested:
%test_unbounded_derivation_obeys_resource_guards]. Calling it keeps that a
%property of the SCOPE rather than of this predicate, so a proof walked inside
%an open scope is charged exactly as evaluation is.
%
metta_py_body_after_stack_charge(Owner, Body, Premises) :-
    metta_host_stack_charge(Body, Charge, Premises), !,
    call(Owner:Charge).
metta_py_body_after_stack_charge(_, Body, Body).

metta_py_findall_results([], [], [], complete).
metta_py_findall_results(
    [[Value, SubTree, SubStatus]|Results], [Value|Values], Tree, Status) :-
    metta_py_findall_results(Results, Values, RestTree, RestStatus),
    append(SubTree, RestTree, Tree),
    ( SubStatus == truncated -> Status = truncated ; Status = RestStatus ).

metta_py_next_depth(D, D) :- D < 0, !.
metta_py_next_depth(D, D1) :- D1 is D - 1.

%A match over a space names the atom it found; anything else names its goal:
metta_py_leaf(_, match(Space, Pattern, _, _), [fact(Space, Pattern)]) :- !.
metta_py_leaf(Module, Goal, [fact(Space, Fact)]) :-
    metta_host_native_fact(Module, Goal, Space, Fact), !.
metta_py_leaf(_, Goal, [fact('&self', Fact)]) :-
    functor(Goal, Space, _),
    atom_concat('&', _, Space), !,
    Goal =.. [Space|Fact].
metta_py_leaf(_, Goal, [builtin(Goal)]).

%The tree crosses as nested tagged expressions:
%  (derivation Conclusion Steps...) with each step
%  (step Conclusion (= Head Body) Substeps...), (fact Atom), (builtin Text),
%  or (truncated Goal).
%NAMED, because metta_py_encode/2 spells a variable with term_to_atom/2 and
%SWI derives that spelling from the cell's global-stack offset, which a
%garbage collection moves. One variable therefore crossed under two names
%when a collection landed between two of its occurrences, and the sharing
%decoder, which aliases by name, read two variables. A five-deep (fact 5)
%proof crossed as
%  (= (fact $_17642) (if (> $_17642 0) (* $_17642 (fact (- $_2528 1))) 1))
%whose free $_2528 made the body non-ground, so the consumer's substitution
%left (- $_2528 1) and evaluating it raised the CLP(FD) refusal rather than
%answering [measured 2026-08-31 against a proof tree of six steps].
%
%A whole tree is one term, so its variables are named ONCE from
%term_variables/2's order, which is a property of the term and not of the
%stack. That is engine/tracer.pl's metta_trace_variable_names/3 exactly: _0,
%_1 and so on by first occurrence, carried beside the term as Name-Var pairs
%and resolved by metta_py_var_name/3's identity lookup
%[source: engine/tracer.pl, metta_trace_variable_names/3].
metta_py_encode_tree(Steps, Root, Out, ["e", [["s", "derivation"], RootE | StepEs]]) :-
    metta_py_encode([Root, '=', Out], [], Names0, ["e", [R, _, O]]),
    RootE = ["e", [["s", "answer"], R, O]],
    metta_py_encode_steps(Steps, Names0, _, StepEs).

metta_py_encode_steps([], N, N, []).
metta_py_encode_steps([Step|Steps], N0, N, [E|Es]) :-
    metta_py_encode_step(Step, N0, N1, E),
    metta_py_encode_steps(Steps, N1, N, Es).

metta_py_encode_step(step(Goal, Source, Sub), N0, N,
                     ["e", [["s", "step"], GoalE, SourceE | SubEs]]) :-
    metta_py_encode_goal(Goal, N0, N1, GoalE0),
    metta_py_goal_term(GoalE0, GoalE),
    metta_py_encode(Source, N1, N2, SourceE),
    metta_py_encode_steps(Sub, N2, N, SubEs).
%A leaf's space is the NAME of the space the fact came from, an atom, so the
%map reaches it and comes back unchanged. Threaded rather than asserted
%unchanged, because pinning it would turn a space that is somehow not an atom
%into a silent failure instead of an encoding.
metta_py_encode_step(fact(Space, Fact), N0, N,
                     ["e", [["s", "fact"], SpaceE, FactE]]) :-
    metta_py_encode(Space, N0, N1, SpaceE),
    metta_py_encode(Fact, N1, N, FactE).
metta_py_encode_step(builtin(Goal), N0, N,
                     ["e", [["s", "builtin"], ["g", Text]]]) :-
    metta_py_written_goal(Goal, N0, N, Text).
metta_py_encode_step(truncated(Goal), N0, N,
                     ["e", [["s", "truncated"], ["g", Text]]]) :-
    metta_py_written_goal(Goal, N0, N, Text).

%A leaf that crosses as TEXT rather than as structure still holds the tree's
%variables: the solver records goals such as builtin(\+ A) whose A an
%equation beside it also holds. term_string/2 wrote the cell's address there
%while the equation carried the tree's name for the same variable, so a
%reader could not see that the two are one. write_term/2's variable_names
%option takes the same map spelled Name=Var.
metta_py_written_goal(Goal, Names0, Names, Text) :-
    term_variables(Goal, Variables),
    metta_py_wire_names(Variables, Names0, Names),
    metta_py_name_assignments(Names, Assignments),
    term_string(Goal, Text, [variable_names(Assignments)]).

%A written leaf mints its variables' names the way an encoded one does, so
%the two spell one cell the same. Only the map moves; nothing is encoded.
metta_py_wire_names([], N, N).
metta_py_wire_names([Variable|Rest], N0, N) :-
    metta_py_wire_name(Variable, N0, N1, _),
    metta_py_wire_names(Rest, N1, N).

metta_py_name_assignments([], []).
metta_py_name_assignments([Name-Variable|Pairs], [Name=Variable|Assignments]) :-
    metta_py_name_assignments(Pairs, Assignments).

%metta_py_encode_named/3 carries its pairs through variables and lists and
%hands every other compound to the unscoped encoder, and a step's goal is a
%compiled call f(A1..An, Out), which is one. Encoding it unscoped inside a
%tree that is otherwise named is worse than naming nothing: a variable a
%parent's equation and a child's goal share would cross under two names and
%stop being one variable. Goal is a clause head, so it is an atom or a
%compound with an atom functor, and the list [f, A1..An, Out] encodes to the
%same ["e", [["s", f] | Es]] the compound clause writes.
metta_py_encode_goal(Goal, N0, N, Encoded) :-
    compound(Goal),
    compound_name_arguments(Goal, Functor, Arguments),
    atom(Functor), !,
    metta_py_encode([Functor|Arguments], N0, N, Encoded).
metta_py_encode_goal(Goal, N0, N, Encoded) :-
    metta_py_encode(Goal, N0, N, Encoded).

%A compiled goal f(A1..An,Out) renders as the call (f A1..An) with its answer:
metta_py_goal_term(["e", [F | ArgsAndOut]], ["e", [["s", "call"], ["e", [F|Args]], Out]]) :-
    append(Args, [Out], ArgsAndOut), !.
metta_py_goal_term(E, ["e", [["s", "call"], E, ["s", "?"]]]).

%%%%%%%%%% Foreign spaces %%%%%%%%%%
%
% A space whose atoms live in a Python provider: a database, a dataframe, an
% API. The engine's hooks route match, add, remove and get-atoms here; the
% provider enumerates candidate atoms for a pattern, and unification against
% the pattern happens in Prolog, so the provider may over-approximate freely
% and soundness stays the engine's. Registration is dynamic, from Python.

:- multifile seam:foreign_space/1.
:- multifile seam:foreign_match/3.
:- multifile seam:foreign_add/2.
:- multifile seam:foreign_add_many/2.
:- multifile seam:foreign_plan/5.
:- multifile seam:foreign_remove/3.
:- multifile seam:foreign_atoms/2.
:- multifile seam:foreign_pushdown/3.
:- multifile seam:foreign_capability/2.
:- multifile seam:foreign_refuse/2.

:- dynamic metta_py_foreign/1.
:- dynamic metta_py_capability/2.

%What a Python provider provides, in the ENGINE's vocabulary.
%
%The seam had two capability models that never met. foreign.py derives the set
%from the narrow protocols a provider implements and enforces it well; the
%Prolog side reads seam:foreign_capability/2 and saw nothing, so
%foreign_provides/2 reported that every Python provider provides EVERYTHING.
%Not a correctness bug, because the Python half raises anyway, but it meant
%engine logic keyed on a declaration silently excluded exactly the providers
%most likely to be incomplete, and a sixth capability could never be added to
%the vocabulary: claimed by silence on one side, unheard on the other.
%
%A projection rather than a new obligation. The set is computed where it
%already was, at registration, and provider authors write nothing new
%[tested: test_a_python_providers_capabilities_reach_the_engine].

%Each clause guards on the python registry: the foreign hooks are
%multifile, and an engine-side foreign space (a Redis space, say) must
%fall through to its own contribution instead of being claimed here.
%seam:foreign_clear/1 is declared with the other five in engine/ext_points.pl
%now, so it is part of the seam a library author reads rather than something
%only this file knew about.

seam:foreign_space(Space) :- metta_py_foreign(Space).

seam:foreign_capability(Space, Capability) :-
    metta_py_foreign(Space),
    metta_py_capability(Space, Capability).

%The refusal, handed back to the side that has the words. This raises; see
%metta.foreign.foreign_refuse for why it may not return.
seam:foreign_refuse(Space, Capability) :-
    metta_py_foreign(Space),
    atom_string(Space, SpaceStr),
    atom_string(Capability, CapabilityStr),
    py_call(metta_ops:foreign_refuse(SpaceStr, CapabilityStr), _).

%The declared-mode stream: the mode crosses WITH the call, the Python
%side enforces it where the provider's exceptions are native (a
%mid-iteration exception tunnels past every Prolog catch), and a kept
%failure arrives as the reserved ["x","error",AtomWire] item. The
%["x","end"] item marks exhaustion so an empty stream still claims the
%route and the engine never re-consults the provider through the
%fallback, which would consume a linear source twice.
seam:foreign_erring(Space, Pattern, Licensed, Mode, Item) :-
    metta_py_foreign(Space),
    ( memberchk(limit(Limit), Licensed) -> true ; Limit = @(none) ),
    metta_py_encode(Pattern, [], Table, W),
    atom_string(Space, SpaceStr),
    atom_string(Mode, ModeStr),
    py_iter(metta_ops:foreign_match(SpaceStr, W, Limit, ModeStr), CW),
    metta_py_erring_item(CW, Pattern, Limit, Table, Space, Item).

metta_py_erring_item([XTag, End], _, _, _, _, end) :-
    ( XTag == "x" ; XTag == x ),
    ( End == "end" ; End == end ), !.
metta_py_erring_item([XTag, Err, ErrorW], _, _, _, _, kept(Kept)) :-
    ( XTag == "x" ; XTag == x ),
    ( Err == "error" ; Err == error ), !,
    metta_py_decode_shared(ErrorW, Kept, _).
metta_py_erring_item(CW, Pattern, Limit, Table, Space, answer) :-
    metta_py_answer_match(CW, Pattern, Limit, Table, Space).

%Custom matching for Python grounded values, Hyperon's CustomMatch: a
%value whose class defines match_/1 owns its matching logic inside
%`unify`, no registration, exactly as any grounded atom. The hook
%streams the object's answers and holds each to the met operand through
%the provider answer form, so bindings, an explicit value and a residue
%all work; an annotation is refused by the kappa gate below because a
%bare value has no context to declare a semiring on, and weighted
%matching is a context's job. Errors abort: a value's matching logic
%has no (on-error ...) home, so a raising match_ is a defect at its own
%yield site.
seam:matchable_value(Blob) :-
    seam:host_object(Blob),
    py_call(metta_ops:is_matchable(Blob), R),
    R == @(true).
seam:custom_match(Blob, Other) :-
    metta_py_encode(Other, [], Table, W),
    py_iter(metta_ops:match_object(Blob, W), CW),
    metta_py_answer_match(CW, Other, Table, '$metta-matchable').

%Transactional participation for Python providers, driven by (writes Ctx
%transactional): the provider's own begin/commit/rollback methods.
seam:foreign_begin(Space) :-
    metta_py_foreign(Space),
    atom_string(Space, SpaceStr),
    py_call(metta_ops:foreign_transaction(SpaceStr, "begin"), _).
seam:foreign_commit(Space) :-
    metta_py_foreign(Space),
    atom_string(Space, SpaceStr),
    py_call(metta_ops:foreign_transaction(SpaceStr, "commit"), _).
seam:foreign_rollback(Space) :-
    metta_py_foreign(Space),
    atom_string(Space, SpaceStr),
    py_call(metta_ops:foreign_transaction(SpaceStr, "rollback"), _).

%The option reaches a provider whose match accepts a limit keyword and nobody
%else, which foreign.py decides from the signature, so a provider that never
%heard of it is called with none.
seam:foreign_match(Space, Pattern, Options) :-
    metta_py_foreign(Space),
    ( memberchk(limit(Limit), Options) -> true ; Limit = @(none) ),
    metta_py_encode(Pattern, [], Table, W),
    atom_string(Space, SpaceStr),
    py_iter(metta_ops:foreign_match(SpaceStr, W, Limit), CW),
    metta_py_answer_match(CW, Pattern, Limit, Table, Space).

%What the provider claims about its own filtering for this pattern, asked
%only when there is a bound to act on, so an unbounded match does not pay for
%a crossing it gains nothing from. A provider with no pushdown method answers
%inexact, which is what every provider written before this says.
seam:foreign_pushdown(Space, Pattern, Class) :-
    metta_py_foreign(Space),
    metta_py_encode(Pattern, W),
    atom_string(Space, SpaceStr),
    py_call(metta_ops:foreign_pushdown(SpaceStr, W), ClassStr),
    atom_string(Class, ClassStr).

seam:foreign_atoms(Space, Atom) :-
    metta_py_foreign(Space),
    atom_string(Space, SpaceStr),
    py_iter(metta_ops:foreign_atoms(SpaceStr), CW),
    metta_py_decode_shared(CW, Atom, _).

seam:foreign_add(Space, Term) :-
    metta_py_foreign(Space),
    metta_py_encode(Term, W),
    atom_string(Space, SpaceStr),
    py_call(metta_ops:foreign_add(SpaceStr, W), _).

%The claim seam. A provider without a Planner declares no plan capability, so
%the engine never asks; one that does may still decline per conjunction, which
%is a `None` on the Python side and a failure here.
%
%The rows are materialised and the goal replays them, rather than the goal
%calling back into Python per row. A claim is answered as a whole, so streaming
%would buy nothing and would hold a Python generator open across engine
%backtracking, which is the shape that makes a provider's state hard to reason
%about.
seam:foreign_plan(Space, Patterns, Claimed, Rest,
                  metta_py_plan_rows(Claimed, Rows, Table)) :-
    metta_py_foreign(Space),
    metta_py_capability(Space, plan),
    metta_py_encode_arguments(Patterns, PatternWs, Table),
    atom_string(Space, SpaceStr),
    py_call(metta_ops:foreign_plan(SpaceStr, PatternWs), Answer),
    Answer \== @(none),
    Answer = [ClaimedWs, RestWs, RowWs],
    %The claim is a PARTITION of the caller's own patterns, so each
    %returned wire is resolved back to the caller's TERM by matching the
    %wire it was sent as. Decoding the wires instead built fresh copies:
    %a variable shared across two patterns (every join variable) split
    %into two, and the identity was then restored only as a side effect
    %of refuse_lossy_plan's msort unification pairing the two lists in
    %the same order. That coincidence held for plain variables, whose
    %addresses sorted alike on both sides, and broke the moment the
    %caller's variables carried attributes: the lists paired crosswise,
    %the join variable aliased wrongly, and a planning provider silently
    %lost answers [tested test_planner_rows_may_be_bindings].
    metta_py_plan_selection(ClaimedWs, PatternWs, Patterns, Claimed),
    metta_py_plan_selection(RestWs, PatternWs, Patterns, Rest),
    maplist(metta_py_decode_plan_row(Space), RowWs, Rows).

%Each returned wire is one of the wires we sent, so the caller's own term
%is at the same position. Positions are consumed, so a conjunction that
%repeats a pattern maps one occurrence to one occurrence rather than
%collapsing them.
metta_py_plan_selection(Ws, PatternWs, Patterns, Selected) :-
    maplist(metta_py_wire_key, PatternWs, Keys),
    metta_py_plan_selection_(Ws, Keys, Patterns, Selected).

metta_py_plan_selection_([], _, _, []).
metta_py_plan_selection_([W|Ws], Keys, Patterns, [P|Ps]) :-
    metta_py_wire_key(W, Key),
    (   nth0(I, Keys, K), K == Key
    ->  nth0(I, Patterns, P),
        metta_py_plan_drop(I, Keys, RestWs, Patterns, RestPatterns)
    ;   throw(error(metta_foreign_plan_is_not_a_partition(unknown, Patterns,
                                                          [W], []),
                    context(seam:foreign_plan/5,
                            'a claim names a pattern that was not offered')))
    ),
    metta_py_plan_selection_(Ws, RestWs, RestPatterns, Ps).

%A wire crossing to Python and back is the same structure with janus's own
%text convention applied, so the comparison normalizes every leaf to an
%atom rather than demanding string-for-string identity.
metta_py_wire_key(W, Key) :-
    (   is_list(W)
    ->  maplist(metta_py_wire_key, W, Key)
    ;   string(W)
    ->  atom_string(Key, W)
    ;   Key = W
    ).

metta_py_plan_drop(I, Ws, RestWs, Ps, RestPs) :-
    nth0(I, Ws, _, RestWs),
    nth0(I, Ps, _, RestPs).

metta_py_decode_row(RowW, Row) :- maplist(metta_py_decode_for_add, RowW, Row).

%A theta row keeps its wire until replay: at decode time the claimed
%patterns still hold fresh variables, and only refuse_lossy_plan's
%partition check reconnects them with the caller's own, so applying the
%bindings here would bind copies nobody reads.
metta_py_decode_plan_row(Space, RowW, metta_answer(Space, RowW)) :-
    metta_py_answer_form(RowW, _, _, _, _), !.
metta_py_decode_plan_row(_, RowW, Row) :- metta_py_decode_row(RowW, Row).

%One solution per row, the claimed patterns unified with it. Unifying rather
%than trusting is what keeps a decoding mistake from becoming a wrong answer:
%a row of the wrong shape fails here instead of binding something odd.
%A plain row unifies with the claimed patterns, which is what forces the
%re-unification a theta row deletes: bindings for the patterns' own
%variables apply directly, one row per answer, residue closing as
%everywhere else.
metta_py_plan_rows(Claimed, Rows, Table) :-
    member(Row, Rows),
    (   Row = metta_answer(Space, Wire)
    ->  metta_py_answer_match(Wire, Claimed, Table, Space)
    ;   Claimed = Row
    ).

%The batch seam. A provider without a BulkAdder declares no add-many capability,
%so this fails and the engine falls back to one seam:foreign_add/2 per atom.
seam:foreign_add_many(Space, Terms) :-
    metta_py_foreign(Space),
    metta_py_capability(Space, 'add-many'),
    maplist(metta_py_encode, Terms, Ws),
    atom_string(Space, SpaceStr),
    py_call(metta_ops:foreign_add_many(SpaceStr, Ws), _).

seam:foreign_remove(Space, Term, Removed) :-
    metta_py_foreign(Space),
    metta_py_encode(Term, W),
    atom_string(Space, SpaceStr),
    py_call(metta_ops:foreign_remove(SpaceStr, W), R0),
    metta_py_bool(R0, Removed).

metta_py_register_foreign(Space0, Capabilities, Delivery) :-
    ( atom(Space0) -> Space = Space0 ; atom_string(Space, Space0) ),
    %The engine-side claim comes first, so a name another provider already owns
    %is refused by name here instead of landing in metta_py_foreign/1 and then
    %resolving against MORK's or redis's clauses by load order. A
    %re-registration of a name this side already holds is the same owner and
    %the same extent, which the door treats as idempotent exactly as the line
    %below does.
    metta_claim_space(Space, python),
    ( metta_py_foreign(Space) -> true ; assertz(metta_py_foreign(Space)) ),
    %A newly registered provider is a new source: the linear-consumption
    %mark belongs to the drained OBJECT, and this is the door a fresh one
    %arrives through.
    metta_source_reset(Space),
    retractall(metta_py_capability(Space, _)),
    forall(member(Capability0, Capabilities),
           ( ( atom(Capability0) -> Capability = Capability0
             ; atom_string(Capability, Capability0) ),
             assertz(metta_py_capability(Space, Capability)) )),
    metta_py_declare_delivery(Space, Delivery).

%A provider's event promise, written as the ordinary (events ...)
%declaration so a MeTTa program reads what the engine acts on. It rides
%registration rather than a second crossing because the two are one fact
%about one space: a re-registration that stops promising events must stop
%the space being subscribable in the same step [P12.14].
metta_py_declare_delivery(Space, Delivery) :-
    metta_host_remove_reported('&metta', [events, Space, _, _], _),
    (   Delivery = [Delivery0, Order0]
    ->  ( atom(Delivery0) -> D = Delivery0 ; atom_string(D, Delivery0) ),
        ( atom(Order0) -> O = Order0 ; atom_string(O, Order0) ),
        'add-atom'('&metta', [events, Space, D, O], _)
    ;   true
    ).

metta_py_unregister_foreign(Space0) :-
    ( atom(Space0) -> Space = Space0 ; atom_string(Space, Space0) ),
    retractall(metta_py_capability(Space, _)),
    metta_py_declare_delivery(Space, []),
    retractall(metta_py_foreign(Space)),
    metta_disclaim_space(Space, python).

%%%%%%%%%% Subscriptions %%%%%%%%%%
%
% Standing queries: when Python has subscribers, every committed space write
% crosses to metta_ops for pattern matching and callbacks. An unscoped write
% crosses immediately; a transaction's segment crosses after commit, and a
% discarded segment never crosses. The hook clauses exist only while at least
% one space is watched.
% Their guard is one dynamic fact per subscribed space, first-arg indexed, so
% an unwatched space never crosses to Python while another space is watched.

:- multifile seam:atom_added/2.
:- multifile seam:atom_removed/2.
:- dynamic metta_py_subscribed_space/1.
:- dynamic metta_py_subscription_hook_ref/2.

metta_py_notify_atom_added(Space, Term) :-
    atom(Space),
    metta_py_subscribed_space(Space),
    metta_py_encode(Term, W),
    atom_string(Space, SpaceStr),
    py_call(metta_ops:atom_added(SpaceStr, W), _).

metta_py_notify_atom_removed(Space, Term) :-
    atom(Space),
    metta_py_subscribed_space(Space),
    metta_py_encode(Term, W),
    atom_string(Space, SpaceStr),
    py_call(metta_ops:atom_removed(SpaceStr, W), _).

metta_py_install_subscription_hook(Kind) :-
    metta_py_subscription_hook_ref(Kind, Ref),
    \+ clause_property(Ref, erased), !.
metta_py_install_subscription_hook(added) :-
    retractall(metta_py_subscription_hook_ref(added, _)),
    assertz((seam:atom_added(Space, Term) :-
                metta_py_notify_atom_added(Space, Term)), Ref),
    assertz(metta_py_subscription_hook_ref(added, Ref)).
metta_py_install_subscription_hook(removed) :-
    retractall(metta_py_subscription_hook_ref(removed, _)),
    assertz((seam:atom_removed(Space, Term) :-
                metta_py_notify_atom_removed(Space, Term)), Ref),
    assertz(metta_py_subscription_hook_ref(removed, Ref)).

metta_py_remove_subscription_hooks :-
    forall(retract(metta_py_subscription_hook_ref(_, Ref)),
           ( clause_property(Ref, erased) -> true ; erase(Ref) )).


metta_py_subscriptions(Spaces) :-
    maplist(atom_string, SpaceAtoms, Spaces),
    with_mutex('$metta_py_subscriptions',
               metta_py_subscriptions_locked(SpaceAtoms)).

metta_py_subscriptions_locked(SpaceAtoms) :-
    retractall(metta_py_subscribed_space(_)),
    forall(member(Space, SpaceAtoms),
           assertz(metta_py_subscribed_space(Space))),
    ( SpaceAtoms == []
      -> metta_py_remove_subscription_hooks
    ; metta_py_install_subscription_hook(added),
      metta_py_install_subscription_hook(removed) ).

%%%%%%%%%% Protocol types for host objects %%%%%%%%%%
%
% The engine asks seam:grounded_extra_type/2 for names beyond an object's own
% classes; the answer comes from the Python-side protocol registry, so a
% library teaches typing without touching Prolog.

:- multifile seam:grounded_type_names/2.

%Values cross the boundary boxed so janus cannot rewrite them; the names
%are computed on the held value, in Python, and cross as plain text: the
%classes off the method resolution order, then every satisfied protocol.
seam:grounded_type_names(X, Names) :-
    py_is_object(X),
    py_call(metta_ops:type_names(X), Names).

%(context-space) lives in the engine now (engine/metta.pl); the shim keeps
%nothing to add for it.

%%%%%%%%%% Retranslation on late definitions %%%%%%%%%%
%
% The engine decides call-against-data per equation at compile time, so a
% body mentioning a name that only becomes a function later stays data: the
% classic case is (= (f) (g)) in one run and (= (g) 5) in the next, and the
% Python case is an operation registered after equations that call it.
% The dependent-recompile that used to ride here as clauses of the
% seam:function_changed/1 and seam:function_removed/1 EVENTS is the
% engine's own now (announce_function_changed/2 and announce_function_removed/1 in
% engine/spaces.pl): an event observer must be optional, and an engine without
% this host in the process has to repair its own compiled code. The
% invalidation was already the engine's, threaded with the module each write
% goes to, which is the only place that knows it
%[tested: specializer_invalidation:writing_in_one_space_leaves_another_alone,
%test_adding_in_one_space_never_removes_atoms_from_another].

%%%%%%%%%% Trusted fast cache I/O %%%%%%%%%%
%
%One fast_write carries the whole atom list. The text header pins both this
%container contract and the SWI release whose private term encoding produced
%the payload. Python validates it before calling the reader, and this section
%checks it again on the same stream before fast_read can see any payload byte.

%The fast cache and the digest are engine machinery now, the host run and
%load surface in engine/filereader.pl: this side maps the term outcomes to
%the wire and answers the ONE host question the engine asks through the
%seam:host_object/1 seam, whether a term is a live Python object (the
%bridge contributes that clause). Results: object(Atom) and symbol(Atom)
%name a refusing offender, saved(Count) and digest(Hash) land.

%The first atom in a space with no round-trip text spelling, so a host
%validating a save asks the grammar instead of keeping a second copy of its
%rules, which is how the host's copy came to miss three classes.
%
%This asked about the atoms' NAMES until 2026-08-19 and so missed a fourth
%class, which is not a name at all: a number whose printed form is not read
%back as that number. A space holding `(py-atom "float('inf')")`'s answer saved
%to a .metta file and loaded back came back holding the SYMBOL of that
%spelling, silently [measured 2026-08-19]. metta_unwritable_symbol/2 is the
%grammar's own answer about a whole atom, one of the four text services in
%engine/ext_points.pl, and it is the same question metta_py_fast_save/3 and
%metta_py_digest/2 below already ask.
metta_py_unwritable_atom(Space, Bad) :-
    'get-atoms'(Space, Atom),
    metta_unwritable_symbol(Atom, Unwritable), !,
    metta_py_encode(Unwritable, Bad).

%One boolean crossing for consumers that must validate a name before they
%mutate host state. The parser remains the authority, including reader token
%classes registered after startup.
metta_py_symbol_writable(Name, '@'(true)) :- metta_symbol_writable(Name), !.
metta_py_symbol_writable(_, '@'(false)).

%A refusal witness for a host error. Testing each one-character spelling
%against the grammar finds a delimiter or reserved literal opener without a
%second delimiter table; when only the whole token is reserved (True or a
%registered token class), its first character locates the competing token.
metta_py_symbol_refusal(Name0, Refusal) :-
    ( atom(Name0) -> Name = Name0 ; atom_string(Name, Name0) ),
    \+ metta_symbol_writable(Name),
    metta_py_symbol_refusal_detail(Name, Refusal).

metta_py_symbol_refusal_detail('', [empty]) :- !.
metta_py_symbol_refusal_detail(Name, [token, Character]) :-
    atom_string(Name, Text),
    metta_reader_token_source(Text, custom),
    atom_codes(Name, [First|_]),
    atom_codes(Character, [First]),
    !.
metta_py_symbol_refusal_detail(Name, [character, Character]) :-
    atom_codes(Name, Codes),
    member(Code, Codes),
    atom_codes(Character, [Code]),
    \+ metta_symbol_writable(Character),
    !.
metta_py_symbol_refusal_detail(Name, [token, Character]) :-
    atom_codes(Name, [First|_]),
    atom_codes(Character, [First]).

metta_py_fast_save(File, Space, Result) :-
    metta_host_save_fast(File, Space, Outcome),
    metta_py_persist_result(Outcome, Result).

metta_py_fast_load(File, Space) :-
    metta_host_load_fast(File, Space).

metta_py_persist_result(object(Atom), ["object", Encoded]) :- !,
    metta_py_encode(Atom, Encoded).
metta_py_persist_result(symbol(Atom), ["symbol", Encoded]) :- !,
    metta_py_encode(Atom, Encoded).
metta_py_persist_result(saved(Count), ["saved", Count]) :- !.
metta_py_persist_result(digest(Hash), ["digest", Hash]).

%%%%%%%%%% Content digest %%%%%%%%%%
%
%A space's content as one sha256: each atom canonicalized (fresh copy,
%numbered variables, quoted write) so alpha-equivalent equations print
%identically in every process, the lines multiset-sorted so insertion
%order cannot matter, then hashed as one utf8 document. Live objects
%print by address and are refused, the save contract.

metta_py_digest(Space, Result) :-
    metta_host_digest(Space, Outcome),
    metta_py_persist_result(Outcome, Result).
