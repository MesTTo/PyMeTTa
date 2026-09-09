% Purpose: transact, clear, allocate and release logical spaces.
% Assumes: loaded through _binding/shim.pl in its host module.
% Owns resources: anonymous space names; metta_py_release_space/1 clears and returns eligible names to the pool
% [source: extensions/python/metta/_binding/lifecycle.pl:193; commit=cd62330ceacc8f1254eed9791c3f6203b48a1c9e].

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

%The unit-answering face, as metta_py_add/3 is to metta_py_add/2.
metta_py_clear(Space, true) :-
    metta_py_clear(Space).

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
%property 'new-space'/1 has: (chain (new-space) $s (get-type $s)) is SpaceType
%[source: engine/metta/control.pl, 'new-space'/1]. Minting only the NAME left
%metta.space() answering
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
    \+ spaces:space_parent_child_used(Name),
    \+ metta_py_foreign(Name),
    \+ metta_host_stored(Name, _).

%asserta, so the pool is a STACK and the next mint answers the name just
%released. With assertz it was a queue, and `retract/1` takes the oldest free
%clause, so `drop()` then `_new_space()` returned the same name only while
%nothing else was free -- which is every test run alone and not a suite.
%Measured 2026-09-07 under `--randomly-seed=13683517`: two earlier tests had
%freed &pyspace_42 and &pyspace_43, the mint took 42, the drop put 42 back
%BEHIND 43, and the next mint answered 43 for a released 42, failing
%test_a_dropped_handle_cannot_write_into_the_name_it_released and
%test_new_spaces_drop_and_names_recycle, which both state the property.
%A queue promises nothing a caller can use; a stack promises exactly what they
%assert. The scan below is unaffected: retract still backtracks past a revived
%candidate, now from the newest free name rather than the oldest
%[tested: test_a_dropped_handle_cannot_write_into_the_name_it_released,
% test_new_spaces_drop_and_names_recycle,
% test_a_second_context_does_not_reuse_a_revived_space_name].
metta_py_pool_space(Name) :-
    ( metta_py_free_space(Name) -> true ; asserta(metta_py_free_space(Name)) ).

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
