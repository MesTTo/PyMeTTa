% Purpose: translate engine exceptions and assertion outcomes.
% Assumes: loaded through _binding/shim.pl in its host module.

%%%%%%%%%% Errors %%%%%%%%%%
%
% Some exceptions are control signals rather than errors; converting one into a
% value would swallow the very signal its thrower waits for.
metta_py_raise(Kind, Detail) :-
    throw(error(metta_control_signal(Kind, Detail), context(metta, Kind))).

%The reserved envelope's kind and payload, with this side's absence marker
%put back. The kind list and both ball shapes are the engine's
%(metta_host_control_signal_info/3), where every seat reads the same table;
%the engine leaves a payload the ball does not carry UNBOUND, which is the
%convention metta_py_operation_part/2 already maps to janus's None. Two of
%the three shapes are SWI's own resource balls, which reach this side
%unenveloped whenever the goal that spent the budget was a NESTED query:
%janus's apply_once opens one with PL_Q_CATCH_EXCEPTION, so it takes the ball
%before the enclosing call_with_inference_limit/3 can see it and turn it into
%the envelope. A Python callback that re-enters the engine is exactly that
%shape, and without them its budget arrived at the Python door as
%`EngineError: Unknown message: inference_limit_exceeded`, naming neither the
%resource nor the caller's own bound [tested:
%test_a_reentrant_provider_generator_reports_the_budget_that_stopped_it;
%commit=0ee5a2dfee0e37a23b0eb9c765b477d7f90295fe].
%
%A SECOND copy of the kind list lived here until 2026-09-07, which is the
%drift the metta_py_control_exception/1 note below records happening once
%already; the Node seat meanwhile read the kinds out of the rendered message
%and knew five of them.
metta_control_signal_info(Error, Kind, Detail) :-
    metta_host_control_signal_info(Error, Kind, Detail0),
    metta_py_operation_part(Detail0, Detail).

%WHERE a reader failure stopped, for the one control signal that has a place
%as well as a sentence. The envelope's context slot is the engine's and
%metta_host_control_signal_line/2 reads it; the name stays this side's
%because it is what the Python door's own goal text asks for, and so does the
%FAILURE where no line was named, which is every other syntax refusal in this
%tree (a single form read through metta_py_read_form/3, a numeric literal past
%binary64) and which the Python side reads as MettaSyntaxError.line staying
%None rather than a guessed line.
metta_control_signal_line(Error, Line) :-
    metta_host_control_signal_line(Error, Line).

%The classification is the engine's metta_host_operation_error/5; this side
%maps its neutral absence, an unbound part, onto janus's None.
metta_py_operation_error(Error, Operation, Kind, Expected, Culprit) :-
    metta_host_operation_error(Error, Operation, Kind, Expected0, Culprit0),
    metta_py_operation_part(Expected0, Expected),
    metta_py_operation_part(Culprit0, Culprit).

metta_py_operation_part(Part, @none) :- var(Part), !.
metta_py_operation_part(Part, Part).

%A bag of ANSWERS on its way to Python, which is what an assertion's two
%directed differences are. It crosses on metta_py_encode_answer/2, the wire
%every other answer takes, so `.missing` and `.excess` arrive DECODED as atoms
%and carry the rational-tree refusal with them; janus's own reading of the
%engine's storage would hand a caller nested Python lists of strings instead.
%Absence stays absence, the same unbound-is-@none convention the operation
%parts above use, so an empty bag and a bag the form never computed remain two
%different answers [tested:
%extensions/python/tests/ch10_errors_and_refusals/test_assertion_difference.py].
metta_py_answer_bag(Bag, @none) :- var(Bag), !.
metta_py_answer_bag(Bag, Wires) :- maplist(metta_py_encode_answer, Bag, Wires).

%The term is the engine's (engine/spaces/lifecycle.pl raises and renders it)
%and so is the reading, metta_host_space_capability_error/4; this side keeps
%the name its own goal text asks for.
metta_py_space_capability_error(Error, Space, Operation, Capability) :-
    metta_host_space_capability_error(Error, Space, Operation, Capability).
%The two ASSERTION doors a Python test reaches, one per relation, each of them
%the engine door its MeTTa twin already reaches. A Python harness comparing two
%answer bags could subtract them itself, and then the two faces would hold two
%multiset relations agreeing only by review: 'subtraction-atom'/3 removes by
%standard-order EQUALITY and never unifies, so two separately named variables
%are two answers there where Python's Variable('x') == Variable('x') is one
%[source: engine/metta/input_guards.pl, subtraction-atom/3 and the count_assoc
%note above it]. Handing the bags over instead makes the agreement structural:
%one relation, one difference, one sentence, and the same AssertionFailure
%classifier metta_assertion_failure/6 above already answers for.
%
%ONE wire carries the whole call, `(assert-answers <actual> <expected>)` or the
%same with a message, because that term is BOTH what the doors report as the
%form the program wrote and where the two bags are read from. Decoding it once
%shares a variable by NAME across the two bags, which is what one MeTTa source
%writing the same two bags does.
%
%The verdict stays the caller's on the engine side, so it is computed here, and
%it is the relation each door's MeTTa twin computes: assertEqualToResult's two
%empty differences, and assertIncludes' one
%[source: engine/prelude.metta, assertEqualToResult and assertIncludes;
%tested: extensions/python/tests/ch12_testing/test_assert_answers.py].
metta_py_assert_answers(Tagged) :-
    metta_py_assertion_call(Tagged, Form, Actual, Expected),
    'subtraction-atom'(Expected, Actual, Missing),
    'subtraction-atom'(Actual, Expected, Excess),
    (   Missing == [], Excess == []
    ->  Verdict = true
    ;   Verdict = false
    ),
    'assert-answers'(Verdict, Form, Actual, Expected, _).

%The one-sided twin, containment rather than equality, so only the answers
%missing from the expectation decide the verdict and only they are reported.
metta_py_assert_includes(Tagged) :-
    metta_py_assertion_call(Tagged, Form, Actual, Expected),
    'subtraction-atom'(Expected, Actual, Missing),
    (   Missing == []
    ->  Verdict = true
    ;   Verdict = false
    ),
    'assert-includes-answers'(Verdict, Form, Actual, Expected, _).

%The call as the Python side wrote it, with its two bags read off it. Both are
%proper LISTS, which is what the doors themselves check before computing a
%difference; the Python side builds them out of its own two tuples, so failing
%here is this file's bug rather than a caller's input, and the Python side
%raises rather than reading the failure as a false verdict.
metta_py_assertion_call(Tagged, Form, Actual, Expected) :-
    metta_py_decode_shared(Tagged, Form, _),
    Form = [_Head, Actual, Expected|_],
    is_list(Actual),
    is_list(Expected).

%The catalog's DECLARATION for whichever kind a raised ball is: the class name
%the taxonomy gives that kind, the FIELDS that kind carries in this very ball,
%the authority the refusal stands on and the repair, with the remedy template's
%<field> holes already filled. metta_host_refusal/6 is the one renderer; this
%side only puts the rows on the wire, encoded the way every other atom crosses,
%so the Python side reads them back with Ground.from_atom/1 and
%Remedy.from_atom/1 rather than parsing a rendered sentence.
%
%The fields cross as [Name, Value] pairs rather than as Prolog's Name-Value,
%which janus has no Python spelling for. They are what lets the seat build the
%class its row names with the parts that class declares: a stack overflow
%carries its ceiling and a missing source carries its path, where before both
%arrived as a sentence with nothing to read off it.
%
%It FAILS for a ball whose kind carries no catalog row, which the row lane
%forbids and a program that removed the row can still produce; the Python side
%then raises the class it already chose, with no ground and no remedy.
metta_py_refusal(Error, Kind, Fields, Class, Ground, Remedy) :-
    metta_host_refusal(Error, Kind, Pairs, Class, GroundRow, RemedyRow),
    maplist(metta_py_refusal_field, Pairs, Fields),
    metta_py_encode(GroundRow, Ground),
    metta_py_encode(RemedyRow, Remedy).

%One Name-Value pair as the two-element list janus has a Python spelling for.
metta_py_refusal_field(Name-Value, [Name, Value]).

%The Python side's contributions to the engine's control-signal seam. There
%was a metta_py_control_exception/1 here holding a SECOND copy of the list,
%and nothing ever called it: it had drifted from the engine's, missing
%metta_host_interrupted and both of this side's limit errors, so anyone who found it
%and used it would have swallowed exactly the signals this side raises.
%metta_engine: because this shim is consulted into `user` and the seam's home is
%the engine core's module: control_exception/1 is the one seam the translator
%emits into compiled bodies, so protect_engine_emitted/1 imports it into every
%space from there [source: engine/ext_points.pl:kind/2; commit=ede2ac57e213a0d4502c6bbbca6227f97015b720]. Unqualified here it would create
%user:control_exception/1, SWI would report `Local definition of
%user:control_exception/1 overrides weak import from metta_engine`, and the
%engine's recovery sites would read the host's one clause instead of the
%engine's whole list [tested: extensions/python/tests/ch07_control_flow/test_control_signals.py; commit=ede2ac57e213a0d4502c6bbbca6227f97015b720].
:- multifile metta_engine:control_exception/1.
metta_engine:control_exception(error(metta_control_signal(_, _), context(metta, _))).
