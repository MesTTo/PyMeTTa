"""Purpose: the engine's own PLN library driven from Python: implications
with truth values, evidence, and queries whose answers carry (stv strength
confidence), read back as atoms Python destructures.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from _common import check, done

from metta import MeTTa

# PLN's => writes derived equations into &self by design, so this
# example lives there, the way the engine's own PLN examples do.
m = MeTTa().self
m.run("!(import! &self (library lib_pln))")
m.run(
    "(: => (-> Atom Atom %Undefined% %Undefined%))\n"
    "(= (=> $A $C $stv)\n"
    "   (add-atom &self (= $C (Truth_ModusPonens $A $stv))))\n"
    # unique-atom declares an Expression parameter, so it holds its argument
    # as written; the collapse is named first and the variable handed over.
    "(: ? (-> Atom %Undefined%))\n"
    "(= (? $term)\n"
    "   (let $found (collapse ($term (progn (reduce $term)\n"
    "     (let $evidence (collapse (reduce $term))\n"
    "       (foldl-atom $evidence (stv 0.5 0.0) Truth_Revision)))))\n"
    "     (unique-atom $found)))"
)
m.run(
    "!(=> (smokes $x) (cancer $x) (stv 0.6 0.9))\n"
    "(= (smokes anna) (stv 1.0 0.95))"
)
# The answer is a tuple of (conclusion (stv strength confidence)) pairs.
(group,) = m.run("!(? (cancer anna))")
(answers,) = group
(pair,) = answers
conclusion, stv = pair[0], pair[1]
check("conclusion", str(conclusion), "(cancer anna)")
strength, confidence = float(stv[1]), float(stv[2])
check("uncertainty carried", 0.0 < strength < 1.0 and 0.0 < confidence < 1.0)
check("modus ponens strength", strength, 0.6)
done("pln_uncertain_reasoning")
