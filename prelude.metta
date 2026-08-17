; %%%% The engine's prelude: standard vocabulary, no import needed. %%%%
;
; Every form here is part of the core engine. The loader in metta.pl
; compiles these equations into the base tier at startup and registers
; each name as a builtin, so they are reachable from every space with no
; import!, shadowable per named space exactly as builtins are, and their
; atoms appear in NO space: a program enumerating &self sees only its
; own writes. Declarations land in the engine's prelude type register,
; where get-type and the call-site compiler read them after a program's
; own declarations, so a user redeclaration wins.
;
; The forms are Hyperon's standard vocabulary, promoted from
; lib/lib_he.metta by the same route unify, add-reduct, add-atoms,
; add-reducts and evalc took before them: standard library operations
; rather than compatibility shims, and a program should not have to
; import anything to reach them. The equations ARE the executable spec;
; the parameter-evaluation decisions (which arguments are Atom) are
; carried over from the library unchanged, with the reasoning kept
; beside each.

;;; Equality and reduction ;;;

;if-equal compares by ALPHA-EQUIVALENCE, not ==: Hyperon implements it
;with core.rs atoms_are_equivalent, atoms equal up to a consistent
;variable renaming, and the arbiter mechanises exactly that
;[source: LeaTTa MettaHyperonFull/Minimal/Stdlib.lean, ifEqualOp]. The
;library shim compared with ==, which misses (f $x $x) against
;(f $y $y); the promotion fixes the contract, the same way add-reduct's
;promotion fixed its.
(= (if-equal $A $B $Then $Else)
   (if (=alpha $A $B) $Then $Else))

(= (if-equal2 $A $B $Then $Else)
   (if (=alpha $A $B) $Then $Else))

;The non-Msg assert forms take Atom parameters and compare RESULT SETS,
;exactly as their own Msg twins below always did and as the arbiter
;declares them [source: same file, (: assertEqual (-> Atom Atom (->)))].
;The library evaluated the arguments applicatively and asserted once per
;combination, so a nondeterministic side asserted pairwise instead of
;set-wise; the two spellings agreed only on deterministic arguments.
;The return type stays %Undefined% for the reason type-cast's note
;records: an Atom RESULT type would leave the body untranslated.
(: assertEqual (-> Atom Atom %Undefined%))
(= (assertEqual $A $B)
   (assert (== (collapse (eval $A)) (collapse (eval $B)))))

(: assertAlphaEqual (-> Atom Atom %Undefined%))
(= (assertAlphaEqual $A $B)
   (assert (=alpha (collapse (eval $A)) (collapse (eval $B)))))

;The ToResult forms do not evaluate their second argument: it is the set
;of expected results, written as a tuple. Both parameters are Atom so
;neither is evaluated on the way in, and the first is collapsed here into
;the tuple of every result it produces. Hyperon's own corpus states the
;contract, in tests/corpus/a1_symbols.metta: "assertEqualToResult checks
;all the results of the first expression; it doesn't evaluate the second
;expression, which is treated as a set of expected results."
(: assertEqualToResult (-> Atom Atom %Undefined%))
(= (assertEqualToResult $A $B)
   (assert (== (collapse (eval $A)) $B)))

(: assertAlphaEqualToResult (-> Atom Atom %Undefined%))
(= (assertAlphaEqualToResult $A $B)
   (assert (=alpha (collapse (eval $A)) $B)))

;Every expected result must appear among the results produced.
;Subtracting the produced set from the expected one leaves nothing when
;all of them did.
(: assertIncludes (-> Atom Atom %Undefined%))
(= (assertIncludes $A $B)
   (assert (== (subtraction-atom $B (collapse (eval $A))) ())))

;The Msg variants carry a failure message. assert/2 already reports the
;failing expression, so each delegates and the message is accepted but
;unused.
(: assertEqualMsg (-> Atom Atom Atom %Undefined%))
(= (assertEqualMsg $A $B $M)
   (assert (== (collapse (eval $A)) (collapse (eval $B)))))

(: assertAlphaEqualMsg (-> Atom Atom Atom %Undefined%))
(= (assertAlphaEqualMsg $A $B $M)
   (assert (=alpha (collapse (eval $A)) (collapse (eval $B)))))

(: assertEqualToResultMsg (-> Atom Atom Atom %Undefined%))
(= (assertEqualToResultMsg $A $B $M)
   (assertEqualToResult $A $B))

(: assertAlphaEqualToResultMsg (-> Atom Atom Atom %Undefined%))
(= (assertAlphaEqualToResultMsg $A $B $M)
   (assertAlphaEqualToResult $A $B))

;;; Error handling ;;;

(= (if-error $X $A $B)
   (if (= $X (cons Error $_))
       $A $B))

(= (return-on-error $result $B)
   (if-error $result
             $result
             $B))

;;; Evaluation control ;;;

(= (for-each-in-atom $L $f)
   (map-atom $L $f))

;;; Quoting ;;;

;Two clauses, and the second is not a deviation from the arbiter but
;its PeTTa-native encoding. Upstream carries only
;(= (unquote (quote $atom)) $atom): a non-quote argument matches no
;equation and minimal MeTTa's NotReducible leaves the call standing AS
;WRITTEN. PeTTa has no NotReducible; a call no equation matches answers
;nothing. The quote-wrapping catch-all is how the library encoded
;"stays as written" here, quote keeping the term inert and the printer
;rendering it as itself, so (repr (unquote 42)) answers "(unquote 42)"
;exactly as upstream observes. The cut in the first clause is what
;keeps the catch-all from also firing on quotes.
(: unquote (-> Atom %Undefined%))
(= (unquote (quote $A))
   (let $cut (cut) (eval $A)))
(= (unquote $A) (quote (unquote $A)))

(: noreduce-eq (-> Atom Atom Bool))
(= (noreduce-eq $A $B)
   (== $A $B))

;;; Types ;;;

(= (is-function (-> $A $B)) (let $temp (cut) True))
(= (is-function $X) False)

;get-type-space is a native builtin now: the engine's own get-type run
;with the selected space as context, upstream's selected-space spelling
;[source: pinned stdlib.md:849-868 via the arbiter]. The library's stub
;matched the literal &self and answered nothing for any named space.

;match-types is UNIFICATION with wildcards, not equality: %Undefined%
;and Atom on either side match anything, and otherwise the two types
;unify, bindings and all [source: LeaTTa Stdlib.lean, the corelib
;match-types equation]. The library compared with ==, which missed every
;one of those cases.
(= (match-types $t1 $t2 $then $else)
   (if (=alpha $t1 %Undefined%)
       $then
       (if (=alpha $t2 %Undefined%)
           $then
           (if (=alpha $t1 Atom)
               $then
               (if (=alpha $t2 Atom)
                   $then
                   (unify $t1 $t2 $then $else))))))

;Upstream's parameter order: the fold accumulator FIRST, then the
;candidate type, then the wanted type [source: same file,
;(= (match-type-or $folded $next $type) ...)]. The library had the
;accumulator first but swapped the two types through its own helper.
(= (match-type-or $folded $next $type)
   (or $folded (match-types $next $type True False)))

;type-cast, upstream's contract: the atom when the cast holds, the flat
;(Error $atom BadType) when it does not. UNDECLARED ON PURPOSE, and the
;absence carries behaviour: upstream ships this equation with no
;(: type-cast ...) line, so the operands evaluate before the equation
;runs, and an ill-typed subject reports its OWN error instead of being
;swallowed by an Atom mask. The arbiter measured exactly that against
;pinned Hyperon 0.2.10 [source: LeaTTa Stdlib.lean, the type-cast note
;and tests/semantics/types-basic/50-53]. The library declared Atom
;parameters and compared metatypes with ==; both diverged.
(= (type-cast $atom $type $space)
   (if (=alpha $type (get-metatype $atom))
       $atom
       (if (type-cast-holds $atom $type $space)
           $atom
           (Error $atom BadType))))

;The fold upstream writes inline, named here because PeTTa is
;applicative where the corelib chains; match-type-or does the wildcard
;and unification reading per candidate, so an undeclared atom
;(%Undefined%) casts to anything, which is upstream's answer too.
(= (type-cast-holds $atom $type $space)
   (foldl-atom (collapse (get-type-space $space $atom)) False $acc $declared
      (match-type-or $acc $declared $type)))
