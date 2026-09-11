% Purpose: forward engine messages with a reentrancy guard.
% Assumes: loaded through _binding/shim.pl in its host module.
% Owns resources: metta_with_trailed/3 restores the thread message guard at delivery exit.
% [source: extensions/python/metta/_binding/messages.pl:user:thread_message_hook/3;
% commit=WORKTREE]

%%%%%%%%%% Engine messages %%%%%%%%%%
%
% Every message the engine prints is also a `metta.engine` log record, so the
% tool a Python program already configures does the filtering and the
% formatting, and an engine warning lands in the same place the application's
% own warnings do.
%
% thread_message_hook/3 rather than message_hook/3, for the reason
% engine/metta/interop.pl:1200 gives and one more. SWI declares it thread_local
% [source: SWI-Prolog 10.1.13 boot/messages.pl:2083-2084], so a clause
% consulted here belongs to the thread that consulted this file, which is the
% thread Python drives the engine on. That IS the thread-safety argument: the
% Python callback only ever runs inside a crossing this process asked for, on
% a thread that has an interpreter state, and a message emitted on a Prolog
% worker thread finds no clause here and prints exactly as it did before
% [measured 2026-09-06: a clause asserted into user:thread_message_hook/3 from
% one janus crossing is still counted by clause/2 in the NEXT crossing on the
% same thread, and is absent from a Python worker thread's own engine].
%
% It FAILS after delivering, and must. print_message_guarded/2 reads a
% succeeding thread_message_hook as "handled", calling neither message_hook/3
% nor the printer [source: SWI-Prolog 10.1.13 boot/messages.pl:2135-2141], so
% succeeding here would silence the engine's own stderr. interop.pl's clause
% fails for that reason too, and both run: they are clauses of one predicate
% and neither claims the message.
%
% Messages emitted before this file is consulted -- the engine's own load --
% have no hook to reach and print only.
:- multifile user:thread_message_hook/3.
user:thread_message_hook(_, Kind, Lines) :-
    Kind \== silent,
    \+ nb_current('$metta_py_message_bridge', true),
    context_module(Host),
    % Workaround: swi-cleanup-window - delivery uses the engine's trailed reentrancy scope.
    metta_engine:metta_with_trailed('$metta_py_message_bridge', true,
                                   Host:metta_py_deliver_message(Kind, Lines)),
    fail.

%The flag above is a guard and not an optimisation: a logging handler that
%writes its way back into the engine emits from inside this call, and without
%it the message that raised would re-enter here without end. The Node seat's
%capture window carries the same flag for the same reason
%(extensions/node/bridge.pl:139).
%
%The rendered text is the lines SWI is about to print, not a second
%translation of the term, so the record and the stderr line say the same
%thing. Everything is caught: a message is not a place to fail from, and a
%Python side that is not ready yet -- metta_ops unimportable, an interpreter
%shutting down -- must cost the engine nothing but the attempt.
metta_py_deliver_message(Kind, Lines) :-
    catch(( metta_py_message_level(Kind, Level),
            print_message_lines(atom(Text), '', Lines),
            metta_py_message_location(File, Line),
            py_call(metta_ops:engine_message(Level, Text, File, Line), _) ),
          _,
          true).

%The location SWI's own printer prefixes the message with, so the record says
%as much as the stderr line beside it. It reads source_location/2 for the same
%reason print_system_message/3 does, and a message with none -- most of them,
%outside a load -- carries no location rather than a made-up one
%[source: SWI-Prolog 10.1.13 boot/messages.pl:2175-2179]. A syntax error is
%the exception there and here alike: its own location is already inside the
%rendered text.
metta_py_message_location(File, Line) :-
    (   source_location(Path, Line0)
    ->  atom_string(Path, File), Line = Line0
    ;   File = "", Line = -1
    ).

%SWI's kind as the word the Python side maps to a logging level. A compound
%kind -- debug(Topic) is the one that ships -- carries its functor, and the
%topic stays SWI's own business.
metta_py_message_level(Kind, Level) :-
    ( atom(Kind) -> Level = Kind ; functor(Kind, Level, _) ).
