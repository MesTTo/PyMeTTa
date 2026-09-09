% Purpose: hold and resume debugger stops across host calls.
% Assumes: loaded through _binding/shim.pl in its host module.
% Owns resources: held debugger engines until metta_py_debug_close/1 releases them
% [source: extensions/python/metta/_binding/debug.pl:51; commit=cd62330ceacc8f1254eed9791c3f6203b48a1c9e].

%%%%%%%%%% The debugger %%%%%%%%%%
%
% A debug session is a held engine, the same shape a lazy cursor is: the
% engine keeps the suspended program's state between crossings and the host
% steps it. What differs is what a crossing carries. A cursor's engine
% yields ANSWERS by succeeding; this one yields STOPS through
% engine_yield/1 from inside the tracer's wrapper, deep in the call tree,
% and takes a command back through engine_fetch/1 before it carries on.
%
% The policy rides inside the engine's goal for the reason
% metta_py_execution_policy_goal/3 already records: a transaction wrapped
% around the caller's engine_next/2 cannot roll back work the engine did,
% so it has to span the suspended goal. The cursor's speculative form
% collects and replays because a held query is nondeterministic; a debug run
% is one semidet execution, so the ordinary constructor is the right one.
%
% Inferences bounds the WHOLE session cumulatively and rides inside the
% engine, where the counter the budget reads is. There is no wall bound, and
% that is deliberate rather than missing: a session is suspended by design,
% so a clock would run while a person reads a stop.
metta_py_debug_open_controlled(Source, Space, Armed, Inferences, Count,
                               [Mode, _Capture], prolog(Engine)) :-
    metta_debug_begin(Armed, Count),
    catch(( metta_py_execution_policy_goal(
                Mode, metta_debug_run(Source, Space, Groups), Controlled),
            metta_host_inference_budget(Controlled, Inferences, Bounded),
            metta_host_hold(done(Groups), Bounded, Engine) ),
          Error,
          ( metta_debug_end, throw(Error) )).

%The first event, and every later one. The handle crosses to Python inside
%prolog/1 at the open and comes back as the bare engine, the same round trip
%a lazy cursor's handle makes. resume/2 is the session's own command
%term: the mode the program runs under next, and the WHOLE armed set, so a
%breakpoint added or dropped between stops needs no second protocol and
%leaves no edit to lose.
metta_py_debug_next(Engine, Answer) :-
    metta_py_hold_reified(Engine, Event),
    metta_py_debug_event(Event, Answer).

metta_py_debug_resume(Engine, Mode, Armed, Answer) :-
    ( metta_host_hold_post(Engine, resume(Mode, Armed), Row)
    -> Event = the(Row) ; Event = no ),
    metta_py_debug_event(Event, Answer).

metta_py_debug_close(Engine) :-
    metta_host_hold_close(Engine),
    metta_debug_end.

% The host hold service owns both suspended engines and transaction-held rows.
% Reify its pull as SWI's engine_next_reified/2 does, preserving the same
% debugger and dirty-lane result protocol [source:
% https://github.com/SWI-Prolog/swipl-devel/blob/V10.1.13/boot/engines.pl#L82-L89;
% commit=c6e1198c490a824b96f6fc6e1c0622a542917024].
metta_py_hold_reified(Handle, Event) :-
    catch(( metta_host_hold_next(Handle, Row)
          -> Event = the(Row) ; Event = no ), Error, Event = throw(Error)).

%A stop carries what a trace event carries, in the same encoding, so a host
%that renders one renders the other. `done` carries the run's answer groups,
%encoded exactly as metta_py_run/3 encodes them.
metta_py_debug_event(the(stop(Seq, Time, Depth, exit, Term, Answer, Names)),
                     [Seq, Time, Depth, "exit", EncodedTerm,
                      EncodedAnswer]) :- !,
    metta_py_encode_named(Term, Names, EncodedTerm),
    metta_py_encode_named(Answer, Names, EncodedAnswer).
metta_py_debug_event(the(stop(Seq, Time, Depth, Kind, Term, _, Names)),
                     [Seq, Time, Depth, KindText, EncodedTerm]) :- !,
    atom_string(Kind, KindText),
    metta_py_encode_named(Term, Names, EncodedTerm).
metta_py_debug_event(the(done(TermGroups)), [-1, -1, -1, "done", Groups]) :- !,
    maplist(metta_py_encode_group, TermGroups, Groups).
metta_py_debug_event(no, [-1, -1, -1, "failed"]) :- !.
metta_py_debug_event(throw(Error), _) :-
    throw(Error).
