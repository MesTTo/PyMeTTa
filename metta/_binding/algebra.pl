% Purpose: identify the declared algebra of a host value.
% Assumes: loaded through _binding/shim.pl in its host module.
% Guarantees: shipped operations use metta_apply_algebra_operation/5 with
%   caller context and accounting [tested:
%   test_visibility_operations_share_the_native_carrier; commit=90ba93eb8f6e98ebfefc55416859bf13de6a8427].

metta_py_algebra_operation_accounted(Space, Algebra0, OperationWire, [Wire, Used]) :-
    metta_py_work(Before),
    atom_string(Algebra, Algebra0),
    metta_py_decode_shared(OperationWire, [Operation, Left, Right], _),
    metta_py_module(Space, Module),
    metta_py_in_module(Module,
        metta_apply_algebra_operation(Algebra, Operation, Left, Right, Result)),
    metta_py_encode(Result, Wire),
    metta_py_work(After), Used is After - Before.

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
