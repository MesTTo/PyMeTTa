!(import! &self mettamorph)

!(metta compileme.metta)
!(metta "(= (h $x) (+ $x 40))")
!(metta (= (j $x) (+ $x 39)))

!(metta (h 2))
!(metta (j 2))
!(metta (fib 10))
