% Purpose: store MeTTa atoms, compile equations into per-space modules,
%   route matching to native and foreign space providers, and validate
%   '&petta' declarations against the self-describing catalog.
% Assumes:
%   - the removal funnel takes a space NAME rather than a handle, so
%     metta_remove_atom/3, unstore_atom/3 and remove_equation/6 each take an
%     atom first; remove_equation/6 is reached only for a stored equation, so
%     its function symbol is an atom; and all three answer whether anything
%     went in a `true` or `false` last argument [measured 2026-08-19 by
%     wrapping the three and reading every call the 19 shipped MeTTa files
%     that remove an atom make]. Each of those is a PlDoc mode line above its
%     clause, so the development build checks it at run time rather than
%     leaving it prose [tested:
%     the_dev_build_inserts_checks_and_types_a_planted_violation]; the
%     dev-typed gate lane also runs every plunit suite under that build.
% Guarantees:
%   - Every native space stores its atoms in a private data module that does
%     not inherit user predicates [tested: spaces_storage_modules].
%   - stored_atom_of_ref/3 is add_sexp_in/4's inverse over both stored shapes,
%     and answers for a stored atom's clause reference alone: not for a
%     compiled clause's, not for a registration's, not for an erased one
%     [tested 2026-08-19:
%     spaces_storage_modules:a_stored_atoms_reference_decodes_to_its_atom,
%     spaces_storage_modules:an_erased_reference_decodes_to_nothing].
%   - An equation for a name this space's module already DERIVED as a
%     specialization is not stored again, so enumerating a space and re-adding
%     its atoms answers a space that holds and answers what the first one did
%     [tested: test_a_copy_reproduces_the_space_it_copied].
%   - Five 2,000-row native joins take 270305 direct and 270307 prepared
%     inferences [measured: 270305 and 270307 inferences on 2026-08-15].
%   - Native spaces preserve scalar atoms and expressions as distinct values
%     [tested 2026-08-14: spaces_arbitrary_atoms].
%   - A '&petta' declaration violating its declared (kind ...) row is a hard
%     error at both write doors, naming the atom, the argument position and
%     the argspec; a head with no kind row passes untouched
%     [tested 2026-08-20: catalog_self_description].
%   - A selective native match is one indexed probe rather than a scan, and
%     the acyclic guard does not change that because it runs on the answer
%     [tested 2026-08-18:
%     a_selective_match_costs_the_same_on_a_hundredfold_larger_space]
%     [measured 2026-08-18: 6,502 inferences per 500 matches on spaces of
%     100, 1,000 and 10,000 atoms].
%   - Removing one scoped get-type rule keeps sibling extension rules visible
%     [tested 2026-08-15: spaces_type_extensions].
%   - Clearing a native space clears its import life without making wildcard
%     atom removal touch that life [tested 2026-08-15:
%     filereader_import_lifecycle].
%   - Dynamic function registration is atomic and failed source loads remove
%     its asserted compiler state [tested 2026-08-14:
%     change_hook_error_rolls_back_every_registration_write,
%     filereader_source_rollback].
%   - match_foreign/5 passes options only to a provider that declared
%     metta_foreign_match/3, and unification and the caller's own bound stay
%     on this side, so an option cannot change an answer [tested 2026-08-16:
%     test_a_provider_ignoring_the_bound_is_still_bounded_by_the_engine].
%   - (top k ...) answers the k best by declared-semiring annotation,
%     stable on ties, refuses unordered contexts, and hands the provider
%     the bound only under Exact route + ordered annotations + best-first
%     merge [tested 2026-08-17: answers_annotations].
%   - A declared (handles ...) entry outranks metta_foreign_pushdown/3
%     shape by shape, a routed Refuse throws on any match of its shape
%     with a join checked conjunct by conjunct at plan time, and an
%     undeclared context pays one indexed probe per query
%     [tested 2026-08-17: spaces_handles_guard] [measured 2026-08-17:
%     pure-Prolog foreign match 34 to 41 inferences, bounded take 41 to
%     55].
% Guarded by: '$petta_native_storage' serializes private module creation and
%   publication in native_storage_module_cache/2.
% Open Obligations:
%   To Do: None
%   Hacks: None
%   Future Enhancements: None

% Storage modules are separate from execution modules. They inherit nothing,
% so a user predicate cannot appear as a space atom, and unknown arities fail
% without a catch on the indexed read path. The fixed prefix maps every space
% atom injectively to one module name.
native_storage_module(Space, Module) :-
    atom_concat('$petta_atoms:', Space, Module).

:- dynamic native_storage_module_cache/2.
%Whether a HOST's own add hooks are idle, the host's clause of it: the
%shim answers for the Python side, and with no host loaded the seam has no
%clause and the engine's own test above already answered.
:- multifile metta_host_add_hooks_idle/1.
ext_point_kind(metta_host_add_hooks_idle/1, ownership).

%Only a module that actually holds something belongs to somebody else.
%current_module/1 is not that test: SWI creates a module as a side effect of
%merely naming it, including from read-only introspection, so
%predicate_property('$petta_atoms:&kb':anything, dynamic) was enough to make
%&kb throw on every write for the life of the process, with clear/1 reporting
%success and changing nothing. An empty module of that name is ours to claim
%[tested: spaces_registration:naming_the_storage_module_does_not_claim_it].
native_storage_module_occupied(Module) :-
    current_module(Module),
    predicate_property(Module:Head, defined),
    \+ predicate_property(Module:Head, imported_from(_)),
    \+ predicate_property(Module:Head, foreign), !.

native_storage_ready(Module) :-
    current_predicate(Module:'$petta_native_storage'/0),
    predicate_property(Module:'$petta_native_storage', dynamic),
    \+ predicate_property(Module:'$petta_native_storage',
                           imported_from(_)).

native_storage_module_ready(Space, Module) :-
    native_storage_module_cache(Space, Module).

%Whether a NAME is a space, which is the wider question: one this engine
%already holds, or one it would create by being written to. A space is created
%on demand here, so the second half cannot be the registry, and the rule for it
%is the engine's own: an atom beginning with `&`, which is what is-space/2
%answers, what evalc/3 has enforced at its door since it was written, and what
%python/petta/space.py enforces at the library's
%[tested: space_argument_refusals].
petta_space_name(S) :- atom(S), sub_atom(S, 0, 1, _, '&'), !.
petta_space_name(S) :- petta_space_operand(S).
%HERE rather than beside petta_space_operand/1 below, because the two
%directives that create &self's and &petta's storage modules run while this
%file loads and a directive can only call what is already defined.

ensure_native_storage_module(Space, Module) :-
    native_storage_module_cache(Space, Module), !.
%CREATION is where a name that is not a space is refused, and refusing here is
%what makes the check free: a space this engine already holds answered from the
%cache above without asking, and only a name it would have to CREATE reaches
%the question. The doors above turn this failure into the arbiter's own error
%answer [tested: space_argument_refusals]. Asking at each door instead cost one
%to three inferences on every space operation and four benchmarks saw it
%[measured 2026-08-20: direct-join +10, prepared-join +10, register-op +200,
%py-method-call +30,002].
ensure_native_storage_module(Space, Module) :-
    petta_space_name(Space),
    native_storage_module(Space, Module),
    with_mutex('$petta_native_storage',
               ensure_native_storage_module_locked(Space, Module)).

ensure_native_storage_module_locked(Space, Module) :-
    native_storage_module_cache(Space, Module), !.
ensure_native_storage_module_locked(Space, Module) :-
    native_storage_ready(Module), !,
    assertz(native_storage_module_cache(Space, Module)).
ensure_native_storage_module_locked(Space, Module) :-
    ( native_storage_module_occupied(Module)
      -> throw(error(permission_error(create, native_space_storage, Module),
                     context(ensure_native_storage_module/2,
                             'the reserved storage module name is already in use')))
    ; set_prolog_flag(Module:unknown, fail),
      dynamic(Module:'$petta_native_storage'/0),
      assertz(native_storage_module_cache(Space, Module)) ).

%The dynamic marker and module properties survive transaction rollback even
%when its cache fact does not. A later write can therefore recover the cache
%instead of finding a stranded reserved module name [tested:
%spaces_registration:rolled_back_first_write_keeps_storage_reusable].
:- ensure_native_storage_module('&self', _).
:- dynamic '$petta_atoms:&self':'&self'/3.
%&petta too, at load: the contract read path probes it on every foreign
%match, and against a module that does not exist yet each probe is a thrown
%and caught existence error, 65 inferences where the created module's
%unknown=fail flag answers the same miss in a handful [measured 2026-08-17:
%petta_handles_route 136 to 30 inferences per miss].
:- ensure_native_storage_module('&petta', _).

% Return the asserted clause reference so a source load can roll back every
% atom it added if a later form fails.
add_sexp(Space, Term) :- add_sexp(Space, Term, _).
%&self's storage module is fixed and created when this file loads, so the
%default space skips the cache lookup that every other space needs. Writes are
%the one path that pays per atom: resolving the module per write cost four
%inferences of every seven on this path [measured 2026-08-15: 7.00 to 5.00
%inferences per write over 200,000 writes].
add_sexp('&self', Term, Ref) :- !, add_sexp_in('$petta_atoms:&self', '&self', Term, Ref).
%The contract flag rides an indexed clause of its own, so an ordinary
%add never even tests for '&petta': first-argument indexing dispatches
%past this clause for every other space at zero cost, where a guard
%inside the shared funnel taxed every write (+26k on source-load's
%counter, caught by the gate).
add_sexp('&petta', Term, Ref) :- !,
    petta_declaration_check(Term),
    petta_note_ctx_declared(Term),
    ensure_native_storage_module('&petta', Module),
    add_sexp_in(Module, '&petta', Term, Ref),
    petta_catalog_note_added(Term).
add_sexp(Space, Term, Ref) :- ensure_native_storage_module(Space, Module),
                              add_sexp_in(Module, Space, Term, Ref).

%The two clause bodies below are native_atom_clause/3 written out rather than
%called, and that is measured rather than assumed: calling it cost one goal
%per write, +2001 inferences over add-batch's thousand atoms, +2 per write on
%a seven-inference path. native_atom_clause/3 stays the definition, this is
%its copy on the hot path, and native_storage_shapes_agree binds them.
:- dynamic petta_ctx_declared/1.

%Monotone-conservative contract flag, set at the one funnel every native
%'&petta' write passes: flag ABSENT proves no declaration has ever named
%the context, so the per-call guards below skip their probes outright;
%flag PRESENT only means "run the real probes", so a declaration removed
%or rolled back later costs nothing but the shortcut. The subject is
%conservatively the declaration's first argument whatever the head,
%because over-flagging a non-context symbol is harmless while missing a
%real context would silently skip a guard. This closes CA-7's open
%squeeze: the undeclared pure-Prolog foreign match paid the handles,
%source and on-error probes on every call.
petta_note_ctx_declared([Head|_]) :-
    petta_catalog_head(Head),
    !.
petta_note_ctx_declared([_, Ctx|_]) :-
    atom(Ctx),
    \+ petta_ctx_declared(Ctx),
    !,
    assertz(petta_ctx_declared(Ctx)).
petta_note_ctx_declared(_).

%The catalog's own rows never name a context in their first argument, a
%kind head or a vocabulary name being what sits there, and flagging those
%grew petta_ctx_declared from a handful of real contexts to forty rows,
%which the guards' first miss then paid as a linear walk before the JIT
%index built [measured 2026-08-20: the single-pattern snapshot probe read
%687 against 685 by warm-up order]. Skipping them keeps the flag exactly
%what it says: a context some declaration names.
petta_catalog_head(kind).
petta_catalog_head(vocabulary).
petta_catalog_head(claim).
petta_catalog_head('routed-by-shape').

add_sexp_in(Module, Space, [Rel|Args], Ref) :- !,
                                               Term =.. [Space, Rel | Args],
                                               assertz(Module:Term, Ref).
%A scalar or empty expression cannot be a plain Space(Term) fact, because that
%is already the encoding of the singleton expression (Term). It gets its own
%predicate rather than a marked rule inside the space: a marked rule makes
%every clause of the space predicate a rule, so reading one back has to go
%through clause/2, which walks the clause list instead of using SWI's clause
%indexing. Measured on examples/spaces/matespace.metta, that cost 15.3x,
%99.5 billion instructions against 1,520 billion. Keeping scalars in
%the private scalar predicate leaves expressions as facts a direct indexed
%call reaches.
add_sexp_in(Module, _, Atom, Ref) :-
    assertz(Module:'$petta_native_scalar'(Atom), Ref).

%%%% The catalog describes its own kinds %%%%
%
%Three declaration heads make the catalog self-describing, themselves
%ordinary '&petta' atoms a program can match and remove:
%
%    (vocabulary Name Value...)       a named value set, every value a symbol
%    (claim Vocab Value Property...)  properties of one value, read where a
%                                     consultation site needs a per-value fact
%                                     rather than a list compiled into the
%                                     engine
%    (kind Head ArgSpec...)           the positional shape of every (Head ...)
%                                     declaration
%
%An argspec is symbol, integer, pattern, term, (one-of Vocab),
%(optional Spec) in the tail only, or (rest Spec) in final position matching
%zero or more. pattern and term both admit any term; the two names keep a
%kind's row readable, a pattern is matched against queries and a term is
%carried.
%
%The checker runs at the two doors every native '&petta' write passes, the
%per-atom funnel above and the bulk door below. A head with a declared kind
%is validated positionally, and a violation is a hard error naming the atom,
%the argument position and the argspec it missed, where the old behaviour
%was an atom that silently never matched its consultation site. A head with
%NO declared kind passes untouched, which is what keeps the data axis open:
%a third-party declaration kind is atoms here first, schema-checked only
%once its author declares a kind row for it. The shape is PostgreSQL's: enum
%values are catalog rows and a write validates against the catalog, not
%against a list compiled into the server [source: PostgreSQL documentation,
%8.7 Enumerated Types]. Removal is monotone-conservative, the
%petta_ctx_declared rule: a removed kind row means later adds of that head
%pass unchecked, and remove-then-redeclare, even WIDER than the shipped
%preset, is how a program deliberately loosens a shipped kind.
%
%Self-description bootstraps by declaration order: the presets below add the
%vocabularies first, then (kind kind ...) while no kind row exists yet, so
%it enters unchecked, and from that atom on every (kind ...) add is
%validated against it, its argspecs walked by the same checker that walks
%any other declaration.
petta_declaration_check(Term) :-
    Term = [Head|Args],
    atom(Head),
    petta_kind_spec(Head, Spec),
    !,
    petta_check_positions(Args, Spec, 1, Term),
    petta_check_catalog_semantics(Head, Args, Term).
petta_declaration_check(_).

%A landed catalog row must beat any negative cache row for its subject:
%the positive rows self-heal through their stored reference, the negative
%ones have nothing to watch, so the write funnel retracts them here. A
%kind or routing row landing also rebuilds its head's materialized route
%dispatch, which is how the shipped routes come up during the preset walk
%and how a third-party routed kind starts routing the moment its rows are
%in.
petta_catalog_note_added([kind, Head|_]) :-
    !,
    retractall(petta_kind_cache(Head, _, _)),
    petta_materialize_route(Head).
petta_catalog_note_added([vocabulary, Vocab|_]) :-
    !,
    retractall(petta_vocab_cache(Vocab, _, _)).
petta_catalog_note_added(['routed-by-shape', Head|_]) :-
    !,
    petta_materialize_route(Head).
petta_catalog_note_added(_).

%The removal twin, called by the '&petta' clause of remove_sexp below for
%a row that actually left. A variable head means the caller removed by
%pattern and anything may have gone, so everything derived is dropped and
%rebuilt, which over-invalidates and never under-invalidates.
petta_catalog_note_removed([Rel|_]) :-
    var(Rel),
    !,
    retractall(petta_kind_cache(_, _, _)),
    retractall(petta_vocab_cache(_, _, _)),
    petta_materialize_routes.
petta_catalog_note_removed([kind, Head|_]) :-
    !,
    retractall(petta_kind_cache(Head, _, _)),
    petta_materialize_route(Head).
petta_catalog_note_removed([vocabulary, Vocab|_]) :-
    !,
    retractall(petta_vocab_cache(Vocab, _, _)).
petta_catalog_note_removed(['routed-by-shape', Head|_]) :-
    !,
    petta_materialize_route(Head).
petta_catalog_note_removed(_).

%One catalog row as a list, whatever its arity: '&petta'(kind, handles,
%symbol, ...) reads back as [kind, handles, symbol, ...]. The walk over the
%arities the storage module holds runs on catalog edits and cache misses,
%never on a match path and never on the per-write fast path below.
petta_catalog_row(Row) :-
    petta_catalog_clause(Row, _).

petta_catalog_clause([Rel|Args], Ref) :-
    native_storage_module('&petta', Module),
    current_predicate(Module:'&petta'/N),
    N >= 1,
    functor(Goal, '&petta', N),
    Goal =.. ['&petta', Rel|Args],
    clause(Module:Goal, true, Ref).

%The write-path cache. The checker runs on every '&petta' write, and the
%uncached lookup walks current_predicate over the storage arities, which
%cost register-op +2,302 inferences and made its samples drift as the
%bench's own writes created new arities [measured 2026-08-20: 42,632 to
%44,934..46,707]. One first-arg-indexed row per head fixes both. A hit
%carries the catalog clause's reference and revalidates with erased/1, so
%removing a kind or vocabulary row self-heals on the next lookup with no
%hook in the removal path; a miss is cached as a negative row, which the
%write funnel retracts when a row for that head lands. Cache writes inside
%a transaction roll back with the catalog writes they mirror, so the two
%cannot part ways.
:- dynamic petta_kind_cache/3.    %Head, Spec | none, ref(Ref) | none
:- dynamic petta_vocab_cache/3.   %Vocab, Values | none, ref(Ref) | none

petta_kind_spec(Head, Spec) :-
    (   petta_kind_cache(Head, Spec0, Validity)
    ->  (   Validity = ref(Ref)
        ->  (   petta_catalog_ref_erased(Ref)
            ->  retractall(petta_kind_cache(Head, _, _)),
                petta_kind_spec_fresh(Head, Spec)
            ;   Spec = Spec0
            )
        ;   fail
        )
    ;   petta_kind_spec_fresh(Head, Spec)
    ).

%A reference whose clause is gone, by property or by the reference itself
%having been collected, either way the cached row is stale.
petta_catalog_ref_erased(Ref) :-
    catch(clause_property(Ref, erased), _, true).

petta_kind_spec_fresh(Head, Spec) :-
    (   petta_catalog_clause([kind, Head|Fresh], Ref)
    ->  assertz(petta_kind_cache(Head, Fresh, ref(Ref))),
        Spec = Fresh
    ;   assertz(petta_kind_cache(Head, none, none)),
        fail
    ).

petta_vocabulary_values(Vocab, Values) :-
    (   petta_vocab_cache(Vocab, Values0, Validity)
    ->  (   Validity = ref(Ref)
        ->  (   petta_catalog_ref_erased(Ref)
            ->  retractall(petta_vocab_cache(Vocab, _, _)),
                petta_vocabulary_values_fresh(Vocab, Values)
            ;   Values = Values0
            )
        ;   fail
        )
    ;   petta_vocabulary_values_fresh(Vocab, Values)
    ).

petta_vocabulary_values_fresh(Vocab, Values) :-
    (   petta_catalog_clause([vocabulary, Vocab|Fresh], Ref)
    ->  assertz(petta_vocab_cache(Vocab, Fresh, ref(Ref))),
        Values = Fresh
    ;   assertz(petta_vocab_cache(Vocab, none, none)),
        fail
    ).

%The positional walk. Position counts declaration arguments from 1, the way
%the refusal prints them; the Expected a refusal carries is the argspec as
%declared, so the message shows the row's own words.
petta_check_positions([], [], _, _) :- !.
petta_check_positions([], [Spec|Rest], Position, Term) :-
    !,
    (   forall(member(S, [Spec|Rest]), petta_spec_omittable(S))
    ->  true
    ;   petta_declaration_refused(Term, Position, Spec)
    ).
petta_check_positions([_|_], [], Position, Term) :-
    !,
    petta_declaration_refused(Term, Position, 'no further argument').
petta_check_positions(Args, [[rest, Spec]], Position, Term) :-
    !,
    petta_check_rest(Args, Spec, Position, Term).
petta_check_positions([Arg|Args], [[optional, Spec]|Rest], Position, Term) :-
    !,
    petta_check_value(Arg, Spec, Position, Term),
    Next is Position + 1,
    petta_check_positions(Args, Rest, Next, Term).
petta_check_positions([Arg|Args], [Spec|Rest], Position, Term) :-
    petta_check_value(Arg, Spec, Position, Term),
    Next is Position + 1,
    petta_check_positions(Args, Rest, Next, Term).

petta_check_rest([], _, _, _).
petta_check_rest([Arg|Args], Spec, Position, Term) :-
    petta_check_value(Arg, Spec, Position, Term),
    Next is Position + 1,
    petta_check_rest(Args, Spec, Next, Term).

petta_spec_omittable([optional, _]).
petta_spec_omittable([rest, _]).

petta_check_value(Arg, symbol, Position, Term) :-
    !,
    (   atom(Arg) -> true ; petta_declaration_refused(Term, Position, symbol) ).
petta_check_value(Arg, integer, Position, Term) :-
    !,
    (   integer(Arg) -> true ; petta_declaration_refused(Term, Position, integer) ).
petta_check_value(_, pattern, _, _) :- !.
petta_check_value(_, term, _, _) :- !.
petta_check_value(Arg, ['one-of', Vocab], Position, Term) :-
    !,
    (   atom(Arg),
        petta_vocabulary_values(Vocab, Values),
        memberchk(Arg, Values)
    ->  true
    ;   petta_declaration_refused(Term, Position, ['one-of', Vocab])
    ).
petta_check_value(_, Spec, Position, Term) :-
    petta_declaration_refused(Term, Position, Spec).

%kind and claim rows carry meaning past their shape, and the checker owns
%their language, so their adds get the deeper walk: a kind's argspecs must
%be well-formed with optional confined to the tail and rest final, and a
%claim must name a declared vocabulary and one of its values. Everything
%else was already covered by the positional walk.
petta_check_catalog_semantics(kind, [KindHead|Spec], Term) :-
    !,
    (   petta_kind_spec(KindHead, _)
    ->  petta_declaration_refused(Term, 1,
                                  'one kind row per head; remove the old row first')
    ;   true
    ),
    petta_check_argspecs(Spec, 2, Term),
    %A head already routed by shape keeps routable: re-declaring its kind
    %(remove, then add) with a spec the route cannot dispatch would leave a
    %standing routed-by-shape row over an unroutable shape, so the unfit
    %spec is refused here rather than discovered as dead routing.
    (   petta_routed_head(KindHead, Key)
    ->  petta_check_route_fit(Key, Spec, Term)
    ;   true
    ).
petta_check_catalog_semantics('routed-by-shape', [Head|KeyArgs], Term) :-
    !,
    (   KeyArgs == []
    ->  Key = context
    ;   KeyArgs = [Key]
    ),
    (   petta_kind_spec(Head, Spec)
    ->  petta_check_route_fit(Key, Spec, Term)
    ;   petta_declaration_refused(Term, 1,
                                  'a kind row for the routed head, declared first')
    ).
petta_check_catalog_semantics(vocabulary, [Name|_], Term) :-
    !,
    (   petta_vocabulary_values(Name, _)
    ->  petta_declaration_refused(Term, 1,
                                  'one vocabulary row per name; remove the old row first')
    ;   true
    ).
petta_check_catalog_semantics(claim, [Vocab, Value|_], Term) :-
    !,
    (   petta_vocabulary_values(Vocab, Values)
    ->  (   memberchk(Value, Values)
        ->  true
        ;   petta_declaration_refused(Term, 2, 'a value of the vocabulary')
        )
    ;   petta_declaration_refused(Term, 1, 'a declared vocabulary')
    ).
petta_check_catalog_semantics(_, _, _).

petta_check_argspecs([], _, _).
petta_check_argspecs([Spec|Rest], Position, Term) :-
    petta_check_argspec_form(Spec, Position, Term),
    (   Spec = [rest, _], Rest \== []
    ->  petta_declaration_refused(Term, Position, 'rest only in final position')
    ;   Spec = [optional, _], Rest = [NextSpec|_], \+ petta_spec_omittable(NextSpec)
    ->  petta_declaration_refused(Term, Position, 'optional only in the tail')
    ;   true
    ),
    Next is Position + 1,
    petta_check_argspecs(Rest, Next, Term).

petta_check_argspec_form(symbol, _, _) :- !.
petta_check_argspec_form(integer, _, _) :- !.
petta_check_argspec_form(pattern, _, _) :- !.
petta_check_argspec_form(term, _, _) :- !.
petta_check_argspec_form(['one-of', Vocab], Position, Term) :-
    !,
    (   atom(Vocab),
        petta_vocabulary_values(Vocab, _)
    ->  true
    ;   petta_declaration_refused(Term, Position,
                                  'a vocabulary declared before the kind that names it')
    ).
petta_check_argspec_form([optional, Spec], Position, Term) :-
    !,
    petta_check_argspec_form(Spec, Position, Term).
petta_check_argspec_form([rest, Spec], Position, Term) :-
    !,
    petta_check_argspec_form(Spec, Position, Term).
petta_check_argspec_form(_, Position, Term) :-
    petta_declaration_refused(Term, Position, 'an argspec').

petta_declaration_refused(Term, Position, Expected) :-
    throw(error(petta_declaration_malformed(Term, Position, Expected), none)).

%%%% Materialized shape-route dispatch %%%%
%
%(routed-by-shape Head [Key]) in the catalog makes (Head ...) declarations
%route by shape through metta.pl's one algorithm: specificity over adorned
%entries, coherence among the maximal ones. The materializer compiles the
%head's kind row into the exact petta_shape_fact/4 and
%petta_shape_declared/2 clauses the router dispatches on, one fact clause
%per stored arity with omitted trailing optionals padded to none, and one
%guard clause probing those arities, so consulting a route costs what the
%hand-written clauses cost, indexed clause dispatch, and the catalog pays
%at its own writes: every add or removal of a kind or routing row lands in
%the notes above and rebuilds that head's clauses from the rows then
%standing. The shipped handles, on-error and merge dispatch is built by
%this same walk from the presets below, which is what makes a third-party
%routed kind and a shipped one the same thing.
petta_materialize_routes :-
    forall(petta_routed_head(Head, _), petta_materialize_route(Head)).

petta_routed_head(Head, Key) :-
    petta_catalog_row(['routed-by-shape', Head|KeyArgs]),
    (   KeyArgs == []
    ->  Key = context
    ;   KeyArgs = [Key]
    ).

petta_materialize_route(Head) :-
    \+ atom(Head),
    !,
    petta_materialize_routes.
petta_materialize_route(Head) :-
    retractall(petta_shape_fact(Head, _, _, _)),
    retractall(petta_shape_declared(Head, _)),
    (   petta_routed_head(Head, Key),
        petta_kind_spec(Head, Spec),
        petta_route_shape(Key, Spec, PayloadSpecs)
    ->  forall(petta_payload_slice(PayloadSpecs, Stored, Payload),
               petta_assert_route_fact(Key, Head, Stored, Payload)),
        petta_assert_route_guard(Key, Head, PayloadSpecs)
    ;   true
    ).

%How a kind row reads as a route: a context-keyed route is (head ctx-symbol
%entry-pattern payload...), a global one is (head entry-pattern payload...),
%and the payload may not carry rest, whose open arity nothing could probe.
petta_route_shape(context, [symbol, pattern|PayloadSpecs], PayloadSpecs) :-
    \+ memberchk([rest, _], PayloadSpecs).
petta_route_shape(global, [pattern|PayloadSpecs], PayloadSpecs) :-
    \+ memberchk([rest, _], PayloadSpecs).

petta_check_route_fit(Key, Spec, Term) :-
    (   petta_route_shape(Key, Spec, _)
    ->  true
    ;   petta_declaration_refused(Term, 1,
            'a kind row the route can dispatch: (symbol pattern payload...) \c
             under the context key, (pattern payload...) under global, \c
             payload without rest')
    ).

%Stored and consumed payload pairs, one per legal arity: mandatory specs
%are always stored, and the first omitted trailing optional pads every
%remaining consumed position with none, which is the padding the handles
%consumers have always read for an entry that declared no determinism.
petta_payload_slice([], [], []).
petta_payload_slice([_Spec|Specs], [V|Stored], [V|Payload]) :-
    petta_payload_slice(Specs, Stored, Payload).
petta_payload_slice([[optional, _]|Specs], [], [none|Padding]) :-
    petta_payload_padding(Specs, Padding).

petta_payload_padding([], []).
petta_payload_padding([_|Specs], [none|Padding]) :-
    petta_payload_padding(Specs, Padding).

petta_assert_route_fact(context, Head, Stored, Payload) :-
    assertz((petta_shape_fact(Head, Ctx, Entry, Payload) :-
                 petta_contract_fact([Head, Ctx, Entry|Stored]))).
petta_assert_route_fact(global, Head, Stored, Payload) :-
    assertz((petta_shape_fact(Head, global, Entry, Payload) :-
                 petta_contract_fact([Head, Entry|Stored]))).

%The guard probes the smallest stored arity first, the common case (an
%entry declaring no trailing optionals), each probe deterministic the way
%the hand-written guards were.
petta_assert_route_guard(Key, Head, PayloadSpecs) :-
    findall(N,
            ( petta_payload_slice(PayloadSpecs, Stored, _),
              length(Stored, N) ),
            Ns),
    sort(0, @<, Ns, Arities),
    petta_route_probes(Key, Head, Module, Ctx, Arities, Probes),
    petta_probe_chain(Probes, Chain),
    assertz((petta_shape_declared(Head, Ctx) :-
                 petta_contract_storage(Module),
                 Chain)).

%A global route's guard leaves Ctx free on purpose: petta_shape_declared
%(merge, _) has always matched any context, the entries being keyed by
%query shape alone.
petta_route_probes(context, Head, Module, Ctx, Arities, Probes) :-
    maplist(petta_route_probe(Head, Module, Ctx), Arities, Probes).
petta_route_probes(global, Head, Module, _Ctx, Arities, Probes) :-
    maplist(petta_route_probe_global(Head, Module), Arities, Probes).

petta_route_probe(Head, Module, Ctx, N, Module:Goal) :-
    length(Vars, N),
    Goal =.. ['&petta', Head, Ctx, _Entry|Vars].
petta_route_probe_global(Head, Module, N, Module:Goal) :-
    length(Vars, N),
    Goal =.. ['&petta', Head, _Entry|Vars].

petta_probe_chain([Probe], (Probe -> true)) :- !.
petta_probe_chain([Probe|Probes], (Probe -> true ; Chain)) :-
    petta_probe_chain(Probes, Chain).

:- multifile prolog:error_message//1.
prolog:error_message(petta_declaration_malformed(Term, Position, Expected)) -->
    { Term = [Head|_],
      swrite(Term, TermText),
      (   is_list(Expected)
      ->  swrite(Expected, ExpectedText)
      ;   ExpectedText = Expected
      ) },
    [ 'the declaration ~w does not fit its declared kind: argument ~w \c
       expects ~w. Match (kind ~w $spec) in &petta to read the declared \c
       shape, or remove the kind row and re-declare it to widen the \c
       kind'-[TermText, Position, ExpectedText, Head] ].

%The shipped catalog, as data. Every row becomes an ordinary '&petta' atom
%when the directive below runs, matchable and removable like any other.
%Vocabularies come first; (kind kind ...) enters while no kind row exists
%to check it; every later row is validated by the self-description already
%in place, claims last so their kind row checks them. The value sets are
%exactly what the engine's consultation sites act on today, strict by
%design: a value no site acts on would pass the checker only to sit
%silently inert, the failure mode this catalog exists to make loud.
petta_catalog_preset([vocabulary, fidelity, 'Exact', 'Partial', 'Sound', 'Refuse']).
petta_catalog_preset([vocabulary, determinism, det, semidet, nondet]).
petta_catalog_preset([vocabulary, 'on-error-mode', keep, empty, abort]).
petta_catalog_preset([vocabulary, 'answer-policy', depth, fair, 'best-first']).
petta_catalog_preset([vocabulary, semiring, bool, bag, set, ranked, prob, prov]).
petta_catalog_preset([vocabulary, 'source-kind', linear, repeated, peek]).
petta_catalog_preset([vocabulary, world, 'closed-world', 'open-world']).
petta_catalog_preset([vocabulary, atomicity,
                      transactional, 'atomic-single', 'best-effort']).
petta_catalog_preset([vocabulary, 'cache-mode', unchecked]).
petta_catalog_preset([vocabulary, 'effect-class', immutable]).
petta_catalog_preset([vocabulary, 'op-kind', det, many, raw_det, raw_many]).
petta_catalog_preset([vocabulary, 'subscription-edge', add, remove, both]).
petta_catalog_preset([vocabulary, volatility, volatile, stable, immutable]).
petta_catalog_preset([vocabulary, 'route-key', context, global]).
petta_catalog_preset([kind, kind, symbol, [rest, term]]).
petta_catalog_preset([kind, 'routed-by-shape', symbol,
                      [optional, ['one-of', 'route-key']]]).
petta_catalog_preset([kind, vocabulary, symbol, [rest, symbol]]).
petta_catalog_preset([kind, claim, symbol, symbol, [rest, symbol]]).
petta_catalog_preset([kind, handles, symbol, pattern, ['one-of', fidelity],
                      [optional, ['one-of', determinism]]]).
petta_catalog_preset([kind, 'on-error', symbol, pattern,
                      ['one-of', 'on-error-mode']]).
petta_catalog_preset([kind, merge, pattern, ['one-of', 'answer-policy']]).
petta_catalog_preset([kind, annotations, symbol, ['one-of', semiring]]).
petta_catalog_preset([kind, source, symbol, ['one-of', 'source-kind']]).
petta_catalog_preset([kind, context, symbol, ['one-of', world]]).
petta_catalog_preset([kind, admits, symbol, term]).
petta_catalog_preset([kind, capacity, symbol, integer]).
petta_catalog_preset([kind, writes, symbol, ['one-of', atomicity]]).
petta_catalog_preset([kind, emits, symbol, ['one-of', 'answer-policy']]).
petta_catalog_preset([kind, cache, symbol, ['one-of', 'cache-mode']]).
petta_catalog_preset([kind, effect, symbol, ['one-of', 'effect-class']]).
petta_catalog_preset([kind, inverse, symbol]).
petta_catalog_preset([kind, op, symbol, integer, ['one-of', 'op-kind']]).
petta_catalog_preset([kind, on, symbol, pattern, term]).
petta_catalog_preset([kind, tabled, symbol, symbol, integer]).
petta_catalog_preset([kind, defined, symbol, symbol]).
petta_catalog_preset([kind, subscription, symbol, pattern,
                      ['one-of', 'subscription-edge']]).
petta_catalog_preset(['routed-by-shape', handles]).
petta_catalog_preset(['routed-by-shape', 'on-error']).
petta_catalog_preset(['routed-by-shape', merge, global]).
petta_catalog_preset([claim, semiring, ranked, ordered]).
petta_catalog_preset([claim, semiring, prob, ordered]).

%Presets land only where their subject has no row yet, which makes the
%directive reconsult-idempotent (a re-consulted engine meets its own rows
%and the duplicate refusal must not fire) and keeps a program's own
%remove-then-redeclare widening standing across an engine reload.
petta_catalog_preset_missing([kind, Head|_]) :-
    !,
    \+ petta_kind_spec(Head, _).
petta_catalog_preset_missing([vocabulary, Name|_]) :-
    !,
    \+ petta_vocabulary_values(Name, _).
petta_catalog_preset_missing(['routed-by-shape', Head|_]) :-
    !,
    \+ petta_routed_head(Head, _).
petta_catalog_preset_missing(Atom) :-
    \+ petta_catalog_row(Atom).

:- forall(( petta_catalog_preset(Atom), petta_catalog_preset_missing(Atom) ),
          add_sexp('&petta', Atom, _)).

%The inverse of add_sexp_in/4, written here beside it for the same reason
%metta_module_space/2 is written beside space_module/2: the mapping is
%injective, so the inverse is a function rather than a search, and keeping the
%pair together is what stops one of them drifting.
%
%The caller is a RELOAD. A source load records a clause reference for
%everything it asserts, atoms and compiled clauses and registrations alike,
%and taking a file's atoms back out has to go through metta_remove_atom/3,
%which takes an atom rather than a reference. So this is how the reload tells
%an atom's reference from the rest: it FAILS on any reference that is not a
%stored atom's, and on an erased one, and it answers the SPACE as well as the
%atom because a file's !(add-atom &elsewhere ...) is recorded by the load that
%ran it and belongs back in &elsewhere rather than in the space being reloaded
%[tested: spaces_storage_modules:a_stored_atoms_reference_decodes_to_its_atom].
%
%The module comes from clause_property/2 and not from the head clause/3 hands
%back, because that head is qualified only when the clause's module differs
%from the CALLER's: read from the engine it arrives bare, so stripping it named
%the engine's own module and every atom looked like something else
%[measured 2026-08-19: the withdrawal reported 0 atoms while removing them].
stored_atom_of_ref(Ref, Space, Atom) :-
    catch(clause_property(Ref, predicate(Module:Name/_)), _, fail),
    native_storage_module(Space, Module),
    catch(clause(Stored, true, Ref), _, fail),
    strip_module(Stored, _, Head),
    (   Name == '$petta_native_scalar'
    ->  Head = '$petta_native_scalar'(Atom)
    ;   Name == Space,
        Head =.. [_, Rel|Args],
        Atom = [Rel|Args]
    ).

%The clause a native space stores an atom AS. This is the definition of that
%shape, and lib_import.pl's static-import! writes exactly this to a file so a
%large data file can be qcompiled once instead of parsed every run. The two
%used to disagree and it was invisible: the converter wrote '&self'(fact,a,1)
%into USER while native atoms live in the storage module '$petta_atoms:&self',
%so a static import loaded clauses nothing could read and reported success
%[tested: native_storage_shapes_agree,
%import_facts_land_where_the_space_reads_them].
native_atom_clause(Space, [Rel|Args], Term) :- !, Term =.. [Space, Rel | Args].
native_atom_clause(_, Atom, '$petta_native_scalar'(Atom)).

%Remove ONE atom that unifies with the requested value. Expressions and
%scalars live in different predicates, so neither erases the other.
remove_sexp(Space, Atom) :- remove_sexp(Space, Atom, _).

%The same removal, answering whether anything WAS there.
%
%ONE occurrence, because removal is multiset SUBTRACTION. This used to take
%every occurrence, and its stated reason was an invalid inference: "a MeTTa
%space is a multiset unless something forbids it, SO removal takes EVERY
%occurrence". The premise argues for the opposite conclusion, and the tree it
%described was a multiset on ADD and a set on REMOVE, so three adds of (dup 1)
%gave count 3 and one removal gave count 0. The arbiter reads the premise the
%other way: "remove-atom must behave as multiset subtraction on the
%reader-visible view of &self", and its own model "removes the first exact
%occurrence and returns unit"
%[source: LeaTTa MettaHyperonFullTests/Properties.lean:107,
%MettaHyperonFull/Minimal/Stdlib.lean:2223, and wiki/Mechanization-Ledger.md
%row "Represented removal consumes the first exact occurrence", which pins
%(one two one) minus (one) as (two one) executably].
%
%This engine had already decided it everywhere else. The seam declares
%metta_foreign_remove/3 as "remove one" (EXTENDING.md), and drop_fun_meta/4
%takes "one variant-equivalent retained equation" at a time
%(src/translator.pl:115). The native store was the one holdout.
%
%retract/1 under double negation, which makes the answer and the removal one
%lookup instead of two. retractall/1 succeeds whether or not it matched, so
%the answer had to come from a separate clause/2 probe in front of it, and
%that pair was also a check-then-act race: retract/1 reports what it did, and
%SWI adjusts each thread's entry generation so "if multiple threads use
%once(retract(Term)), no two threads will retract the same clause". Exactly
%ONE clause goes because the double negation takes retract/1's first solution
%and never backtracks into it, and it has to: under the logical update view
%"retract/1 succeeds for all clauses that match Term when the predicate was
%called", so a retract left open on backtracking would drain the lot
%[source: SWI-Prolog 10.1 Reference Manual, retract/1].
%
%Double negation rather than a copy because the bindings must NOT escape.
%That is the engine's own rule for the compiled half, "retraction must not
%bind the caller's variables" (src/translator.pl:115), and the language's:
%remove-atom answers unit, so (remove-atom &self (pair $x)) is a request, not
%a query, and $x is no more bound afterwards than before. It is also the
%cheaper of the two isolations. Measured 2026-08-19 over 20,000 removals, min
%of three: 1.0001 inferences per removal against the probe-and-retractall
%shape's 2.0001, and against 2.0001 for the copy_term spelling
%[measured 2026-08-19, ai-tmp/spaces-p1/rmcost.pl].
%
%Answering truthfully at all is worth it because the engine already disagreed
%with ITSELF. Removing an EQUATION answers false when nothing matched, forty
%lines up, and a foreign provider fills metta_foreign_remove/3's Removed
%argument honestly, so a MeTTa program branching on (remove-atom $space $atom)
%was correct against two of the three and wrong against the third, with
%nothing in its text saying which it would get
%[tested: spaces_removal_answers_unit_for_success_and_an_error_for_absence,
%test_remove_atom_removes_one_occurrence_not_all].
remove_sexp('&petta', [Rel|Args], Removed) :- !,
    (   native_storage_module_ready('&petta', Module)
    ->  Term =.. ['&petta', Rel|Args],
        native_retract_one(Module:Term, Removed),
        (   Removed == true
        ->  petta_catalog_note_removed([Rel|Args])
        ;   true
        )
    ;   Removed = false
    ).
remove_sexp(Space, [Rel|Args], Removed) :- !,
    (   native_storage_module_ready(Space, Module)
    ->  Term =.. [Space, Rel | Args],
        native_retract_one(Module:Term, Removed)
    ;   Removed = false
    ).
remove_sexp(Space, Atom, Removed) :-
    (   native_storage_module_ready(Space, Module)
    ->  native_retract_one(Module:'$petta_native_scalar'(Atom), Removed)
    ;   Removed = false
    ).

native_retract_one(Head, Removed) :-
    ( \+ \+ retract(Head) -> Removed = true ; Removed = false ).

%Which module a space's compiled clauses live in. EVERY space gets one, &self
%included, and the mapping is the storage one with a different prefix: total,
%injective, and with no clause for a special case.
%
%&self used to compile into the module the ENGINE itself resolves in, and an
%equation asserted there does not shadow a predicate of that name, it REPLACES
%it for the rest of the process. Two shipped examples did exactly that
%[measured 2026-08-19: examples/functions/invertpeanoplus.metta took
%user:plus/3 from imported_from(system) to a local definition, after which
%plus(1,2,X) failed instead of answering 3; examples/libraries/
%minimal_metta.metta did the same to user:rule/3]. Every gate stayed green
%through both, because nothing that ran afterwards in those processes called
%either predicate. tests/prolog/engine_integrity.pl is the check that would
%not have let it stand, and it is a GATE at zero findings.
%
%A goal unresolved in a space's module still reaches the engine, the builtins
%and the libraries through the base chain below, so nothing has to be
%published for a compiled clause to run
%[tested: spaces_execution_modules].
%DETERMINISTIC, and the if-then-else is what makes it so. Asserting the known
%spaces as facts of space_module/2 itself in front of the rule reads one
%inference cheaper, and costs far more than it saves: the rule's head unifies
%with every space too, so a known one succeeds holding a CHOICE POINT, and
%backtracking into it re-enters the rule and takes the mutex. Measured
%2026-08-19 on that shape: eval-arith 172,009 -> 237,980 inferences, op-raw
%178,011 -> 253,976, op-encoded 214,011 -> 289,969.
space_module(Space, Module) :-
    (   metta_exec_module_known(Space, Module)
    ->  true
    ;   metta_exec_module_prefix(Prefix),
        atom_concat(Prefix, Space, Module),
        with_mutex('$petta_metta_exec',
                   ensure_metta_exec_module_locked(Space, Module))
    ).

:- dynamic metta_exec_module_known/2.

%The chain, and why each link is where it is.
%
%  system  ->  the ENGINE's module  ->  '$petta_exec:&self'  ->  every other
%                                                                space
%
%&self's module inherits the engine's, so every builtin, every library
%predicate and every function imported from Prolog still resolves from a
%compiled MeTTa clause. Every other space inherits &self's, which is the
%sharing rule the engine already states for functions and types ("&self is the
%shared space", fun_here_in/2) and which named spaces used to get by accident:
%&self WAS `user`, and SWI gives an implicitly created module the base `user`.
%
%The base is SET rather than left to the name. SWI gives an implicitly created
%module whose name starts with `$` the base `system` and every other name the
%base `user`, and a module created by a :- module(...) FILE gets `user`
%whatever its name; neither rule is stated in the manual, and the first one
%alone makes '$petta_exec:&self' unable to see the engine at all
%[measured 2026-08-19: '$petta_exec:&self':'add-atom'/3 raised
%existence_error on boot until the base was set explicitly]
%[tested: spaces_execution_modules:the_chain_is_engine_then_self_then_space].
metta_exec_module_base(Space, Base) :-
    (   Space == '&self'
    ->  petta_engine_module(Base)
    ;   space_module('&self', Base)
    ).

%set_module/1 is idempotent and works on a module that already holds clauses
%[measured 2026-08-19: import_module went [user] -> ['$petta_exec:&self'] in
%place and the module's own predicates still answered], so recovering a cache
%fact a rolled-back transaction erased costs one redundant set and no repair,
%the same shape ensure_native_storage_module_locked/2 uses above.
%asserta, so the facts stay in front of the rule above and a known space never
%reaches it. Re-entered when a rolled-back transaction erased the fact and left
%the module based: set_module/1 is idempotent, so the repair is one redundant
%set rather than a special case, which is the shape
%ensure_native_storage_module_locked/2 uses.
ensure_metta_exec_module_locked(Space, Module) :-
    metta_exec_module_known(Space, Module), !.
ensure_metta_exec_module_locked(Space, Module) :-
    metta_exec_module_base(Space, Base),
    set_module(Module:base(Base)),
    assertz(metta_exec_module_known(Space, Module)),
    protect_engine_emitted(Module).

%Bind the engine's own emitted goals into this module so a MeTTa equation
%cannot take one over. See metta_engine_emitted/1 (src/translator.pl) for what
%that means and why an import rather than a guard.
%
%The export half is what keeps it quiet: import/1 warns when the source module
%does not export the name, and the engine's module has no export list at all.
%current_predicate/1 guards the order: this runs for &self's module at LOAD,
%before src/duals.pl is consulted, so the one predicate that file emits is not
%there yet and the initialization below sweeps it in afterwards.
protect_engine_emitted(Module) :-
    petta_engine_module(Engine),
    forall(( metta_engine_emitted(PI), current_predicate(Engine:PI) ),
           ( Engine:export(PI), Module:import(Engine:PI) )).

%Every module that already exists, which at boot is &self's. Called from
%src/metta.pl's own initialization rather than from one here, and BEFORE the
%prelude compiles: an initialization/1 goal runs after the file it appears in
%finishes, so one here would run before src/metta.pl had defined half the
%names above, and initialization goals do not reliably order against each
%other either [source: src/metta.pl's own note on that].
protect_metta_exec_modules :-
    forall(metta_exec_module_known(_, Module), protect_engine_emitted(Module)).

%The inverse of space_module/2. It used to be written out by hand in four
%places, three of them outside this file, each as
%`Module == user -> Space = '&self' ; Space = Module`
%[source: ai-phase11-module-survey.md section 1.3]. One prefix strip replaces
%all four, and the mapping being injective is what makes the inverse a
%function rather than a search. It FAILS on a module that is not a space's,
%because every caller has one in hand and a silent pass-through would answer a
%module name where a space name was asked for
%[tested: spaces_execution_modules:the_module_to_space_map_is_the_inverse].
metta_module_space(Module, Space) :-
    metta_exec_module_prefix(Prefix),
    atom_concat(Prefix, Space, Module).

%&self's execution module exists from load, the way its storage module does,
%so nothing has to create it on a first write and metta_self_module/1
%(src/metta.pl) names a module that is already based.
:- space_module('&self', _).

%Whether anything still holds a clause for a function, which decides whether
%removing an equation forgets the NAME as well. Two sources, and `user` used to
%stand for both of them at once: a space's own module, and the ENGINE's, since
%a builtin goes on meaning the builtin after a space's equation for it is
%removed.
%
%compiled_function_name/2 rather than the written name, which is the same fix
%module_owns_function/2 below already carries: `get-type` compiles to
%get_type_rule/2, so asking for a predicate called `get-type` found the
%ENGINE's get-type/2 and answered "still defined" for every space and every
%state of the rules. Removing one of two scoped get-type rules then wiped
%fun_in/2 for the name and the surviving rule stopped answering
%[tested: spaces_type_extensions:removing_one_rule_keeps_the_other_visible].
%number_of_clauses/1 before clause/3, which is the guard tracer.pl already
%carries and for the same reason: clause/3 REFUSES a predicate it cannot show,
%raising permission_error(access, private_procedure, _) rather than failing,
%and the engine's module holds plenty of those. Removing an equation for any
%system-builtin name reached one and raised out of remove-atom
%[measured 2026-08-19: with_output_to/2]. The property is true for exactly the
%predicates clause/3 accepts [source: src/tracer.pl, metta_trace_target/1
%measured 2026-08-16].
%A BUILTIN is defined by the engine and by no equation, so no removal can
%undefine it. Without this, a space that extended an engine operation by
%writing an equation for its name took the ENGINE's operation with it when the
%equation went: the compiled-clause probe below is the only thing that was
%asked, a builtin has no compiled clause of that shape, so `fun/1` and the
%name-wide registers were retracted and `!(get-type 1)` answered
%`(get-type 1)` unreduced for the rest of the process. Removing an equation
%for `match`, `+` or any other builtin name did the same
%[tested: builtin_survives_equation_removal].
function_still_defined(F) :- builtin_fun(F), !.
function_still_defined(F) :- compiled_function_name(F, Predicate),
                             ( fun_in(Module, F) ; petta_engine_module(Module) ),
                             current_predicate(Module:Predicate/Arity),
                             functor(Head, Predicate, Arity),
                             predicate_property(Module:Head, number_of_clauses(_)),
                             clause(Module:Head, _, _),
                             !.

%Whether this module itself holds a clause for a function. Inherited clauses
%do not count: clause/3 sees user's clauses through module inheritance, and
%counting those would keep a module's claim alive on another space's strength.
module_owns_function(Module, F) :- compiled_function_name(F, Predicate),
                                   current_predicate(Module:Predicate/Arity),
                                   functor(Head, Predicate, Arity),
                                   predicate_property(Module:Head,
                                                      number_of_clauses(_)),
                                   clause(Module:Head, _, Ref),
                                   clause_property(Ref, module(Module)),
                                   !.

%The UNIT value, not true. `add-atom` is typed `(-> spaceType Atom (->))` and
%`(->)` IS the unit type, which the language also says in prose: "bind! returns
%the unit value () similar to println! or add-atom"
%[source: the language's Working with spaces].
%
%This reverses a deliberate earlier translation, recorded in
%ai-todo-fast-libraries.md F11.3 as "HE's unit result `(->)` is PeTTa's `Bool`,
%because every one of those operations answers `true`". That reasoning had the
%direction backwards: it read the type off the implementation instead of
%correcting the implementation to the type. The engine was already inconsistent
%with itself, `trace!` answering `()` beside these answering `true`, and the
%arbiter's spaces corpus disagreed on every file
%[tested: an_effectful_operation_answers_unit].
%The write itself decides whether the first argument is a space: a name that is
%not one reaches no storage module, so nothing is written and this refuses.
%Asking BEFORE the write cost an inference on every add
%[measured 2026-08-20: register-op +200], and asking after costs nothing
%because the failure branch runs only when the write did not happen. A write
%that failed for its own reasons, a foreign provider refusing one, still fails
%without an answer, which is what it did before.
'add-atom'(Space, Term, Result) :-
    (   atom(Space), metta_add_atom(Space, Term, _)
    ->  Result = []
    ;   petta_space_name(Space)
    ->  fail
    ;   space_argument_error('add-atom', [Space, Term], Result)
    ).

%Adding an atom is two independent decisions: WHERE it is stored, which is a
%property of the space, and WHAT the engine must do because of what the atom
%MEANS, which is a property of the atom. This predicate dispatched on storage
%first, mixing them, and three defects came out of that one shape:
%
%  - a (: f T) added to a FOREIGN space never recompiled f's call sites,
%    because the foreign clause cut before the declaration clause could run.
%    The same program answered ((+ 1 2)) in a native named space and (3) in a
%    foreign one [measured 2026-08-16].
%  - metta_add_atoms/2 had to re-derive which atoms carry work and looked only
%    for equations, so a BATCHED declaration skipped the recompile the same
%    atom performs alone: m.add(decl) answered (+ 1 2) and m.add(decl, other)
%    answered 3 [measured 2026-08-16].
%  - the Python shim re-derived it a third time and routed MORK's batch around
%    this predicate entirely, so an equation added to a space that holds rules
%    was stored inert whenever it arrived with any other atom
%    [measured 2026-08-16].
%
%So MEANING is decided first and storage second, which is the whole of the fix.
%The order is the fix: a foreign space's declaration now reaches the clause that
%recompiles, because nothing cuts in front of it any more.
%
%The tests stay in the clause HEADS rather than moving to a classifier the batch
%path could also call, and that is measured rather than tidy. This is the
%hottest write path in the engine, and routing it through
%atom_effect/2 + add_with_effect/3 cost three inferences of every twelve per
%atom, 25%, which the save-load benchmarks caught at once [measured 2026-08-16:
%12.0012 to 15.0012 inferences per add over 20,000 adds]. atoms_store_only/1
%below repeats these two tests for the batch path, and the two are held together
%by a differential rather than by sharing code: every shape is added alone and
%in a batch and the resulting state compared
%[tested: spaces_batch_is_only_a_transport].
metta_add_atom(Space, Term, true) :- Term = [=, [FAtom|W], _], !,
                                     must_be(atom, FAtom),
                                     add_equation(Space, Term, FAtom, W).
%A type declaration decides how a call site compiles, most sharply for an Atom
%parameter, which is what makes a control form possible: (: f (-> Atom
%%Undefined%)) is the difference between the argument arriving evaluated and
%arriving as written. A call site compiled before the declaration landed kept
%evaluating the argument for ever, so the same call written two ways in one
%program behaved differently and nothing said why. The engine already knows how
%to recompile what a change made stale; the declaration route simply never told
%it [tested: a_late_type_declaration_repairs_its_call_sites].
metta_add_atom(Space, Term, true) :- Term = [':', FAtom, _], atom(FAtom),
                                     fun(FAtom), !,
                                     %A declaration written into &self replaces the
                                     %prelude's for the same name, the user-wins rule
                                     %evict_prelude_definition/1 documents; the
                                     %recompile below then re-reads call sites under
                                     %the user's masking.
                                     (   Space == '&self'
                                     ->  retract_prelude_declarations(FAtom)
                                     ;   true
                                     ),
                                     store_atom(Space, Term),
                                     recompile_definitions_mentioning(FAtom),
                                     space_module(Space, DeclModule),
                                     function_changed(DeclModule, FAtom).
metta_add_atom(Space, Term, true) :- metta_foreign_space(Space), !,
                                     foreign_write(Space, add,
                                                   metta_foreign_add(Space, Term)).
metta_add_atom(Space, Term, true) :- add_sexp(Space, Term, Ref),
                                     record_source_assertion(Ref).

%Whether every atom in a batch stores and does nothing else, which is the only
%kind a bulk crossing may carry. It repeats metta_add_atom/3's first two clause
%heads, and they are repeated rather than shared for the reason given there.
%
%Written as clause heads and not as a test called per atom, which is measured:
%head unification costs no inference where a call costs one, and over a whole
%batch that is the difference between one and two per atom [measured 2026-08-16:
%8.00 back to 7.00 inferences per atom over 20,000]. Cut-then-fail so the scan
%stops at the first atom that carries work.
atoms_store_only([]).
atoms_store_only([[=|_]|_]) :- !, fail.
atoms_store_only([[':', FAtom, _]|_]) :- atom(FAtom), fun(FAtom), !, fail.
atoms_store_only([_|Terms]) :- atoms_store_only(Terms).

%Where an atom goes. A foreign space's provider owns its storage entirely; a
%native space's storage is the Prolog database.
store_atom(Space, Term) :- metta_foreign_space(Space), !,
                           foreign_write(Space, add,
                                         metta_foreign_add(Space, Term)).
store_atom(Space, Term) :- add_sexp(Space, Term, Ref),
                           record_source_assertion(Ref).

%An equation is the one atom whose storage and meaning cannot be separated, so
%they are not: it compiles inside the transaction that stores it, wherever it is
%stored. Only the storage step differs between a native space and a foreign one.
%
%An equation in a foreign space used to be a silent lie: accepted, stored, and
%inert, so (only-foreign 21) answered itself where the identical shape in a
%native named space answered 42. In MeTTa a space is BOTH a data source and
%where the program lives, so accepting a rule that can never fire is the engine
%agreeing to something it will not do. A provider that holds rules declares the
%`rules` capability; one that does not is refused here, where the author can
%still act on it, rather than at the call that quietly answers itself much later
%[tested: adding_a_rule_to_a_ruleless_foreign_space_is_refused].
%
%It goes through the SAME compiler as a native equation, and the first attempt
%at this did not: it asserted one bridge clause per function that matched the
%space for (= (f Args) Body) at call time and reduced whatever came back.
%
%That is the naive reading of evaluation, and the language documents exactly why
%it falls short. Evaluating (only-a A) "can be thought of as execution of query
%(match &self (= (only-a A) $result) $result)", and then: "There is one
%difference. match produces the empty result in the second case, while the
%interpreter keeps this expression unreduced. The interpreter is performing some
%additional processing on top of such equality queries"
%[source: metta-lang.dev/docs/learn, Functions and unification].
%
%Three of those differences were live here. A body is evaluated FURTHER, so
%(= (bnest) (+ 1 (* 2 3))) raised "+: number expected, found (* 2 3)"; a
%bare-variable body must NOT be evaluated, so an Atom parameter came back
%reduced; and (if ...) evaluates only the branch it takes, so (= (loop) (loop))
%under an if would not have terminated. Every one is a rule the translator
%already implements [source: metta-lang.dev/docs/learn, Basic evaluation and
%Recursion and control].
%
%What the seam gives up by compiling at add time is an equation that appears in
%the space by some other door, MORK's own loader or an mm2-exec write: it is
%stored and inert, because nothing told the engine. That is the honest edge and
%it is narrower than a second evaluator that is wrong on every program above.
%A specialization is DERIVED: the specializer wrote it from this module's own
%equations and owns the name. An equation arriving for a derived name that is
%an ALPHA-DUPLICATE of one already stored carries nothing, and storing it a
%second time is what made a space stop reproducing itself: MeTTa.copy()
%enumerates a space and re-adds every atom into a fresh one, the clone
%re-derived the specialization while compiling the equation that triggered
%it, and the copied atom then landed on top, so a four-atom space cloned to
%five and answered its query twice [measured 2026-08-19]. The guard used to
%swallow by NAME alone, which was right while clones re-derived; with
%adoption the copied equations ARE the derived ones, and the name-only
%swallow ate every clause of a copied specialization that arrived after its
%sibling had been adopted, so a two-clause specialization cloned to one
%[measured 2026-08-20]. Only the true duplicate is swallowed now, and the
%probe runs only on derived-name adds, which are rare by construction
%[tested: a_copied_space_adopts_its_specializations_instead_of_duplicating].
add_equation(Space, Term, FAtom, _) :-
    space_module(Space, Module),
    ho_specialization(Module, _, FAtom),
    copy_term(Term, Probe),
    get_native_atom(Space, Stored),
    Stored = [=, [FAtom|_], _],
    Stored =@= Probe,
    !.
add_equation(Space, Term, FAtom, W) :-
    metta_foreign_space(Space), !,
    refuse_ruleless_equation(Space, Term),
    space_module(Space, Module),
    transaction(add_function_atom(provider, Space, Module, Term, FAtom, W)).
add_equation(Space, Term, FAtom, W) :-
    space_module(Space, Module),
    ensure_native_storage_module(Space, Storage),
    transaction(add_function_atom(Storage, Space, Module, Term, FAtom, W)).

%Where the equation itself goes. `provider` is a foreign space, whose provider
%owns its storage; anything else is a native storage module. transaction/1 wraps
%the compile either way, and rolls back only the Prolog side of it: a provider's
%write is outside the database and stays written if the translation then fails.
store_equation(provider, Space, Term) :- !, store_atom(Space, Term).
store_equation(Storage, Space, Term) :- add_sexp_in(Storage, Space, Term, Ref),
                                        record_source_assertion(Ref).

%Everything a change to FAtom leaves stale, in one place because three callers
%need exactly it: a new equation, a new declaration, and a removed equation.
%
%The MODULE is threaded rather than read, because a change hook fires outside
%the compile door's own module switch and the invalidation behind it is scoped
%to one space now: reading the ambient module here would have made a write in
%one space invalidate whichever space happened to be in force.
function_changed(Module, FAtom) :- forall(metta_on_function_changed(FAtom), true),
                                   invalidate_specializations(Module, FAtom).

%The caller has classified the atom as an equation, so the shape test that used
%to be here is gone with it.
refuse_ruleless_equation(Space, Term) :-
    (   foreign_provides(Space, rules)
    ->  true
    ;   throw(error(petta_foreign_space_holds_no_rules(Space, Term),
                    context('add-atom'/3, 'the equation would never fire')))
    ).

%A native batch containing no equations and no observer for this space can
%resolve its storage module once. Equation batches and observed writes keep
%using add-atom/3 so registration and per-atom events retain their ordinary
%behavior.
metta_add_hooks_idle(_) :-
    \+ metta_atom_hook_clause(added, _), !.
metta_add_hooks_idle(Space) :-
    metta_host_add_hooks_idle(Space).

%%%% The foreign seam's failure contract %%%%
%
%A declared provider that does not answer an operation is the registrant's
%bug, and it is reported with the space and the operation named. It is never
%read as "there is nothing there". Four of the five operations used to fail
%silently: a write vanished, a removal reported nothing removed, and a match
%answered the empty set while the space demonstrably held matching atoms.
%Only clear said what happened, and it said it from the Python bridge.
%
%The Python half of the same seam has always done this, refusing with the
%provider class and the operation named, and it is the half a library author
%is told to port INTO Prolog for speed
%[tested: spaces_foreign_contract].
%A space that declares NOTHING provides everything, which is what every
%provider written before the declaration existed assumed.
%
%THE TRAP, and it is worth knowing before you extend the vocabulary: the
%default stops the moment this space has ANY solution. Declaring one
%capability is declaring the complete set, so a provider adding a sixth to the
%five silently loses the five it did not restate. Python providers do not have
%to think about it, because foreign.py projects the whole set at registration
%from the protocols the provider implements
%[tested: test_a_python_providers_capabilities_reach_the_engine,
%a_partial_declaration_declares_the_whole_set].
foreign_provides(Space, Capability) :-
    (   metta_foreign_capability(Space, _)
    ->  metta_foreign_capability(Space, Capability)
    ;   true
    ).

%A capability the space does not provide. The provider gets to say why, if it
%has words for it: metta_foreign_refuse/2 raises, and "does not implement add"
%reads differently from "declines this add request", which is a distinction the
%Python half already draws and this one could not.
%
%The hook is expected to throw. Reaching the throw below means it did not,
%which is the engine and the provider disagreeing about what is provided.
refuse_absent_capability(Space, Capability) :-
    (   foreign_provides(Space, Capability)
    ->  true
    ;   metta_foreign_refuse(Space, Capability)
    ->  throw(error(permission_error(Capability, foreign_space, Space),
                    context(foreign_write/3,
                            'the provider declined this operation and did not \c
                             say why')))
    ;   throw(error(permission_error(Capability, foreign_space, Space),
                    context(foreign_write/3,
                            'the provider does not declare this operation')))
    ).

%A write either happened or it did not, so failure here is unambiguous and is
%an error. A read that finds nothing is an ordinary empty answer, so reads do
%not go through this.
:- meta_predicate foreign_write(+, +, 0).
foreign_write(Space, Capability, Goal) :-
    refuse_absent_capability(Space, Capability),
    %Inside a transaction the write's fate follows the declared
    %atomicity: a transactional provider enlists (one begin per
    %outermost transaction) and is committed or rolled back with it,
    %best-effort is the author's declared acceptance of a write that
    %survives a rollback, and anything else is refused loudly, because
    %a foreign write silently surviving a rolled-back transaction was
    %the wrong answer this replaces.
    (   current_transaction(_),
        petta_in_user_transaction
    ->  petta_writes(Space, Atomicity),
        (   Atomicity == transactional
        ->  petta_enlist_foreign(Space)
        ;   Atomicity == 'best-effort'
        ->  true
        ;   throw(error(petta_transaction_unsupported(Space, Atomicity),
                        none))
        )
    ;   true
    ),
    (   call(Goal)
    ->  true
    ;   throw(error(petta_foreign_operation_failed(Space, Capability),
                    context(foreign_write/3,
                            'the provider refused the write without saying why')))
    ).

%A batch is a TRANSPORT optimisation and never a semantic one: what the engine
%does for an atom on its own it must still do when the atoms arrive together.
%So only atoms that store and nothing more take a bulk crossing, and
%atom_stores_only/1 decides that rather than this predicate re-deriving it,
%which is how a batched type declaration came to skip its recompile.
%[prior art: a multi-row SQL INSERT still fires per-row triggers, JDBC's
%executeBatch runs the same statements, and Redis pipelining changes round
%trips and never commands.]
metta_add_atoms(_, []) :- !.
metta_add_atoms(Space, Terms) :-
    atoms_store_only(Terms),
    add_atoms_in_one_crossing(Space, Terms), !.
metta_add_atoms(Space, Terms) :-
    forall(member(Term, Terms), 'add-atom'(Space, Term, _)).

%A provider's own batch crossing when it has one, and the native store's
%otherwise. A provider without metta_foreign_add_many/2 fails here and gets one
%metta_foreign_add/2 per atom, which is what every provider written before this
%gets. The native path writes behind the write wrapper's back, so it is
%available only while no observer is installed; a provider's own crossing owns
%the write hooks exactly as its per-atom add does.
add_atoms_in_one_crossing(Space, Terms) :-
    metta_foreign_space(Space), !,
    refuse_absent_capability(Space, add),
    metta_foreign_add_many(Space, Terms).
add_atoms_in_one_crossing(Space, Terms) :-
    metta_add_hooks_idle(Space),
    ensure_native_storage_module(Space, Storage),
    %The bulk door checks and notes contract subjects exactly as the
    %per-atom door does, once per batch head test rather than per space
    %test per atom; the whole batch is checked before any of it lands.
    (   Space == '&petta'
    ->  forall(member(Decl, Terms),
               (   petta_declaration_check(Decl),
                   petta_note_ctx_declared(Decl)
               ))
    ;   true
    ),
    forall(member(Term, Terms),
           ( add_sexp_in(Storage, Space, Term, Ref),
             record_source_assertion(Ref) )),
    (   Space == '&petta'
    ->  forall(member(Term, Terms), petta_catalog_note_added(Term))
    ;   true
    ).

%Compile and register a dynamic equation as one database transaction. A
%translation or change-hook error therefore leaves no stored atom, function
%marker, arity, meta-clause, or executable clause behind.
%The one equation-compile spine: prelude eviction (user-wins), function
%registration, translation, clause assertion, provenance records, and the
%COMPLETE change notification. Three doors used to carry this separately,
%this file's add_function_atom and filereader.pl's two process_form
%clauses, so a cross-cutting rule had to be hooked one door at a time
%(the prelude eviction was the precedent), and one rule HAD drifted: the
%loader doors notified metta_on_function_changed but never
%invalidate_specializations, so an equation added by a string run or a
%compile-mode load left a prior specialization of the same name
%answering stale clauses. One door means the next such rule lands once
%[tested specializer:string_run_equation_invalidates_specializations].
compile_metta_equation(Module, Term, Clause, Ref) :-
    Term = [=, [F|_], _],
    (   metta_self_module(Module) -> evict_prelude_definition(F) ; true ),
    register_fun_in(Module, F),
    %Stale specializations go FIRST, before this body compiles. They are
    %clones of the PREVIOUS definition, and that is the whole content of
    %the claim; a clone this compilation creates for its own recursive
    %call belongs to the NEW definition and must survive. Invalidating
    %afterwards abolished exactly those clones while the clause naming
    %them stood, so (= (f $g) (... (f (+ 2)) ...)) compiled a generic
    %clause calling an empty predicate: the direct call answered through
    %its own specialization and a call that reached the generic clause,
    %(let $h (+ 1) (f $h)), silently answered NOTHING. Found by the
    %verify-specializations differential over examples/
    %[tested specializer:a_recursive_specialization_survives_its_compile].
    invalidate_specializations(Module, F),
    once(with_metta_module(Module, translate_clause(Term, Clause))),
    assert_function_clause(Module, Clause, Ref),
    record_source_assertion(Ref),
    record_translated_from(Ref, Term, SourceRef),
    record_source_assertion(SourceRef),
    %The dependent-recompile hooks run AFTER the clause is in place, so
    %a definition that mentions F recompiles against the new one.
    forall(metta_on_function_changed(F), true).

add_function_atom(Storage, Space, Module, Term, FAtom, W) :-
    store_equation(Storage, Space, Term),
    length(W, N),
    Arity is N + 1,
    register_arity(FAtom, Arity),
    compile_metta_equation(Module, Term, Clause, _Ref),
    maybe_print_compiled_clause("added function", Term, Clause).

%What is left to refuse, now that every space compiles into a module of its
%own: SWI's PROTECTED CORE. Defining a builtin's name in a space is an
%ordinary local shadow and is accepted; SWI still refuses `assertz` outright
%for a small set of system predicates, with a permission error naming
%assertz/2, the Prolog arity and the absolute path of a source file, none of
%which is language the program that wrote the equation can act on. Say it in
%MeTTa's terms instead, and say that this set is the same in every space
%rather than pointing at a named one, which is no longer the difference
%[measured 2026-08-19: of the 428 names imported into `user`, 7 at MeTTa arity
%0, 4 at arity 1, 2 at arity 2 and 1 at arity 3 are refused in a space's
%module, against 86, 217, 163 and 64 in the engine's]
%[tested: spaces_builtin_override].
:- multifile prolog:error_message//1.

assert_function_clause(Module, Clause, Ref) :-
    catch(assertz(Module:Clause, Ref),
          error(permission_error(modify, static_procedure, _), _),
          throw_builtin_redefinition(Module, Clause)).

%Two refusals, because SWI raises the same permission error for two different
%reasons and only one of them is about Prolog. A name the ENGINE emits into
%compiled bodies is bound into every space's module on purpose
%(protect_engine_emitted/1 above), and telling its author that it is one of
%Prolog's core predicates would send them looking in the wrong place.
throw_builtin_redefinition(Module, Clause) :-
    ( Clause = (Head :- _) -> true ; Head = Clause ),
    functor(Head, Name, Arity),
    InputArity is Arity - 1,
    metta_module_space(Module, Space),
    (   metta_engine_emitted(Name/Arity)
    ->  throw(error(petta_engine_goal_redefinition(Name, InputArity, Space),
                    context('=', 'the engine compiles this name into function \c
                                  bodies')))
    ;   throw(error(petta_builtin_redefinition(Name, InputArity, Space),
                    context('=', 'a builtin cannot be redefined in this space')))
    ).

%The refusal that reads worst when it is unrendered, because the term names a
%capability nobody has heard of and the whole point of the refusal is to teach
%it. `rules` is a promise about what a space HOLDS rather than about which
%methods a provider has, so no protocol can derive it and the message has to
%say how to opt in [tested: test_a_space_without_rules_says_how_to_hold_one].
prolog:error_message(petta_foreign_space_holds_no_rules(Space, Term)) -->
    { swrite(Term, TermText) },
    [ '~w does not hold rules, so ~w was refused rather than stored where it \c
       could never fire'-[Space, TermText], nl,
      '  a foreign space holds DATA unless it says otherwise; declare the \c
       rules capability on the provider to hold a program' ].

prolog:error_message(petta_foreign_operation_failed(Space, Capability)) -->
    [ 'the provider for ~w did not complete the ~w operation and gave no \c
       reason. A provider that cannot serve a request should raise, so the \c
       program can see why.'-[Space, Capability] ].
prolog:error_message(petta_foreign_plan_is_not_a_partition(Space, Patterns,
                                                          Claimed, Rest)) -->
    [ '~w claimed ~w and left ~w of the conjunction ~w, which do not partition \c
       it. A claim may take any subset and leave the rest, and may not drop a \c
       conjunct: the engine plans only what you leave, so a dropped pattern \c
       stops constraining the query and the join answers rows that were never \c
       asked for.'-[Space, Claimed, Rest, Patterns] ].
prolog:error_message(petta_engine_goal_redefinition(Name, Arity, Space)) -->
    [ '~w with ~w arguments is a name the engine itself compiles into function \c
       bodies, so no space can redefine it, ~w included.'-[Name, Arity, Space], nl,
      '  an equation for it would capture the engine\'s own goal in this \c
       space\'s compiled clauses rather than shadowing a function: rename it, \c
       or write the behaviour you want as a wrapper around it' ].
prolog:error_message(petta_builtin_redefinition(Name, Arity, Space)) -->
    [ '~w with ~w arguments is one of Prolog\'s protected core predicates, \c
       which no space can redefine, ~w included.'-[Name, Arity, Space], nl,
      '  every other builtin name is free: an equation for one compiles into \c
       this space\'s own module and shadows it there, leaving the engine\'s \c
       and every other space\'s alone' ].

%Unit for a removal that happened, an error for one that found nothing.
%
%The language's own text is what asks for this rather than what forbids it:
%"if the given atom is not in the space, remove-atom currently neither raises a
%error nor returns the empty result" is a COMPLAINT, and upstream carries the
%same question as a TODO it has not answered, `stdlib/space.rs:219`, "Is it
%necessary to distinguish whether the atom was removed or not?". The arbiter
%answers it: LeaTTa's Hyperon-Hacks-Register row 15 rules "Implement. Keep the
%distinction", records it SATISFIED in `Metta.Minimal.removeAtomStep`, and
%pins the wording this reproduces. Hyperon as shipped answers unit for both,
%so this is a deliberate divergence from the implementation towards the
%specification, which is also what this engine's own hard-error rule says
%[source: LeaTTa wiki/Hyperon-Hacks-Register.md row 15, and
%MettaHyperonFull/Minimal/Interpreter.lean removeAtomStep at 5407-5426].
%
%metta_remove_atom/3 still answers whether anything went and still answers ONLY
%that, because the engine's own callers read the boolean: the loader's
%rollback, the storage modules, and the seam's removal hooks all ask "did the
%store hold it" rather than "what does a program see".
'remove-atom'(Space, Term, Result) :-
    (   petta_space_name(Space)
    ->  metta_remove_atom(Space, Term, Removed),
        (   Removed == true
        ->  Result = []
        ;   space_operation_error('remove-atom', [Space, Term],
                                  "remove-atom: atom is not in the space",
                                  Result)
        )
    ;   space_argument_error('remove-atom', [Space, Term], Result)
    ).

%WHY THE DOORS ASK IT WHERE THEY DO, which is the decision this section makes.
%
%A space is a NAME that is one, and petta_space_name/1 decides which. The doors
%used to share a metta_space_argument/1 whose whole body was `atom(Space)`, on
%the reading that PeTTa CANNOT reproduce the arbiter's
%`(add-atom not-a-space (bad add))` diagnostic: the two model spaces
%differently, upstream's being a grounded atom wrapping a space object while
%PeTTa's is a symbol, and a write to a name that does not exist yet creates it,
%so `not-a-space` and a program's own fresh name looked like the same kind of
%thing. That reading was wrong on its own terms, and the engine already
%disagreed with it in three places: is-space/2 answers False for a name without
%`&`, evalc/3 refuses one as a type error rather than reading a silently empty
%space, and python/petta/space.py refuses one with "the prefix is
%load-bearing". Only these doors did not, so `(add-atom not-a-space (bad add))`
%made a space called `not-a-space` while `(is-space not-a-space)` answered
%False in the same program.
%
%The arbiter decides it the same way for the same reason. LeaTTa dispatches by
%name as this engine does, and its `spaceName` says "bare symbols resolve only
%through the running context's token table; an unbound symbol is not a space",
%with every space-consuming operation resolving through `resolveSpace`
%[source: LeaTTa MettaHyperonFull/Minimal/Interpreter.lean:1565-1573,1621-1627].
%What it does not have is creation on demand, which is why the second half of
%petta_space_name/1 is the prefix rather than the registry: a fresh `&kb` is a
%space the moment a program writes to it, and that capability is kept whole.
%The one example that used a name without the prefix,
%examples/spaces/add_atom_fun_space.metta, still returns a space name from a
%function and still lands its write there, spelled `&my_space_name`.
%
%The atom is ANSWERED rather than thrown, because that is what the arbiter
%does: `(collapse (add-atom not-a-space (bad add)))` is a one-element collapse
%holding the error, and a raise would have emptied the collapse instead
%[source: LeaTTa tests/semantics/spaces/add_atom.metta]
%[tested: space_argument_refusals].
%
%NO DOOR ASKS ON THE PATH THAT SUCCEEDS. A shared test called before the
%operation cost one to three inferences on every space operation and four
%benchmarks saw it [measured 2026-08-20: direct-join +10, prepared-join +10,
%register-op +200, py-method-call +30,002], so each door asks the question it
%was already asking: a write reaches no storage module for a name that is not a
%space, a read misses the storage lookup it was already making, and a
%conjunctive match answers no rows. Only then, on a path that was going to
%answer nothing, is petta_space_name/1 consulted to tell a space that is empty
%from a name that is not one. That is why metta_space_argument/1 is gone rather
%than renamed: one shared test in front of every door is exactly the shape the
%measurements refuse.

%The shape every space operation refuses in: the arbiter's `errAtom a0`, whose
%subject is the CALL that failed rather than a generic complaint, which is
%what lets a program tell one refusal from another without reading the message.
%
%The subject is a COPY of that call, and that is load-bearing rather than tidy.
%match/4 takes the output template and the answer in the SAME term: the
%translator emits `match('&self', [foo, A], A, A)` for
%`!(match &self (foo $x) $x)`, so unifying the answer with an error whose
%subject repeats the template builds `A = (Error (match _ (foo A) A) "...")`,
%a rational tree. SWI has no occurs check here, so nothing failed; the term
%printed until the 7.5Gb stack ran out, 50,707,153 frames deep in maplist/3
%[measured 2026-08-19]. Copying makes the subject a snapshot, which is what a
%record of a call that will not run is, and it makes every caller of this safe
%whether or not its output slot aliases an input.
space_operation_error(Operation, Arguments, Reason, Error) :-
    copy_term(Arguments, Subject),
    Error = ['Error', [Operation|Subject], Reason].

%get-atoms is worded differently because upstream words it differently: it
%takes ONE argument, so pinned `space.rs:143` says "its argument" where the
%two-operand operations' `:172` and `:199` say "the first argument"
%[source: LeaTTa MettaHyperonFull/Minimal/Interpreter.lean, getAtomsStep at
%5450-5452 against addAtomStep at 5386-5388].
space_argument_error(Operation, Arguments, Error) :-
    (   Operation == 'get-atoms'
    ->  Position = "its argument"
    ;   Position = "the first argument"
    ),
    format(string(Message),
           "~w expects a space as ~w", [Operation, Position]),
    space_operation_error(Operation, Arguments, Message, Error).

%%%% The three the standard library defines beside add-atom %%%%
%
%All three were reachable only through `(import! &self (library lib_he))`, and
%only one of them at that, so a program written against the standard library
%found `(add-reduct &self (+ 1000 1))` sitting in the space UNREDUCED as the
%call itself. They are stdlib operations, not extensions:
%
%  add-atoms    "adds atoms in Expression into given space without reduction"
%  add-reduct   "Reduces atom (second argument) and adds it into the space"
%  add-reducts  "evaluates atoms in it and adds them into given space"
%
%[source: LeaTTa stdlib.md:330-361, quoted in its tests/semantics/spaces].
%
%Each answers the UNIT value, like add-atom, and each takes its second argument
%unreduced: the reducing ones do their own reducing, which is the whole of what
%distinguishes them from the plain ones.
%All three DELEGATE the space check to add-atom rather than repeating it, and
%that is observable: the arbiter answers `(Error (add-atom not-a-space 7001)
%...)` for `(add-reduct not-a-space (+ 7000 1))`, naming add-atom and the
%REDUCED atom, because the refusal happens where the write does. Checking here
%would name add-reduct and the unreduced call, which is a different answer.
'add-atoms'(Space, Terms, Result) :-
    metta_space_expression('add-atoms', Terms, List),
    add_expression_to_space(Space, List, Result).

'add-reduct'(Space, Term, Result) :-
    reduced_for_space(Term, Reduced),
    'add-atom'(Space, Reduced, Result).


'add-reducts'(Space, Terms, Result) :-
    metta_space_expression('add-reducts', Terms, List),
    maplist(reduced_for_space, List, Reduced),
    add_expression_to_space(Space, Reduced, Result).

%The batch crossing is kept for the space that has one, so the plural forms are
%still one write rather than n. A bad space is refused before any of it, and
%the error names the first atom because that is the one add-atom would have
%refused first.
%The batch door asks BEFORE the crossing rather than reading its failure, which
%the two doors above can do: a batch has its own crossing and a per-atom
%fallback that answers the error atom instead of failing, so a failure here
%does not mean what it means there. It costs the test once per batch and not
%once per atom.
add_expression_to_space(Space, List, Result) :-
    (   petta_space_name(Space)
    ->  metta_add_atoms(Space, List), Result = []
    ;   List = [First|_]
    ->  space_argument_error('add-atom', [Space, First], Result)
    ;   Result = []
    ).

%The plural forms take ONE expression holding the atoms, which is the shape the
%standard library gives them, so anything else is a mistake worth naming rather
%than a silent no-op over a term that is not a list.
%A DEFINITION reduces its body and keeps its head, and everything else reduces
%whole. Both readings are required by the two things this has to satisfy:
%
%  (add-reduct &self (+ 1000 1))          adds 1001
%  (add-reduct &self (= (foo) (+ 3 4)))   makes (foo) answer 7
%
%[source: LeaTTa tests/semantics/spaces/add_reduct.metta for the first, the
%language's Working with spaces for the second]. Reducing the second one whole
%cannot work HERE, and the reason is local rather than general: `=` is
%overloaded in this engine, the head of a definition and also the equality
%operator, so `(= (foo) (+ 3 4))` reduces to `false` rather than staying an
%equation with its body reduced. Upstream has no such collision, which is why
%it can state the rule as one sentence and this cannot.
reduced_for_space([=, Head, Body], [=, Head, ReducedBody]) :-
    !,
    reduced_for_space(Body, ReducedBody).

%reduce/3 takes an expression, and a symbol or a number is already its own
%value, so asking it to reduce one raises rather than answering. Both callers
%above may be handed either, because their argument arrives unreduced.
reduced_for_space(Term, Reduced) :-
    (   is_list(Term)
    ->  once(reduce(Term, Reduced, _))
    ;   Reduced = Term
    ).

metta_space_expression(_, Terms, Terms) :- is_list(Terms), !.
metta_space_expression(Operation, Terms, _) :-
    throw(error(type_error(expression, Terms),
                context(Operation, 'takes one expression of atoms'))).

%The mirror of the write path, and it has to be: an atom that compiled when it
%was added has to un-compile when it is taken out, wherever it was stored. This
%dispatched on storage first for the same reason the write path did, so a
%foreign space's equation kept its compiled clause after the atom was gone.
%A pattern that is ITSELF a variable is the remove-everything reading a
%multiset space gives it, and it must be answered here: left to the next
%clause, the unbound term UNIFIED into the equation shape and took the
%equation-removal path with an unbound function symbol, whose behaviour
%then depended on whatever equations the whole process happened to hold
%(found 2026-08-18: (remove-atom &cstore $any) raised
%atomic_list_concat/2 instantiation errors only when other suites had
%run first). Enumerating and removing each atom through its own proper
%path keeps equations, their compiled clauses, and foreign providers
%all handled by the code that owns them.

%% metta_remove_atom(+Space:atom, ?Atom, -Removed:boolean) is semidet.
metta_remove_atom(Space, Term, Removed) :- var(Term), !,
    findall(A, 'get-atoms'(Space, A), Atoms),
    (   Atoms == []
    ->  Removed = false
    ;   forall(member(A, Atoms),
               ( metta_remove_atom(Space, A, _) -> true ; true )),
        Removed = true
    ).
metta_remove_atom(Space, Term, Removed) :- Term = [=, [F|Args], Body], !,
                                           remove_equation(Space, Term, F, Args,
                                                           Body, Removed).
%A declaration decides how call sites compile, so taking one away leaves them
%stale exactly as adding one did, and for the same reason: the argument that
%arrived as written now arrives evaluated. The write path learned this and the
%removal path did not.
metta_remove_atom(Space, Term, Removed) :- Term = [':', F, _], atom(F), fun(F), !,
                                           unstore_atom(Space, Term, Removed),
                                           recompile_definitions_mentioning(F),
                                           space_module(Space, DeclModule),
                                           function_changed(DeclModule, F).
metta_remove_atom(Space, Term, Removed) :- unstore_atom(Space, Term, Removed).

%% remove_equation(+Space:atom, +Equation, +Function:atom, +Arguments, ?Body, -Removed:boolean) is semidet.
remove_equation(Space, Term, F, Args, Body, Removed) :-
    unstore_atom(Space, Term, Stored),
    space_module(Space, Module),
    drop_fun_meta(Module, F, Args, Body),
    %ONE compiled clause, the multiset law applied to the compiled half. The
    %retained-equation half above already worked this way and said so, "remove
    %one variant-equivalent retained equation... duplicate equations are
    %removed one at a time", so the two halves used to disagree: the same
    %equation written twice answered twice, and one removal left the function
    %undefined because this erased both clauses under the one atom that went.
    %
    %Only this space's compiled clauses die: the same equation imported into two
    %spaces compiles into two modules, and the term-keyed lookup alone would
    %erase the twin space's clause and, through the term-wide retractall, its
    %record with it.
    %
    %The probe is a COPY for drop_fun_meta/4's reason: a lookup that binds the
    %caller's Term would narrow every later use of it in this clause.
    copy_term(Term, Probe),
    (   translated_from(Ref, Probe), clause_property(Ref, module(Module))
    ->  erase(Ref), retractall(translated_from(Ref, _)), Erased = true
    ;   Erased = false
    ),
    function_changed(Module, F),
    ( module_owns_function(Module, F) -> true ; unregister_fun_in(Module, F) ),
    ( \+ function_still_defined(F)
      -> retractall(fun(F)), unregister_fun_everywhere(F),
         forall(metta_on_function_removed(F), true)
      ; true ),
    ( Erased == false, Stored \== true -> Removed = false ; Removed = true ).

%Where an atom comes out of, the counterpart of store_atom/2. Both answer
%whether the store actually held it.

%% unstore_atom(+Space:atom, ?Atom, -Removed:boolean) is semidet.
unstore_atom(Space, Term, Removed) :- metta_foreign_space(Space), !,
                                      foreign_write(Space, remove,
                                                    metta_foreign_remove(Space, Term,
                                                                         Removed)).
%One atom that unifies, and whether one was there. A MeTTa space is a multiset,
%and subtracting from a multiset takes one occurrence.
unstore_atom(Space, Term, Removed) :- remove_sexp(Space, Term, Removed).

%A CONJUNCTION finds every row before any of them leaves, which is specified
%behaviour and not an implementation detail we are free to pick: "match first
%finds all the matches, and then instantiates the output pattern with them,
%which is evaluated outside match. If remove-atom and add-atom would be
%executed right away for each found matching, the condition of circular links
%would be broken after the first rewrite" [source: the language's Working with
%spaces, the graph-rewriting example]. The arbiter pins it with an experiment
%built to tell an eager snapshot from a lazy query that happens to be fully
%consumed: both implementations retain every row through a template that
%removes the other one, and only the effect ORDER is a recorded free
%divergence [source: LeaTTa tests/semantics/matching/
%nondeterministic_match_snapshot.metta and its EVIDENCE entry].
%
%A SINGLE pattern needs nothing here and still streams. It is one goal over
%one dynamic predicate, and the logical update view already fixes what it sees
%at the call, so a template that writes cannot change what the goal still has
%to answer; the arbiter's own single-pattern experiment passes on that alone.
%A conjunction is where it runs out, because each later conjunct is a fresh
%goal STARTED AFTER the previous row's template ran, and a fresh goal sees the
%new generation. Measured on the doc's own example: upstream reverses all
%three loop edges, and this reversed one, the first template's remove-atom
%breaking the cycle for every later conjunct [measured 2026-08-19,
%ai-tmp/spaces-p1/p116/linkloop.metta].
%
%What is collected is the BINDINGS, term_variables over the pattern and the
%output template together, because that is where a row lives: the translator
%compiles the template into goals reading the PATTERN's own variables,
%`'remove-atom'('&self', [link, B, C], _)` beside `match('&self', [',',
%[link,B,C], ...], A, A)`, so collecting the output slot alone would collect a
%variable the match never binds and lose every row. Taking both terms'
%variables keeps whatever they share.
%
%Cheaper than the arbiter, which collects a BindingsSet for every match; this
%pays only where a conjunction is written, and leaves
%(once (match &big (foo $x) $x)) streaming
%[tested: test_match_snapshots_rows_before_template_effects,
%spaces_match_snapshot:a_conjunction_finds_every_row_before_any_template_runs].
%An ANNOTATED space's rows carry their annotation as well as their bindings,
%because that rides '$petta_answer_k' BACKTRACKABLY and findall would undo it:
%reset-call-read is metta_top/3's own idiom below, and the write after member/2
%is what hands the row's k to the template that reads (annotation).
%
%A space whose semiring is bool takes the plain collection, which is three
%inferences a row cheaper and is the traffic: under bool an answer's k can
%only be 1, because a provider handing one to an undeclared context raises
%rather than setting it ("a real k is admitted exactly when its context
%declared a non-Boolean semiring", python/petta/shim.pl), and the engine's own
%join writes nothing when both sides read 1. Measured on direct-join
%[measured 2026-08-19: 320,322 inferences with the capture on every row
%against 289,819 without it, over 10,000 rows]
%[tested: test_a_join_multiplies_provenance,
%test_a_conjunction_carries_each_rows_annotation].
%atom/1 rather than a space test, and the refusal reached through the SOFT CUT
%below: a conjunction that answered rows was a space, and only one that
%answered none has anything left to decide. A space test in the guard cost one
%inference on every join [measured 2026-08-20: direct-join and prepared-join
%+10 each].
match(Space, Pattern, OutPattern, Result) :- nonvar(Pattern), Pattern = [Comma|_], Comma == ',',
                                             atom(Space), !,
                                             (   conjunctive_match(Space, Pattern,
                                                                   OutPattern, Result)
                                             *-> true
                                             ;   petta_space_name(Space)
                                             ->  fail
                                             ;   space_argument_error('match',
                                                                      [Space, Pattern,
                                                                       OutPattern],
                                                                      Result)
                                             ).

%A single pattern over a foreign space: the provider answers, and the
%conjunction door above has already taken the conjunctive case.
match(Space, Pattern, OutPattern, Result) :- nonvar(Space),
                                             metta_foreign_space(Space), !,
                                             match_foreign(Space, Pattern, OutPattern, Result).
%An unbound space would make this dynamic call enumerate every space that has
%ever been written to, so a program in &self could read &kb without naming it.
%Matching is against a space you NAME, and the refusal is the write path's
%own: `(add-atom $unbound (foo 1))` already answered
%`(Error (add-atom $_ (foo 1)) "add-atom expects a space as the first
%argument")` while this raised SWI's bare `Arguments are not sufficiently
%instantiated`, which names neither the operation nor the call and reached
%Python as an EngineError with no operation field at all. Same question, same
%kind of answer [tested: test_get_atoms_on_an_unbound_space_names_the_operation,
%spaces_storage_modules:matching_requires_a_named_space].
%
%The storage lookup this clause was already making IS the space test for every
%name the engine holds, so a match against a space that exists reaches
%match_native/5 exactly as it did and the two clauses below it never run. The
%CUT is what lets them exist: without it an answered match would produce the
%refusal as a second answer.
match(Space, Pattern, OutPattern, Result) :-
    atom(Space),
    native_storage_module_cache(Space, Module), !,
    match_native(Module, Space, Pattern, OutPattern, Result).
%Only a name the engine holds no space for reaches here, and the question left
%is which kind it is: a space nothing has written to yet answers nothing, which
%is what an empty space answers, and anything else is refused by name.
%
%GUARDED RATHER THAN LEFT TO THE CUT ABOVE, and that is load-bearing: the
%derivation meta-interpreter walks a predicate by enumerating clause/3 and
%calling each body through call/1, where a cut in an earlier body cannot prune
%this clause. Written without the guard, every match against a real space grew
%a second answer, the refusal, and `(anc-d $x $y)` recursed on it until the
%process hung [reproduced 2026-08-20: python/tests/test_derivation.py]. Every
%clause of a predicate a proof can walk has to say for itself when it applies,
%which is what the three clauses above already do.
match(Space, Pattern, OutPattern, Result) :-
    \+ petta_space_name(Space),
    space_argument_error('match', [Space, Pattern, OutPattern], Result).

conjunctive_match(Space, Pattern, OutPattern, Result) :-
    term_variables(Pattern-OutPattern, Row),
    (   petta_annotations(Space, bool)
    ->  findall(Row,
                match_conjunction(Space, Pattern, OutPattern),
                Rows),
        member(Row, Rows)
    ;   findall(Row-K,
                ( b_setval('$petta_answer_k', 1),
                  match_conjunction(Space, Pattern, OutPattern),
                  b_getval('$petta_answer_k', K) ),
                Rows),
        member(Row-K, Rows),
        b_setval('$petta_answer_k', K)
    ),
    Result = OutPattern.

%THE ENGINE'S OWN READ of a space, the counterpart of get_native_atom/2 behind
%'get-atoms'/2 and there for the same reason: its callers hold a space name the
%ENGINE gave them rather than one a program wrote, so there is nothing to
%refuse and an error atom would be read back as a stored atom. The type lookups
%are why it has to exist rather than being a tidy split: a declaration lookup
%runs on every typed call, and routing those through the door made each one pay
%the door's refusal decision whenever the space had no atoms yet
%[measured 2026-08-20: py-method-call 2,250,095 inferences against 2,220,093,
%three per call over 10,000 evaluations in a space nothing had written to].
match_stored(Space, Pattern, OutPattern, Result) :-
    nonvar(Space), metta_foreign_space(Space), !,
    match_foreign(Space, Pattern, OutPattern, Result).
match_stored(Space, Pattern, OutPattern, Result) :-
    atom(Space),
    native_storage_module_cache(Space, Module),
    match_native(Module, Space, Pattern, OutPattern, Result).

%Choose the provider once for the whole conjunction. It may enumerate millions
%of native candidates, so deciding per candidate would repeat the foreign-space
%probe every time. A native space is a Prolog predicate named after the space
%and stays on the direct helper; anything else routes each conjunct back
%through match/4, which is how a space implemented by its own clause sees it.
match_conjunction(Space, Pattern, OutPattern) :- metta_foreign_space(Space), !,
                                                 match_foreign(Space, Pattern, OutPattern, _).
match_conjunction(Space, Pattern, OutPattern) :- native_storage_module_cache(Space, Module), !,
                                                 match_native(Module, Space, Pattern, OutPattern, _).
match_conjunction(Space, Pattern, OutPattern) :- match_routed(Space, Pattern, OutPattern, _).

match_routed(_, LComma, OutPattern, Result) :- LComma == [','], !,
                                               Result = OutPattern.
match_routed(Space, [','|[Head|Tail]], OutPattern, Result) :-
    match(Space, Head, conj, conj),
    match_routed(Space, [','|Tail], OutPattern, Result).

%One matching step of Hyperon's unify: each solution is one binding set,
%bindings applied by Prolog unification itself. The clause order is the
%case order of the arbiter's matcher, LeaTTa
%MettaHyperonFull/Core/Matching.lean matchAtomsWith (209-241): variables
%bind before anything is consulted, with the occurs check the arbiter's
%variable cases carry; expressions match pointwise, consistency kept by
%the shared bindings; then a grounded operand's own matching logic runs,
%left before right, which is how a space becomes queryable inside unify
%(Hyperon: `impl CustomMatch for DynSpace` is query, hyperon-space
%src/lib.rs); a host value with declared matching runs its hook the same
%way; numbers compare promoted, so 1 matches 1.0 [source: LeaTTa
%tests/semantics/matching/grounded_value_matching.metta, measured
%2026-08-11]; everything else is ground equality. A space is named by a
%symbol here rather than a grounded atom, so the operand test is the
%registered-space probe, and an unregistered name falls through to
%equality like any symbol. The leading identity clause is the arbiter's
%diagonal collapsed to one C comparison: two identical operands match
%with the empty binding set case for case (equal grounds trivially; a
%shared variable is the same-variable case; identical compounds decide
%pointwise to the same), and it spares the per-leaf probe cascade on the
%equal-operand traffic that dominates eval-branch tests
%[measured 2026-08-17: test_unify_eval_branches].
petta_match_atoms(L, R) :- L == R, !.
petta_match_atoms(L, R) :- ( var(L) ; var(R) ), !,
                           unify_with_occurs_check(L, R).
petta_match_atoms(L, R) :- is_list(L), is_list(R), !,
                           petta_match_all(L, R).
petta_match_atoms(L, R) :- petta_space_operand(L), !, match(L, R, [], _).
petta_match_atoms(L, R) :- petta_space_operand(R), !, match(R, L, [], _).
petta_match_atoms(L, R) :- metta_matchable_value(L), !,
                           metta_custom_match(L, R).
petta_match_atoms(L, R) :- metta_matchable_value(R), !,
                           metta_custom_match(R, L).
petta_match_atoms(L, R) :- number(L), number(R), !, L =:= R.
petta_match_atoms(L, R) :- L == R.

petta_match_all([], []).
petta_match_all([X|Xs], [Y|Ys]) :-
    petta_match_atoms(X, Y),
    petta_match_all(Xs, Ys).

%Whether an operand names a space this engine can query: a foreign
%provider or a native storage module. Both probes are indexed lookups.
petta_space_operand(S) :-
    atom(S),
    (   metta_foreign_space(S)
    ->  true
    ;   native_storage_module_cache(S, _)
    ).


%Every space name this engine registers: '&self' and '&petta' from load
%time, every native space that (new-space) made or that has been written
%to, and every foreign provider currently bound. Naming a space never
%registers it, only creating it, writing to it or binding one does, so
%this is the same set petta_space_operand/1 accepts. sort/2 makes the
%answer stable and duplicate-free.
metta_space_names(Names) :-
    findall(S, native_storage_module_cache(S, _), Native),
    findall(S, metta_foreign_space(S), Foreign),
    append(Native, Foreign, All),
    sort(All, Names).

%The Empty prune behind every computed collapse. The gate is memberchk
%NEGATED, which makes it sound AND C-fast: when nothing in the list
%unifies with Empty (the overwhelmingly common all-ground case,
%4 inferences however long the list), the list is shared untouched; when
%something unified, the negation has already undone the binding, and the
%identity (==) walk decides whether it was a real Empty or an unbound
%answer variable. Bare memberchk once BOUND such a variable and pruned
%it, which turned `!(let $b (is-alpha-member (1 $x) ...) $x)`'s unbound
%answer into nothing
%[tested translated_success_leaves_the_query_variable_unbound].
petta_prune_empty(All, Kept) :-
    (   \+ memberchk('Empty', All)
    ->  Kept = All
    ;   petta_member_empty_(All)
    ->  petta_drop_empty_(All, Kept)
    ;   Kept = All
    ).

petta_member_empty_([X|Xs]) :-
    (   X == 'Empty'
    ->  true
    ;   petta_member_empty_(Xs)
    ).

petta_drop_empty_([], []).
petta_drop_empty_([X|Xs], Kept) :-
    (   X == 'Empty'
    ->  petta_drop_empty_(Xs, Kept)
    ;   Kept = [X|Kept1],
        petta_drop_empty_(Xs, Kept1)
    ).


%A foreign provider enumerates candidates. Unification against the pattern
%stays here, so an approximate provider cannot change matching soundness.
%Which way this space answers, decided ONCE for the whole match. It depends
%only on Space, so asking per conjunct is invariant work inside a loop:
%measured at 8.00 inferences of the seam's 9.00 fixed overhead, paid once per
%OUTER ROW in a join because the inner conjunct is re-dispatched on every
%backtrack. Hoisting it took a 200-row join from 1.89x a direct match/4 clause
%to 1.10x, saving 8.01 per row.
%
%match_native/5 one clause up already does this and says why: "The recursive
%helper keeps the provider decision outside the candidate loop."
foreign_route(Space, Route) :-
    (   foreign_provides(Space, match)
    ->  Route = match
    ;   refuse_absent_capability(Space, enumerate),
        Route = enumerate
    ).

%Whether a provider takes this conjunction, decided ONCE and committed to. A
%provider that could yield a row and then decline would leave the engine unable
%to tell "no rows" from "not mine", which is the ambiguity metta_foreign_match/3
%was fixed for; once/1 here and the cut at the call site are what prevent it.
foreign_claims_plan(Space, Conjuncts, Rest, Goal) :-
    foreign_provides(Space, plan),
    once(metta_foreign_plan(Space, Conjuncts, Claimed, Rest, Goal)),
    Claimed \== [],
    refuse_lossy_plan(Space, Conjuncts, Claimed, Rest).

%Claimed and Rest have to PARTITION the conjunction. Both sides hold the
%CALLER'S OWN pattern terms (the Python seam resolves its answer back to
%them by wire identity), so this compares like with like and is a real
%check; it used to double as the mechanism that reconnected freshly
%decoded copies to the caller, which worked only while both lists
%happened to sort into the same order. A provider that drops a
%conjunct answers more rows than the query asks for, and nothing downstream
%would catch it: the engine plans Rest and never looks at the original patterns
%again, so the dropped conjunct is simply not part of the query any more. Once
%per join and never per row.
refuse_lossy_plan(Space, Patterns, Claimed, Rest) :-
    append(Claimed, Rest, Both),
    msort(Both, Sorted),
    (   msort(Patterns, Sorted)
    ->  true
    ;   throw(error(petta_foreign_plan_is_not_a_partition(Space, Patterns,
                                                          Claimed, Rest),
                    context(match/4,
                            'a claim must partition the conjunction')))
    ).

%A declared Refuse fires on ANY match of its shape, bounded or not: the
%author said this context cannot answer it, and a silent partial answer is
%the failure the declaration exists to prevent. One route consultation per
%query, never per answer. Handles entries describe MATCH shapes, so a
%conjunction is decomposed and each conjunct asked on its own; offering the
%raw [','|_] term instead let an ($f ...) entry capture the comma itself.
petta_refuse_guard(Space, _) :-
    \+ petta_ctx_declared(Space),
    !.
petta_refuse_guard(Space, Pattern) :-
    (   nonvar(Pattern), Pattern = [Comma|Conjuncts], Comma == ','
    ->  \+ \+ petta_refuse_guard_conjuncts(Conjuncts, Space)
    ;   %The route is computed with fidelity UNBOUND and tested after, so
        %the coherence check inside it runs on every consultation; asking
        %for 'Refuse' directly would fail out before two disagreeing
        %entries are compared, and the conflict would surface only under a
        %bound instead of on every match.
        petta_handles_route(Space, Pattern, Entry, Fidelity, _),
        Fidelity == 'Refuse'
    ->  throw(error(petta_refused_shape(Space, Pattern, Entry), none))
    ;   true
    ).

%Left-to-right, the way the nested loop executes: a conjunct's variables are
%bound by the time later conjuncts run, so each is checked with the earlier
%ones' variables marked bound. This is adornment-level analysis, Mercury's
%modes and the database bindability check: an (in $x) refusal fires here at
%plan time, while a refusal keyed to a literal VALUE can only fire on a
%direct query where the value is visible. The double negation above undoes
%the marker bindings; a throw passes through it.
petta_refuse_guard_conjuncts([], _).
petta_refuse_guard_conjuncts([Conjunct|Rest], Space) :-
    petta_refuse_guard(Space, Conjunct),
    term_variables(Conjunct, Vars),
    maplist(=('$petta_bound'), Vars),
    petta_refuse_guard_conjuncts(Rest, Space).

match_foreign(Space, Pattern, OutPattern, Result) :-
    petta_refuse_guard(Space, Pattern),
    petta_negation_world_guard(Space),
    foreign_route(Space, Route),
    match_foreign_routed(Space, Route, Pattern, [], OutPattern, Result).

match_foreign_routed(_, _, LComma, _, OutPattern, Result) :- LComma == [','], !,
                                                             Result = OutPattern.
%The conjunction is offered to the provider WHOLE before it is split, which is
%the only way a backend's own join is reachable: the split below is a
%nested-loop plan, and a provider that never sees more than one pattern at a
%time cannot do better than one however fast it is.
%
%Two or more conjuncts, because a single one is the ordinary match path and
%offering it here would only duplicate that.
match_foreign_routed(Space, Route, [Comma|Conjuncts], _, OutPattern, Result) :-
    Comma == ',', Conjuncts = [_, _|_],
    foreign_claims_plan(Space, Conjuncts, Rest, Goal), !,
    call(Goal),
    match_foreign_routed(Space, Route, [','|Rest], [], OutPattern, Result).
match_foreign_routed(Space, Route, [Comma|[Head|Tail]], _, OutPattern, Result) :-
    Comma == ',', !,
    match_foreign_routed(Space, Route, Head, [], conj, conj),
    petta_annotation(HeadK),
    match_foreign_routed(Space, Route, [','|Tail], [], OutPattern, Result),
    %The polynomial construction along the join: a row's annotation is
    %the product of its conjuncts'. Both 1, the Boolean point, combines
    %to 1 without a write, so an unannotated join pays two reads only;
    %the LAST conjunct combines with nothing, since the base case that
    %follows it contributes no answer of its own.
    (   HeadK == 1
    ->  true
    ;   Tail == []
    ->  true
    ;   petta_annotation(TailK),
        petta_k_times(HeadK, TailK, RowK),
        b_setval('$petta_answer_k', RowK)
    ).
%An unbound pattern is enumeration whichever way the space answers matches, so
%it asks for that capability on its own rather than riding the route.
match_foreign_routed(Space, _, PatternVar, _, OutPattern, Result) :-
    var(PatternVar), !,
    refuse_absent_capability(Space, enumerate),
    %The source guard sits at the three clauses that PHYSICALLY touch the
    %provider, not at the conjunction entry: a join's inner conjunct is
    %its own touch per outer row, and that second touch of a drained
    %linear source is exactly what must be loud.
    petta_source_guard(Space),
    metta_foreign_atoms(Space, PatternVar),
    acyclic_term(OutPattern),
    Result = OutPattern.
match_foreign_routed(Space, match, Pattern, Options, OutPattern, Result) :- !,
    licensed_options(Space, Pattern, Options, Licensed),
    petta_source_guard(Space),
    (   petta_on_error_mode(Space, Pattern, Mode),
        Mode \== abort
    ->  petta_match_erring(Mode, Space, Pattern, Licensed, OutPattern, Result)
    ;   metta_foreign_match(Space, Pattern, Licensed),
        acyclic_term(OutPattern),
        Result = OutPattern
    ).

match_foreign_routed(Space, enumerate, Pattern, _, OutPattern, Result) :-
    petta_source_guard(Space),
    metta_foreign_atoms(Space, Candidate),
    Candidate = Pattern,
    acyclic_term(OutPattern),
    Result = OutPattern.
%A declared keep delivers the provider's own failure as one final (Error
%...) answer beside the answers that already streamed, LeaTTa's
%adjudicated reading of evaluation errors turned to the provider
%boundary; empty ends the stream by declaration. Control signals and
%transport failures pass through both, always: an interrupt is the
%caller's, and an absent backend is never a data answer.
%
%WHERE the failure is caught depends on the provider's host, and that is
%not a style choice: a Python exception raised mid-iteration TUNNELS
%through py_iter back to the outer Python interpreter and no Prolog
%catch/3 can hold it [measured 2026-08-17: a catch-all around py_iter
%still surfaced the raw ValueError in janus.query_once], so a Python
%provider's mode is enforced on the Python side of the crossing, with a
%kept failure arriving as the reserved ["x","error",...] wire item
%through the metta_foreign_erring/5 adapter hook. A provider whose host
%is Prolog throws ordinary catchable exceptions, and the fallback below
%handles those here; catch/3 keeps the goal's choice points, so streamed
%answers survive the wrapping.
petta_match_erring(Mode, Space, Pattern, Licensed, OutPattern, Result) :-
    (   metta_foreign_erring(Space, Pattern, Licensed, Mode, Item)
    *-> (   Item == answer
        ->  acyclic_term(OutPattern),
            Result = OutPattern
        ;   Item = kept(Kept),
            Result = Kept
        )
    ;   catch(( metta_foreign_match(Space, Pattern, Licensed),
                Outcome = answer ),
              Error,
              petta_match_error_outcome(Error, Mode, Outcome)),
        (   Outcome == answer
        ->  acyclic_term(OutPattern),
            Result = OutPattern
        ;   Outcome = kept(E),
            petta_error_answer(Pattern, E, Result)
        )
    ).

petta_match_error_outcome(Error, _, _) :-
    control_exception(Error), !, throw(Error).
petta_match_error_outcome(Error, _, _) :-
    petta_transport_failure(Error), !, throw(Error).
petta_match_error_outcome(Error, keep, kept(Error)).

%A bound pattern went straight to the match hook, so a provider that
%implements only enumeration answered NOTHING to every real query while the
%space demonstrably held matching atoms. python/petta/foreign.py states the
%opposite contract for the same seam, in as many words: "An Enumerable
%provider need not implement Matcher: enumeration is the correct default
%candidate set". Porting a working Python provider to Prolog for speed, which
%is exactly what EXTENDING.md recommends, turned every match into an empty
%answer set.
%
%The provider is handed a FRESH variable and the filter happens here, so a
%provider written to enumerate never sees a bound pattern it was not written
%for. Unification staying on this side is also what makes over-approximation
%sound, which is the seam's central claim.
%The same match, carrying what the caller intends to do with it. Honouring an
%option is the provider's decision and not the engine's; see src/ext_points.pl.
%Unification and the engine's own bound stay here whatever the provider does,
%so an option cannot make an answer wrong, only cheaper.
match_foreign(Space, Pattern, Options, OutPattern, Result) :-
    petta_refuse_guard(Space, Pattern),
    petta_negation_world_guard(Space),
    foreign_route(Space, Route),
    match_foreign_routed(Space, Route, Pattern, Options, OutPattern, Result).

%The bound reaches a provider that PROMISED it can act on it, and nobody else.
%
%It used to reach everyone as advice, with the rule for using it soundly
%written in the contract: honour it only where an exact match is
%distinguishable from a candidate, because N candidates are not N answers and
%truncating without knowing which of them unify under-answers. That rule is
%correct and it is a trap, since nothing checked whether a provider that
%truncated was entitled to. This engine's own test fixture had "its match is
%exact" in a docstring and nothing testing it.
%
%So the number goes to a provider that declared exact for this pattern, and
%the trap closes by construction: a provider that never promised is never
%given a number it could truncate to. Apache DataFusion's planner does the
%same thing with the same reasoning, dropping its own FilterExec only for a
%source that answered Exact.
%
%What the engine deliberately does NOT do with the class is stop pulling
%earlier. That was the obvious use and it buys nothing, measured both ways: a
%Prolog provider is already cut by the caller's own limit/2 after the Nth
%answer, and a Python one is pulled one ahead by janus's py_iter whatever the
%engine asks for, so limit(3) produced 3 and 4 candidates respectively with
%and without the classification wired to it [measured 2026-08-16,
%ai-tmp/x7pl.pl]. Unification is not skippable either: it is not a filter here
%but the step that binds the pattern's variables. An exact claim can therefore
%make a provider cheaper and can never make an answer wrong.
licensed_options(Space, Pattern, Options, Licensed) :-
    (   selectchk(limit(_), Options, WithoutBound)
    ->  (   foreign_pushdown_class(Space, Pattern, exact)
        ->  Licensed = Options
        ;   Licensed = WithoutBound
        )
    ;   Licensed = Options
    ).

%%%% take: at most K answers, and the bound the provider gets %%%%
%
%limit/2 is applied OUTSIDE the producer in both clauses, and that is what
%makes the whole thing correct rather than merely fast: it cuts the producer
%after the Kth answer whatever the producer did, so an infinite one terminates
%and a pushdown below it cannot change an answer. The pushdown decides only
%how much work the backend does before the first one.
metta_take(Count, Goal) :-
    metta_take_count(take, Count),
    limit(Count, Goal).

%The bound reaches the PROVIDER only when the expression is exactly one match
%over one space. Across a join the bound belongs to the joined rows, and an
%outer match truncated at N loses the rows its later candidates would have
%joined to; that is the rule petta_py_query_limit_all/5 already follows for
%m.query(limit=), and this is the same rule at the MeTTa level rather than a
%second one.
%
%A provider that never claimed `exact` for this pattern is not handed the
%number at all, which licensed_options/4 enforces on the way through, so the
%one thing the contract forbids stays impossible from here too.
metta_take_match(Count, Space, Pattern, Out) :-
    metta_take_count(take, Count),
    (   nonvar(Space),
        metta_foreign_space(Space)
    ->  limit(Count, match_foreign(Space, Pattern, [limit(Count)], Out, Out))
    ;   limit(Count, match(Space, Pattern, Out, Out))
    ).

%A count that is not a number is a mistake rather than an empty answer, for
%the reason every refusal here is: failing into "there is nothing there" sends
%the author looking at their data. A count of zero or less answers nothing,
%which is what "at most K" means and what limit/2 already does.
metta_take_count(_, Count) :- integer(Count), !.
metta_take_count(Form, Count) :-
    throw(error(type_error(integer, Count),
                context(Form/2, 'take needs a whole number of answers'))).

%%%% top: the k BEST by annotation, where take is any k %%%%
%
%Two bounds, two specifications. take k is "at most k, no promise which",
%correct for unordered contexts. top k is the k best in the context's
%declared semiring order, the operation a vector index actually
%implements. Each answer's annotation rides '$petta_answer_k',
%backtrackably: the seam sets it per explicit answer and the default 1
%is restored on redo, so an unannotated answer between two annotated
%ones reads 1 rather than a stale neighbour.
:- meta_predicate metta_take(+, 0), metta_top(+, 0, ?).
%The same reason the block above metta_timeout/3 in metta.pl records:
%without this the bounded goal loses its module and a named space's own
%functions are unreachable inside take and top.

metta_top(Count, Goal, Out) :-
    metta_take_count(top, Count),
    findall(Annotation-Out,
            ( b_setval('$petta_answer_k', 1),
              call(Goal),
              b_getval('$petta_answer_k', Annotation) ),
            Pairs),
    metta_top_best(Count, Pairs, Best),
    member(Out, Best).

%The single-match form checks the context's declared order and decides the
%push. The bound reaches the provider only when three declarations hold
%together: the route is Exact for this shape, the annotations are ordered,
%and the merge policy is best-first, since the first k of a best-first
%emission ARE the k best. Drop any one and a pushed bound can return the
%wrong k, not merely a permutation, so the bound stays here and the
%ordering happens after collection.
metta_top_match(Count, Space, Pattern, Out) :-
    metta_take_count(top, Count),
    (   petta_annotations_ordered(Space)
    ->  true
    ;   petta_annotations(Space, Semiring),
        throw(error(petta_top_unordered(Space, Semiring), none))
    ),
    (   nonvar(Space),
        metta_foreign_space(Space)
    ->  (   petta_top_pushable(Space, Pattern)
        ->  Options = [limit(Count)]
        ;   Options = []
        ),
        Producer = match_foreign(Space, Pattern, Options, Out, Out)
    ;   %A native space that declares an ordered semiring still stores
        %plain atoms, so every annotation reads 1 and top k keeps the
        %first k by emission order, the all-ties reading.
        Producer = match(Space, Pattern, Out, Out)
    ),
    findall(Annotation-Out,
            ( b_setval('$petta_answer_k', 1),
              Producer,
              b_getval('$petta_answer_k', Annotation) ),
            Pairs),
    metta_top_best(Count, Pairs, Best),
    member(Out, Best).

petta_top_pushable(Space, Pattern) :-
    %A cap below exact, or a cap refusal, declines the pushdown here and
    %lets the match itself surface the loud error, so (top k) never pushes
    %a bound an advisor has withdrawn the licence for.
    catch(( petta_handles_route(Space, Pattern, 'Exact', _),
            petta_route_cap_apply(Space, Pattern, exact, exact) ),
          _, fail),
    petta_emits(Space, 'best-first').

%Best first, ties in emission order: sort/4 with @>= keeps duplicates and
%is stable, so equal annotations keep the provider's own order.
metta_top_best(Count, Pairs, Best) :-
    sort(1, @>=, Pairs, Ordered),
    length(Ordered, Total),
    Keep is min(Count, Total),
    length(Prefix, Keep),
    append(Prefix, _, Ordered),
    findall(Out, member(_-Out, Prefix), Best).

:- multifile prolog:error_message//1.
prolog:error_message(petta_top_unordered(Ctx, Semiring)) -->
    [ '(top k ...) asks for the k BEST and ~w declares the ~w semiring, \c
       which carries no order. Declare (annotations ~w ranked) if this \c
       context annotates its answers, or use (take k ...) for any \c
       k'-[Ctx, Semiring, Ctx] ].

%What a provider claims about its own filtering for THIS pattern. Silence is
%inexact, which is Prolog's own closed-world reading of the question, "any
%conclusion that cannot be proved to follow from the facts and rules in the
%database is false" [source: Bramer, Logic Programming with Prolog, 3.1], and
%the cautious answer: an inexact provider gets no bound to truncate to and its
%candidates are re-unified.
foreign_pushdown_class(Space, Pattern, Class) :-
    foreign_pushdown_declared_class(Space, Pattern, Declared),
    petta_route_cap_apply(Space, Pattern, Declared, Class).

foreign_pushdown_declared_class(Space, Pattern, Class) :-
    (   petta_handles_route(Space, Pattern, Entry, Fidelity, _Det)
    ->  %A declared (handles ...) entry outranks the provider's own method:
        %the declaration is the author's claim, checked by its lanes, and
        %the method stays as the dynamic floor for the undeclared. Exact
        %licenses the bound; Partial and Sound are candidates needing
        %re-unification, today's inexact; Refuse is the author's NO and it
        %is loud, the same precedence volatile has over unchecked.
        (   Fidelity == 'Exact'  -> Class = exact
        ;   Fidelity == 'Refuse' -> throw(error(petta_refused_shape(Space,
                                                                    Pattern,
                                                                    Entry),
                                                none))
        ;   Class = inexact
        )
    ;   metta_foreign_pushdown(Space, Pattern, Claimed)
    ->  Class = Claimed
    ;   Class = inexact
    ).

%The advisors' fold: every metta_route_cap/4 clause is a voice and the
%most conservative wins, refuse below inexact below exact, so an advisor
%can only DEMOTE what the declaration or the method proposed. refuse is
%loud and names the advisor's Why; a cap outside the vocabulary is a bug
%in the advisor and refuses as one. The common engine has no advisor
%loaded, and that costs one failed indexed call; with advisors present
%the probe's work is repeated inside findall, which is accepted, advisors
%being rare and the fold running only at route classification, never per
%answer.
petta_route_cap_apply(Space, Pattern, Class0, Class) :-
    (   \+ metta_route_cap(Space, Pattern, _, _)
    ->  Class = Class0
    ;   findall(Cap-Why, metta_route_cap(Space, Pattern, Cap, Why), Caps),
        (   member(BadCap-BadWhy, Caps),
            \+ memberchk(BadCap, [exact, inexact, refuse])
        ->  throw(error(petta_route_cap_invalid(Space, BadCap, BadWhy),
                        none))
        ;   member(refuse-Why, Caps)
        ->  throw(error(petta_route_capped(Space, Pattern, Why), none))
        ;   memberchk(inexact-_, Caps)
        ->  Class = inexact
        ;   Class = Class0
        )
    ).

:- multifile prolog:error_message//1.
prolog:error_message(petta_route_capped(Space, Pattern, Why)) -->
    { swrite(Pattern, PatternText) },
    [ 'a route advisor refuses ~w for ~w: ~w. The cap rides \c
       metta_route_cap/4; remove the advisor''s reason or its declaration \c
       to route again'-[Space, PatternText, Why] ].
prolog:error_message(petta_route_cap_invalid(Space, Cap, Why)) -->
    [ 'a route advisor for ~w answered the cap ~w (why: ~w), outside \c
       exact, inexact and refuse; an unknown cap would silently advise \c
       nothing, so it is an error in the advisor'-[Space, Cap, Why] ].

%%%% Multi-context matching: one query over several spaces %%%%
%
%(match (superpose (&a &b ...)) P T), the multi-context idiom, merges
%the spaces' answer streams under the declared (merge <pattern>
%<policy>): depth is today's space-after-space order and the undeclared
%floor; fair interleaves the streams round-robin through SWI engines,
%LogicT's msplit in the engine's own machinery (the reified-backtracking
%meta-interpreter shape, threadless); best-first is a k-way ordered
%merge by annotation, sound only when every context's own emission is
%best-first, which its (emits ...) declaration promises and this
%refuses loudly without.
petta_merged_match(Spaces, Pattern, Out) :-
    (   petta_merge_route(Pattern, Policy)
    ->  petta_merged_match_(Policy, Spaces, Pattern, Out)
    ;   member(Space, Spaces),
        match(Space, Pattern, Out, Out)
    ).

petta_merged_match_(depth, Spaces, Pattern, Out) :-
    member(Space, Spaces),
    match(Space, Pattern, Out, Out).
petta_merged_match_(fair, Spaces, Pattern, Out) :-
    maplist(petta_match_engine(Pattern, Out), Spaces, Engines),
    setup_call_cleanup(true,
                       petta_round_robin(Engines, Pattern-Out),
                       maplist(petta_engine_done, Engines)).
petta_merged_match_('best-first', Spaces, Pattern, Out) :-
    forall(member(Space, Spaces),
           (   petta_emits(Space, 'best-first')
           ->  true
           ;   throw(error(petta_merge_unordered(Space, Pattern), none))
           )),
    maplist(petta_scored_engine(Pattern, Out), Spaces, Engines),
    setup_call_cleanup(true,
                       petta_best_merge(Engines, Pattern-Out),
                       maplist(petta_engine_done, Engines)).

petta_match_engine(Pattern, Out, Space, Engine) :-
    engine_create(Pattern-Out, match(Space, Pattern, Out, Out), Engine).

petta_scored_engine(Pattern, Out, Space, Engine) :-
    engine_create(K-(Pattern-Out),
                  ( b_setval('$petta_answer_k', 1),
                    match(Space, Pattern, Out, Out),
                    b_getval('$petta_answer_k', K) ),
                  Engine).

petta_engine_done(Engine) :-
    catch(engine_destroy(Engine), _, true).

petta_round_robin([], _) :- fail.
petta_round_robin([Engine|Engines], Template) :-
    (   engine_next(Engine, Answer)
    ->  (   Answer = Template
        ;   append(Engines, [Engine], Rotated),
            petta_round_robin(Rotated, Template)
        )
    ;   petta_round_robin(Engines, Template)
    ).

%One lookahead per stream; deliver the best, refill that stream. Each
%stream is itself best-first by declaration, so the maximum of the
%lookaheads is the maximum of everything unseen.
petta_best_merge(Engines, Template) :-
    foldl(petta_prime_engine, Engines, [], Primed),
    petta_best_merge_(Primed, Template).

petta_prime_engine(Engine, Primed0, Primed) :-
    (   engine_next(Engine, Answer)
    ->  Primed = [Engine-Answer|Primed0]
    ;   Primed = Primed0
    ).

petta_best_merge_([], _) :- fail.
petta_best_merge_(Primed, Template) :-
    Primed = [_|_],
    foldl(petta_better_head, Primed, none, Engine-Best),
    selectchk(Engine-Best, Primed, Rest),
    Best = _-Answer0,
    (   Answer0 = Template
    ;   petta_prime_engine(Engine, Rest, Refilled),
        petta_best_merge_(Refilled, Template)
    ).

petta_better_head(Engine-(K-Answer), none, Engine-(K-Answer)) :- !.
petta_better_head(Engine-(K-Answer), _-(BestK-_), Engine-(K-Answer)) :-
    K @> BestK, !.
petta_better_head(_, Best, Best).

:- multifile prolog:error_message//1.
prolog:error_message(petta_merge_unordered(Ctx, Pattern)) -->
    [ 'a best-first merge over ~q needs every context emitting best \c
       first, and ~w declares no (emits ~w best-first): merging ordered \c
       streams is only sound when each stream is ordered'-[Pattern, Ctx,
                                                           Ctx] ].

%Native conjunctions call their space predicate directly. The recursive helper
%keeps the provider decision outside the candidate loop.
match_native(_, _, LComma, OutPattern, Result) :- LComma == [','], !,
                                                  Result = OutPattern.
match_native(Module, Space, [Comma|[Head|Tail]], OutPattern, Result) :- Comma == ',',
                                                                        var(Head), !,
                                                                        get_native_atom(Module, Space, Head),
                                                                        acyclic_term(OutPattern),
                                                                        match_native(Module, Space, [','|Tail], OutPattern, Result).
match_native(Module, Space, [Comma|[Head|Tail]], OutPattern, Result) :- Comma == ',',
                                                                        ( Head == [] ; \+ is_list(Head) ), !,
                                                                        get_native_scalar_atom_in(Module, Head),
                                                                        acyclic_term(OutPattern),
                                                                        match_native(Module, Space, [','|Tail], OutPattern, Result).
match_native(Module, Space, [Comma|[[Rel|PatArgs]|Tail]], OutPattern, Result) :- Comma == ',', !,
                                                                                native_expression(Module, Space, Rel, PatArgs),
                                                                                acyclic_term(OutPattern),
                                                                                match_native(Module, Space, [','|Tail], OutPattern, Result).

%When the native pattern itself is a variable, enumerate all atoms.
match_native(Module, Space, PatternVar, OutPattern, Result) :- var(PatternVar), !,
                                                               get_native_atom(Module, Space, PatternVar),
                                                               acyclic_term(OutPattern),
                                                               Result = OutPattern.

match_native(Module, _, Pattern, OutPattern, Result) :-
    ( Pattern == [] ; \+ is_list(Pattern) ), !,
    get_native_scalar_atom_in(Module, Pattern),
    acyclic_term(OutPattern),
    Result = OutPattern.

match_native(Module, Space, [Rel|PatArgs], OutPattern, Result) :- native_expression(Module, Space, Rel, PatArgs),
                                                                  acyclic_term(OutPattern),
                                                                  Result = OutPattern.

%Read one stored expression through its private module. The module's unknown
%flag is fail, so a virgin arity fails directly and this indexed path needs no
%exception handler.
%The storage call unifies raw, so first-argument indexing dispatches, and
%the occurs check runs once on the answer instead: a cyclic binding fails
%THIS candidate and enumeration continues. Without it, a repeated-variable
%pattern like (f $y $y) against a stored (f (g $x) $x) "matched" whenever
%the out template did not mention $y, while the same pattern failed when it
%did, one match with two answers. The arbiter's matcher occurs-checks its
%variable cases (LeaTTa MettaHyperonFull/Core/Matching.lean matchAtomsWith),
%so a rational-tree instantiation is never a MeTTa answer.
native_expression(Module, Space, Rel, PatArgs) :-
    Term =.. [Space, Rel | PatArgs],
    call(Module:Term),
    acyclic_term(PatArgs).

'get-atoms'(Space, Pattern) :- nonvar(Space),
                               metta_foreign_space(Space), !,
                               refuse_absent_capability(Space, enumerate),
                               petta_source_guard(Space),
                               metta_foreign_atoms(Space, Pattern).

%Get all atoms in space, irregard of arity. A first argument that is not a
%space is refused HERE and not in get_native_atom/2 below, for the same reason
%metta_add_atom/3 leaves the check to 'add-atom'/3: this is the door a MeTTa
%program comes through and the one that owes it a MeTTa answer, while the
%storage read below is an engine internal whose callers hold a space name
%already and would read an error atom as a stored atom
%[tested: test_get_atoms_on_an_unbound_space_names_the_operation].
%The storage lookup decides it here too, for match/4's reason: a read of a
%space the engine holds pays nothing, and only an unknown name reaches
%petta_space_name/1. get_native_atom/3 rather than /2 because the lookup /2
%would repeat has already happened in the condition.
'get-atoms'(Space, Pattern) :-
    (   atom(Space)
    ->  (   native_storage_module_ready(Space, Module)
        ->  get_native_atom(Module, Space, Pattern)
        ;   petta_space_name(Space)
        ->  fail
        ;   space_argument_error('get-atoms', [Space], Pattern)
        )
    ;   space_argument_error('get-atoms', [Space], Pattern)
    ).

%Drop every atom a space holds. Expressions and scalars live in different
%predicates, so a caller that wipes only the space predicate would leave the
%scalars standing and a pooled name's next life would inherit them.
%Clearing a foreign space is the provider's own operation, and it lived in
%python/petta/shim.pl, so a Prolog provider that implemented clear (as
%lib/lib_redis.pl does) was reachable only when Python was in the process:
%under run.sh the engine had no path to it at all. The shim now calls this.
clear_foreign_atoms(Space) :-
    foreign_write(Space, clear, metta_foreign_clear(Space)).

%A space has two halves and this used to empty one of them. The storage sweep
%below drops every stored atom, and the atoms that also COMPILED left their
%clauses standing in the space's execution module, so a space holding nothing
%still answered its own functions: define (= (past-life) inherited), clear,
%and `!(past-life)` in that space still answered `inherited` over an empty
%space [measured 2026-08-19, ai-tmp/spaces-p1/probe_p116h.pl]. Space names
%are POOLED, so that is a previous life answering through a recycled name.
%
%It was masked rather than absent: python/petta/shim.pl's clear removes
%equations through the removal funnel before calling this, so the Python door
%was whole and the ENGINE's own door was not. Every other caller got the half
%clear, and P1.14's reload will come through this one.
%
%So the compiled half leaves first, through metta_remove_atom/3, which is the
%code that owns each shape: an equation un-compiles its clause and forgets the
%function name when nothing else defines it, a declaration recompiles the call
%sites it was shaping. Only those two shapes, because only those two have a
%compiled half, which is exactly the two clauses metta_remove_atom/3 answers
%specially; a plain atom is storage and nothing else, so the sweep is both
%correct and one retractall per arity rather than one removal per atom.
%
%The funnel is idempotent, so the shim's own pass in front of this one leaves
%nothing here to find and no removal is announced twice
%[tested: spaces_execution_modules:clearing_a_space_empties_its_execution_module,
%test_a_recycled_space_name_inherits_no_clauses_from_its_past_life].
clear_native_atoms(Space) :-
    (   native_storage_module_ready(Space, Module)
    ->  findall(Atom, compiled_half_atom(Space, Module, Atom), Compiled),
        forall(member(Atom, Compiled),
               ( metta_remove_atom(Space, Atom, _) -> true ; true )),
        forall(( current_predicate(Module:Space/Arity),
                 functor(Head, Space, Arity) ),
               retractall(Module:Head)),
        retractall(Module:'$petta_native_scalar'(_))
    ;   true
    ),
    retractall(import_life(Space, _, _)),
    forget_space_source_loads(Space).

%The atoms whose removal has a consequence beyond storage, which are exactly
%the two shapes metta_remove_atom/3 answers specially; a shape added there
%without being added here would go back to leaving its compiled half behind a
%clear.
%
%Asked of the storage predicate by HEAD SYMBOL rather than by filtering a walk
%of the space. The head is the first argument, so this is one indexed lookup
%per shape and a space of plain atoms pays nothing for the question; filtering
%an enumeration cost one inference per stored atom on every clear, which the
%benchmarks saw as +20,002 inferences on py-method-call and +8,000 on
%handle-round-trip [measured 2026-08-19].
compiled_half_atom(Space, Module, [=, Head, Body]) :-
    Term =.. [Space, =, Head, Body],
    call(Module:Term),
    Head = [F|_], atom(F).
compiled_half_atom(Space, Module, [':', F, Type]) :-
    Term =.. [Space, ':', F, Type],
    call(Module:Term),
    atom(F), fun(F).

%Enumeration answers the space's expressions and then its scalar atoms.
%native_storage_module_ready/2 is a dynamic lookup, so an unbound space
%enumerated every space ever written to and !(collapse (get-atoms $any))
%answered with another space's atoms without ever naming it.
%
%This raise is the ENGINE's invariant and not the language's answer: a MeTTa
%program cannot reach it, because 'get-atoms'/2 above refuses a first argument
%that is not a space before it gets here. What is left is an engine caller
%that lost its space name, and that is a bug in the engine rather than in a
%program, so it throws instead of answering an atom the caller would store
%[tested: spaces_storage_modules:reading_atoms_requires_a_named_space].
get_native_atom(Space, Pattern) :-
    ( var(Space) -> instantiation_error(Space) ; true ),
    native_storage_module_ready(Space, Module),
    get_native_atom(Module, Space, Pattern).

get_native_atom(Module, Space, Pattern) :-
    current_predicate(Module:Space/Arity),
    functor(Head, Space, Arity),
    clause(Module:Head, true),
    Head =.. [Space | Pattern].
get_native_atom(Module, _, Pattern) :-
    get_native_scalar_atom_in(Module, Pattern).

get_native_scalar_atom_in(Module, Pattern) :-
    Module:'$petta_native_scalar'(Pattern).
