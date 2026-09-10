% Purpose: preserve live callback exceptions and classify transport failures.
% Assumes: loaded through _binding/shim.pl in its host module.

%The live Python exception object inside a python_error term, so the
%boundary can re-raise the ORIGINAL, structured fields intact, instead of
%a flattened transcript of it. Handing Obj back through janus converts
%the blob to the very object the callback raised.
metta_py_original_exception(error(python_error(_, Obj), _), Obj) :-
    py_is_object(Obj).
