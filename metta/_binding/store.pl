% Purpose: read and mutate atom bags through the engine storage doors.
% Assumes: loaded through _binding/shim.pl in its host module.
% Guarantees: transfer lands the stored occurrence metta_host_subtract/4
%   answers, never the wire instantiated by the subtraction's match
%   [tested 2026-09-30T08:34:03+10:00: test_transfer_lands_the_occurrence_that_left].
% Guarantees: metta_py_held/3 answers in one crossing which recorded atoms the
%   space holds as stored variants, one stored occurrence per wire
%   [tested 2026-09-30T08:34:03+10:00: test_definition_caches_agree_with_the_space,
%   test_definition_caches_follow_atoms_given_back].
% Guarantees: metta_py_publish_definition/2 makes every write of a define, and
%   of the door that removes a Defined, one transaction, so a define failing
%   at any write leaves every space whose storage the transaction reaches as it
%   was, a native space and a provider declaring transactional writes, which
%   it enlists, and no subscriber hears any of its writes; a provider that
%   declares nothing about its writes takes a definition and gives it back,
%   and what one whose storage no transaction reaches kept and lost of a
%   failed publication is counted against what it held before and left for
%   the define's error (metta_py_publication_residue/1)
%   [tested 2026-09-30T08:34:03+10:00: test_a_define_failing_at_any_write_changes_nothing,
%   test_a_define_failing_part_way_leaves_an_equal_equation_standing,
%   test_a_definition_publishes_into_and_leaves_a_provider_that_declares_nothing,
%   test_a_define_into_a_transactional_provider_rolls_it_back,
%   test_a_define_failing_in_a_provider_outside_the_engine_names_what_it_kept,
%   test_a_removal_failing_in_a_provider_outside_the_engine_names_what_it_lost,
%   test_a_define_failing_in_the_foreign_rules_provider_leaves_it_as_it_was,
%   test_a_provider_unreadable_after_a_failed_define_is_named_not_hidden].

%%%%%%%%%% Space operations %%%%%%%%%%
%
% Writes go through MeTTa's own 'add-atom'/3, so an equation takes the
% engine's function path (register_fun, arity, translate_clause, invalidation)
% exactly as one read from a file does, and removals through the engine's own
% doors: one occurrence through 'subtract-atom'/3, or its reporting face
% metta_host_subtract/4 where the occurrence itself is wanted, and the drain
% through remove-atom.

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
    metta_py_work(open, Before),
    metta_py_check_algebra_values(Space, Name, CarrierWire, ValuesWire),
    metta_py_work(close, After),
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
%engine's own subtraction rather than the private service beneath it:
%'subtract-atom'/3 for remove(), its variadic face and the `-=` operator, and
%for transfer, which lands what it took, the reporting face
%metta_host_subtract/4, which shares subtract-atom's refusals and selection.
%So the unbound-term guard is written once and the four doors cannot disagree
%about what one occurrence means, while a removing door leaves the read to
%the engine, which makes it only while a removal handler exists or the
%pattern needs the occurrence to say how it leaves.
%Reaching past the head is what made them disagree: remove(V.x) read the
%variable as the whole space and DRAINED it while answering True, and
%transfer(V.x, to=b) died on an opaque instantiation error, its transaction
%rolling the source back [measured 2026-09-01].
metta_py_subtract(Space, Term, Verdict) :-
    'subtract-atom'(Space, Term, Result),
    metta_py_subtract_verdict(Result, Verdict).

metta_py_subtract(Space, Term, Verdict, Occurrence) :-
    metta_host_subtract(Space, Term, Result, Occurrence),
    metta_py_subtract_verdict(Result, Verdict).

metta_py_subtract_verdict(Result, Verdict) :-
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

%One crossing MOVES a batch: each wire subtracts one occurrence from the
%source and, when one was there, lands THAT occurrence in the target, all
%inside one engine transaction, so a mid-move failure rolls every side back
%and an atom is never lost between spaces. What lands is the stored atom that
%left, never the wire as the subtraction's unification instantiated it: over
%a stored (= (subject $y) $y), that instantiation of (= (subject $x)
%(+ $x 10)) is a rational tree, and landing it raised cyclic_term out of
%assertz and rolled the whole move back [measured 2026-09-29T23:29:54+10:00:
%spaces_tokens:a_subtraction_binds_nothing_of_its_pattern, failing at
%c122ab1f6 where the subtraction binds the wire]. The count answers how many
%moved; an absent member moves nothing and counts nothing, the
%found-reporting grain of the one-occurrence remove door.
metta_py_transfer(From, To, Wires, Count) :-
    metta_transaction(metta_py_transfer_each(Wires, From, To, 0, Count)).

metta_py_transfer_each([], _, _, Count, Count).
metta_py_transfer_each([Wire|Wires], From, To, Count0, Count) :-
    metta_py_decode_shared(Wire, Term, _),
    metta_py_subtract(From, Term, Verdict, Occurrence),
    (   Verdict == true
    ->  'add-atom'(To, Occurrence, _),
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

%A Python definition's publication in ONE transaction: every write it makes,
%in the order given, reflection rows, declarations, the equations it retires
%and the ones it adds, and its doc, with the definition's watch on its
%equations' heads (subscriptions.pl, metta_py_watch/1) lapsed while they run
%and set to its new heads after, so the definition never hears its own writes.
%The door that removes a Defined publishes its removals the same way, with an
%empty watch. A failure part way rolls every write back, so nothing has to
%find by value an atom the space may also hold an equal copy of: the cleanup
%this replaced removed an added batch by value when the add failed part way,
%taking a user's own equal equation with it
%[tested 2026-09-30T08:34:03+10:00: test_a_define_failing_part_way_leaves_an_equal_equation_standing].
%The transaction is the engine's internal form, SWI's transaction/1, which
%its rule registrations and repairs run in and metta_py_declare_handles/3
%already uses, entered holding the typing-policy mutex, never the user's
%(transaction ...) form: metta_transaction/1 guards every foreign write for a
%rollback of its own, so it refused a define into a provider that declares
%nothing about its writes, which the foreign rules example publishes into
%(engine/metta/space_hooks.pl,
%metta_in_user_transaction/0) [tested 2026-09-30T08:34:03+10:00:
%test_a_definition_publishes_into_and_leaves_a_provider_that_declares_nothing],
%and its outer commit walks every clause update the transaction made through
%the owned-record and retirement checks [source 2026-09-30T04:48:53+10:00:
%engine/spaces/owned_records.pl, metta_prepare_owned_records/1, and
%engine/spaces/lifecycle.pl, metta_prepare_retirements/1]. A define inside
%the user's transaction or speculative() nests in it and meets its rules.
%How far the transaction reaches a written space's storage decides the rest
%(metta_py_storage_reach/2): a native space's storage is the engine's
%database; a provider declaring transactional writes is enlisted, which only
%the engine's coordinator does, so a publication writing to one runs in
%metta_transaction/1 and the provider rolls back with it
%[tested 2026-09-30T08:34:03+10:00: test_a_define_into_a_transactional_provider_rolls_it_back];
%any other provider keeps what it takes whatever the transaction does, so
%the publication counts each atom it writes there before it starts and,
%when it fails, leaves what the provider kept and lost for the define's
%error to name (metta_py_publication_residue/1) [tested 2026-09-30T08:34:03+10:00:
%test_a_define_failing_in_a_provider_outside_the_engine_names_what_it_kept,
%test_a_define_failing_in_the_foreign_rules_provider_leaves_it_as_it_was].
%The mutex comes first, as
%the engine's own writers take it: a clause compiled inside a transaction
%that opened before it keeps every dynamic type check, since the snapshot the
%transaction reads may be older than a typing policy another owner has
%published since [source 2026-09-30T06:12:17+10:00: engine/type_rules.pl,
%with_typing_policy_stable/1 and typing_policy_shortcuts_allowed/1], and
%then a Number argument paid the whole check on every call where number/1
%decides it [tested 2026-09-30T08:34:03+10:00:
%test_a_defined_function_keeps_its_static_type_shortcuts].
%The frame is the user form's own (ext_points.pl, observation_begin/0):
%it holds the writes' events until the transaction commits and drops them
%when it does not [tested 2026-09-30T08:34:03+10:00: test_a_define_failing_at_any_write_changes_nothing].
%Each write is [add, Space, Wires] or [remove, Space, Wires]. An add of one
%atom crosses the one-atom door and of several the batch door, as Space.add
%chooses, so the equations still arrive as one definition batch; a remove
%takes one occurrence of each atom, as Space.remove's variadic door does.
metta_py_publish_definition(Writes, Watches) :-
    Publication = metta_py_publication(Writes, Watches),
    (   member([_, Written, _], Writes), seam:foreign_space(Written)
    ->  metta_py_foreign_plan(Writes, Publication, Transaction, Before)
    ;   Transaction = transaction(Publication), Before = []
    ),
    nb_setval('$metta_py_publication_residue', []),
    seam:observation_begin,
    catch((   type_rules:with_typing_policy_stable(Transaction)
          ->  Outcome = commit
          ;   Outcome = discard
          ),
          Error,
          Outcome = error(Error)),
    metta_py_publication_finished(Outcome, Before).

metta_py_publication(Writes, Watches) :-
    maplist(metta_py_unwatch, Watches),
    maplist(metta_py_definition_write, Writes),
    metta_py_watch(Watches).

%A publication writing to a foreign space: the coordinator's transaction when
%a provider it writes enlists, and, for each provider that keeps what it
%takes, the atoms it writes there with how many equal occurrences it holds
%before the transaction starts.
metta_py_foreign_plan(Writes, Publication, Transaction, Before) :-
    findall(Space, member([_, Space, _], Writes), Spaces0),
    sort(Spaces0, Spaces),
    maplist(metta_py_storage_reach, Spaces, Reaches),
    (   memberchk(enlisted, Reaches)
    ->  Transaction = metta_transaction(Publication)
    ;   Transaction = transaction(Publication)
    ),
    findall(Space-Counted,
            ( nth1(I, Spaces, Space), nth1(I, Reaches, provider),
              metta_py_written_counts(Writes, Space, Counted) ),
            Before).

metta_py_publication_finished(commit, _) :- !,
    seam:observation_commit.
%A publication that did not commit drops its frame, then notes what each
%provider outside the transaction kept, whatever the frame's rollback
%callbacks answered: a failing one still fails the publication, as a failed
%discard always has, but only after the residue is noted, so it cannot hide
%what a provider kept.
metta_py_publication_finished(Outcome, Before) :-
    (   seam:observation_discard -> Discarded = true ; Discarded = false ),
    (   Outcome = error(Cause) -> true ; Cause = failed ),
    metta_py_note_residue(Before, Cause),
    Discarded == true,
    Outcome = error(Error),
    throw(Error).

%How far a transaction opened here reaches a space's storage: engine for a
%native space, whose storage is the engine's database; enlisted for a
%provider declaring (writes Space transactional), which the engine's
%coordinator begins, commits and rolls back with it (engine/spaces/foreign.pl,
%foreign_write/3); provider for any other, whose storage keeps what it takes.
metta_py_storage_reach(Space, Reach) :-
    (   \+ seam:foreign_space(Space)
    ->  Reach = engine
    ;   metta_writes(Space, transactional)
    ->  Reach = enlisted
    ;   Reach = provider
    ).

%Each distinct atom the writes add to or remove from Space, with how many
%occurrences equal to it Space holds now.
metta_py_written_counts(Writes, Space, Counted) :-
    findall(Term,
            ( member([_, Written, Wires], Writes), Written == Space,
              member(Wire, Wires), metta_py_decode_for_add(Wire, Term) ),
            Terms),
    foldl(metta_py_distinct_variant, Terms, [], Distinct),
    findall(Term-Count,
            ( member(Term, Distinct), metta_py_stored_count(Space, Term, Count) ),
            Counted).

metta_py_distinct_variant(Term, Seen, Seen) :-
    member(Earlier, Seen), Earlier =@= Term, !.
metta_py_distinct_variant(Term, Seen, [Term|Seen]).

%The occurrences equal to Term a space holds, through the space's own match,
%so a foreign space answers from its provider; a more general stored atom
%that merely unifies with Term is not one of them.
metta_py_stored_count(Space, Term, Count) :-
    aggregate_all(count,
                  ( copy_term(Term, Probe),
                    match_stored(Space, Probe, Probe, _),
                    Probe =@= Term ),
                  Count).

%What each provider kept and lost of a failed publication, counted against
%what it held before, so an occurrence it held before is never named. A
%provider that cannot be read back is an error of its own, naming the cause:
%what it kept is then unknown, and saying nothing would hide that.
metta_py_note_residue(Before, Cause) :-
    foldl(metta_py_space_residue(Cause), Before, [], Residue),
    nb_setval('$metta_py_publication_residue', Residue).

metta_py_space_residue(Cause, Space-Counted, Residue0, Residue) :-
    catch(metta_py_count_moves(Space, Counted, Kept, Lost), ReadError,
          throw(error(metta_py_provider_unread(Space, ReadError, Cause), none))),
    (   Kept == [], Lost == []
    ->  Residue = Residue0
    ;   metta_py_encode(Space, SpaceWire),
        append(Residue0, [[SpaceWire, Kept, Lost]], Residue)
    ).

metta_py_count_moves(Space, Counted, Kept, Lost) :-
    foldl(metta_py_count_move(Space), Counted, []-[], Kept-Lost).

metta_py_count_move(Space, Term-Before, Kept0-Lost0, Kept-Lost) :-
    metta_py_stored_count(Space, Term, After),
    metta_py_encode(Term, Wire),
    (   After > Before
    ->  N is After - Before, length(Copies, N), maplist(=(Wire), Copies),
        append(Kept0, Copies, Kept), Lost = Lost0
    ;   After < Before
    ->  N is Before - After, length(Copies, N), maplist(=(Wire), Copies),
        append(Lost0, Copies, Lost), Kept = Kept0
    ;   Kept = Kept0, Lost = Lost0
    ).

%The residue the last failed publication on this thread left, taken once:
%[SpaceWire, KeptWires, LostWires] for each provider that kept or lost part
%of it, empty when every space it wrote rolled back.
metta_py_publication_residue(Residue) :-
    (   nb_current('$metta_py_publication_residue', Residue0)
    ->  Residue = Residue0
    ;   Residue = []
    ),
    nb_setval('$metta_py_publication_residue', []).

:- multifile prolog:error_message//1.
prolog:error_message(metta_py_provider_unread(Space, ReadError, Cause)) -->
    [ 'a define writing to ~w failed, and ~w\'s provider, which keeps what it \c
       takes whatever a transaction does, could not be read back to say \c
       what it kept: ~q. The define failed with: ~q'-[Space, Space, ReadError,
                                                     Cause] ].

%The unit-answering face, as metta_py_add/3 is to metta_py_add/2.
metta_py_publish_definition(Writes, Watches, true) :-
    metta_py_publish_definition(Writes, Watches).

metta_py_definition_write([add, Space, [Wire]]) :- !,
    metta_py_add(Space, Wire).
metta_py_definition_write([add, Space, Wires]) :-
    metta_py_add_many(Space, Wires).
metta_py_definition_write([remove, Space, Wires]) :-
    metta_py_remove_each(Wires, Space, 0, _).

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

%An occurrence of EXACTLY Term in a native space, variables renamed apart,
%one solution per stored copy. The probe unifies, so the stored clause is
%decoded and compared as a variant: a more general sibling such as
%(= (f $x) $y) unifies with (= (f $x) (g $x)) and is not an occurrence of it,
%which is why match/4, the containment door's test, cannot answer this.
metta_py_stored_variant(Space, Term, Token) :-
    copy_term(Term, Probe),
    spaces:metta_native_pair(Space, Probe, Token, Ref),
    spaces:metta_owned_clause(Ref, _:Head),
    native_storage_functor(Space, Functor),
    metta_storage_term(Functor, Stored, _, Head),
    Stored =@= Term.

%Which of these atoms the space holds, one 1 or 0 per wire, each stored
%occurrence answering one wire, so an atom published twice needs two copies.
%A Python definition asks this of the space before it trusts what it once
%published (extensions/python/metta/_declare/definitions.py, _standing): the
%space is the authority, and the registry only remembers what it wrote.
%Time: one indexed probe per wire plus one variant test per stored atom that
%unifies with it; a foreign space pays one enumeration of its provider.
metta_py_held(Space, Wires, Held) :-
    maplist(metta_py_decode_for_add, Wires, Terms),
    (   seam:foreign_space(Space)
    ->  findall(Atom, 'get-atoms'(Space, Atom), Pool),
        foldl(metta_py_held_pooled, Terms, Held, Pool, _)
    ;   foldl(metta_py_held_native(Space), Terms, Held, [], _)
    ).

metta_py_held_native(Space, Term, Flag, Taken0, Taken) :-
    (   metta_py_stored_variant(Space, Term, Token),
        \+ memberchk(Token, Taken0)
    ->  Flag = 1, Taken = [Token|Taken0]
    ;   Flag = 0, Taken = Taken0
    ).

metta_py_held_pooled(Term, Flag, Pool0, Pool) :-
    (   select(Atom, Pool0, Rest), Atom =@= Term
    ->  Flag = 1, Pool = Rest
    ;   Flag = 0, Pool = Pool0
    ).

%One initial future snapshot and the change-stream position that follows it.
%The dedicated answer mutex makes the two fields one observation rather than a
%bag read followed by an unrelated counter read.
metta_py_future_snapshot(Space, [Watermark, Encoded]) :-
    lib_thread:metta_future_snapshot(Space, Atoms, Watermark),
    maplist(metta_py_encode, Atoms, Encoded).
