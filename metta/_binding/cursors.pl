% Purpose: retain, advance and close host answer cursors.
% Assumes: loaded through _binding/shim.pl in its host module.
% Owns resources: held cursors and captured memory; metta_py_cursor_close/1 releases either cursor representation
% [source: extensions/python/metta/_binding/cursors.pl:metta_py_cursor_close/1; commit=8358dfc233bf299bb23eceddd94593a62372fe4b].

% The captured cursor's text buffer is a memory file; declared here rather
% than left to the library index, which the no-autoload configuration
% (run.sh NO_AUTOLOAD=1) does not consult.
:- autoload(library(memfile),
            [new_memory_file/1, open_memory_file/4, memory_file_to_string/2,
             free_memory_file/1]).

%%%%%%%%%% Lazy cursors %%%%%%%%%%
%
% A query held open as an SWI engine: engine_next pulls one answer per
% call, the goal's join state stays alive inside the engine between
% pulls, and unrelated calls interleave freely, which a raw janus cursor
% forbids (its frames nest LIFO and it dies crossing threads; probed).
% The handle crosses to Python opaquely inside prolog/1, and both
% stepping and destroying work from any thread outside a transaction. A
% cursor opened inside a transaction is evaluated eagerly on its thread by
% metta_host_hold/3; only that thread may step its held rows. Close from another
% thread queues cleanup on the owner. The engine runs
% under the logical update view: a fact added after the first pull is not
% seen by this cursor, the snapshot-like enumeration contract.

%Inf bounds the cursor's WHOLE engine work, cumulatively across pulls, and the
%engine publishes the wrapper because a host cannot place this bound correctly
%from outside: an engine counts its own inferences and this thread cannot see
%them, so a limiter around one pull charges the pull loop rather than the
%engine. This file used to read that measurement the other way round and wrap
%each pull, which left the budget inert; metta_host_inference_budget/3 in
%engine/metta/control.pl carries the numbers and the reasoning.
%
%THE WALL BOUND IS INSIDE NOW TOO, for the same reason and against what this
%comment used to say. "Wall bounds stay outside, per pull, where idle time
%between pulls cannot count" assumed an outside bound ACTS, and it does not: a
%time limit in the caller cannot interrupt a goal running inside an engine at
%all, measured in plain SWI with none of this engine in it
%[measured 2026-09-05: call_with_time_limit(2, engine_next(E, _)) over a
%non-terminating engine goal ran ninety seconds without firing]. So the outside
%guard left the caller's timeout inert exactly as the outside inference limit
%once did. Idle time between pulls DOES count now, because the deadline is
%absolute from the engine's start, which is what a caller passing timeout= to a
%query means by it.
metta_py_cursor_open(Space, PatternsTagged, GuardTagged, VarNames, Limit, Inf,
                     TimeS, prolog(Engine)) :-
    metta_py_cursor_open_controlled(
        Space, PatternsTagged, GuardTagged, VarNames, Limit, Inf, TimeS, none,
        prolog(Engine)).

metta_py_cursor_open_controlled(
        Space, PatternsTagged, GuardTagged, VarNames, Limit, Inf, TimeS, Policy,
        prolog(Engine)) :-
    metta_py_cursor_goal(Space, PatternsTagged, GuardTagged, VarNames, Limit,
                         Row, Goal),
    metta_host_time_budget(Goal, TimeS, Timed),
    metta_host_inference_budget(Timed, Inf, Bounded),
    metta_py_open_controlled_cursor(Policy, Row, Bounded, Engine).

metta_py_cursor_goal(Space, PatternsTagged, GuardTagged, VarNames, Limit,
                     Row, Goal) :-
    (   GuardTagged == [], Limit > 0,
        PatternsTagged = [PatternTagged], seam:foreign_space(Space)
    ->  Goal0 = metta_py_bounded_query(Space, PatternTagged, VarNames,
                                       Limit, Row)
    ;   GuardTagged == []
    ->  Goal0 = metta_py_query(Space, PatternsTagged, VarNames, Row)
    ;   Goal0 = metta_py_query_guarded(Space, PatternsTagged, GuardTagged,
                                       VarNames, Row)
    ),
    ( Limit > 0 -> Goal = limit(Limit, Goal0) ; Goal = Goal0 ).

%The annotation-returning cursor is a separate wire so the ordinary hot path
%keeps its one Row. The override lives INSIDE the held engine goal, because
%engine_create defers execution until the first pull. Ordered carriers collect
%and stably sort in the engine; Answers slicing then reads a genuine best
%prefix rather than sorting a Python materialisation [tested:
%extensions/python/tests/ch06_many_answers/test_under_algebra.py;
%commit=c7468b2789746bcf95c4bacc0e2d517ec4d972fa].
metta_py_cursor_open_under(Space, PatternsTagged, GuardTagged, VarNames,
                           Limit, Inf, Algebra, Direction, TimeS,
                           prolog(Engine)) :-
    metta_py_cursor_open_under_controlled(
        Space, PatternsTagged, GuardTagged, VarNames, Limit, Inf, Algebra,
        Direction, TimeS, none, prolog(Engine)).

metta_py_cursor_open_under_controlled(
        Space, PatternsTagged, GuardTagged, VarNames, Limit, Inf, Algebra,
        Direction, TimeS, Policy, prolog(Engine)) :-
    (   Direction \== none
    ->  (   GuardTagged == [], PatternsTagged = [PatternTagged]
        ->  metta_py_decode(PatternTagged, Pattern),
            metta_ordered_match_limit(
                Space, Pattern, Algebra, Limit, Direction, ProducerLimit)
        ;   ProducerLimit = 0
        ),
        metta_py_cursor_goal(Space, PatternsTagged, GuardTagged, VarNames,
                             ProducerLimit, Row, Producer),
        Core = metta_py_ordered_under_query(
                   Space, Direction, TimeS, Producer, Row, K),
        ( Limit > 0 -> Goal = limit(Limit, Core) ; Goal = Core )
    ;   metta_py_cursor_goal(Space, PatternsTagged, GuardTagged, VarNames,
                             Limit, Row, Producer),
        Goal = metta_py_under_query(Space, Producer, K)
    ),
    Scoped = metta_with_evaluation_context(
                 evaluation_context(Algebra, Limit, Direction), Goal),
    Encoded = ( Scoped, metta_py_encode(K, KWire) ),
    metta_host_time_budget(Encoded, TimeS, Timed),
    metta_host_inference_budget(Timed, Inf, Bounded),
    metta_py_open_controlled_cursor(Policy, [Row, KWire], Bounded, Engine).

metta_py_under_query(Space, Producer, K) :-
    metta_algebra_one(Space, One),
    b_setval('$metta_answer_k', One),
    call(Producer),
    b_getval('$metta_answer_k', K).

metta_py_ordered_under_query(Space, Direction, TimeS, Producer, Row, K) :-
    metta_py_ordered_within_time(
        TimeS, Direction, K0-Row,
        metta_py_under_query(Space, Producer, K0), Ordered),
    member(K-Row, Ordered).

%An ordered cursor cannot yield before its whole input is collected and sorted,
%so the between-answer deadline around its held engine cannot see a producer
%stuck before that first answer. call_with_time_limit/2 is safe on exactly this
%DETERMINISTIC prefix: it is cancelled before member/2 starts yielding, hence no
%alarm remains armed while the engine is suspended. Putting the same guard
%around member/2 is the rejected shape that silently truncated a resumed cursor
%[tested: test_an_ordered_algebra_view_is_bounded_by_its_timeout;
%commit=51e719767e3dd322a9cf88bd096410bbc5647493].
:- meta_predicate metta_py_ordered_within_time(+, +, ?, 0, -).
metta_py_ordered_within_time(TimeS, Direction, Pair, Producer, Ordered) :-
    metta_py_guarded(
        TimeS, -1,
        ( findall(Pair, Producer, Pairs),
          metta_py_ordered_pairs(Direction, Pairs, Ordered) )).

metta_py_ordered_pairs(ascending, Pairs, Ordered) :- !,
    sort(1, @=<, Pairs, Ordered).
metta_py_ordered_pairs(_, Pairs, Ordered) :-
    sort(1, @>=, Pairs, Ordered).

%[] is exhaustion, [Row] one answer, so Python needs no sentinel value.
metta_py_cursor_next(Engine, Answer) :-
    ( metta_host_hold_next(Engine, Row) -> Answer = [Row] ; Answer = [] ).

metta_py_captured_cursor_next(rows(Handle), Answer, Text) :- !,
    (   metta_host_hold_next(Handle, [Answer, Text])
    ->  true
    ;   Answer = [], Text = ""
    ).
metta_py_captured_cursor_next(Engine, Answer, Text) :-
    setup_call_cleanup(
        new_memory_file(Memory),
        ( setup_call_cleanup(
              open_memory_file(
                  Memory, write, Stream,
                  [free_on_close(false), encoding(utf8)]),
              ( ( metta_host_hold_post(Engine, Stream, Row)
                -> Answer = [Row]
                ;  Answer = [] ),
                flush_output(Stream) ),
              close(Stream)),
          memory_file_to_string(Memory, Text) ),
        free_memory_file(Memory)).

%The controlled variants normalize both handle kinds to [payload, text]. A
%retained-count replay cursor has no captured engine because its target output
%was already collected during the retaining call; it therefore contributes an
%empty text chunk here.
metta_py_cursor_next_controlled(
        metta_py_captured_cursor(Engine), [Answer, Text]) :- !,
    metta_py_captured_cursor_next(Engine, Answer, Text).
metta_py_cursor_next_controlled(Engine, [Answer, ""]) :-
    metta_py_cursor_next(Engine, Answer).

%Up to Count answers in ONE crossing, which is the whole of the optimisation:
%a pull costs 2.55us of janus crossing against 2.55us of engine work, so a
%cursor that crosses per answer spends half its time in the boundary
%[measured 2026-08-31, extensions/python/tests/ch18_performance/test_cursor_chunking.py].
%A SHORT list is the whole of the exhaustion signal, the same reading the
%remote seat's _pull/2 takes, so nothing here looks ahead: the answer after
%the last one asked for is never computed. Count is what Python asked for and
%Python is what decides it may ask for more than one; see _Chunk in
%_space_objects.py for when that is sound.
binding_forward(metta_py_cursor_chunk/3).

metta_py_captured_cursor_chunk(_, Count, [], []) :-
    Count =< 0, !.
metta_py_captured_cursor_chunk(Engine, Count, Answers, Texts) :-
    metta_py_captured_cursor_next(Engine, Answer, Text),
    (   Answer = [Row]
    ->  Answers = [Row|Rest],
        Texts = [Text|MoreText],
        Left is Count - 1,
        metta_py_captured_cursor_chunk(Engine, Left, Rest, MoreText)
    ;   Answers = [],
        Texts = [Text]
    ).

metta_py_cursor_chunk_controlled(
        metta_py_captured_cursor(Engine), Count, [Answers, Text]) :- !,
    metta_py_captured_cursor_chunk(Engine, Count, Answers, Texts),
    atomics_to_string(Texts, "", Text).
metta_py_cursor_chunk_controlled(Engine, Count, [Answers, ""]) :-
    metta_py_cursor_chunk(Engine, Count, Answers).

%Idempotent close: a second destroy finds no engine and is at peace.
metta_py_cursor_close(metta_py_captured_cursor(Engine)) :- !,
    metta_py_cursor_close(Engine).
metta_py_cursor_close(rows(Handle)) :- !,
    metta_host_hold_close(Handle).
binding_forward(metta_py_cursor_close/1).
