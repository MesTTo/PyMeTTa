% Purpose: bound and capture execution and account for interrupt polling.
% Assumes: loaded through _binding/shim.pl in its host module.
% Guarantees: native algebra operations compose with the same bounds as
%   carrier checks [tested: test_visibility_operations_share_the_native_carrier;
%   commit=90ba93eb8f6e98ebfefc55416859bf13de6a8427].
% Owns resources: held-engine output redirection; cleanup restores current_output
% [source: extensions/python/metta/_binding/control.pl:416; commit=cd62330ceacc8f1254eed9791c3f6203b48a1c9e].

%%%%%%%%%% Guarded and captured calls %%%%%%%%%%
%
% Two meta entry points wrap the run, query and eval entry points without
% changing them. metta_py_limited applies the engine's own per-call guards,
% call_with_time_limit (seconds) and call_with_inference_limit (steps);
% metta_py_captured collects everything the wrapped goal prints to the
% current output. Both name their target as data, a listed entry point plus
% its input list and one output, so they compose by listing
% metta_py_captured as itself wrappable: limited over captured is a capture
% inside a limit. Exceeding a guard throws the reserved exception envelope;
% the Python side classifies its exact shape, never its rendered text.
% A guard that stops a goal stops it mid-way, so writes it already made
% stand, the honest semantics of every timeout.

metta_py_wrappable(metta_py_run).
metta_py_wrappable(metta_py_run_using).
metta_py_wrappable(metta_py_query_all).
metta_py_wrappable(metta_py_query_guarded_all).
metta_py_wrappable(metta_py_query_limit_all).
metta_py_wrappable(metta_py_query_count).
metta_py_wrappable(metta_py_query_count_if_repeatable).
metta_py_wrappable(metta_py_eval_all).
metta_py_wrappable(metta_py_eval_accounted).
metta_py_wrappable(metta_py_check_algebra_values_accounted).
metta_py_wrappable(metta_py_algebra_operation_accounted).
metta_py_wrappable(metta_py_tagged_sources).
metta_py_wrappable(metta_py_eval_using_all).
metta_py_wrappable(metta_py_eval_many_all).
metta_py_wrappable(metta_py_eval_many_using_all).
metta_py_wrappable(metta_py_eval_status_all).
metta_py_wrappable(metta_py_reducible).
metta_py_wrappable(metta_py_eval_status_using_all).
metta_py_wrappable(metta_py_run_status).
metta_py_wrappable(metta_py_captured).
metta_py_wrappable(metta_py_in_evaluation_context).
metta_py_wrappable(metta_py_atomic).
metta_py_wrappable(metta_py_speculative).
metta_py_wrappable(metta_py_profiled).
%The trace door stays wrappable for the execution POLICY wrappers, which is
%what this list is for; its RUN bounds ride inside it as an argument instead,
%so metta_py_limited never charges a caller's budget for encoding the trace.
metta_py_wrappable(metta_py_trace).
%Opening a debug session creates the engine that will run the program, and
%the scope's policy goes INSIDE that engine's goal, the way a lazy cursor's
%does: a transaction wrapped around the host's later steps could not roll
%back what the engine did between them.
metta_py_wrappable(metta_py_debug_open_controlled).
metta_py_wrappable(metta_py_function_shape).
metta_py_wrappable(metta_py_cursor_next).
metta_py_wrappable(metta_py_cursor_chunk).
metta_py_wrappable(metta_py_cursor_next_controlled).
metta_py_wrappable(metta_py_cursor_chunk_controlled).
metta_py_wrappable(metta_py_cursor_open_controlled).
metta_py_wrappable(metta_py_cursor_open_under_controlled).
metta_py_wrappable(metta_py_eval_cursor_open_controlled).
metta_py_wrappable(metta_py_eval_cursor_open_under_controlled).
metta_py_wrappable(metta_py_eval_count).
metta_py_wrappable(metta_py_eval_count_under).
metta_py_wrappable(metta_py_eval_count_if_repeatable).
metta_py_wrappable(metta_py_eval_count_under_if_repeatable).
metta_py_wrappable(metta_py_eval_count_retaining).
metta_py_wrappable(metta_py_tagged_count).
metta_py_wrappable(metta_py_derivation).
metta_py_wrappable(metta_py_derivations).
metta_py_wrappable(metta_py_load).
metta_py_wrappable(metta_py_fast_load_unit).
%A save is linear in the space in all three of its parts, so all three are
%bounded: the enumeration, the unwritable-atom scan the validator runs, and
%the fast writer. Loading was already bounded and saving was not, which left
%the one door on this surface that does unbounded engine work with no guard.
metta_py_wrappable(metta_py_atoms).
metta_py_wrappable(metta_py_infer_types).
metta_py_wrappable(metta_py_fast_save).
metta_py_wrappable(metta_py_world_eval).
%The WRITE doors. A scope is a per-CALL policy, and a write door is a call
%like any other: inside `with m.speculative():` the write runs against the
%frozen view and goes with it, exactly as `m.run("!(add-atom &self ...)")` in
%the same block already did, and inside `with m.atomic():` it is its own
%committing transaction, exactly as a whole run is. They crossed outside every
%wrapper before this and simply persisted, which made the scopes cover the
%source doors and silently miss the Python ones
%[tested: test_every_public_write_door_honours_the_execution_scopes].
metta_py_wrappable(metta_py_add).
metta_py_wrappable(metta_py_add_many).
metta_py_wrappable(metta_py_clear).
metta_py_wrappable(metta_py_remove).
metta_py_wrappable(metta_py_remove_many).
metta_py_wrappable(metta_py_remove_everything).
metta_py_wrappable(metta_py_drain).
metta_py_wrappable(metta_py_transfer).

metta_py_fast_load_unit(File, Space, []) :-
    metta_py_fast_load(File, Space).

metta_py_wrapped_goal(Pred0, Ins, Out, Goal) :-
    ( atom(Pred0) -> Pred = Pred0 ; atom_string(Pred, Pred0) ),
    ( metta_py_wrappable(Pred) -> true
    ; throw(error(domain_error(metta_py_wrappable, Pred), none)) ),
    append(Ins, [Out], Args),
    Goal =.. [Pred | Args].

%TimeS and Inf use -1 for "no bound"; both bounds may apply at once, the
%inference wrapper outermost so a time signal thrown inside it passes out.
metta_py_limited(TimeS, Inf, Pred, Ins, Out) :-
    metta_py_wrapped_goal(Pred, Ins, Out, Goal),
    metta_py_guarded(TimeS, Inf, Goal).

%The six-argument seam extends rather than changes metta_py_limited/5. A
%negative StackBytes is the same no-bound sentinel the older limits use.
metta_py_limited(TimeS, Inf, StackBytes, Pred, Ins, Out) :-
    metta_py_wrapped_goal(Pred, Ins, Out, Goal),
    metta_py_guarded(TimeS, Inf, StackBytes, Goal).

metta_py_guarded(TimeS, Inf, StackBytes, Goal) :-
    (   StackBytes < 0
    ->  metta_py_guarded(TimeS, Inf, Goal)
    ;   metta_host_with_stack_limit(
            StackBytes, metta_py_guarded(TimeS, Inf, Goal))
    ).

%The caller's own two bounds, and each of them REFUSES when it is exceeded
%rather than answering. The signal is the early stop and the counter read is
%the verdict, because a signal that never reaches this frame lets a goal
%finish and hands its caller an answer for work that ran past the bound: a
%0.3-second load answered after 66.170 seconds at loadavg 90 to 100.
%
%A wall bound loses that way when its alarm arrives late. An INFERENCE bound
%loses it a second way, and this door had it: SWI raises the bare atom
%`inference_limit_exceeded` inside the goal and disarms the limit before
%raising it, so ANY catch inside the goal whose recovery does not re-throw
%eats both the ball and the bound, and call_with_inference_limit/3 then
%reports `!` for a goal that never stopped
%[source: docs/journal/2026-09-04-bounded-trace-keeps-its-events.md, which
%measured 200,000 further inferences running after such a catch]
%[tested: inference_budget:a_swallowed_ball_defeats_the_limiter_alone, the
%control case, and
%inference_budget:a_swallowed_ball_still_refuses_at_the_python_door].
%
%So both halves are built the way the lazy cursors' are, by the engine's own
%two budget builders: the signal stops the work early and the cumulative
%read decides, and a bound whose ball was swallowed still refuses at the
%answer.
%[tested: test_a_wall_clock_bound_that_is_exceeded_refuses,
%time_budget:the_language_timeout_form_refuses_a_bound_it_exceeded,
%inference_budget:a_swallowed_ball_still_refuses_at_the_python_door].
metta_py_guarded(TimeS, Inf, Goal) :-
    ( TimeS < 0 -> Timed = Goal
    ; metta_host_time_budget(Goal, TimeS, Deadlined),
      Timed = catch(call_with_time_limit(TimeS, Deadlined),
                    time_limit_exceeded,
                    metta_py_raise(time_limit, TimeS)) ),
    ( Inf < 0 -> call(Timed)
    ; metta_host_inference_budget(Timed, Inf, Counted),
      call(Counted) ).

%Internal execution carries the same context as an annotated cursor while
%retaining the operation's plain answer wire.
metta_py_in_evaluation_context([Algebra, Limit, Direction], Pred, Ins, Out) :-
    metta_py_wrapped_goal(Pred, Ins, Out, Goal),
    metta_with_evaluation_context(
        evaluation_context(Algebra, Limit, Direction), Goal).

metta_py_captured(Pred, Ins, [Out, Text]) :-
    metta_py_wrapped_goal(Pred, Ins, Out, Goal),
    with_output_to(string(Text), call(Goal)).

%%%%%%%%%% The interrupt poll, and keeping it out of the counters %%%%%%%%%%
%
%SWI calls prolog:heartbeat/0 every `heartbeat` inferences of the running
%thread. That hook is why a Ctrl-C reaches a program while the engine spins:
%only CPython runs CPython's signal handlers, and nothing enters CPython while
%Prolog is running, so the hook crosses into Python and CPython takes its
%queued signals there. janus arms it with a clause of its own,
%`prolog:heartbeat :- py_call(janus_swi:heartbeat_tick())`, whose Python side
%has an empty body: the CROSSING is the whole mechanism
%[source: janus_swi 1.5.3, janus.py, heartbeat/1].
%
%The hook is COUNTED WORK, and that is the defect this seat had. Its call port
%and its body's are ordinary inferences in whatever thread the VM interrupted,
%so they landed in whichever measurement was open and a stats() block that
%happened to contain a tick read higher than the identical block beside it: at
%the shipped 100,000-inference interval, 51 of 4,000 measurements of one
%659-inference evaluation read 667, and 2,568 of 4,000 did at an interval of
%1,000 [measured 2026-09-08; command=python extensions/python/benchmarks/
%probes/interrupt_poll_accounting.py --raw; fixture=three edges in a scratch
%space, the poll at 0, 100,000 and 1,000 in one process; commit=5f92ecfb105f7a11d8f3b1a4c0a7e3b6d4b656a6]. Two
%measurements of the SAME work therefore differed, in either direction
%depending on which window the tick fell in, which is what
%test_analyze_numbers_equal_the_stats_of_the_same_query read as an intermittent
%on two batteries.
%
%So the seat arms its OWN hook, which does the same crossing and records what
%it spent, and the seat takes that out of the counters it reports. Turning the
%poll off around a measurement was rejected instead: it would make Ctrl-C wait
%for the block it is trying to interrupt, and writing the flag disturbs the
%countdown, which measured half the ticks over a loop that rewrote it.
%
%The record is per THREAD, because an exited thread's inferences are added to
%the thread that JOINS it while a running thread's are its own: a worker's
%ticks must not be subtracted from the measurement its parent is taking.
%nb_current/2 rather than a bare read, so a thread that reached the hook
%without this file's thread_initialization/1 counts from zero instead of
%raising inside the VM's hook.
%
%WHAT IT SPENT TRAVELS WITH THE COUNTER READING IT SPENT IT AT, in one term,
%and that is how the correction stays exact. The seat has two numbers to read,
%the engine's counter and this record, and no goal reads two things at one
%instant, so a tick landing between the two reads would put its cost on one
%side and its tally on the other: the same error the subtraction exists to
%remove. A seqlock's answer is to detect the overlap and retry [source: Linux
%kernel seqlock, read_seqbegin/read_seqretry], but a retry's own goals land
%inside the measurement, which measured one reading in four thousand nine
%inferences high. So the hook records WHERE it fired and what the ticks before
%it had spent, and the seat leaves out a tick whose recorded reading is past
%its own. One read, one comparison, no retry, and no window in which the pair
%can disagree
%[tested: heartbeat_accounting:a_tick_records_what_it_spent_and_where_it_happened,
%test_a_reading_leaves_out_a_tick_that_fired_after_it].
:- thread_initialization(
       nb_setval('$metta_heartbeat_ticks', ticks(0, 0, 0, 0))).

prolog:heartbeat :-
    py_call(metta_ops:heartbeat_tick()),
    metta_py_heartbeat_tick.

%One term per thread: how many ticks, what they have spent, the counter
%reading the LAST one happened at, and what the ticks before it had spent.
%The last pair is what lets the door leave out a tick that fired after its own
%reading without a second read to ask about it.
metta_py_heartbeat_tick :-
    statistics(inferences, At),
    metta_py_heartbeat_charge(Charge),
    (   nb_current('$metta_heartbeat_ticks', ticks(Count, Before, _, _))
    ->  true
    ;   Count = 0, Before = 0
    ),
    Next is Count + 1,
    Total is Before + Charge,
    nb_setval('$metta_heartbeat_ticks', ticks(Next, Total, At, Before)).

%What one tick costs the counter, MEASURED THE WAY THE VM SPENDS IT rather
%than written down: a constant here would be wrong the first time the hook's
%body changes, and the body changes whenever the crossing does. The poll is
%armed densely, one fixed loop is spent with it off and with it on, and the
%difference is divided by the ticks it took, which is how a benchmark harness
%prices its own overhead rather than assuming it [source: OpenJDK JMH,
%org.openjdk.jmh.infra.Blackhole, calibrated per run].
%
%A calibration that priced ONE tick would price the wrong one: the first call
%of a predicate in a process costs an inference more than the calls after it,
%so a charge taken from it subtracts more than a tick spends and every window
%that absorbs a tick then reads one LOW. The hook is therefore called once
%before the measurement and the measurement needs two ticks; once warm, a
%direct call and a tick the VM raises cost the same
%[measured 2026-09-08: both 8 inferences; command=python extensions/python/
%benchmarks/probes/interrupt_poll_accounting.py; commit=5f92ecfb105f7a11d8f3b1a4c0a7e3b6d4b656a6].
:- dynamic metta_py_heartbeat_charge/1.
metta_py_heartbeat_charge(0).

%Arm the poll: calibrate first, then set the flag. Interval is the caller's
%config.heartbeat_interval; 0 disarms, and the charge then measures nothing
%because no tick can advance the record.
%
%The calibration spends about 3,400 inferences of the seat's boot, which the
%engine's own boot benchmark does not see because it boots without this seat,
%and buys counters that report the caller's work rather than the seat's
%polling.
metta_py_heartbeat_arm(Interval) :-
    must_be(nonneg, Interval),
    set_prolog_flag(heartbeat, 0),
    retractall(metta_py_heartbeat_charge(_)),
    assertz(metta_py_heartbeat_charge(0)),
    prolog:heartbeat,
    metta_py_heartbeat_calibrate(800, 4, Charge),
    retractall(metta_py_heartbeat_charge(_)),
    assertz(metta_py_heartbeat_charge(Charge)),
    set_prolog_flag(heartbeat, Interval).

%The same loop twice, and the difference divided by the ticks. Fewer than two
%ticks is not a measurement and a difference that does not divide exactly did
%not measure one uniform cost, so both grow the loop and try again; a
%calibration that cannot be made cannot be guessed, and the seat says so
%rather than reporting counters it cannot account for.
%
%The warm-up and the two-tick floor are the arming door's, above, and the
%reason is there with them: a charge taken from a cold first call is one
%inference too high.
metta_py_heartbeat_calibrate(Iterations, Attempts, Charge) :-
    set_prolog_flag(heartbeat, 0),
    metta_py_heartbeat_bracket(Iterations, Bare, _),
    set_prolog_flag(heartbeat, 1000),
    metta_py_heartbeat_bracket(Iterations, Armed, Ticks),
    set_prolog_flag(heartbeat, 0),
    Spent is Armed - Bare,
    (   Ticks > 1,
        0 =:= Spent mod Ticks
    ->  Charge is Spent // Ticks
    ;   Attempts > 1
    ->  Left is Attempts - 1,
        Longer is Iterations * 2,
        metta_py_heartbeat_calibrate(Longer, Left, Charge)
    ;   throw(error(metta_py_heartbeat_uncalibrated(Spent, Ticks),
                    context(metta_py_heartbeat_arm/1,
                            'the interrupt poll spent no uniform cost over a \c
                             loop of known size, so its charge cannot be \c
                             taken out of the counters')))
    ).

%The rendering, so a boot that cannot price the poll says what happened
%rather than printing `Unknown error term:`.
:- multifile prolog:error_message//1.
prolog:error_message(metta_py_heartbeat_uncalibrated(Spent, Ticks)) -->
    [ 'the engine\'s interrupt poll spent ~w inferences over ~w ticks of a \c
       loop of known size, which is not one uniform cost a measurement can \c
       be corrected by. The counters would report the seat\'s own polling as \c
       the caller\'s work, so the engine refuses to arm it'-[Spent, Ticks] ].

metta_py_heartbeat_bracket(Iterations, Spent, Ticks) :-
    statistics(inferences, Raw0),
    metta_py_heartbeat_term(Before, _, _, _),
    forall(between(1, Iterations, _), true),
    statistics(inferences, Raw1),
    metta_py_heartbeat_term(After, _, _, _),
    Spent is Raw1 - Raw0,
    Ticks is After - Before.

%The counter with the interrupt poll's own spending already out of it, for the
%doors that report a measurement FROM here rather than handing the pieces
%across the way metta_py_stats/1 does. Same rule, same arithmetic: a tick
%whose recorded reading is past this one spent its inferences after it, so
%what the ticks BEFORE it had spent comes out instead. Without it a door that
%reports `Used` charges its caller for the seat's Ctrl-C polling, which is one
%tick's charge in about every fifty thousand inferences it measures
%[tested: test_nominal_subtyping_does_not_scan_unrelated_declarations, which
%compares two hundred-evaluation measurements of the same work and allows
%four].
metta_py_work(Work) :-
    statistics(inferences, Raw),
    metta_py_heartbeat_term(_, Spent, At, Before),
    Late is max(0, sign(At - Raw)),
    Work is Raw - Spent + Late * (Spent - Before).

%One crossing for the engine's own counters: statistics/2 inferences and
%cputime, the garbage_collection triple (collections, bytes freed,
%milliseconds spent), the thread's answer-table bytes, which the tabling
%review found reachable only through the lower-level runtime, and the
%interrupt poll's four-field term. The Python side reads deltas around a
%with-block and takes the poll's charge out there.
%
%The DECISION is Python's and the reading is this door's, because this door
%is INSIDE every measurement it takes: what it spends between the two
%readings is added to the work the caller measures, so a subtraction spelled
%here would cost the caller inferences to be told what it cost him. The term
%crosses whole, one read, and arithmetic on the other side is free
%[measured 2026-09-08: an empty stats() block reads 6 inferences with the
%term crossing and 10 with the subtraction spelled here, against 5 before the
%poll was accounted at all; command=python extensions/python/benchmarks/
%probes/interrupt_poll_accounting.py; commit=5f92ecfb105f7a11d8f3b1a4c0a7e3b6d4b656a6].
metta_py_stats([Inferences, CpuTime, GcCount, GcFreed, GcTimeMs, TableBytes,
                Ticks, Spent, At, Before]) :-
    statistics(inferences, Inferences),
    metta_py_heartbeat_term(Ticks, Spent, At, Before),
    statistics(cputime, CpuTime),
    statistics(garbage_collection, [GcCount, GcFreed, GcTimeMs|_]),
    statistics(table_space_used, TableBytes).

%The poll's own term, and zeros for a thread that reached this door without
%this file's thread_initialization/1 rather than an exception from a counter
%read.
metta_py_heartbeat_term(Ticks, Spent, At, Before) :-
    (   nb_current('$metta_heartbeat_ticks', ticks(Ticks0, Spent0, At0, Before0))
    ->  Ticks = Ticks0, Spent = Spent0, At = At0, Before = Before0
    ;   Ticks = 0, Spent = 0, At = 0, Before = 0
    ).

%Run the wrapped call through the engine's user-transaction coordinator:
%dynamic state and enlisted providers finish first, then the buffered atom
%event segment is published. A failure or throw discards that segment with
%the rolled-back writes.
metta_py_atomic(Pred, Ins, Out) :-
    metta_py_wrapped_goal(Pred, Ins, Out, Goal),
    metta_py_execution_policy_goal(atomic, Goal, Scoped),
    call(Scoped).

%Run against a frozen view and discard every change: snapshot/1, the
%what-if reading. The answers return; the space stays as it was. Atom events
%and process-shared State writes are effects a snapshot cannot roll back, so
%the former stay in a discarded observation frame and the latter refuse.
metta_py_speculative(Pred, Ins, Out) :-
    metta_py_wrapped_goal(Pred, Ins, Out, Goal),
    metta_py_execution_policy_goal(speculative, Goal, Scoped),
    call(Scoped).

%The policy constructor is also used by held engines. Wrapping engine_next/2
%on the caller cannot roll back work performed by the engine it resumes; the
%transaction must be part of the engine's suspended Goal so it spans every
%pull and closes with that one execution.
metta_py_execution_policy_goal(none, Goal, Goal) :- !.
metta_py_execution_policy_goal(atomic, Goal, metta_transaction(Goal)) :- !.
metta_py_execution_policy_goal(
    speculative,
    Goal,
    metta_speculate(metta_with_state_write_fence(Goal))) :- !.
metta_py_execution_policy_goal(Mode, _, _) :-
    throw(error(domain_error(metta_py_execution_policy, Mode), none)).

%A held engine has its own current_output, so redirecting engine_next/2 in the
%caller cannot capture it. The captured engine asks for a fresh memory stream
%before each resume, yields one answer, and asks again before backtracking.
%The caller can then close and read an unbounded memory file without a pipe's
%finite-buffer deadlock.
metta_py_captured_engine(Template, Goal) :-
    setup_call_cleanup(
        current_output(Old),
        ( engine_fetch(Stream0),
          set_output(Stream0),
          call(Goal),
          flush_output,
          engine_yield(Template),
          engine_fetch(Stream),
          set_output(Stream),
          fail ),
        set_output(Old)).

%A held evaluation is nondeterministic, and so is every policy here: the
%speculative one used to need its own findall-then-member because
%metta_speculate/1 ran its goal as once/1, and it answers every answer itself
%now, so a cursor takes the same construction the eager doors take.
metta_py_open_controlled_cursor(none, Template, Goal, Handle) :- !,
    metta_host_hold(Template, Goal, Handle).
metta_py_open_controlled_cursor([Mode, Capture], Template, Goal, Handle) :-
    metta_py_execution_policy_goal(Mode, Goal, Controlled),
    (   Capture == @(true), current_transaction(_)
    ->  metta_host_hold(
            Packet, metta_py_hold_captured(Template, Controlled, Packet), Held),
        Handle = metta_py_captured_cursor(rows(Held))
    ;   Capture == @(true)
    ->  metta_host_hold(_, metta_py_captured_engine(Template, Controlled), Engine),
        Handle = metta_py_captured_cursor(Engine)
    ;   metta_host_hold(Template, Controlled, Handle)
    ).

% The service owns holding; this predicate selects the capture transport for
% an enumeration that cannot suspend. An empty enumeration still has output.
metta_py_hold_captured(Template, Goal, Packet) :-
    with_output_to(string(Text), findall(Template, Goal, Rows)),
    (   Rows = [First|Rest]
    ->  ( Packet = [[First], Text]
        ; member(Row, Rest), Packet = [[Row], ""] )
    ;   Packet = [[], Text]
    ).
