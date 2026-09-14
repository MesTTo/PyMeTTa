% Purpose: supply the Python binding's ownership seam clauses.
% Guarantees: a Python-backed space answers length refinements through its
% Sized promise without enumeration [tested:
% test_foreign_space_length_refinements_use_the_owner;
% test_foreign_space_length_failures_preserve_the_owner_error; commit=WORKTREE].
% Open variables never choose a registered provider [tested:
% test_foreign_space_length_does_not_choose_a_value_for_a_variable; commit=WORKTREE].
% Assumes: bindinggen projects each row into its declared load audience
% and defining module.
% Guarantees: every supplied head has this file's engine kind
% [tested: test_binding_provisions_keep_audience_and_kind; commit=8358dfc233bf299bb23eceddd94593a62372fe4b].
% Guarantees: optional add-token and remove-token callbacks preserve exact
%   provider identities [tested: test_token_mutation_receives_and_withdraws_a_reference;
%   commit=90ba93eb8f6e98ebfefc55416859bf13de6a8427].
% Guarantees: grounded_length/2 reads tuple arity or Python's Sized protocol
%   without enumerating elements [tested:
%   test_host_length_refinements_do_not_read_elements; commit=9b0a084e534ddf7dd67980ad84c27c8279b877f1].

provides_declaration(engine, user, grounded_apply/3).

provides_declaration(engine, user, grounded_algebra_equal/3).

provides_declaration(engine, user, grounded_numeric/1).

provides_declaration(engine, user, grounded_numeric_operation/3).

provides_declaration(engine, user, grounded_structure/2).

provides_declaration(engine, user, grounded_length/2).

provides_declaration(engine, user, grounded_text/2).

%%%% The structural view %%%%

% Janus's tuple carrier already holds its length in the functor arity.
provides(engine, user, (
seam:grounded_length(Tuple, Length) :-
    compound(Tuple),
    compound_name_arity(Tuple, -, Length)
)).

provides(engine, user, (
seam:grounded_length(Obj, Length) :-
    python_object_blob(Obj),
    py_is_object(Obj),
    metta_py_bridge,
    py_call('metta._binding.host':sized_length(Obj), Length),
    Length >= 0
)).

%A Python tuple crosses by default as the Prolog compound -/N, which is
%janus's encoding and is faithful in BOTH directions: `(1, (2, 3))` is
%`1-(2-3)`, and handing `1-2` back to Python yields a real tuple, class and all
%[measured 2026-08-16]. Its default structural reading therefore costs no
%crossing: the elements are already there. An explicit Grounded request takes
%a separate path below, because Janus converts an exact tuple even when
%py_object(true) asks for a reference.
%
%That reading is what makes `(car-atom (py-atom "(1, 2)"))` answer 1 while the
%same value still passes into Python as a tuple. Neither reading is a separate
%answer; see seam:grounded_structure/2 in engine/ext_points.pl.
%
%Elements are normalized because the VIEW is MeTTa's reading of the value: a
%None inside a tuple reads as `()` here. The carrier itself is left exactly as
%janus made it, because that is what has to go back.
provides(engine, user, (
seam:grounded_structure(Tuple, Elements) :-
    metta_py_tuple_arguments(Tuple, Raw),
    maplist(metta_py_result, Raw, Elements)
)).

%And a Python object that IS a sequence, which costs a crossing because the
%elements live on the other side. PEP 634's rule decides which objects qualify;
%extensions/python/metta/_binding/host.py carries it.
%
%The length is asked first and separately. A pattern of fixed shape is rejected
%by its length without pulling a single element, so matching `($x $y)` against
%a million-element list costs one crossing rather than a million.
provides(engine, user, (
seam:grounded_structure(Obj, Elements) :-
    python_object_blob(Obj),
    py_is_object(Obj),
    metta_py_bridge,
    py_call('metta._binding.host':sequence_length(Obj), Length),
    Length >= 0,
    (   is_list(Elements)
    ->  length(Elements, Length)
    ;   true
    ),
    findall(E, 'py-iter'(Obj, E), Elements)
)).

%%%% Display %%%%

%repr, so a Python value says what it is instead of naming an address. The
%converted -/N tuple is the exception: it is the ordinary MeTTa expression its
%structural reading already supplies, so the engine and the library expose the
%same value and both spell the empty tuple as one empty expression answer.
%The elements render through the display writer: a nested opaque host value
%(a list inside a tuple) has a repr but no round-trip text, and a display
%is presentation, exactly as the answer printers already treat it.
provides(engine, user, (
seam:grounded_text(Tuple, Text) :-
    metta_py_tuple_arguments(Tuple, Raw),
    !,
    maplist(metta_py_result, Raw, Elements),
    sdisplay(Elements, Text)
)).

provides(engine, user, (
seam:grounded_text(Obj, Text) :-
    python_object_blob(Obj),
    py_is_object(Obj),
    metta_py_bridge,
    py_call('metta._binding.host':render(Obj), Text)
)).

provides_declaration(engine, user, grounded_class_type/2).

provides(engine, user, (
seam:grounded_class_type(X, T) :-
    metta_py_bridge,
    py_call('metta._binding.host':class_names(X), Names, [py_string_as(string)]),
    member(Name, Names),
    ( atom(Name) -> T = Name ; atom_string(T, Name) )
)).

% Algebra equality asks Python for values, with one explicit negative answer.
% [tested: test_finite_tensor_semiring_checks_every_law; commit=074dc0a88b1605c54824de677d586b6f60998bcf].
provides(engine, user, (
seam:grounded_algebra_equal(Left, Right, Equal) :-
    ( python_object_blob(Left) -> true ; python_object_blob(Right) ),
    metta_py_bridge,
    py_call('metta._binding.host':algebra_equal(Left, Right), Truth),
    ( Truth == @true -> Equal = true ; Equal = false )
)).

%The standard numeric tower is the admission rule, rather than an MRO class
%name: numpy.int64 is a Number without inheriting builtins.int. Execution goes
%through one guarded bridge call so Python owns reflected-operator selection and
%the result remains a reference under metta_py_opts/1.
provides(engine, user, (
seam:grounded_numeric(X) :-
    python_object_blob(X),
    metta_py_bridge,
    py_call('metta._binding.host':is_numeric(X), @true)
)).

provides(engine, user, (
seam:grounded_numeric_operation(Operation, Arguments, Result) :-
    member(Operand, Arguments),
    python_object_blob(Operand), !,
    metta_py_call([Operation|Arguments],
             numeric_operation(Operation, Arguments), Result)
)).

%%%% Application %%%%

%A resolved callable applied in head position, which is what makes the surface
%higher-order: `((py-atom numpy.absolute) -5)`, a Python function passed to
%map-atom, a torch module held in a space.
%
%The engine consults this only for a head that is neither a function name nor a
%partial application, so an ordinary MeTTa call never reaches it. Failing is how
%a grounded value that is NOT an operation stays unreduced, which is what a
%value should do.
provides(engine, user, (
seam:grounded_apply(Obj, Args, Result) :-
    python_object_blob(Obj),
    py_is_object(Obj),
    metta_py_bridge,
    py_call('metta._binding.host':is_callable(Obj), @true),
    metta_py_split_kwargs(Args, Positional0, Kwargs),
    maplist(py_arg_norm, Positional0, Positional),
    metta_py_opts(Opts),
    metta_py_guard([Obj|Args],
                   py_call('metta._binding.host':apply(Obj, Positional, Kwargs), Raw, Opts)),
    metta_py_result(Raw, Result)
)).

provides_declaration(engine, user, grounded_applicable/1).

%The same blob-first guard protects every runtime probe in this file
%(structure, text, apply, the cycle check), because each of them is
%consulted with plain engine terms on ordinary paths: a nested-call data
%shape reaches seam:grounded_apply/3, and probing its list head with
%py_is_object/1 booted CPython inside examples/ch04-spaces-and-matching/04-02-patterns-and-bindings/02-matchnested.metta,
%~104M instructions for a four-atom program [measured 2026-08-17].
%The blob test comes FIRST because it is the one that costs nothing:
%py_is_object/1 "fails silently" on a non-object [source: janus.pl doc,
%py_is_object/1], but janus initialises lazily on its first call, so
%probing a plain integer here booted CPython, ~104M instructions, inside
%typed-call TRANSLATION of every literal argument. The types_dependent
%example paid 3.4x upstream's whole run for it [measured 2026-08-17:
%148.2M net instructions to 44M after this guard]. blob/2 is SWI-side
%introspection and never touches janus.
provides(engine, user, (
seam:grounded_applicable(Obj) :-
    python_object_blob(Obj),
    py_is_object(Obj),
    metta_py_bridge,
    py_call('metta._binding.host':is_callable(Obj), @true)
)).

provides_declaration(engine, user, host_import/1).

provides(engine, user, (
seam:host_import(File) :-
    python_import_file(File),
    resolve_python_import_path(File, CanonPath),
    import_when(not_loaded, '$python', CanonPath,
                load_python_source(CanonPath))
)).

provides_declaration(engine, user, host_object/1).

provides(engine, user, (
seam:host_object(X) :- python_object_blob(X), py_is_object(X)
)).

%This host's transport-failure shape, and the reason text for an error it
%threw: janus wraps a Python exception as python_error(Class, Value), and
%the value may be a live exception object only this bridge can render.
provides_declaration(engine, user, host_transport_failure/1).

provides(engine, user, (
seam:host_transport_failure(error(python_error('TransportFailure', _), _))
)).

provides_declaration(engine, user, host_error_reason/2).

provides(engine, user, (
seam:host_error_reason(error(python_error(Class, Message0), _), Reason) :-
    (   string(Message0) -> Message = Message0
    ;   metta_py_exception_message(Message0, Message)
    ),
    format(string(Reason), "~w: ~w", [Class, Message])
)).

%Ownership is established by the live Python object before the cut implicit in
%the caller's first-success seam. Constructors receive the complete lexeme and
%return an Atom wire; shared decoding preserves repeated variables if a custom
%class deliberately constructs them.
provides(host, user, (
seam:host_reader_token_construct(Constructor, Text, Term) :-
    seam:host_object(Constructor),
    catch(py_call(metta_ops:construct_token(Constructor, Text), Wire),
          Error, metta_py_failure(['reader-token', Text], Error)),
    metta_py_decode_shared(Wire, Term, _)
)).

%The bridge's class-name fast path cannot recognize Python subclasses.
%Classify the live object with the library's shared transport predicate.
provides_declaration(host, user, host_transport_failure/1).

provides(host, user, (
seam:host_transport_failure(error(python_error(Class, Obj), _)) :-
    Class \== 'TransportFailure',
    py_is_object(Obj),
    py_call('metta._errors.errors':is_transport_failure(Obj), @(true))
)).

%The host's clause of the hooks-idle ownership seams: the engine hands the
%handler census in as clause references, and this side answers from the one
%reference it installed, the subscription bridge, without consulting any
%engine internals. Idle means this unwatched space's only handler is the
%bridge itself.
provides_declaration(host, user, host_add_hooks_idle/2).

provides(host, user, (
seam:host_add_hooks_idle(Space, [OnlyRef]) :-
    \+ metta_py_subscribed_space(Space),
    metta_py_subscription_hook_ref(added, OnlyRef)
)).

provides_declaration(host, user, host_remove_hooks_idle/2).

provides(host, user, (
seam:host_remove_hooks_idle(Space, [OnlyRef]) :-
    \+ metta_py_subscribed_space(Space),
    metta_py_subscription_hook_ref(removed, OnlyRef)
)).

provides_declaration(host, user, pattern_modifier/3).

provides(host, user, (
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
    !
)).

provides_declaration(host, user, effect_operation_name/3).

provides(host, user, (
seam:effect_operation_name(metta_py_dispatch(_, Name, Args, _), Name, Arity) :-
    metta_py_dispatch_arity(Args, Arity)
)).

provides(host, user, (
seam:effect_operation_name(metta_py_dispatch_eq(_, _, _), 'py-eq', 2)
)).

provides(host, user, (
seam:effect_operation_name(metta_py_dispatch_truthy(_, _), 'py-truthy', 1)
)).

provides_declaration(host, user, foreign_space/1).

provides_declaration(host, user, grounded_length/2).

provides(host, user, (
seam:grounded_length(Space, Length) :-
    atom(Space),
    metta_py_foreign(Space),
    py_call('metta.foreign':'_provider_length'(Space), Length),
    integer(Length),
    Length >= 0
)).

provides_declaration(host, user, foreign_match/3).

provides_declaration(host, user, foreign_add/2).

provides_declaration(host, user, foreign_add_many/2).

provides_declaration(host, user, foreign_plan/5).

provides_declaration(host, user, foreign_remove/3).

provides_declaration(host, user, foreign_atoms/2).

provides_declaration(host, user, foreign_token/3).

provides_declaration(host, user, foreign_pushdown/3).

provides_declaration(host, user, foreign_refuse/2).

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
provides(host, user, (
seam:foreign_space(Space) :- metta_py_foreign(Space)
)).

%The refusal, handed back to the side that has the words. This raises; see
%metta.foreign.foreign_refuse for why it may not return.
provides(host, user, (
seam:foreign_refuse(Space, Capability) :-
    metta_py_foreign(Space),
    atom_string(Space, SpaceStr),
    atom_string(Capability, CapabilityStr),
    py_call(metta_ops:foreign_refuse(SpaceStr, CapabilityStr), _)
)).

%The declared-mode stream: the mode crosses WITH the call, the Python
%side enforces it where the provider's exceptions are native (a
%mid-iteration exception tunnels past every Prolog catch), and a kept
%failure arrives as the reserved ["x","error",AtomWire] item. The
%["x","end"] item marks exhaustion so an empty stream still claims the
%route and the engine never re-consults the provider through the
%fallback, which would consume a linear source twice.
provides(host, user, (
seam:foreign_erring(Space, Pattern, Licensed, Mode, Item) :-
    metta_py_foreign(Space),
    ( memberchk(limit(Limit), Licensed) -> true ; Limit = @(none) ),
    metta_py_encode(Pattern, [], Table, W),
    atom_string(Space, SpaceStr),
    atom_string(Mode, ModeStr),
    py_iter(metta_ops:foreign_match(SpaceStr, W, Limit, ModeStr), CW),
    metta_py_erring_item(CW, Pattern, Limit, Table, Space, Item)
)).

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
provides(host, user, (
seam:matchable_value(Blob) :-
    seam:host_object(Blob),
    py_call(metta_ops:is_matchable(Blob), R),
    R == @(true)
)).

provides(host, user, (
seam:custom_match(Blob, Other) :-
    metta_py_encode(Other, [], Table, W),
    py_iter(metta_ops:match_object(Blob, W), CW),
    metta_py_stream_item(CW),
    metta_py_answer_match(CW, Other, Table, '$metta-matchable')
)).

%Transactional participation for Python providers, driven by (writes Ctx
%transactional): the provider's own begin/commit/rollback methods.
provides(host, user, (
seam:foreign_begin(Space) :-
    metta_py_foreign(Space),
    atom_string(Space, SpaceStr),
    py_call(metta_ops:foreign_transaction(SpaceStr, "begin"), _)
)).

provides(host, user, (
seam:foreign_commit(Space) :-
    metta_py_foreign(Space),
    atom_string(Space, SpaceStr),
    py_call(metta_ops:foreign_transaction(SpaceStr, "commit"), _)
)).

provides(host, user, (
seam:foreign_rollback(Space) :-
    metta_py_foreign(Space),
    atom_string(Space, SpaceStr),
    py_call(metta_ops:foreign_transaction(SpaceStr, "rollback"), _)
)).

%The option reaches a provider whose match accepts a limit keyword and nobody
%else, which foreign.py decides from the signature, so a provider that never
%heard of it is called with none.
provides(host, user, (
seam:foreign_match(Space, Pattern, Options) :-
    metta_py_foreign(Space),
    ( memberchk(limit(Limit), Options) -> true ; Limit = @(none) ),
    metta_py_encode(Pattern, [], Table, W),
    atom_string(Space, SpaceStr),
    py_iter(metta_ops:foreign_match(SpaceStr, W, Limit), CW),
    metta_py_stream_item(CW),
    metta_py_answer_match(CW, Pattern, Limit, Table, Space)
)).

%What the provider claims about its own filtering for this pattern, asked
%only when there is a bound to act on, so an unbounded match does not pay for
%a crossing it gains nothing from. A provider with no pushdown method answers
%inexact, which is what every provider written before this says.
provides(host, user, (
seam:foreign_pushdown(Space, Pattern, Class) :-
    metta_py_foreign(Space),
    metta_py_encode(Pattern, W),
    atom_string(Space, SpaceStr),
    py_call(metta_ops:foreign_pushdown(SpaceStr, W), ClassStr),
    atom_string(Class, ClassStr)
)).

%Optional exact mutation for a provider that declared `add-token` and
%`remove-token`: the returned token keeps the provider's own identity, so a
%reference row can be withdrawn by exactly the occurrence it added.
provides(host, user, (
seam:foreign_add_token(Space, Term, Token) :-
    metta_py_foreign(Space),
    metta_py_encode(Term, W),
    atom_string(Space, SpaceStr),
    py_call(metta_ops:foreign_add_token(SpaceStr, W), Wire),
    metta_py_decode_shared(Wire, Decoded, _),
    ( Decoded = [t, Actor, Generation]
    -> Token = t(Actor, Generation)
    ; throw(error(domain_error(occurrence_token, Decoded), none)) )
)).

provides(host, user, (
seam:foreign_remove_token(Space, t(Actor, Generation), Removed) :-
    metta_py_foreign(Space),
    metta_py_encode([t, Actor, Generation], Wire),
    atom_string(Space, SpaceStr),
    py_call(metta_ops:foreign_remove_token(SpaceStr, Wire), Raw),
    metta_py_bool(Raw, Removed)
)).

provides(host, user, (
seam:foreign_atoms(Space, Atom) :-
    metta_py_foreign(Space),
    atom_string(Space, SpaceStr),
    py_iter(metta_ops:foreign_atoms(SpaceStr), CW),
    metta_py_stream_item(CW),
    metta_py_decode_shared(CW, Atom, _)
)).

provides(host, user, (
seam:foreign_token(Space, Pattern, Token) :-
    metta_py_foreign(Space),
    atom_string(Space, SpaceStr),
    metta_py_encode(Pattern, Wire),
    py_iter(metta_ops:foreign_tokens(SpaceStr, Wire), CW),
    metta_py_stream_item(CW),
    metta_py_decode_shared(CW, Pair, _),
    (   Pair = [[t, Actor, Generation], Candidate]
    ->  Token = t(Actor, Generation), Pattern = Candidate
    ;   throw(error(domain_error(occurrence_pair, Pair), none))
    )
)).

provides(host, user, (
seam:foreign_add(Space, Term) :-
    metta_py_foreign(Space),
    metta_py_encode(Term, W),
    atom_string(Space, SpaceStr),
    py_call(metta_ops:foreign_add(SpaceStr, W), _)
)).

%The claim seam. A provider without a Planner declares no plan capability, so
%the engine never asks; one that does may still decline per conjunction, which
%is a `None` on the Python side and a failure here.
%
%The rows are materialised and the goal replays them, rather than the goal
%calling back into Python per row. A claim is answered as a whole, so streaming
%would buy nothing and would hold a Python generator open across engine
%backtracking, which is the shape that makes a provider's state hard to reason
%about.
provides(host, user, (
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
    maplist(metta_py_decode_plan_row(Space), RowWs, Rows)
)).

%The batch seam. A provider without a BulkAdder declares no add-many capability,
%so this fails and the engine falls back to one seam:foreign_add/2 per atom.
provides(host, user, (
seam:foreign_add_many(Space, Terms) :-
    metta_py_foreign(Space),
    metta_py_capability(Space, 'add-many'),
    maplist(metta_py_encode, Terms, Ws),
    atom_string(Space, SpaceStr),
    py_call(metta_ops:foreign_add_many(SpaceStr, Ws), _)
)).

provides(host, user, (
seam:foreign_remove(Space, Term, Removed) :-
    metta_py_foreign(Space),
    metta_py_encode(Term, W),
    atom_string(Space, SpaceStr),
    py_call(metta_ops:foreign_remove(SpaceStr, W), R0),
    metta_py_bool(R0, Removed)
)).

provides_declaration(host, user, grounded_type_names/2).

%Class names cross as text; protocol type atoms use the ordinary wire.
%Decode each complete type with shared variables so (Pair $t $t) remains
%one constraint rather than two independently fresh variables.
provides(host, user, (
seam:grounded_type_names(X, Names) :-
    py_is_object(X),
    py_call(metta_ops:type_names(X), Candidates),
    maplist(metta_py_protocol_type, Candidates, Names)
)).

provides_declaration(host, user, grounded_algebra_type/3).

% Carrier predicates use the ordinary atom codec: Symbol and Expression stay
% atoms while Grounded unwraps. Exceptions reach the enclosing resource guard
% [tested: test_carrier_preserves_text_and_symbol_types; commit=8358dfc233bf299bb23eceddd94593a62372fe4b].
provides(host, user, (
seam:grounded_algebra_type(Type, Value, Truth) :-
    py_is_object(Type),
    metta_py_encode(Type, TypeWire),
    metta_py_encode(Value, ValueWire),
    py_call('metta.algebra':'_carrier_type_accepts'(TypeWire, ValueWire), Raw),
    ( Raw == @(true) -> Truth = true ; Truth = false )
)).
