% Purpose: register and invoke Python operations through the native wire.
% Assumes: loaded through _binding/shim.pl in its host module.
% Owns resources: operation declarations until metta_py_unregister_op/2 removes their native registrations
% [source: extensions/python/metta/_binding/operations.pl:903; commit=cd62330ceacc8f1254eed9791c3f6203b48a1c9e].

%%%%%%%%%% Python-backed MeTTa functions %%%%%%%%%%
%
% A registered operation is an ordinary MeTTa function whose body lives in
% Python. Arguments cross encoded so Python sees real atoms; results cross
% back encoded. kind det calls once; kind many enumerates a Python iterator
% through py_iter/2, which is genuine nondeterminism. The raw kinds skip the
% encoding for speed and receive janus's default conversion instead, which
% suits operations over object references such as tensors.

:- dynamic metta_py_op_spec/3.

%An operation that answers nothing sends the declined sentinel, which turns
%into failure here: the semidet reading of a Python None or a raised Decline.
metta_py_declined(TR) :- TR = [T, D], metta_py_tag(T, x), metta_py_tag(D, declined).

%A variable that crosses and comes back is the CALLER'S variable, not a fresh
%one with the same name. Without this the boundary silently broke variable
%identity, which is the whole of why no relational use of a Python operation
%worked: a native (= (mcons $h $t) ($h 2 3)) answers an expression whose head
%IS $x, so binding the result to (9 2 3) binds $x to 9, while the same shape
%through a registered operation answered a fresh $_34678 that binding did
%nothing to [tested: test_a_variable_crossing_python_comes_back_the_same_variable].
%
%The decoder already shares by name WITHIN one term, which is what makes an
%answer mentioning $x twice mention one variable. It just started from an
%empty table. Seeding it with the arguments is the whole fix, and the seed is
%now the very map metta_py_encode_arguments/3 wrote for those arguments
%rather than one rebuilt from them afterwards: rebuilding read the cells'
%addresses a whole Python crossing later, by which time a collection could
%have moved them. A call whose arguments hold no variable seeds an empty map
%and mints nothing, so it still pays nothing at all for this.
%metta_py_failure/2 is extensions/python/metta/_binding/surface.pl's, and a registered operation was the one
%Python caller not reaching it. That is not a cosmetic gap: without it janus's
%own error term reaches MeTTa carrying the live exception OBJECT and a live
%TRACEBACK object, which is the defect metta_py_failure/2 was written to fix
%for py-call and py-atom, and it names a Python file and line and no MeTTa
%call at all. What a program gets instead is
%(Error (python_error ZeroDivisionError "division by zero") (context (op 1) ...)),
%which it can branch on, compare and print after the failure
%[tested: test_an_operation_failure_names_the_metta_call].
%
%The catch is written out here rather than going through metta_py_guard/2, its
%three other callers' spelling, because the wrapper is a predicate call and
%this is the hot path: guard plus catch cost two inferences per call where the
%catch alone costs one [measured 2026-08-17: the encoded operation at 14.01
%through the wrapper, 13.01 written out]. Same catcher, same recovery.
%Python's equality and truth protocols are richer than Prolog term identity,
%but the wire's structural classes have exact local answers. Keep this pair
%ahead of the generic dispatch so a compiled Python body does not cross the
%host once per comparison. Failure means an opaque grounded value is present;
%its Python class may implement __eq__ or __bool__, so only the retained host
%route may decide it [source: Python 3.14 data model, object.__eq__ and
%object.__bool__, https://docs.python.org/3/reference/datamodel.html;
%commit=551f6236be947d5c52f5243e3d56f0009a000071].
%Numbers lead because compiled arithmetic comparisons are the loop case. The
%two guards and arithmetic comparison are in this clause so that case pays no
%classification or helper calls.
metta_py_dispatch_eq(Left, Right, Result) :-
    number(Left), number(Right),
    !,
    ( Left =:= Right -> Result = true ; Result = false ).
%The railway rows, the same law the host table's guard carries: a compiled
%strict position propagates error DATA instead of computing over it, so a
%comparison meeting an (Error ...) answers the error rather than reading
%it as an expression. The native lanes decide without crossing, so they
%need their own rows; they sit after the number clause, which cannot meet
%an error, so the compiled loop case pays nothing.
metta_py_dispatch_eq(Left, _Right, Left) :-
    nonvar(Left), Left = ['Error'|_], !.
metta_py_dispatch_eq(_Left, Right, Right) :-
    nonvar(Right), Right = ['Error'|_], !.
metta_py_dispatch_eq(Left, Right, Result) :-
    metta_py_native_eq(Left, Right, Result),
    !.
metta_py_dispatch_eq(Left, Right, Result) :-
    metta_py_dispatch([det, false, false], 'py-eq', [Left, Right], Result).

metta_py_dispatch_truthy(Value, Result) :-
    number(Value),
    !,
    ( Value =:= 0 -> Result = false ; Result = true ).
metta_py_dispatch_truthy(Value, Value) :-
    nonvar(Value), Value = ['Error'|_], !.
metta_py_dispatch_truthy(Value, Result) :-
    metta_py_native_truthy(Value, Result),
    !.
metta_py_dispatch_truthy(Value, Result) :-
    metta_py_dispatch([det, false, false], 'py-truthy', [Value], Result).

% The key is compiled from the catalog kind once at registration. Inverse
% calls always stream, including inverses of deterministic forward functions.
metta_py_dispatch([Kind, Raw, Inverse], Name, Args, Result) :-
    ( Kind == async
    -> metta_py_launch(Name, Args, Result)
    ; ( Inverse == true
      -> Call = [Name, Result],
         ( Raw == true -> Payload = Result
         ; metta_py_encode(Result, [], Table, Payload) )
      ; Call = [Name|Args],
        ( Raw == true -> Payload = Args
        ; metta_py_encode_arguments(Args, Payload, Table) )
      ),
      ( ( Kind == many ; Inverse == true ) -> Stream = true ; Stream = false ),
      ( Raw == false, Inverse == false, Stream == true,
        metta_on_error_mode(Name, Call, DeclaredMode), DeclaredMode \== abort
      -> Mode = DeclaredMode
      ; Mode = abort
      ),
      ( nb_current('$metta_python_context', Context0), integer(Context0)
      -> Context = Context0
      ; Context = @(none)
      ),
      Spec = metta_ops:dispatch([Kind, Raw, Inverse], Context, Name, Payload, Mode),
      ( Stream == true -> Crossing = py_iter(Spec, Wire) ; Crossing = py_call(Spec, Wire) ),
      catch(metta_py_host_call(Name, Stream, Crossing), Error,
            Wire = '$metta_op_error'(Error)),
      ( Wire = '$metta_op_error'(Failure)
      -> ( ( Raw == true ; Inverse == true )
         -> metta_py_failure(Call, Failure)
         ; metta_py_op_erring(Name, Args, Failure, Result) )
      ; Stream == true, metta_py_stream_frame(Wire, Exception)
      -> metta_py_stream_failure(Call, Exception)
      ; Inverse == true
      -> metta_py_inverse_width(Name, Args, Wire),
         ( Raw == true -> maplist(metta_py_raw_norm, Wire, Args)
         ; metta_py_decode_arguments(Wire, Table, Args) )
      ; Raw == true
      -> Wire \== @(none), metta_py_raw_norm(Wire, Result)
      ; Stream == true, metta_py_relation_form(Wire, Fields)
      -> metta_py_relation_result(Fields, Args, Table, Result)
      ; ( Stream == true -> true ; \+ metta_py_declined(Wire) ),
        ( Wire = [_, _, _, _|_]
        -> metta_py_answer_result(Wire, Name, Table, Result)
        ; metta_py_decode_shared_(Wire, Result, Table, _) )
      )
    ).

%Go's blocking-syscall handoff applied at the five-rank admission boundary:
%oracleIO yields before entering Python; the scheduler detaches that engine
%onto a transient worker and keeps every bounded normal carrier available.
%writesState stays on normal carriers and serializes at the store write door;
%the three read ranks remain eligible on every normal carrier. A deterministic
%call reifies success, failure, or error and hands back to normal explicitly.
%A nondeterministic call runs in a nested SWI engine: each pull happens after
%a dirty handoff and each answer returns after a normal handoff, avoiding both
%carrier pinning and a cleanup-time yield (SWI forbids engine_yield/1 from a
%cleanup handler) [source:
%https://github.com/golang/go/blob/c19862e5f8415b4f24b189d065ed739517c548ba/src/runtime/proc.go#L4781-L4831,
%Go 1.26.5 entersyscallblock; tested:
%test_a_blocking_oracle_uses_the_dirty_lane_without_pinning_normal_work;
%commit=39092863ae34184a9f955f185ff57c1ff177ec40].
metta_py_host_call(Name, Stream, Goal) :-
    (   nb_current('$metta_scheduler_task', _),
        metta_operation_effect(Name, oracleIO)
    ->  (   Stream == true
        ->  metta_py_dirty_many(Goal)
        ;   metta_py_dirty_once(Goal)
        )
    ;   call(Goal)
    ).

metta_py_dirty_once(Goal) :-
    engine_yield('$metta_scheduler_lane'(dirty)),
    catch(( once(call(Goal)) -> Outcome = success ; Outcome = failure ),
          Error,
          Outcome = error(Error)),
    engine_yield('$metta_scheduler_lane'(normal)),
    metta_py_dirty_outcome(Outcome).

metta_py_dirty_outcome(success).
metta_py_dirty_outcome(failure) :- fail.
metta_py_dirty_outcome(error(Error)) :- throw(Error).

metta_py_dirty_many(Goal) :-
    term_variables(Goal, Variables),
    (   nb_current('$metta_python_context', Context0)
    ->  Context = Context0
    ;   Context = none
    ),
    setup_call_cleanup(
        metta_host_hold(Variables,
                      metta_py_dirty_inner(Context, Goal, Variables),
                      HostEngine),
        metta_py_dirty_many_next(HostEngine, Variables),
        metta_host_hold_close(HostEngine)).

metta_py_dirty_inner(none, Goal, _) :- !,
    call(Goal).
metta_py_dirty_inner(Context, Goal, _) :-
    b_setval('$metta_python_context', Context),
    call(Goal).

metta_py_dirty_many_next(HostEngine, Variables) :-
    engine_yield('$metta_scheduler_lane'(dirty)),
    metta_py_hold_reified(HostEngine, Event),
    metta_py_dirty_many_event(Event, HostEngine, Variables).

metta_py_dirty_many_event(the(Values), HostEngine, Variables) :-
    engine_yield('$metta_scheduler_lane'(normal)),
    (   Variables = Values
    ;   metta_py_dirty_many_next(HostEngine, Variables)
    ).
metta_py_dirty_many_event(no, _, _) :-
    engine_yield('$metta_scheduler_lane'(normal)),
    fail.
metta_py_dirty_many_event(throw(Error), _, _) :-
    engine_yield('$metta_scheduler_lane'(normal)),
    throw(Error).

%The coroutine itself is not created here. async_prepare retains decoded
%arguments and a copied Context; observation_defer starts it only after the
%outer transaction has committed and discards it on rollback. The launch atom
%therefore rides the transaction's ordinary buffered event segment, while the
%landing atom below is a later write from the event-loop thread.
metta_py_launch(Name, Args, Space) :-
    metta_py_encode_arguments(Args, Tagged, _),
    metta_async_future_new(Space, Done),
    (   catch(metta_py_async_prepare(Name, Tagged, Space, Done, Token),
              Error,
              ( metta_async_future_abandon(Space, Done), throw(Error) ))
    ->  true
    ;   metta_async_future_abandon(Space, Done),
        fail
    ),
    metta_py_async_publish_launch(Name, Space, Token, Done).

%A local observation frame makes the event and deferred start one ordered
%segment even outside a user transaction. Nested commit merges the pair into
%an outer frame; a direct commit publishes launch and then starts. If the
%launch watcher fails after the write committed, observation_commit/0 still
%runs the later deferred start before rethrowing.
metta_py_async_publish_launch(Name, Space, Token, Done) :-
    seam:observation_begin,
    catch((   'add-atom'('&metta', ['async-op', Name, Space, launch], _),
              seam:observation_defer(
                  metta_py_async_start(Token),
                  metta_py_async_discard(Token, Space, Done))
          ->  Outcome = commit
          ;   Outcome = discard
          ),
          Error,
          Outcome = error(Error)),
    metta_py_async_finish_launch(Outcome, Token, Space, Done).

metta_py_async_finish_launch(commit, _, _, _) :- !,
    seam:observation_commit.
metta_py_async_finish_launch(discard, Token, Space, Done) :- !,
    seam:observation_discard,
    metta_py_async_discard(Token, Space, Done),
    fail.
metta_py_async_finish_launch(error(Error), Token, Space, Done) :-
    seam:observation_discard,
    metta_py_async_discard(Token, Space, Done),
    throw(Error).

metta_py_async_prepare(Name, Tagged, Space, Done, Token) :-
    (   nb_current('$metta_python_context', Context), integer(Context)
    ->  Parent = Context
    ;   Parent = @(none)
    ),
    metta_py_host_call(
        Name, false,
        py_call(metta_ops:async_prepare(Name, Tagged, Parent), Token)),
    metta_async_future_bind(Token, Name, Space, Done).

metta_py_async_start(Token) :-
    py_call(metta_ops:async_start(Token), Started),
    metta_py_bool(Started, true), !.
metta_py_async_start(Token) :-
    throw(error(metta_async_start_failed(Token),
                context(metta_py_async_start/1,
                        'the prepared coroutine was absent at commit'))).

metta_py_async_discard(Token) :-
    catch(py_call(metta_ops:async_discard(Token), _), _, true),
    metta_async_future_discard(Token).

metta_py_async_discard(Token, Space, Done) :-
    catch(py_call(metta_ops:async_discard(Token), _), _, true),
    metta_async_future_discard(Token, Space, Done).

metta_py_async_land(Token, Status0, Payload) :-
    metta_py_tag(Status0, Status),
    metta_async_future(Token, Name, Space, _),
    catch(metta_py_async_outcome(Status, Payload, Space, Outcome),
          Error,
          Outcome = error(Error)),
    %Terminal state precedes the landing notification: a synchronous landing
    %observer may await the future it was told has landed without deadlocking
    %the callback that still needs to settle it. The converse is therefore not
    %promised. Settling releases every waiter here, so an await that has
    %returned orders nothing against the publication below, which on a loaded
    %box may not have started; an observation that must be seen is awaited on
    %its own signal. CPython resolves the same pair the same way, waking
    %Future.result() inside the lock and running the done-callbacks after
    %releasing it [CPython 3.14, Lib/concurrent/futures/_base.py,
    %Future.set_result]. Swapping these two goals hangs
    %test_a_blocking_landing_observer_does_not_delay_the_future in 5.24s and
    %deadlocks test_a_landing_observer_can_await_the_future_it_observes
    %outright, whose observer awaits the very future the callback would still
    %owe a settle.
    metta_async_future_settle(Token, Outcome, Name, Space),
    metta_py_async_publish_landing(Name, Space).

%A failed primary call still has the captured runtime and token. This path
%records that failure but emits no lifecycle atom, because publication itself
%is the failed operation. The future's single-assignment rule preserves an
%outcome committed before a watcher raised.
metta_py_async_fail_landing(Token, Class0, Exception) :-
    metta_py_async_outcome(error, [Class0, Exception], _, Outcome),
    metta_async_future_fail(Token, Outcome).

%A watcher failure is raised to the background publisher and logged there; it
%cannot rewrite an operation outcome that was already committed to its future.
metta_py_async_publish_landing(Name, Space) :-
    (   'add-atom'('&metta', ['async-op', Name, Space, landing], _)
    ->  true
    ;   throw(error(metta_async_landing_publish_failed(Name, Space),
                    context(metta_py_async_land/3,
                            'the lifecycle write answered no result')))
    ).

metta_py_async_outcome(ok, Tagged, Space, done) :-
    (   metta_py_declined(Tagged)
    ->  true
    ;   metta_py_decode_shared(Tagged, Result, _),
        future_add_atom(Space, Result)
    ).
metta_py_async_outcome(cancelled, _, _, cancelled).
metta_py_async_outcome(error, [Class0, Exception], _,
                       error(error(python_error(Class, Exception), none))) :-
    metta_py_tag(Class0, Class).

:- multifile prolog:error_message//1.
prolog:error_message(metta_async_start_failed(Token)) -->
    [ 'async operation ~w was prepared but absent when its transaction committed'-[Token] ].
prolog:error_message(metta_async_landing_publish_failed(Name, Space)) -->
    [ 'async operation ~w could not publish its landing for ~w'-[Name, Space] ].

metta_py_native_eq(Left, Right, Result) :-
    metta_py_native_class(Left, LeftClass),
    metta_py_native_class(Right, RightClass),
    metta_py_native_eq_classes(LeftClass, Left, RightClass, Right, Result).

%Order matters: true and false are atoms in Prolog but bool is a numeric
%subclass in Python, and an unbound variable must never bind to either while
%being classified.
metta_py_native_class(Value, variable) :- var(Value), !.
metta_py_native_class(true, boolean) :- !.
metta_py_native_class(false, boolean) :- !.
metta_py_native_class(Value, number) :- number(Value), !.
metta_py_native_class(Value, string) :- string(Value), !.
metta_py_native_class(Value, symbol) :- atom(Value), !.
%The decoder has already proved an expression wire is a proper list. Inspect
%only its outer cell here: is_list/1 would walk the whole operand before the
%recursive comparison and would make repeated end-of-list comparisons
%quadratic in a traversal.
metta_py_native_class([], expression) :- !.
metta_py_native_class([_|_], expression).

metta_py_native_eq_classes(boolean, Left, boolean, Right, Result) :-
    metta_py_boolean_number(Left, LeftNumber),
    metta_py_boolean_number(Right, RightNumber),
    metta_py_numeric_eq(LeftNumber, RightNumber, Result).
metta_py_native_eq_classes(boolean, Left, number, Right, Result) :-
    metta_py_boolean_number(Left, LeftNumber),
    metta_py_numeric_eq(LeftNumber, Right, Result).
metta_py_native_eq_classes(number, Left, boolean, Right, Result) :-
    metta_py_boolean_number(Right, RightNumber),
    metta_py_numeric_eq(Left, RightNumber, Result).
metta_py_native_eq_classes(number, Left, number, Right, Result) :-
    metta_py_numeric_eq(Left, Right, Result).
metta_py_native_eq_classes(string, Left, string, Right, Result) :-
    ( Left == Right -> Result = true ; Result = false ).
metta_py_native_eq_classes(symbol, Left, symbol, Right, Result) :-
    ( Left == Right -> Result = true ; Result = false ).
metta_py_native_eq_classes(variable, Left, variable, Right, Result) :-
    ( Left == Right -> Result = true ; Result = false ).
metta_py_native_eq_classes(expression, Left, expression, Right, Result) :-
    metta_py_native_expression_eq(Left, Right, Result).
metta_py_native_eq_classes(_, _, _, _, false).

metta_py_boolean_number(true, 1).
metta_py_boolean_number(false, 0).

%Arithmetic comparison gives Python's numeric widening, signed-zero equality,
%and NaN inequality directly.
metta_py_numeric_eq(Left, Right, Result) :-
    ( Left =:= Right -> Result = true ; Result = false ).

metta_py_native_expression_eq([], [], true).
metta_py_native_expression_eq([], [_|_], false).
metta_py_native_expression_eq([_|_], [], false).
metta_py_native_expression_eq([Left|Lefts], [Right|Rights], Result) :-
    metta_py_native_eq(Left, Right, HeadResult),
    (   HeadResult == false
    ->  Result = false
    ;   metta_py_native_expression_eq(Lefts, Rights, Result)
    ).

metta_py_native_truthy(Value, Result) :-
    metta_py_native_class(Value, Class),
    metta_py_native_truth_class(Class, Value, Result).

metta_py_native_truth_class(variable, _, true).
metta_py_native_truth_class(boolean, Value, Value).
metta_py_native_truth_class(number, Value, Result) :-
    ( Value =:= 0 -> Result = false ; Result = true ).
metta_py_native_truth_class(string, Value, Result) :-
    ( Value == "" -> Result = false ; Result = true ).
metta_py_native_truth_class(symbol, _, true).
metta_py_native_truth_class(expression, Value, Result) :-
    ( Value == [] -> Result = false ; Result = true ).

%The guard wraps the whole enumeration and that is safe in both directions:
%catch/3 keeps Goal's choice points and re-establishes the catcher on
%backtracking, so a generator yielding two values and then raising is caught
%on the third [measured 2026-08-17: catch/3 over member/2 gives all three
%solutions, and a throw on the last one is caught].


%A Python stream pulled through py_iter/2 cannot raise. py_iter reads a raising
%pull as an exhausted one: it never consults the Python error indicator after
%PyIter_Next, so the goal carries on over a SILENTLY TRUNCATED stream and the
%still-set exception surfaces at whatever crossing runs next
%[source: janus 1.5.3 janus.c:py_iter3, the two
%`state->next = PyIter_Next(state->iterator)` calls, neither followed by
%check_error; commit=0ee5a2dfee0e37a23b0eb9c765b477d7f90295fe]. What "whatever runs next" turned out to be was
%a provider match answering one atom instead of two and then taking SIGSEGV
%inside janus's own error path, and a KeyboardInterrupt out of a
%nondeterministic operation printing "foreign predicate
%system:$new_findall_bag/0 did not clear exception" and then vanishing
%[tested:
%test_an_inference_limit_spent_inside_a_provider_callback_is_an_inference_limit_error,
%test_a_control_signal_out_of_a_python_stream_leaves_no_pending_exception;
%commit=0ee5a2dfee0e37a23b0eb9c765b477d7f90295fe].
%
%So every Python stream this file pulls ends a failure with this reserved frame
%instead, and the live exception is handed straight back to Python to raise
%there. Nothing is reconstructed: janus's own check_error then converts it
%exactly as it converts a deterministic py_call callback's exception, the
%unwind forms for KeyboardInterrupt and SystemExit included, and
%metta_py_original_exception/2 still finds the very object for the Python
%boundary to re-raise. metta._errors.errors.stream_failure is the other half.
%
%py_is_object/1 is what keeps the frame reserved on the RAW doors, whose items
%are the operation author's own values rather than encoded wire.
metta_py_stream_frame([Tag, Raise, _Class, Exception], Exception) :-
    metta_py_tag(Tag, x),
    metta_py_tag(Raise, raise),
    py_is_object(Exception).

%Hand the carried exception back and let Python raise it. Never returns: a
%py_call that answered instead of raising means stream_reraise stopped doing
%the one thing it exists for, which must not read as an empty stream.
metta_py_stream_raise(Exception) :-
    py_call(metta_ops:stream_reraise(Exception), _),
    throw(error(metta_py_stream_reraise_returned(Exception), none)).

%The same raise, reported through Call's structured boundary: what a
%deterministic operation's failure already does, so an operation's answer
%stream fails the way its single answer would. Never returns either.
metta_py_stream_failure(Call, Exception) :-
    catch(metta_py_stream_raise(Exception), Error, metta_py_failure(Call, Error)).

%Succeeds for an ordinary stream item, for the provider seam, whose eager
%refusals reach the caller as janus made them and whose lazy ones must read
%identically.
%
%Two clauses rather than one if-then-else, which is the bounded cursor's own
%shape and for the same measured reason: SWI charges an if-then-else one more
%inference when its condition FAILS than when it succeeds, and the condition
%here fails on every ordinary item. Both provider routes ask this PER
%CANDIDATE, so that one inference is a third of the guard's whole price
%[measured 2026-09-06 over 2000 provider candidates: get-atoms 52,036
%inferences unguarded, 58,036 through the if-then-else and 56,036 through these
%two clauses; the same 2,000-candidate match through collapse 66,311, 70,311
%and 68,311; commit=0ee5a2dfee0e37a23b0eb9c765b477d7f90295fe]. The remaining 2 per candidate are this call and
%metta_py_stream_frame/2's. Spelling that predicate's three goals into the
%first clause head instead would take it to 1, and is deliberately not done:
%one reservation rule serves five doors, and nothing measures this constant as
%a bottleneck.
metta_py_stream_item(Item) :-
    metta_py_stream_frame(Item, Exception),
    !,
    metta_py_stream_raise(Exception).
metta_py_stream_item(_).

prolog:error_message(metta_py_stream_reraise_returned(Exception)) -->
    [ 'metta_ops:stream_reraise answered ~q instead of raising it'-[Exception] ].

%An encoded generator's exact tuple/dict yield is a relation row, tagged away
%from the atom wire. Python has already mapped sparse parameter names to their
%argument positions and checked the row shape. Decode every field against the
%call's shared variable table, then use the engine matcher itself: custom
%grounded matching, numeric promotion, space operands and the occurs check all
%remain one law. Failure filters the candidate; success binds the call and
%answers unit. py_iter contributes one choice point per yielded occurrence, so
%duplicates remain duplicates.
metta_py_relation_form([Tag, Fields], Fields) :-
    metta_py_tag(Tag, r).

metta_py_relation_result(Fields, Args, Table, []) :-
    metta_py_relation_fields(Fields, Args, Table, _).

metta_py_relation_fields(Fields, Args, Table0, Table) :-
    metta_py_relation_fields(Fields, Args, 0, Table0, Table).

metta_py_relation_fields([], _, _, Table, Table).
metta_py_relation_fields([[Index, Wire]|Fields], Args0, Offset, Table0, Table) :-
    integer(Index),
    Index >= Offset,
    Skip is Index - Offset,
    metta_py_relation_argument(Skip, Args0, Actual, Args),
    metta_py_decode_shared_(Wire, Candidate, Table0, Table1),
    metta_match_atoms(Candidate, Actual),
    Next is Index + 1,
    metta_py_relation_fields(Fields, Args, Next, Table1, Table).

metta_py_relation_argument(0, [Actual|Args], Actual, Args).
metta_py_relation_argument(Skip, [_|Args0], Actual, Args) :-
    Skip > 0,
    Next is Skip - 1,
    metta_py_relation_argument(Next, Args0, Actual, Args).

%An operation's declared error mode, consulted only in the recovery, so
%the success path pays one functor test. keep reduces the failed call to
%its (Error ...) atom; empty answers nothing, the semidet reading;
%control signals and transport failures always pass to the thrower.
metta_py_op_erring(Name, Args, Error, Result) :-
    (   control_exception(Error)
    ->  metta_py_failure([Name|Args], Error)
    ;   metta_transport_failure(Error)
    ->  metta_py_failure([Name|Args], Error)
    ;   metta_on_error_mode(Name, [Name|Args], Mode)
    ->  (   Mode == keep
        ->  metta_error_answer([Name|Args], Error, Result)
        ;   Mode == empty
        ->  fail
        ;   metta_py_failure([Name|Args], Error)
        )
    ;   metta_py_failure([Name|Args], Error)
    ).

%Raw results skip the wire encoding, so a Python boolean arrives as janus's
%@(true)/@(false); normalize to the language booleans exactly as 'py-call'
%does, so raw operations compose with if, and, or:
metta_py_raw_norm('@'(true), true) :- !.
metta_py_raw_norm('@'(false), false) :- !.
metta_py_raw_norm(R, R).

%A raw None is janus's @(none); it reads as no answer, the same semidet rule
%the encoded path applies, since MeTTa has no None value to hand back:
%The same catcher the encoded paths carry, and for the same reason: without it
%a raw operation's failure reaches MeTTa as janus's own term, holding the live
%exception OBJECT, a live TRACEBACK and an unbound context, so `(catch (op 1))`
%answered
%(Error (python_error ZeroDivisionError <ZeroDivisionError>)
%       (context $_26320 (python_stack <traceback>)))
%which names an address, cannot be compared and says nothing about which MeTTa
%call failed. Skipping the wire encoding is a speed decision about ARGUMENTS
%and results; it was never a decision to report failures differently
%[tested: test_a_raw_operation_fails_like_an_encoded_one].
%
%It costs one inference, and that is the floor rather than a choice: "the
%overhead of calling a goal through catch/3 is comparable to call/1"
%[source: SWI-Prolog manual, catch/3]. The zero-cost alternative was looked
%for and rejected. prolog:prolog_exception_hook/5 fires only on an actual
%exception, and it is a process-global singleton `library(prolog_stack)`,
%trap/1 and the GUI debugger already use, it "is never called recursively",
%and converting this error means calling back into Python to render the
%message, which is exactly what a non-reentrant hook must not do.
%
%Against the crossing it guards, one inference is not the number that matters:
%a raw operation costs 0.87 microseconds where a MeTTa function costs 0.09
%[measured 2026-08-17], so janus dominates it by an order of magnitude.
%Register every arity of a Python-backed function in one step, checked
%before anything mutates: a name whose compiled predicate would collide
%with a static procedure ((+)/3, say) throws HERE, with no state touched,
%and every previously registered arity of the name is replaced rather than
%left behind for calls the new callable no longer serves.
%The dogfood route: registration parameters read from the contract atoms in
%&metta rather than passed. The Python keywords are sugar that asserts the
%atoms ((op Name Arity Kind) per arity, (inverse Name) when a backwards
%direction exists), and this compiles the predicate FROM them, through
%exactly the builders the passed-parameter route uses, so the clause is
%identical by construction and the cube gate proves it stays that way.
metta_py_compile_op(Name0) :-
    ( atom(Name0) -> Name = Name0 ; atom_string(Name, Name0) ),
    findall(Arity-Kind, metta_contract_fact([op, Name, Arity, Kind]), Pairs),
    (   Pairs == []
    ->  throw(error(metta_contract_missing_op(Name), none))
    ;   true
    ),
    pairs_keys(Pairs, Arities),
    Pairs = [_-Kind|_],
    (   forall(member(_-K, Pairs), K == Kind)
    ->  true
    ;   throw(error(metta_contract_conflict(Name, Pairs), none))
    ),
    (   metta_contract_fact([inverse, Name])
    ->  Invertible = true
    ;   Invertible = false
    ),
    metta_py_register_op_set(Name, Arities, Kind, Invertible).

%A (handles ...) declaration, written and coherence-checked in one
%transaction: the new entry is asserted, every critical pair over the
%context is routed, and a disagreeing tie throws metta_contract_conflict,
%which rolls the assert back. The overlap is caught at declaration time
%naming both entries, not on the first query that falls into it.
metta_py_declare_handles(Space, Tagged, Ctx0) :-
    ( atom(Ctx0) -> Ctx = Ctx0 ; atom_string(Ctx, Ctx0) ),
    transaction(( metta_py_add(Space, Tagged),
                  metta_handles_coherent(Ctx) )).

:- multifile prolog:error_message//1.
prolog:error_message(metta_contract_missing_op(Name)) -->
    [ 'compiling ~w from the contract found no (op ~w Arity Kind) atom in \c
       &metta; the registration sugar asserts them before compiling, so \c
       reaching this means the atoms and the compile call got out of \c
       order'-[Name, Name] ].
prolog:error_message(metta_contract_conflict(Name, Pairs)) -->
    [ 'the contract atoms for ~w disagree on its kind across arities: ~w. \c
       One operation has one kind'-[Name, Pairs] ].

metta_py_register_op_set(Name0, Arities, Kind, Invertible) :-
    ( atom(Name0) -> Name = Name0 ; atom_string(Name, Name0) ),
    metta_py_set_invertible(Name, Invertible),
    %OPEN before any mutation: the tier refusal and the name probe both run
    %while there is still nothing to undo, and each one's diagnostic names
    %what to do about it. The unregister of prior arities may release the
    %name; the adopt below claims it again, so the set's final state is
    %claimed whatever order the arities land in.
    forall(member(A, Arities),
           (   metta_py_op_spec(Name, A, _)
           ->  true
           ;   PredArity is A + 1,
               metta_host_open_function(Name, python, PredArity)
           )),
    forall(metta_py_op_spec(Name, Old, _), metta_py_unregister_op(Name, Old)),
    forall(member(A, Arities), metta_py_register_op(Name, A, Kind)).

%The name probe, its owner-naming refusal and the metta_op_name_taken
%message live in the engine now (metta_host_open_function/3): the protocol
%was host-agnostic bookkeeping every binding restated in order. The one
%shortcut kept here is the caller's: an arity this file already registered
%occupies its own functor, so re-opening it proves nothing.

%Register a Python-backed function of the given MeTTa arity. The compiled
%predicate carries one extra output argument, the engine's own convention:
metta_py_register_op(Name0, Arity, Kind) :-
    ( atom(Name0) -> Name = Name0 ; atom_string(Name, Name0) ),
    metta_py_unregister_op(Name, Arity),
    length(Args, Arity),
    append(Args, [Result], HeadArgs),
    Head =.. [Name | HeadArgs],
    metta_py_op_body(Kind, Name, Args, Result, Forward),
    metta_py_directed_body(Name, Kind, Args, Result, Forward, Body),
    %Into &self's module, which every other space inherits, so the operation is
    %callable from all of them and its name is free: asserting into the module
    %the ENGINE resolves in is what made 217 ordinary names unusable at MeTTa
    %arity 1.
    metta_py_module('&self', Base),
    assertz(Base:(Head :- Body)),
    assertz(metta_py_op_spec(Name, Arity, Kind)),
    %Adopt AFTER the dispatch clause is in place: the engine marks the name a
    %function of the BASE tier (which every space inherits, so the operation
    %stays callable after a named space defines an equation of the same
    %name), refreshes dependents against the clause that already exists, and
    %claims the name for python.
    PredArity is Arity + 1,
    metta_host_adopt_function(Name, python, Kind, PredArity).

%The engine asks who a dispatch goal really is, so a purity refusal names the
%operation rather than this file's dispatcher. The name is the goal's first
%argument in all four kinds, which is why it is recoverable exactly.


%The MeTTa arity, which is the argument list's length: the engine's extra
%output slot is the dispatch goal's third argument and not one of these.
metta_py_dispatch_arity(Args, Arity) :- is_list(Args), !, length(Args, Arity).
metta_py_dispatch_arity(_, unknown).

metta_py_op_body(det,      'py-eq', [Left, Right], R,
                 metta_py_dispatch_eq(Left, Right, R)) :- !.
metta_py_op_body(det,      'py-truthy', [Value], R,
                 metta_py_dispatch_truthy(Value, R)) :- !.
metta_py_op_body(Kind, Name, Args, R, metta_py_dispatch(Key, Name, Args, R)) :-
    metta_py_dispatch_key(Kind, false, Key).

metta_py_dispatch_key(raw_det, Inverse, [det, true, Inverse]) :- !.
metta_py_dispatch_key(raw_many, Inverse, [many, true, Inverse]) :- !.
metta_py_dispatch_key(Kind, Inverse, [Kind, false, Inverse]).

:- dynamic metta_py_op_invertible/1.

metta_py_set_invertible(Name, Invertible) :-
    retractall(metta_py_op_invertible(Name)),
    ( ( Invertible == true ; Invertible == "true" )
      -> assertz(metta_py_op_invertible(Name)) ; true ).

%An operation that declared an inverse compiles a MODE TEST into its clause,
%and one that did not compiles exactly the body it compiled before. That is
%the point of deciding it here rather than in the dispatch: a direction almost
%no operation can serve must not cost every operation a check per call.
%
%The three modes read in the order a reader would ask them. Ground arguments
%are an ordinary forward call whatever the result slot holds, so a forward
%call never reaches the inverse even when the caller left the result unbound.
%Otherwise a bound result with unbound arguments is the relational position,
%which is what (let (f $h $t) (1 2 3) ...) compiles to. Anything else is
%forwards, and fails the way it always did, because an operation cannot
%invent a result from nothing.
%
%This is Curry's mode-directed reading of a function as a relation, done by
%hand because a foreign function cannot be narrowed: Curry does not invert its
%own `external` functions either, so an explicit backwards direction is the
%same answer Prolog's plus/3 and succ/2 give for their non-narrowable
%builtins [tested: test_a_registered_operation_runs_backwards].
metta_py_directed_body(Name, Kind, Args, Result, Forward, Body) :-
    (   metta_py_op_invertible(Name)
    ->  metta_py_dispatch_key(Kind, true, Key),
        Backward = metta_py_dispatch(Key, Name, Args, Result),
        Body = (   ground(Args)
               ->  Forward
               ;   nonvar(Result)
               ->  Backward
               ;   Forward
               )
    ;   Body = Forward
    ).

%The inverse crosses the way the operation's FORWARD direction crosses. An
%author writes one function pair, and a raw operation whose inverse went
%through the wire encoding saw `str` for a symbol going forwards and `Sym`
%coming back, which is one pair and two value conventions
%[tested: test_a_raw_operations_inverse_crosses_raw_too].
metta_py_inverse_width(Name, Args, Answered) :-
    length(Args, Arity),
    (   is_list(Answered), length(Answered, Arity)
    ->  true
    ;   metta_py_inverse_arity_error(Name, Arity, Answered)
    ).

%ONE table across the answered tuple, seeded with the map the result was
%encoded under. Decoding argument by argument started an empty table at each
%one, so a variable an inverse put in two positions came back as two
%variables, and a variable it took from the RESULT came back as neither the
%result's nor its own. Nothing unifies these afterwards the way a match
%candidate is unified with its pattern: Args is bound from the decode and
%that is the answer.
metta_py_decode_arguments([], _, []).
metta_py_decode_arguments([Tagged|Rest], Table0, [Term|Terms]) :-
    metta_py_decode_shared_(Tagged, Term, Table0, Table),
    metta_py_decode_arguments(Rest, Table, Terms).

metta_py_inverse_arity_error(Name, Arity, TArgs) :-
    ( is_list(TArgs) -> length(TArgs, Got) ; Got = 1 ),
    throw(error(metta_py_inverse_arity(Name, Arity, Got),
                context(metta, 'the inverse answered the wrong number of arguments'))).

:- multifile prolog:error_message//1.

%A tuple of the wrong width would otherwise unify against nothing and read as
%"this result has no preimage", which is the one answer an inverse is entitled
%to give and the one that hides the mistake.
prolog:error_message(metta_py_inverse_arity(Name, Wanted, Got)) -->
    [ 'the inverse of ~w answered an argument tuple of width ~d, and the \c
       operation takes ~d'-[Name, Got, Wanted], nl,
      '  an inverse returns the arguments as a tuple of that width, or the \c
       bare value at arity one' ].

%Remove one registered arity of an operation, leaving other arities alone.
%When nothing defines the name any more, forget the function entirely, the
%same forgetting 'remove-atom'/3 does when a last equation goes: fun/1 and
%arity/2 retract, so the next compile treats the name as data again:
metta_py_unregister_op(Name0, Arity) :-
    ( atom(Name0) -> Name = Name0 ; atom_string(Name, Name0) ),
    %The drop is guarded by this file's own bookkeeping, so only arities this
    %file registered are dropped; the engine's drop then retracts the base
    %tier's clauses and the arity row generically.
    ( metta_py_op_spec(Name, Arity, _)
      -> PredArity is Arity + 1,
         metta_host_drop_function(Name, PredArity),
         retractall(metta_py_op_spec(Name, Arity, _))
    ; true ),
    %"does anything still define this name at any arity" is a question about
    %OUR clauses, and clause/3 raises permission_error(access,
    %private_procedure, _) on a protected system predicate rather than
    %answering it, so unregistering an operation named print or format threw
    %from here instead of unregistering. A builtin is never a clause of ours
    %[tested test_unregistering_a_name_a_system_predicate_shares_does_not_throw].
    ( \+ metta_py_name_still_defined(Name)
      -> metta_host_forget_function(Name)
    ; true ).

%Does anything still define this name at any arity? Two tiers are asked by
%name because ONE of them cannot be reached by generating: current_predicate/1
%with the arity unbound enumerates a module's own predicates and the ones
%explicitly imported into it, and NOT the ones it reaches through its base
%chain. A registered operation's clauses are in the base tier's module and a
%Prolog function's are in the host's, so asking either alone released a name
%the other still defined: registering an operation over a Prolog registration
%was refused, correctly, and dropped the Prolog one's arity/2 and fun/1 on the
%way out, so the call it had been answering came back unreduced
%[tested test_a_prolog_registration_is_not_silently_replaced].
metta_py_name_still_defined(Name) :-
    spaces:metta_ensure_compiled(Name),
    ( metta_py_module('&self', Module) ; Module = user ),
    current_predicate(Module:Name/A),
    functor(Head, Name, A),
    \+ predicate_property(Module:Head, built_in),
    clause(Module:Head, _, _),
    !.

%The names a source declared for itself, so register_prolog can answer what it
%registered without being told. The membership record is the engine's, not the
%library's, which is what makes the extension a unit rather than a list the
%library has to keep: it registers, and the engine remembers
%[source: PostgreSQL, "the objects of the extension go together"].
%The file is compared after resolving both sides, because the engine records
%SWI's canonical absolute path and a caller passes whatever they typed.
%Read off the FILE record rather than off extension membership. An extension
%is optional on the Prolog side, so asking through one made a file with
%`metta_export` and no `metta_extension` look like a failed registration when
%every name in it had registered.
%What a source declares, read WITHOUT running it, so register_prolog can
%refuse a file that declares nothing before consulting it. It used to consult
%first and check after, so a provider file with no declaration raised and
%installed the provider anyway: catching the error made everything work, which
%is the one outcome that teaches an author to ignore an error.
metta_py_source_declares(Source0, Declares) :-
    ( atom(Source0) -> Source = Source0 ; atom_string(Source, Source0) ),
    metta_source_declarations(Source, Declarations),
    metta_py_classify_declarations(Declarations, Declares).

%The same question of source held in memory, which has no file to open.
metta_py_string_declares(Text, Declares) :-
    metta_string_declarations(Text, Declarations),
    metta_py_classify_declarations(Declarations, Declares).

metta_py_classify_declarations(Declarations, Declares) :-
    ( memberchk(export(_), Declarations) -> Exports = true ; Exports = false ),
    ( memberchk(extension(_), Declarations) -> Extension = true
    ; Extension = false ),
    metta_py_declares(Exports, Extension, Declares).

metta_py_declares(true, true, "both").
metta_py_declares(true, false, "exports").
metta_py_declares(false, true, "extension").
metta_py_declares(false, false, "nothing").

metta_py_declared_exports(Source0, Names) :-
    ( atom(Source0) -> Source = Source0 ; atom_string(Source, Source0) ),
    ( absolute_file_name(Source, Resolved, [file_errors(fail)]) -> true
    ; Resolved = Source ),
    findall(S,
            ( metta_file_export(Recorded, Name),
              ( Recorded == Resolved -> true ; Recorded == Source ),
              atom_string(Name, S) ),
            Names0),
    sort(Names0, Names).
