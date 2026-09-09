% Purpose: encode trace events and bracket observation sessions.
% Assumes: loaded through _binding/shim.pl in its host module.
% Owns resources: observation wrappers between metta_py_observe_begin/1 and metta_py_observe_end/1
% [source: extensions/python/metta/_binding/trace.pl:85; commit=cd62330ceacc8f1254eed9791c3f6203b48a1c9e].

%The tracer answers terms; putting them on the wire is the shim's job, as
%it is for every other atom leaving the engine. A call event has no answer
%field at all, rather than a value standing in for its absence.
%One output, because janus binds the LAST argument and a trace now has two
%things to say: the events, and which bound stopped them being all of them.
%Stopped leads so a reader of the wire sees the qualifier before the data it
%qualifies, and carries the bound's own word rather than a yes-or-no,
%because the remedy differs per bound: false, or one of the limit
%vocabulary's events, memory, inferences, timeout and stack.
%
%Bounds is the caller's [Seconds, Inferences, StackBytes] triple, with the
%same -1 no-bound sentinels metta_py_limited uses, and this door applies it
%to the RUN itself rather than taking it from the generic wrapper around the
%whole door. Everything after the run -- harvesting the recorder and encoding
%events for the wire -- is work proportional to Max, which the caller has
%already bounded, and everything BEFORE it -- arming the tracer over every
%name the process has registered, twelve inferences each -- is proportional to
%nothing the caller can see, which is why the bounds ride into the tracer as a
%bounded/2 request rather than wrapping this door in metta_py_guarded/4
%[measured 2026-09-07: 12,016 inferences of arming in a fresh process and
%47,943 with three thousand more names defined, against 3,192 for the program
%beside them, and `inferences=40_000` answering an empty prefix under the whole
%suite in one process]. It is not small either: measured 2026-09-04 on
%examples/ch07-control-flow/07-05-recursion/06-peano.metta's own head, the
%traced run and harvest cost 686,743 inferences and encoding its 10,000
%events cost 4,825,600, seven times more
%[measured 2026-09-04; docs/journal/2026-09-04-bounded-trace-keeps-its-events.md].
%Charged to the run budget, a 2,000,000-inference trace therefore reached
%its EVENT bound during the run and then died encoding events it had already
%recorded, and the caller paid the whole budget to be told only that the
%budget was gone.
%Seed is the fourth run control beside the three bounds, and rides in for the
%same reason they do: it belongs to the PROGRAM, and a caller who pins it is
%recording a run whose draws have to come back the same on a replay. A negative
%number is the no-seed sentinel, the same one the three bounds use.
metta_py_trace(Source, Space, Max, Bounds, [Stopped, Encoded]) :-
    Bounds = [TimeS, Inf, StackBytes, Seed],
    metta_trace_source(Source, Space,
                       bounded(Max, run_bounds(TimeS, Inf, StackBytes, Seed)),
                       Events, Stopped),
    maplist(metta_py_trace_event, Events, Encoded).

%An exit carries the answer and nothing else does, so the shape splits there
%rather than once per kind: a `fail` row is a `call` row wearing its own word.
metta_py_trace_event(event(Seq, Time, Depth, exit, Term, Answer, Names),
                     [Seq, Time, Depth, "exit", EncodedTerm,
                      EncodedAnswer]) :- !,
    metta_py_encode_named(Term, Names, EncodedTerm),
    metta_py_encode_named(Answer, Names, EncodedAnswer).
metta_py_trace_event(event(Seq, Time, Depth, Kind, Term, _, Names),
                     [Seq, Time, Depth, KindText, EncodedTerm]) :-
    atom_string(Kind, KindText),
    metta_py_encode_named(Term, Names, EncodedTerm).

%An OBSERVE session: the same wrappers a trace arms, held across whatever calls
%the host makes next, and the events harvested when it lets go. It exists
%because the tracer does not stream -- an event is recorded into the store and
%read at the end -- so instrumentation over a BLOCK of host-driven work is the
%same recording with the host deciding where it starts and stops rather than one
%source string deciding.
%
%Two things differ from metta_py_trace/5 and both follow from that. The bound
%stops the RECORDING and not the work, because the work is the host's and a
%telemetry budget must not become its error; and the teardown is the host's
%`finally` rather than a setup_call_cleanup here, because the call that arms and
%the call that disarms are two crossings with the host's block between them.
%A second session, trace or debug, refuses through the tracer's own
%permission_error, which is the rule that only one session holds the wrappers.
%The request is metta_py_trace/5's own: a bound alone, or [Bound, Names].
metta_py_observe_begin(Request) :-
    (   nonvar(Request), Request = [Max, Filter]
    ->  true
    ;   Max = Request, Filter = all
    ),
    metta_trace_begin(Max, Filter, observe),
    %After the arming, so an event's time measures the block and not the wrap,
    %the same division metta_trace_session/7 makes for a traced run.
    metta_trace_start_clock.

metta_py_observe_end([Stopped, Encoded]) :-
    setup_call_cleanup(true,
                       ( metta_trace_harvest(Stopped, Events),
                         maplist(metta_py_trace_event, Events, Encoded) ),
                       metta_trace_end).
