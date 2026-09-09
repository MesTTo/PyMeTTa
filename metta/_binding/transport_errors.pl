% Purpose: preserve live callback exceptions and classify transport failures.
% Assumes: loaded through _binding/shim.pl in its host module.

%The live Python exception object inside a python_error term, so the
%boundary can re-raise the ORIGINAL, structured fields intact, instead of
%a flattened transcript of it. Handing Obj back through janus converts
%the blob to the very object the callback raised.
metta_py_original_exception(error(python_error(_, Obj), _), Obj) :-
    py_is_object(Obj).

%The bridge's class-name fast path cannot recognize Python subclasses.
%Classify the live object with the library's shared transport predicate.
:- multifile seam:host_transport_failure/1.
seam:host_transport_failure(error(python_error(Class, Obj), _)) :-
    Class \== 'TransportFailure',
    py_is_object(Obj),
    py_call('metta._errors.errors':is_transport_failure(Obj), @(true)).
