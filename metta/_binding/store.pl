% Purpose: read and mutate atom bags through the engine storage doors.
% Assumes: loaded through _binding/shim.pl in its host module.

%%%%%%%%%% Space operations %%%%%%%%%%
%
% Writes go through MeTTa's own 'add-atom'/3 and 'remove-atom'/3, so an
% equation takes the engine's function path (register_fun, arity,
% translate_clause, invalidation) exactly as one read from a file does, and
% removal keeps the engine's own semantics (a plain atom removal is retractall).

metta_py_add(Space, Tagged) :-
    metta_py_decode_shared(Tagged, Term, _),
    'add-atom'(Space, Term, _).

%The unit-answering face of the same door. An execution policy runs its goal
%with an output argument appended (metta_py_wrapped_goal/4), so a write with
%nothing to answer needs somewhere to put one; `true` is that answer and the
%Python side discards it. Outside a scope the void face is what crosses, so a
%write pays nothing for the scope it is not in.
metta_py_add(Space, Tagged, true) :-
    metta_py_add(Space, Tagged).

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

%The declaration itself remains catalog data in &metta, while the operations
%its law certificate names belong to the space that declared it. Switch to
%that equation module around the ordinary add door so catalog validation and
%runtime annotation evaluation apply the same definitions.
metta_py_declare_algebra(DeclaringSpace, Tagged) :-
    metta_py_decode_shared(Tagged, Term, _),
    metta_py_module(DeclaringSpace, Module),
    metta_py_in_module(Module, 'add-atom'('&metta', Term, _)).

metta_py_check_algebra_values(Space, Name0, CarrierWire, ValuesWire) :-
    ( atom(Name0) -> Name = Name0 ; atom_string(Name, Name0) ),
    metta_py_decode_shared(CarrierWire, Carrier, _),
    maplist(metta_py_decode_for_add, ValuesWire, Values),
    metta_py_module(Space, Module),
    metta_py_in_module(Module,
        maplist(metta_require_algebra_value(Name, Carrier), Values)).

metta_py_check_algebra_values_accounted(Space, Name, CarrierWire, ValuesWire, Used) :-
    metta_py_work(Before),
    metta_py_check_algebra_values(Space, Name, CarrierWire, ValuesWire),
    metta_py_work(After),
    Used is After - Before.

% A nested Janus call can see the raw signal before its enclosing guard does.
metta_py_raw_limit_kind(Error, time_limit) :- Error == time_limit_exceeded.
metta_py_raw_limit_kind(Error, inference_limit) :- Error == inference_limit_exceeded.

metta_py_decode_for_add(Tagged, Term) :-
    metta_py_decode_shared(Tagged, Term, _).

%The engine decides how a batch crosses. This chose for MORK itself and so
%bypassed metta_add_atoms/2 entirely, which is where the rule that a batch may
%not skip per-atom work lives: an equation added to a MORK space alongside any
%other atom was stored inert [measured 2026-08-16].
%The batch is one definition batch, as a Python transaction is
%(metta_py_transaction/2), so its reference publication runs once at the end
%rather than once per origin row it stores: copying a space that borrows from
%K homes re-adds K `(from ...)` rows, and each row published on its own,
%walking every row before it, so a copy cost K^2 [measured 2026-09-17:
%67,690, 211,905, 731,155 and 2,722,368 inferences for 5, 10, 20 and 40
%origins, 13,538 to 68,059 per origin, before; command=ai probe over
%Space.copy() with m.stats(); commit=14a44cfa4dfc67a9cd7c602fafe86dd8b377aaf9].
metta_py_add_many(Space, TaggedList) :-
    maplist(metta_py_decode_for_add, TaggedList, Terms),
    filereader:with_definition_batch(metta_add_atoms(Space, Terms)).

%The unit-answering face, as metta_py_add/3 is to metta_py_add/2.
metta_py_add_many(Space, TaggedList, true) :-
    metta_py_add_many(Space, TaggedList).

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

%One initial future snapshot and the change-stream position that follows it.
%The dedicated answer mutex makes the two fields one observation rather than a
%bag read followed by an unrelated counter read.
metta_py_future_snapshot(Space, [Watermark, Encoded]) :-
    metta_future_snapshot(Space, Atoms, Watermark),
    maplist(metta_py_encode, Atoms, Encoded).
