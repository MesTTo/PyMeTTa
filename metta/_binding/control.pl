% Purpose: bound and capture execution and account for interrupt polling.
% Assumes: loaded through _binding/shim.pl in its host module.
% Guarantees: native algebra operations compose with the same bounds as
%   carrier checks [tested: test_visibility_operations_share_the_native_carrier;
%   commit=90ba93eb8f6e98ebfefc55416859bf13de6a8427].
% Guarantees: declared _controlled entries expose prolog/1 opener handles or
% [payload,text] resume packets to the binding generator
% [tested: test_binding_controlled_signature_mutations_refuse; commit=8358dfc233bf299bb23eceddd94593a62372fe4b].
% Guarantees: an interrupt-poll tick leaves backtracking all it reclaims, since
% the tick record is updated in place rather than copied to the global stack
% [tested 2026-09-27T03:11:33+10:00:
% heartbeat_accounting:a_tick_leaves_backtracking_what_it_reclaims].
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

metta_py_wrappable(metta_py_evaluate).
metta_py_wrappable(metta_py_run).
metta_py_wrappable(metta_py_run_using).
metta_py_wrappable(metta_py_query_all).
metta_py_wrappable(metta_py_query_guarded_all).
metta_py_wrappable(metta_py_query_limit_all).
metta_py_wrappable(metta_py_query_count).
metta_py_wrappable(metta_py_query_count_if_repeatable).
metta_py_wrappable(metta_py_check_algebra_values_accounted).
metta_py_wrappable(metta_py_algebra_operation_accounted).
metta_py_wrappable(metta_py_algebra_fixpoint_accounted).
metta_py_wrappable(metta_py_algebra_model_count_accounted).
metta_py_wrappable(metta_py_tagged_sources).
metta_py_wrappable(metta_py_reducible).
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
metta_py_wrappable(metta_py_source_atoms).
metta_py_wrappable(metta_py_program_source).
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
metta_py_wrappable(metta_py_copy_rows).
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
%thread or engine, at the first clause entry or foreign redo the count reaches.
%That hook is why a Ctrl-C reaches a program while the engine spins: only
%CPython runs CPython's signal handlers, and nothing enters CPython while
%Prolog is running, so the hook crosses into Python and CPython takes its
%queued signals there. janus arms it with a clause of its own,
%`prolog:heartbeat :- py_call(janus_swi:heartbeat_tick())`, whose Python side
%has an empty body: the CROSSING is the whole mechanism
%[source: janus_swi 1.5.3, janus.py, heartbeat/1].
%SWI as released called the hook only where a fact or a foreign predicate
%exited, which a last-call loop never does, so a Ctrl-C waited for such a loop
%to end. The host this engine boots on carries the repair, and
%engine/host_check.pl refuses a host that does not
%[source 2026-09-26T22:48:21+10:00:
%tests/checks/host_workarounds/swi-heartbeat-fires-only-at-exits.patch].
%
%THE POLL CROSSES ONLY ON THE THREAD THAT ARMED IT. CPython runs a signal
%handler only on its main thread
%[source 2026-09-26T22:48:21+10:00:
%https://docs.python.org/3/library/signal.html#signals-and-threads],
%and the seat arms the poll on the thread that starts the runtime, the main one
%when a program builds MeTTa() at its top level. A crossing from any other
%thread delivers nothing and costs a GIL round trip, a wait whenever a Python
%thread holds the GIL. A new thread or engine copies the heartbeat with the
%other Prolog flags, so two rules keep the poll where it works. A thread or
%engine that STARTS on another operating-system thread is disarmed by its
%thread_initialization/1 goal before it runs anything, which also keeps a
%worker's ticks away from the thread that joins it: SWI adds a joined thread's
%inferences to its joiner's, where no correction sees them
%[measured 2026-09-26T20:31:17+10:00: before this rule, a stats() block joining
%one thread that ran forall(between(1,200000,_),true) read 400,025 inferences
%with the poll off and 403,652 at an interval of 1,000]. And an engine, which
%runs on whichever thread steps it, crosses only while it runs on the arming
%one, so a cursor opened and stepped there is interrupted as its caller is,
%while a scheduler task stepped on a carrier thread only pays the check.
%Limitation: an engine started on another thread stays disarmed when the
%arming thread steps it later, and the check a tick pays off that thread is
%taken out of no reading.
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
%The record is per THREAD and per ENGINE, since each counts its own
%inferences: an engine's ticks come out of the readings taken inside it and
%never out of its caller's, whose counter does not hold them. nb_current/2
%rather than a bare read, so a thread that reached the hook without this
%file's thread_initialization/1 counts from zero instead of raising inside the
%VM's hook.
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

%The arming thread's operating-system id, written by metta_py_heartbeat_arm/1.
%Absent until the seat arms, so a thread started during the boot keeps the
%flag it inherited.
:- dynamic metta_py_heartbeat_home/1.

%A new thread or engine starts its tick record from zero, and with the poll
%off when it starts on another thread. One that starts on the arming thread
%keeps the interval it inherited, so a block that changed the flag there, as
%the seat's own tests do, changes it for the engines the block opens too.
metta_py_heartbeat_thread_start :-
    nb_setval('$metta_heartbeat_ticks', ticks(0, 0, 0, 0)),
    (   metta_py_heartbeat_home(Home),
        \+ current_prolog_flag(system_thread_id, Home)
    ->  set_prolog_flag(heartbeat, 0)
    ;   true
    ).

:- thread_initialization(metta_py_heartbeat_thread_start).

%A tick crosses on the arming thread and only checks anywhere else, and each
%path records itself with its own charge, so an engine stepped on another
%thread is corrected as exactly as one stepped on this.
%
%A signal handler that raises runs at the crossing, so its exception leaves
%py_call/2 as a python_error ball, which the seat read as a Python
%operation's failure and raised as an EngineError, and which a MeTTa catch
%could take. It is the run being stopped from outside, so it goes on as that
%signal carrying the handler's exception, and the seat raises that exception
%as itself, as CPython raises a handler's exception in whatever its main
%thread was running
%[tested 2026-09-26T22:47:05+10:00: test_a_signal_stops_every_workload].
%KeyboardInterrupt and SystemExit never reach the catch, since janus raises
%them as unwind(keyboard_interrupt) and unwind(halt(Code)). The tick is
%recorded before the signal goes on, so a reading the caller takes around the
%stopped run is still corrected for it.
prolog:heartbeat :-
    current_prolog_flag(system_thread_id, Thread),
    (   metta_py_heartbeat_home(Thread)
    ->  catch(py_call(metta_ops:heartbeat_tick()),
              error(python_error(_, Raised), _),
              true),
        metta_py_heartbeat_tick(crossed),
        (   var(Raised)
        ->  true
        ;   throw(error(metta_control_signal(interrupted, [python, Raised]),
                        context(metta, interrupted)))
        )
    ;   metta_py_heartbeat_tick(checked)
    ).

%One term per thread: how many ticks, what they have spent, the counter
%reading the LAST one happened at, and what the ticks before it had spent.
%The last pair is what lets the door leave out a tick that fired after its own
%reading without a second read to ask about it.
%
%The term is UPDATED IN PLACE. nb_setval/2 of a compound copies it to the
%global stack and freezes the stack at its top, and backtracking never lowers
%the top below that bar [source 2026-09-27T03:04:42+10:00: SWI-Prolog
%V10.1.14, src/pl-gvar.c setval() and freezeGlobal()]. A tick lands in the
%middle of whatever the program is building, so a record replaced that way
%kept what a failure-driven loop had built so far until the next collection.
%Over sort-atom's instructions benchmark, whose 14 ticks the host's heartbeat
%repair puts inside its sort, that was one collection and one global stack
%shift more than with the poll off, 4,535,902,528 instructions where the
%record updated in place reads 4,072,336,892 [measured
%2026-09-27T03:11:33+10:00: benchmarks.check_instructions sort-atom, min of
%three, on swipl-patched.7, against the lane's 2026-09-27T02:54:16+10:00
%reading before the change]. nb_setarg/3 of a small integer writes the
%argument cell and neither copies nor freezes [source
%2026-09-27T03:05:27+10:00: SWI-Prolog V10.1.14, src/pl-prims.c setarg()], and
%every field is a count far below the tagged integer limit, so a tick
%allocates nothing. The record stays one term, so a reader's single
%unification still takes the four fields of one tick.
metta_py_heartbeat_tick(Path) :-
    statistics(inferences, At),
    metta_py_heartbeat_charge(Path, Charge),
    (   nb_current('$metta_heartbeat_ticks', Record)
    ->  true
    ;   nb_setval('$metta_heartbeat_ticks', ticks(0, 0, 0, 0)),
        nb_getval('$metta_heartbeat_ticks', Record)
    ),
    arg(1, Record, Count),
    arg(2, Record, Before),
    Next is Count + 1,
    Total is Before + Charge,
    nb_setarg(1, Record, Next),
    nb_setarg(2, Record, Total),
    nb_setarg(3, Record, At),
    nb_setarg(4, Record, Before).

%What one tick costs the counter, MEASURED THE WAY THE VM SPENDS IT rather
%than written down: a constant here would be wrong the first time the hook's
%body changes, and the body changes whenever the crossing does. The poll is
%armed densely, one fixed loop is spent with it off and with it on, and the
%difference is divided by the ticks it took, which is how a benchmark harness
%prices its own overhead rather than assuming it [source: OpenJDK JMH,
%org.openjdk.jmh.infra.Blackhole, calibrated per run].
%Each path of the hook, crossing and checking, is priced so.
%
%A calibration that priced ONE tick would price the wrong one: the first call
%of a predicate in a process costs an inference more than the calls after it,
%so a charge taken from it subtracts more than a tick spends and every window
%that absorbs a tick then reads one LOW. The hook is therefore called once
%before the measurement and the measurement needs two ticks. A tick the VM
%raises costs one inference more than a direct call, the call of
%'$heartbeat'/0 that runs the hook, which is why the charge is measured on
%ticks and never on a call
%[measured 2026-09-26T21:39:02+10:00: 12 inferences a crossing tick and 11 a
%direct call; python extensions/python/benchmarks/probes/interrupt_poll_accounting.py].
:- dynamic metta_py_heartbeat_charge/2.
metta_py_heartbeat_charge(crossed, 0).
metta_py_heartbeat_charge(checked, 0).

%Arm the poll: record this thread as the one it crosses on, which the hook
%checks and so must precede the calibration, price both paths, then set the
%flag. The checking path is priced with the record naming no thread, -1 being
%no thread's id. Interval is the caller's config.heartbeat_interval; 0
%disarms, and the charges then measure nothing because no tick can advance
%the record.
%
%The calibration spends about 7,000 inferences of the seat's boot, which the
%engine's own boot benchmark does not see because it boots without this seat,
%and buys counters that report the caller's work rather than the seat's
%polling.
metta_py_heartbeat_arm(Interval) :-
    must_be(nonneg, Interval),
    set_prolog_flag(heartbeat, 0),
    current_prolog_flag(system_thread_id, Home),
    metta_py_heartbeat_price(crossed, Home),
    metta_py_heartbeat_price(checked, -1),
    retractall(metta_py_heartbeat_home(_)),
    assertz(metta_py_heartbeat_home(Home)),
    set_prolog_flag(heartbeat, Interval).

metta_py_heartbeat_price(Path, Home) :-
    retractall(metta_py_heartbeat_home(_)),
    assertz(metta_py_heartbeat_home(Home)),
    retractall(metta_py_heartbeat_charge(Path, _)),
    assertz(metta_py_heartbeat_charge(Path, 0)),
    prolog:heartbeat,
    metta_py_heartbeat_calibrate(800, 4, Charge),
    retractall(metta_py_heartbeat_charge(Path, _)),
    assertz(metta_py_heartbeat_charge(Path, Charge)).

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
    set_prolog_flag(heartbeat, 100),
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
%The joined-worker credits this thread discarded come out the same way
%(engine/metta/control.pl, metta_join_measured/3): a block is charged for the
%workers whose answers it used and not for a stopped branch's spend
%[tested 2026-09-26T00:36:52+10:00: test_a_race_is_charged_for_its_caller_and_its_winner_only].
%Each door reads for one EDGE of the window two readings bracket, and the
%discarded tally is read outside that window: before the inference read at
%the opening edge, after it at the closing edge. Read after the inference
%read at both edges it sat inside every window and charged it the read's
%five inferences, so the corpus lane read 293 of 294 twins at exactly +5
%over pins taken with the six the empty block costs [measured 2026-09-19:
%the twins lane on c7e27cf2a; commit=32335687084e4d8ad43cf8800f2dedce707fa137]. The arithmetic stays inline
%in both clauses rather than behind a shared helper, because a call after the
%opening read is inside the window too and would move every pin by one.
metta_py_work(open, Work) :-
    metta_discarded_inferences(Discarded),
    statistics(inferences, Raw),
    metta_py_heartbeat_term(_, Spent, At, Before),
    Late is max(0, sign(At - Raw)),
    Work is Raw - Spent + Late * (Spent - Before) - Discarded.
metta_py_work(close, Work) :-
    statistics(inferences, Raw),
    metta_py_heartbeat_term(_, Spent, At, Before),
    metta_discarded_inferences(Discarded),
    Late is max(0, sign(At - Raw)),
    Work is Raw - Spent + Late * (Spent - Before) - Discarded.

%One crossing for the engine's own counters: statistics/2 inferences and
%cputime, the garbage_collection triple (collections, bytes freed,
%milliseconds spent), the thread's answer-table bytes, which the tabling
%review found reachable only through the lower-level runtime, the
%interrupt poll's four-field term, and the joined-worker credits this thread
%discarded. The Python side reads deltas around a with-block and takes the
%poll's charge and the discarded credits out there.
%The tick's recorded inference position resolves a tick that arrives between
%the inference read and the tick record; both sides of that boundary retain
%the polling-disabled cost under concurrent workers
%[tested: test_heartbeat_correction_is_exact_with_32_concurrent_workers; commit=8358dfc233bf299bb23eceddd94593a62372fe4b].
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
%The edge, as for metta_py_work/2: the discarded tally is read outside the
%window, so the block's own cost stays the six inferences its pins carry.
metta_py_stats(open, [Inferences, CpuTime, GcCount, GcFreed, GcTimeMs, TableBytes,
                      Ticks, Spent, At, Before, Discarded]) :-
    metta_discarded_inferences(Discarded),
    statistics(inferences, Inferences),
    metta_py_heartbeat_term(Ticks, Spent, At, Before),
    statistics(cputime, CpuTime),
    statistics(garbage_collection, [GcCount, GcFreed, GcTimeMs|_]),
    statistics(table_space_used, TableBytes).
metta_py_stats(close, [Inferences, CpuTime, GcCount, GcFreed, GcTimeMs, TableBytes,
                       Ticks, Spent, At, Before, Discarded]) :-
    statistics(inferences, Inferences),
    metta_py_heartbeat_term(Ticks, Spent, At, Before),
    statistics(cputime, CpuTime),
    statistics(garbage_collection, [GcCount, GcFreed, GcTimeMs|_]),
    statistics(table_space_used, TableBytes),
    metta_discarded_inferences(Discarded).

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
