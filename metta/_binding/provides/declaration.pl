% Purpose: supply the Python binding's declaration seam clauses.
% Assumes: bindinggen projects each row into its declared load audience
% and defining module.
% Guarantees: every supplied head has this file's engine kind
% [tested: test_binding_provisions_keep_audience_and_kind; commit=9b0a084e534ddf7dd67980ad84c27c8279b877f1].

provides_declaration(host, user, transaction_constraint/1).

provides(host, user, (
seam:transaction_constraint(user:metta_py_validate_proxy(Space, Receiver, Token)) :-
    metta_py_pending_proxy(Space, Receiver, Token)
)).

provides_declaration(engine, user, grounded_extra_type/2).

provides(engine, user, (
seam:grounded_extra_type(Obj, Type) :-
    python_object_blob(Obj),
    py_is_object(Obj),
    metta_py_bridge,
    py_call('metta._binding.host':declared_type_texts(Obj), Texts, [py_string_as(string)]),
    member(Text, Texts),
    term_string(Type, Text)
)).

provides_declaration(engine, user, extension_builtin/2).

provides(engine, user, (
seam:extension_builtin('py-call',  oracleIO)
)).

provides(engine, user, (
seam:extension_builtin('py-atom',  oracleIO)
)).

provides(engine, user, (
seam:extension_builtin('py-dot',   oracleIO)
)).

provides(engine, user, (
seam:extension_builtin('py-list',  oracleIO)
)).

provides(engine, user, (
seam:extension_builtin('py-tuple', oracleIO)
)).

provides(engine, user, (
seam:extension_builtin('py-dict',  oracleIO)
)).

provides(engine, user, (
seam:extension_builtin('py-iter',  oracleIO)
)).

provides(engine, user, (
seam:extension_builtin('py-iter-once', oracleIO)
)).

provides_declaration(host, user, foreign_capability/2).

provides(host, user, (
seam:foreign_capability(Space, Capability) :-
    metta_py_foreign(Space),
    metta_py_capability(Space, Capability)
)).
