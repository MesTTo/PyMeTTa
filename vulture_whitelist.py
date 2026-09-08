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
    commit=97df27ef8346695707d87fc9bec6a8761cff574e].
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the contract is one continuous invariant, not summary-and-body prose

# Vulture's whitelist format is intentionally a sequence of otherwise undefined
# expression references. Ruff must leave those references intact for Vulture.
# ruff: noqa: B018, F821


# Public compatibility and plugin entry points.
# The import system's own protocol: Python calls these four, by the finder's
# position in sys.meta_path and through the spec it answers, never by a name
# written in this tree
# [source: https://docs.python.org/3.12/reference/import.html#the-meta-path].
_.find_spec
_.create_module
_.exec_module
_.get_source
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
# EngineProfile.as_stats is a public export door: its callers are programs
# handing SWI's profile to snakeviz, tuna or pstats.Stats, none of which are
# in this package.
_.as_stats
# create_stats is the profiler protocol pstats.Stats loads through: it calls
# it by name on whatever it is handed [source: CPython 3.14 Lib/pstats.py,
# Stats.load_stats].
_.create_stats

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
# Benchmark modules are outside Vulture's paths and import this parser directly.
_._node

# singledispatch and AST visitor methods are selected by registered type or
# syntax-node name rather than a direct call.
_
_._x_BinOp
_._x_UnaryOp
_._x_Compare
_._x_BoolOp
_._x_IfExp
_._x_Lambda
_._x_ListComp
_._x_GeneratorExp
_._x_Dict
_._x_Set
_._x_DictComp
_._x_SetComp
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
# The event-promise law the catalog-types merge (1a3579fa) added to the same
# kit, collected the same way and left without its row.
_.test_a_declared_event_promise_delivers_a_write

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

# The equality family's alpha door: user programs and the twins call it on
# atoms they build; nothing inside the package needs alpha equality of its
# own, which is the same arrangement as eq and ne on the operator protocol.
_.alpha

# Trace.truncated is the yes-or-no reading of Trace.stopped, kept because it is
# what a caller asks first and what every consumer written against the older
# shape already asks; the package itself has the bound's own word to read, so
# nothing inside it loads this name.
_.truncated

# ast.NodeVisitor dispatches its hooks by NAME, `visit_` plus the node class,
# so no attribute load names this one and a reachability scan cannot see it.
# It is the walrus case of _GeneratorReads, the backward liveness walk that
# gives a generator's shared continuation its parameter list, and it is
# reached: measured, a walrus in the statements after a generator branch calls
# it once. Every such program is then REFUSED, and the hook is what keeps the
# refusal accurate. Without it the target counts as a free read, so the
# liveness check fires first and blames the wrong thing: `total = (doubled :=
# n * 2) + 1` after a branch answers "NamedExpr has no MeTTa equivalent in the
# compiled subset" with the hook and "'doubled' is read after a generator
# branch but is not bound on every path reaching that read" without it
# [tested: test_a_generator_walrus_refuses_as_an_unsupported_construct].
_.visit_NamedExpr

# IPython's pretty printer dispatches by NAME, the way rich dispatches to
# __rich__ and __rich_repr__ beside it: only the printer calls this, and only
# when a notebook or an interactive shell is present, so no attribute load in
# the package names it.
_._repr_pretty_

# A MeTTa head as a SQL function is a door for a caller's own connection.
# Nothing inside the package registers one, the way nothing inside it builds a
# DataFrame; the suite and the reference are its consumers.
_.sql_function

# The atom projection of a refusal's two rows. Its consumers are outside this
# package by design: a caller reading a Remedy off an error, the suite that
# round-trips both through from_atom, and the catalog row a refusal kind
# becomes later. Nothing in the package stores one yet, exactly as nothing in
# it registers a SQL function above.
_.as_atom

# SpaceMachine's rules and its invariant. Hypothesis collects them off the
# class and calls them by generating a history, so no attribute load in the
# package names any of them; the decorators are the registration. `for_` binds
# the machine to a factory and is called by whoever runs it, which is a test
# suite outside this package by design.
_.for_
_.add_one
_.add_a_second_copy
_.remove_a_stored_atom
_.remove_an_arbitrary_atom
_.clear_everything
_.query_answers_the_model
_.a_speculative_write_leaves_nothing
_.a_committed_transaction_keeps_its_write
_.a_rolled_back_transaction_keeps_nothing
_.storage_matches_the_model
# Pygments reads a lexer class by ATTRIBUTE after loading it through the
# `pygments.lexers` entry point, and nothing in this package loads
# metta/_pygments.py at all: `filenames` is what get_lexer_for_filename globs
# against and `mimetypes` is what get_lexer_for_mimetype and a Jupyter
# kernel's `language_info` key on. The class's other attributes -- name,
# aliases, url, flags, tokens -- are spelled elsewhere in the tree and reach
# vulture that way.
_.filenames
_.mimetypes

# graphql-core builds a custom scalar from SDL with the identity serializer and
# no value parser, so `_schemas.build_graphql_schema` assigns both onto the
# GraphQLScalarType it made [source:
# https://github.com/graphql-python/graphql-core, GraphQLScalarType's
# constructor assigning `serialize` and `parse_value` as plain attributes].
# `serialize` is spelled elsewhere in that module and reaches vulture that way;
# `parse_value` is written once, at the assignment, and read only by the
# executor inside graphql-core.
_.parse_value
# The seam's own doors, reached by NAME through metta.seam rather than by an
# attribute load anywhere in this package. `_catalog_of` is the `catalog`
# service metta._space publishes and metta.seam.publish calls through
# `seam.at("catalog").call()`; the three Point objects are the declarations
# metta.integrate makes for the doors whose rows it owns, held by the seam's
# own table and spelled `seam.at("repr")` and friends at every call site. The
# other three points it declares -- type_, provider and library -- are absent
# here only because vulture matches a name across the whole scan and those
# three words appear as ordinary locals elsewhere.
_.repr_
_.reflector
_.integration
_._catalog_of
# Two names the package itself never loads, and neither is dead. PROLOG calls
# `_carrier_type_accepts` by name through seam:grounded_algebra_type/3
# (extensions/python/metta/shim.pl:6495, `py_call('metta.algebra':...)`), which
# is the whole point of that seam: the owning host applies a carrier predicate
# without the atom kinds being erased on the way. `boot_seconds` is a property
# a CALLER reads off a pool it was handed, and the caller is outside this
# package by design; the suite's own reader is
# tests/ch17_concurrency_and_the_loop/test_process_pool.py, which vulture does
# not scan.
_._carrier_type_accepts
_.boot_seconds
# The engine reaches this one from PROLOG, not from Python: shim.pl's
# seam:grounded_algebra_type/3 clause calls
# py_call('metta.algebra':'_carrier_type_accepts'(TypeWire, ValueWire), Raw)
# so a host carrier predicate can decide an algebra's membership question. No
# Python name load reaches it, which is what makes it invisible to a
# reachability scan [source: extensions/python/metta/shim.pl,
# seam:grounded_algebra_type/3; commit=11afdcdbad5bbbe37168b5d8528c23a21c42b4b6].
_carrier_type_accepts

# Read by a SIBLING SEAT, which this scan does not reach: the C seat's
# benchmark driver asks its baseline what checkout length its pins were taken
# at and refuses the boot instruction row from a different one, because that
# row's count scales with the length of the engine path the process resolves
# [source: extensions/cmetta/benchmarks/bench.py, observe_all's path_decides;
# commit=11afdcdbad5bbbe37168b5d8528c23a21c42b4b6].
_.pinned_checkout_path_length
# A face reports the version its header pinned against the one installed here,
# and the reader of that report is extensions/python/tools/facegen.py, which
# vulture does not scan: the sync tool is the caller of every door on Face
# that the package itself does not use.
_.drifted_versions

# The engine reaches this one from PROLOG too: shim.pl's
# seam:catalog_row_changed/2 clause calls
# py_call('metta._config':bound_row_changed(Name)) for every `(limit ...)` row
# that lands in or leaves `&metta`, which is what keeps the seat's mirror of
# the bounds in step with a write it never saw. No Python name load reaches it
# [source: extensions/python/metta/shim.pl, seam:catalog_row_changed/2;
# commit=c26b6a4d28ef8fb50742440feed2c0578ebb0f58].
bound_row_changed
# A generated row's own field, read by the suite this scan does not walk:
# tests/repository/test_refusal_rows.py's
# test_a_class_this_seat_spells_differently_carries_its_reason asks every
# refusal row why this seat spells its class differently from the name the
# engine's row declares, and `tools/refusalgen.py` refuses to generate a
# departure without one.
_.departure
