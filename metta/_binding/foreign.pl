% Purpose: register and invoke host providers for foreign spaces.
% Assumes: loaded through _binding/shim.pl in its host module.
% Guarantees: optional add-token and remove-token callbacks preserve exact
%   provider identities [tested: test_token_mutation_receives_and_withdraws_a_reference;
%   commit=90ba93eb8f6e98ebfefc55416859bf13de6a8427].
% Guarantees: seam:foreign_space/1 answers from the engine's claim registry,
%   the one indexed fact the registration and unregistration doors keep in
%   step with the provider record inside the same transaction [tested:
%   extensions/python/tests/ch19_spaces_backed_by_anything/test_foreign.py;
%   commit=d60277df18afee021990c754b6e593fbb32d69a2].
% Owns resources: native provider values and their owned-record markers until
%   metta_py_unregister_foreign/1 removes them; captured clause references keep
%   the original participant alive through completion.
% Assumes: spaces:metta_owned_record_occurrences/3 and metta_owned_clause/2 supply
%   shared occurrence validation and decoding; neither a copied Python map nor
%   a second cardinality check authorizes a provider callback
%   [source: engine/spaces/owned_records.pl:metta_owned_record_occurrences/3; commit=05fae56ad5b23baa140cb4e6454cb7b304c06f4f].

%%%%%%%%%% Foreign spaces %%%%%%%%%%
%
% A space whose atoms live in a Python provider: a database, a dataframe, an
% API. The engine's hooks route match, add, remove and get-atoms here; the
% provider enumerates candidate atoms for a pattern, and unification against
% the pattern happens in Prolog, so the provider may over-approximate freely
% and soundness stays the engine's. Registration is dynamic, from Python.


:- dynamic metta_py_capability/2.

% HostSpace and HostFunction share the provider relation with distinct
% structural keys. The registration lifetime is separate from a Space handle.
metta_py_provider_declaration(Space,
    ['@owned-record', '&metta', ['PythonProvider', ['HostSpace', Space]],
     '&metta', ['@python-provider', ['HostSpace', Space]]]).

%The engine's own claim registry answers it: metta_py_register_foreign_/4
%claims the name for python in the same transaction that writes the provider
%record, and metta_py_unregister_foreign_/1 disclaims it in the one that
%removes the record, so the claim follows commit, rollback and snapshots
%exactly as the record does, and it is one indexed dynamic fact. Reading the
%record here instead went through the general matcher, 12 inferences an ask
%against 3, and the engine asks this of every native match and twice per
%door call: the eval door read 165 inferences a call, 24 of them this
%question [measured 2026-09-17: the door profile and the claim-against-record
%probe recorded in docs/journal/2026-09-11-classes-on-metta.md, "the door tax
%behind the participant capture", claim and record agreeing across register,
%unregister and a rolled-back registration; commit=d60277df18afee021990c754b6e593fbb32d69a2].
metta_py_foreign(Space) :-
    metta_space_claim(Space, python).

% The ownership guard enumerates names; the shared validator then checks the
% original stored keys, owner and cardinality before a host value can escape.
metta_py_provider_reference(Space, Provider, Ref) :-
    snapshot((
        metta_py_foreign(Space),
        metta_py_provider_declaration(Space, Declaration),
        spaces:metta_owned_record_occurrences(Declaration, _,
            [Ref-['@python-provider', ['HostSpace', Space], Provider]])
    )).

%The dispatch read: the row itself, through the reader every catalog row is
%read with. The validating reader above belongs to the doors that change a
%registration; a match, an add or a token crossing asks only which provider
%the name has now, and asked it under a snapshot with the whole owner and
%cardinality check on every crossing, twice per foreign match since Python's
%PROVIDERS mapping asks the engine back from inside the hook [measured
%2026-09-17: foreign-match 561 inferences a query with two snapshots in each,
%wt-battery-3/ai-tmp/ai_foreign_match_profile.py; commit=d60277df18afee021990c754b6e593fbb32d69a2].
metta_py_provider(Space0, Provider) :-
    metta_py_space_atom(Space0, Space),
    once(metta_contract_fact(['@python-provider', ['HostSpace', Space], Provider])).

metta_py_provider_names(Names) :-
    snapshot(findall(Space, metta_py_provider_reference(Space, _, _), Names)).

metta_py_capture_participant(Space, Provider, Protocol) :-
    atom_string(Space, SpaceString),
    py_call(metta_ops:foreign_participant(SpaceString, Provider),
            [Begin, Commit, Rollback]),
    Protocol = transaction(user:py_call(Begin:'__call__'(), _),
                           user:py_call(Commit:'__call__'(), _),
                           user:py_call(Rollback:'__call__'(), _)).


metta_py_erring_item(CW, _, _, _, _, _) :-
    metta_py_stream_frame(CW, Exception), !,
    %A declared mode is enforced on the Python side, so a frame arriving here
    %is what no mode may reinterpret: a transport failure, a control signal,
    %or a failure of the mode enforcement itself.
    metta_py_stream_raise(Exception).
metta_py_erring_item([XTag, End], _, _, _, _, end) :-
    ( XTag == "x" ; XTag == x ),
    ( End == "end" ; End == end ), !.
metta_py_erring_item([XTag, Err, ErrorW], _, _, _, _, kept(Kept)) :-
    ( XTag == "x" ; XTag == x ),
    ( Err == "error" ; Err == error ), !,
    metta_py_decode_shared(ErrorW, Kept, _).
metta_py_erring_item(CW, Pattern, Limit, Table, Space, answer) :-
    metta_py_answer_match(CW, Pattern, Limit, Table, Space).


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


metta_py_register_foreign(Space0, Provider, Capabilities, Delivery) :-
    metta_py_space_atom(Space0, Space),
    metta_transaction(metta_py_register_foreign_(Space, Provider, Capabilities, Delivery)).

metta_py_register_foreign_(Space, Provider, Capabilities, Delivery) :-
    %The engine-side claim comes first, so a name another provider already owns
    %is refused by name here instead of landing in metta_py_foreign/1 and then
    %resolving against MORK's or redis's clauses by load order. A
    %re-registration of a name this side already holds is the same owner and
    %the same extent, which the door treats as idempotent exactly as the line
    %below does.
    metta_claim_space(Space, python),
    (   metta_py_provider_reference(Space, Held, _)
    ->  ( Held == Provider -> true
        ; throw(error(permission_error(register, foreign_provider, Space),
                      context(metta_py_register_foreign/4,
                              'unregister the current provider before replacing it'))) )
    ;   metta_py_provider_schema,
        metta_py_provider_declaration(Space, Record),
        spaces:metta_owned_record_occurrences(Record, Owners, []),
        ( Owners == []
        -> 'add-atom'('&metta', ['owned-by', ['PythonProvider', ['HostSpace', Space]]], _)
        ; true ),
        'add-atom'('&metta', ['@python-provider', ['HostSpace', Space], Provider], _)
    ),
    %A newly registered provider is a new source: the linear-consumption
    %mark belongs to the drained OBJECT, and this is the door a fresh one
    %arrives through.
    metta_source_reset(Space),
    retractall(metta_py_capability(Space, _)),
    %Each word against the engine's own (vocabulary provider-capability ...)
    %row, at the one door a Python provider's set arrives through. A word
    %outside it used to register happily and then gate nothing, which reads
    %exactly like a provider that does not have the capability.
    forall(member(Capability0, Capabilities),
           ( ( atom(Capability0) -> Capability = Capability0
             ; atom_string(Capability, Capability0) ),
             metta_require_foreign_capability(Space, Capability),
             assertz(metta_py_capability(Space, Capability)) )),
    metta_py_declare_delivery(Space, Delivery).

% Registration publishes the shared pattern explicitly. A concrete or changed
% declaration matching its query is not the same source contract.
metta_py_provider_schema :-
    metta_py_provider_declaration(_, Declaration), copy_term(Declaration, Query),
    (   spaces:metta_native_pair('&metta', Query, _, Ref),
        spaces:metta_owned_clause(Ref, _:Head),
        native_storage_functor('&metta', Functor),
        metta_storage_term(Functor, Stored, _, Head), Stored =@= Declaration
    ->  true
    ;   'add-atom'('&metta', Declaration, _)
    ).

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
    metta_py_space_atom(Space0, Space),
    metta_transaction(metta_py_unregister_foreign_(Space)).

metta_py_unregister_foreign_(Space) :-
    metta_py_provider_reference(Space, Provider, _),
    retractall(metta_py_capability(Space, _)),
    metta_py_declare_delivery(Space, []),
    'remove-atom'('&metta', ['@python-provider', ['HostSpace', Space], Provider], _),
    'remove-atom'('&metta', ['owned-by', ['PythonProvider', ['HostSpace', Space]]], _),
    metta_disclaim_space(Space, python).
