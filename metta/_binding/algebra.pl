% Purpose: identify the declared algebra of a host value.
% Assumes: loaded through _binding/shim.pl in its host module.

% Carrier predicates use the same atom codec as registered Python operations.
% In particular, Symbol and Expression remain atoms while Grounded unwraps.
% The direct call retains Python exceptions for the enclosing resource guard
% [tested: test_carrier_preserves_text_and_symbol_types; commit=074dc0a88b1605c54824de677d586b6f60998bcf].
:- multifile seam:grounded_algebra_type/3.
seam:grounded_algebra_type(Type, Value, Truth) :-
    py_is_object(Type),
    metta_py_encode(Type, TypeWire),
    metta_py_encode(Value, ValueWire),
    py_call('metta.algebra':'_carrier_type_accepts'(TypeWire, ValueWire), Raw),
    ( Raw == @(true) -> Truth = true ; Truth = false ).
