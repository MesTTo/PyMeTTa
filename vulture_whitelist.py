"""Purpose: tell Vulture about APIs reached by protocols, plugins, dynamic
dispatch, generated tests, or external callers rather than Python name loads.
Assumes:
  - this file is scanned by Vulture and is never imported or executed.
Guarantees:
  - R5's externally called watch and dynamically installed ordering methods
    remain visible to the dead-code gate [tested: the GATE vulture lane;
    commit=cff2e7f319bd2212f0c2d74f8d5fe5be3ac693b5]
  - each expression names one intentional dynamic use, so the 60 percent
    confidence floor remains actionable instead of globally suppressing a
    name pattern [tested: the GATE vulture lane;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321].
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the contract is one continuous invariant, not summary-and-body prose

# Vulture's whitelist format is intentionally a sequence of otherwise undefined
# expression references. Ruff must leave those references intact for Vulture.
# ruff: noqa: B018, F821


# Public compatibility and plugin entry points.
_.load_metta_file
_.process_metta_string
__dir__
_.alpha_eq
_.info
_._ipython_key_completions_
_.ne
_wire_intern_clear
_.interrupt
_.observe_instructions
_.finish
_.importance
_.strength
_.ping
_.rules
_.complete
_._repr_html_
_.supports
load_ipython_extension
_.starmap
_.closed
imap_unordered
_.compact
scratch_space
_is_authorized
_.server_capabilities
_.asdict
_.raise_for_errors
_.to_dicts
_.to_df
_.to_pl
_.transactional
_.matching
_.reachable
_.watch
_.pre_add
_.send
_.try_recv
_.__match_args__
_.__replace__
_.__metta__
_.__lt__
# Subscription.drain is the queue spelling of Fold.take, documented as the
# sugar it is; the general name is what the library calls internally now.
_.drain

# singledispatch reaches path traversal handlers through registered types.
_path_begin
_path_step
_path_value

# Protocol fields and methods read by getattr, a framework, or the wire.
# PlanDecision is the algebra evaluator's law-gate answer; callers read the
# withheld optimization, whether it applied, and the laws it still misses.
optimization
applied
missing_laws
exact_integers
non_finite
resolves_anonymous
_.cell_contents
severity
docs_link
gc_time
_.gc_time
_.top
_.__signature__
_.__wrapped__
_.begin
_.do_GET
do_PUT
do_DELETE
do_PATCH
_.do_POST
_.log_message
_.daemon_threads
_.maxlevel
_.maxstring
_.maxother
_._parse

# singledispatch and AST visitor methods are selected by registered type or
# syntax-node name rather than a direct call.
_
_._x_UnaryOp
_._x_Compare
_._x_BoolOp
_._x_IfExp
_._x_Lambda
_._x_ListComp
_._x_GeneratorExp
_._x_Call
_._x_Subscript
_._x_Tuple
_._x_List
_._x_Dict
_._x_JoinedStr

# These methods ship as pytest compliance suites and are collected after a
# provider or gateway supplies the fixture class.
_.test_enumeration_answers_what_the_provider_holds
_.test_declared_length_answers_the_provider_size
_.test_a_stored_atom_matches_itself
_.test_an_open_pattern_answers_every_stored_atom_of_its_shape
_.test_a_bound_position_selects_whatever_the_provider_yielded
_.test_a_repeated_variable_selects_equal_positions
_.test_a_conjunction_over_the_provider_joins
_.test_a_claimed_join_answers_what_the_split_answers
_.test_a_write_round_trip_leaves_the_provider_as_it_was
_.test_a_batch_add_stores_every_atom
_.test_a_declared_rule_space_holds_a_program
_.test_clear_empties_the_space
_.test_an_undeclared_write_refuses_rather_than_answering_nothing
_.test_the_provider_joins_with_a_native_space
_.test_a_bounded_query_answers_no_more_than_the_bound
_.test_health_names_the_protocol
_.test_a_bound_is_honored_or_ignored_soundly
_.test_the_operations_keep_space_semantics
_.test_add_many_lands_the_batch
_.test_refusals_carry_json_errors
_.test_wide_integers_are_exact_or_refused
_.test_the_lifecycle_streams_the_same_answers_the_eager_door_gives
_.test_the_lifecycle_refuses_what_it_cannot_answer
_.test_a_client_cursor_takes_two_answers_and_stops
_.test_the_kit_certifies_the_attached_space

# The standard order of terms installs the full rich-comparison protocol on
# Atom (appendix stamp 6); the interpreter calls these through the type slots
# (sorted, min, max, heapq, bisect), never by attribute load.
_.__le__
_.__gt__
_.__ge__

# Generated vocabulary member: the space-capability set crosses as atoms and
# is read by MeTTa-side capability rows; no in-package Python loads the name.
_.network

# BenchmarkBaseline is shipped API whose only callers are the benchmark
# harness: benchmarks/conftest.py stamps the counter configuration,
# check_instructions.py verifies it without restamping, and
# extension_cost.py prunes a pinned row nothing measured. The lane scans
# the shipped package alone, on purpose, so a caller in benchmarks/ is
# outside its sight rather than absent.
_.observe_configuration
_.remove_case

# The same, one component further out: observe_cpu records the counter that a
# foreign-boundary row is checked against, and its caller is the MORK seat's
# own benchmark, extensions/mork/benchmarks/bench.py. DEVELOPING.md tells a
# sibling to import this harness rather than copy it, so a caller outside
# extensions/python is the arrangement rather than a gap.
_.observe_cpu

# The scheduler's context-propagation callbacks: the engine invokes them by
# name through _callbacks.py's string table ("fork_contexts" ->
# ("_task_context", "fork_many"), "release_contexts" ->
# ("_task_context", "release_many")), an indirection a reachability scan
# cannot see; test_import_identity pins the table rows to these callables.
fork_many
release_many

# The settled reacts declaration keeps reaction as the compatibility alias
# on both the live Space and its async mirror; callers reach it by the old
# spelling from user programs, never from inside the package.
_.reaction
