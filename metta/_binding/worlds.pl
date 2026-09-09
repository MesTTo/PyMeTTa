% Purpose: admit and execute frozen worlds and compensating operations.
% Assumes: loaded through _binding/shim.pl in its host module.
% Owns resources: saga wrappers and the receipt sink until metta_py_saga_capture_end/1 releases them
% [source: extensions/python/metta/_binding/worlds.pl:230; commit=WORKTREE].
% Guarded by: $metta_saga_wrappers serializes temporary predicate wrapping.

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
