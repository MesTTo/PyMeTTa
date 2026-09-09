% Purpose: register and invoke host providers for foreign spaces.
% Assumes: loaded through _binding/shim.pl in its host module.
% Owns resources: provider and capability registrations until metta_py_unregister_foreign/1 removes them
% [source: extensions/python/metta/_binding/foreign.pl:329; commit=WORKTREE].

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
:- multifile seam:foreign_token/3.
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
    metta_py_stream_item(CW),
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
    metta_py_stream_item(CW),
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
    metta_py_stream_item(CW),
    metta_py_decode_shared(CW, Atom, _).

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
    ).

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
