% Purpose: select module context for resolution and conversion.
% Assumes: loaded through _binding/shim.pl in its host module.

%%%%%%%%%% Space modules %%%%%%%%%%
%
% On an engine carrying the per-space-equation patch, a space's compiled
% clauses live in a module named after it and space_module/2 says which; a
% stock engine keeps everything in user. Asking rather than assuming keeps
% this shim loadable on both.

metta_py_module(Space, Module) :-
    ( current_predicate(space_module/2) -> space_module(Space, Module)
    ; Module = user ).

metta_py_in_module(Module, Goal) :-
    ( current_predicate(with_metta_module/2) -> with_metta_module(Module, Goal)
    ; call(Goal) ).

%A cast asks get-type, then get-metatype, for a bound target in Space's
%module. It applies the wildcard to the target only and is stricter than a
%typed call: an unknown value does not establish Person. The deliberate
%difference is pinned by test_metatype_targets_reach_through_the_fallback.
%Both decoded terms retain their own repeated-variable relationships, and
%a refusal returns the value's reported types for the Python diagnostic.
%A refused cast answers the value's types, unless the target is refined and
%the base admits the value: then the refusal is the first constraint the value
%violates, `["r", Constraint]`, so CastError names `(Gt 0)` and the value
%rather than a Number that was never the problem.
metta_py_cast(Space, ValueW, TypeW, Out) :-
    metta_py_decode_shared(ValueW, Value, _),
    metta_py_decode_shared(TypeW, Type, _),
    metta_py_module(Space, Module),
    ( metta_py_in_module(Module,
          ( 'get-type'(Value, Type) *-> true ; 'get-metatype'(Value, Type) ))
      -> Out = ["s", "ok"]
    ; metta_py_in_module(Module,
          metta_refinement_violation(Type, Value, Constraint))
      -> metta_py_encode(Constraint, ConstraintW),
         Out = ["r", ConstraintW]
    ; metta_py_in_module(Module, findall(T, 'get-type'(Value, T), Ts)),
      maplist(metta_py_encode, Ts, TsW),
      Out = ["e", TsW] ).
