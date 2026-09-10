% Purpose: register and invoke host providers for foreign spaces.
% Assumes: loaded through _binding/shim.pl in its host module.
% Owns resources: provider and capability registrations until metta_py_unregister_foreign/1 removes them
% [source: extensions/python/metta/_binding/foreign.pl:329; commit=cd62330ceacc8f1254eed9791c3f6203b48a1c9e].

%%%%%%%%%% Foreign spaces %%%%%%%%%%
%
% A space whose atoms live in a Python provider: a database, a dataframe, an
% API. The engine's hooks route match, add, remove and get-atoms here; the
% provider enumerates candidate atoms for a pattern, and unification against
% the pattern happens in Prolog, so the provider may over-approximate freely
% and soundness stays the engine's. Registration is dynamic, from Python.


:- dynamic metta_py_foreign/1.
:- dynamic metta_py_capability/2.


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
