% Purpose: the engine's kernel vocabulary, performance atoms beyond the
%   conforming stdlib (the user's standing ruling, 2026-08-21): each is a
%   grounded head LeaTTa does not speak about, Prolog-bodied by
%   measurement, with its MeTTa spelling kept alive as a differential
%   where one exists. The registries stay in src/metta.pl's tables
%   (metta_grounded_token/1, the register_builtin_fun list, the effect
%   walk's rows), the way every consulted engine file's builtins already
%   work; the Atom masks live in src/prelude.metta's declarations.
% Assumes: consulted by src/metta.pl alongside the other engine files;
%   space_atom_count/2, petta_capacity_count/2 and
%   petta_capacity_count_install/1 come from src/spaces.pl,
%   has_declared_type/2 and the refusal helpers from src/metta.pl.
% Guarantees: each head's own contract comment below, with its evidence.
% Fails when: a caller wants stdlib-conforming vocabulary only; these
%   names are PeTTa's, and a space may shadow any of them.

%(space-atom-count <space>) answers how many atoms the space holds, from
%the store's own per-predicate clause counts (src/spaces.pl,
%space_atom_count/2), so a capacity policy reads a million-atom pool at
%the same cost as a ten-atom one. It observes the space, so the effect
%walk reports it as a read; the pattern 'count' is deliberately not a
%list, which makes a tabled caller land on the unresolved-read refusal:
%no fixed set of storage predicates can invalidate a count that every
%write to any arity moves.
'space-atom-count'(Space, _) :- var(Space), !,
                                refuse_unbound_input('space-atom-count', 1).
'space-atom-count'(Space, Count) :-
    (   'is-space'(Space, true)
    ->  true
    ;   throw_metta_type_error('space-atom-count', 'SpaceType', Space)
    ),
    space_atom_count(Space, Count).

%(has-declared-type $x $type) answers whether a (: $x $type) declaration
%witnesses the type, in the module the call runs in, which for a hook
%handler is the module captured when the claim was declared. The admission
%contract's own question, exposed so a policy written in MeTTa can ask it;
%examples/spaces/admission_pools.metta's metta-admission-typed does. A
%witness, never a consistency judgement: an atom nothing declares answers
%False for every type, because "nothing says it is one" is not evidence
%that it is.
'has-declared-type'(X, T, _) :- ( var(X) ; var(T) ), !,
                                ( var(X) -> Position = 1 ; Position = 2 ),
                                refuse_unbound_input('has-declared-type',
                                                     Position).
'has-declared-type'(X, T, R) :-
    ( has_declared_type(X, T) -> R = true ; R = false ).

%(space-contains <space> <atom>) answers whether the space holds an atom
%unifying with the given one, as one probe against the store rather than
%an enumeration: stored atoms are clauses and SWI's just-in-time argument
%indexing hashes their arguments, so a ground probe costs the same over
%ten thousand held atoms as over ten [measured 2026-08-21: a
%set-semantics pre-add rule spelled over this probe costs 57.01
%inferences per add at 2,000 held atoms and 57.00 at 10,000, against
%69.01 flat for the collapse-over-match spelling it replaces and 27.01
%for a plain add; a replayed duplicate drops at 46.00; the match
%spelling is its differential, pinned in
%test_set_semantics_is_a_declared_rule_not_a_property_of_the_space].
%The Atom mask on the second parameter lives in src/prelude.metta so the
%asked-about atom is never reduced by the asking [tested: spaces_contains].
'space-contains'(Space, _, _) :- var(Space), !,
                                 refuse_unbound_input('space-contains', 1).
'space-contains'(_, Atom, _) :- var(Atom), !,
                                refuse_unbound_input('space-contains', 2).
'space-contains'(Space, Atom, R) :-
    (   'is-space'(Space, true)
    ->  ( \+ \+ 'get-atoms'(Space, Atom) -> R = true ; R = false )
    ;   throw_metta_type_error('space-contains', 'SpaceType', Space)
    ).

%(space-admission-verdict <pool> <atom>) is the shipped judge over the
%(admits <pool> <type>) and (capacity <pool> <n>) contract atoms in
%&petta, the handler petta_admission_claim/2's guard equation applies.
%Prolog-bodied by measurement: the same chain written as prelude
%equations cost 131.01 inferences per add against this body's, the two
%collapse-over-match reads of &petta being the gap, and a pool is a
%millions-of-adds surface [measured 2026-08-20:
%python/benchmarks/extension_cost.py write-door table, min of 3 runs].
%The MeTTa-bodied chain runs on as executable documentation with a
%differential in examples/spaces/admission_pools.metta, and a space may
%shadow this name like any builtin. Every declared admits type must be
%carried, the witness reading has-declared-type states above; the
%verdict names the FIRST violated contract in the general algebra's own
%words, (refuse (does-not-carry <type>)) or
%(refuse (pool-at-capacity <limit>)), so the refusal arrives as
%petta_add_refused like any handler's. The Atom mask on the atom
%parameter lives in src/prelude.metta: the pool judges the offered atom
%as itself [tested: the_sugar_judges_the_offered_atom_as_itself].
%The two fixed contract heads read &petta's boot-created storage directly,
%so an absent row still fails while the general =../catch wrapper is off
%this per-add path.
'space-admission-verdict'(Pool, Atom, Verdict) :-
    (   '$petta_atoms:&petta':'&petta'(admits, Pool, Type),
        \+ has_declared_type(Atom, Type)
    ->  Verdict = [refuse, ['does-not-carry', Type]]
    ;   '$petta_atoms:&petta':'&petta'(capacity, Pool, Limit),
        %A foreign pool's atoms live with its provider, so its count is
        %the enumeration space-atom-count refuses to hide. A native capacity
        %claim owns an incremental dynamic count; the first decision after a
        %direct contract write installs it from the exact store count.
        (   metta_foreign_space(Pool)
        ->  aggregate_all(count, 'get-atoms'(Pool, _), Count)
        ;   (   petta_capacity_count(Pool, Count)
            ->  true
            ;   petta_capacity_count_install(Pool),
                petta_capacity_count(Pool, Count)
            )
        ),
        Count >= Limit
    ->  Verdict = [refuse, ['pool-at-capacity', Limit]]
    ;   Verdict = [accept]
    ).
