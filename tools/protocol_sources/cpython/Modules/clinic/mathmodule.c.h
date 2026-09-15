PyDoc_STRVAR(math_gcd__doc__,
"gcd($module, /, *integers)\n"
"--\n"
"\n"
"Greatest Common Divisor.");
#define MATH_GCD_METHODDEF    \
    {"gcd", _PyCFunction_CAST(math_gcd), METH_FASTCALL, math_gcd__doc__},
PyDoc_STRVAR(math_lcm__doc__,
"lcm($module, /, *integers)\n"
"--\n"
"\n"
"Least Common Multiple.");
#define MATH_LCM_METHODDEF    \
    {"lcm", _PyCFunction_CAST(math_lcm), METH_FASTCALL, math_lcm__doc__},
PyDoc_STRVAR(math_ceil__doc__,
"ceil($module, x, /)\n"
"--\n"
"\n"
"Return the ceiling of x as an Integral.\n"
"\n"
"This is the smallest integer >= x.");
#define MATH_CEIL_METHODDEF    \
    {"ceil", (PyCFunction)math_ceil, METH_O, math_ceil__doc__},
PyDoc_STRVAR(math_floor__doc__,
"floor($module, x, /)\n"
"--\n"
"\n"
"Return the floor of x as an Integral.\n"
"\n"
"This is the largest integer <= x.");
#define MATH_FLOOR_METHODDEF    \
    {"floor", (PyCFunction)math_floor, METH_O, math_floor__doc__},
PyDoc_STRVAR(math_fsum__doc__,
"fsum($module, seq, /)\n"
"--\n"
"\n"
"Return an accurate floating-point sum of values in the iterable seq.\n"
"\n"
"Assumes IEEE-754 floating-point arithmetic.");
#define MATH_FSUM_METHODDEF    \
    {"fsum", (PyCFunction)math_fsum, METH_O, math_fsum__doc__},
PyDoc_STRVAR(math_isqrt__doc__,
"isqrt($module, n, /)\n"
"--\n"
"\n"
"Return the integer part of the square root of the input.");
#define MATH_ISQRT_METHODDEF    \
    {"isqrt", (PyCFunction)math_isqrt, METH_O, math_isqrt__doc__},
PyDoc_STRVAR(math_factorial__doc__,
"factorial($module, n, /)\n"
"--\n"
"\n"
"Find n!.");
#define MATH_FACTORIAL_METHODDEF    \
    {"factorial", (PyCFunction)math_factorial, METH_O, math_factorial__doc__},
PyDoc_STRVAR(math_trunc__doc__,
"trunc($module, x, /)\n"
"--\n"
"\n"
"Truncates the Real x to the nearest Integral toward 0.\n"
"\n"
"Uses the __trunc__ magic method.");
#define MATH_TRUNC_METHODDEF    \
    {"trunc", (PyCFunction)math_trunc, METH_O, math_trunc__doc__},
PyDoc_STRVAR(math_frexp__doc__,
"frexp($module, x, /)\n"
"--\n"
"\n"
"Return the mantissa and exponent of x, as pair (m, e).\n"
"\n"
"m is a float and e is an int, such that x = m * 2.**e.\n"
"If x is 0, m and e are both 0.  Else 0.5 <= abs(m) < 1.0.");
#define MATH_FREXP_METHODDEF    \
    {"frexp", (PyCFunction)math_frexp, METH_O, math_frexp__doc__},
PyDoc_STRVAR(math_ldexp__doc__,
"ldexp($module, x, i, /)\n"
"--\n"
"\n"
"Return x * (2**i).\n"
"\n"
"This is essentially the inverse of frexp().");
#define MATH_LDEXP_METHODDEF    \
    {"ldexp", _PyCFunction_CAST(math_ldexp), METH_FASTCALL, math_ldexp__doc__},
PyDoc_STRVAR(math_modf__doc__,
"modf($module, x, /)\n"
"--\n"
"\n"
"Return the fractional and integer parts of x.\n"
"\n"
"Both results carry the sign of x and are floats.");
#define MATH_MODF_METHODDEF    \
    {"modf", (PyCFunction)math_modf, METH_O, math_modf__doc__},
PyDoc_STRVAR(math_log2__doc__,
"log2($module, x, /)\n"
"--\n"
"\n"
"Return the base 2 logarithm of x.");
#define MATH_LOG2_METHODDEF    \
    {"log2", (PyCFunction)math_log2, METH_O, math_log2__doc__},
PyDoc_STRVAR(math_log10__doc__,
"log10($module, x, /)\n"
"--\n"
"\n"
"Return the base 10 logarithm of x.");
#define MATH_LOG10_METHODDEF    \
    {"log10", (PyCFunction)math_log10, METH_O, math_log10__doc__},
PyDoc_STRVAR(math_fma__doc__,
"fma($module, x, y, z, /)\n"
"--\n"
"\n"
"Fused multiply-add operation.\n"
"\n"
"Compute (x * y) + z with a single round.");
#define MATH_FMA_METHODDEF    \
    {"fma", _PyCFunction_CAST(math_fma), METH_FASTCALL, math_fma__doc__},
PyDoc_STRVAR(math_fmod__doc__,
"fmod($module, x, y, /)\n"
"--\n"
"\n"
"Return fmod(x, y), according to platform C.\n"
"\n"
"x % y may differ.");
#define MATH_FMOD_METHODDEF    \
    {"fmod", _PyCFunction_CAST(math_fmod), METH_FASTCALL, math_fmod__doc__},
PyDoc_STRVAR(math_dist__doc__,
"dist($module, p, q, /)\n"
"--\n"
"\n"
"Return the Euclidean distance between two points p and q.\n"
"\n"
"The points should be specified as sequences (or iterables) of\n"
"coordinates.  Both inputs must have the same dimension.\n"
"\n"
"Roughly equivalent to:\n"
"    sqrt(sum((px - qx) ** 2.0 for px, qx in zip(p, q)))");
#define MATH_DIST_METHODDEF    \
    {"dist", _PyCFunction_CAST(math_dist), METH_FASTCALL, math_dist__doc__},
PyDoc_STRVAR(math_hypot__doc__,
"hypot($module, /, *coordinates)\n"
"--\n"
"\n"
"Multidimensional Euclidean distance from the origin to a point.\n"
"\n"
"Roughly equivalent to:\n"
"    sqrt(sum(x**2 for x in coordinates))\n"
"\n"
"For a two dimensional point (x, y), gives the hypotenuse\n"
"using the Pythagorean theorem:  sqrt(x*x + y*y).\n"
"\n"
"For example, the hypotenuse of a 3/4/5 right triangle is:\n"
"\n"
"    >>> hypot(3.0, 4.0)\n"
"    5.0");
#define MATH_HYPOT_METHODDEF    \
    {"hypot", _PyCFunction_CAST(math_hypot), METH_FASTCALL, math_hypot__doc__},
PyDoc_STRVAR(math_sumprod__doc__,
"sumprod($module, p, q, /)\n"
"--\n"
"\n"
"Return the sum of products of values from two iterables p and q.\n"
"\n"
"Roughly equivalent to:\n"
"\n"
"    sum(map(operator.mul, p, q, strict=True))\n"
"\n"
"For float and mixed int/float inputs, the intermediate products\n"
"and sums are computed with extended precision.");
#define MATH_SUMPROD_METHODDEF    \
    {"sumprod", _PyCFunction_CAST(math_sumprod), METH_FASTCALL, math_sumprod__doc__},
PyDoc_STRVAR(math_pow__doc__,
"pow($module, x, y, /)\n"
"--\n"
"\n"
"Return x**y (x to the power of y).");
#define MATH_POW_METHODDEF    \
    {"pow", _PyCFunction_CAST(math_pow), METH_FASTCALL, math_pow__doc__},
PyDoc_STRVAR(math_degrees__doc__,
"degrees($module, x, /)\n"
"--\n"
"\n"
"Convert angle x from radians to degrees.");
#define MATH_DEGREES_METHODDEF    \
    {"degrees", (PyCFunction)math_degrees, METH_O, math_degrees__doc__},
PyDoc_STRVAR(math_radians__doc__,
"radians($module, x, /)\n"
"--\n"
"\n"
"Convert angle x from degrees to radians.");
#define MATH_RADIANS_METHODDEF    \
    {"radians", (PyCFunction)math_radians, METH_O, math_radians__doc__},
PyDoc_STRVAR(math_isfinite__doc__,
"isfinite($module, x, /)\n"
"--\n"
"\n"
"Return True if x is neither an infinity nor a NaN, and False otherwise.");
#define MATH_ISFINITE_METHODDEF    \
    {"isfinite", (PyCFunction)math_isfinite, METH_O, math_isfinite__doc__},
PyDoc_STRVAR(math_isnan__doc__,
"isnan($module, x, /)\n"
"--\n"
"\n"
"Return True if x is a NaN (not a number), and False otherwise.");
#define MATH_ISNAN_METHODDEF    \
    {"isnan", (PyCFunction)math_isnan, METH_O, math_isnan__doc__},
PyDoc_STRVAR(math_isinf__doc__,
"isinf($module, x, /)\n"
"--\n"
"\n"
"Return True if x is a positive or negative infinity, and False otherwise.");
#define MATH_ISINF_METHODDEF    \
    {"isinf", (PyCFunction)math_isinf, METH_O, math_isinf__doc__},
PyDoc_STRVAR(math_isclose__doc__,
"isclose($module, /, a, b, *, rel_tol=1e-09, abs_tol=0.0)\n"
"--\n"
"\n"
"Determine whether two floating-point numbers are close in value.\n"
"\n"
"  rel_tol\n"
"    maximum difference for being considered \"close\", relative to the\n"
"    magnitude of the input values\n"
"  abs_tol\n"
"    maximum difference for being considered \"close\", regardless of the\n"
"    magnitude of the input values\n"
"\n"
"Return True if a is close in value to b, and False otherwise.\n"
"\n"
"For the values to be considered close, the difference between them\n"
"must be smaller than at least one of the tolerances.\n"
"\n"
"-inf, inf and NaN behave similarly to the IEEE 754 Standard.  That\n"
"is, NaN is not close to anything, even itself.  inf and -inf are\n"
"only close to themselves.");
#define MATH_ISCLOSE_METHODDEF    \
    {"isclose", _PyCFunction_CAST(math_isclose), METH_FASTCALL|METH_KEYWORDS, math_isclose__doc__},
PyDoc_STRVAR(math_prod__doc__,
"prod($module, iterable, /, *, start=1)\n"
"--\n"
"\n"
"Calculate the product of all the elements in the input iterable.\n"
"\n"
"The default start value for the product is 1.\n"
"\n"
"When the iterable is empty, return the start value.  This function is\n"
"intended specifically for use with numeric values and may reject\n"
"non-numeric types.");
#define MATH_PROD_METHODDEF    \
    {"prod", _PyCFunction_CAST(math_prod), METH_FASTCALL|METH_KEYWORDS, math_prod__doc__},
PyDoc_STRVAR(math_perm__doc__,
"perm($module, n, k=None, /)\n"
"--\n"
"\n"
"Number of ways to choose k items from n items without repetition and with order.\n"
"\n"
"Evaluates to n! / (n - k)! when k <= n and evaluates\n"
"to zero when k > n.\n"
"\n"
"If k is not specified or is None, then k defaults to n\n"
"and the function returns n!.\n"
"\n"
"Raises TypeError if either of the arguments are not integers.\n"
"Raises ValueError if either of the arguments are negative.");
#define MATH_PERM_METHODDEF    \
    {"perm", _PyCFunction_CAST(math_perm), METH_FASTCALL, math_perm__doc__},
PyDoc_STRVAR(math_comb__doc__,
"comb($module, n, k, /)\n"
"--\n"
"\n"
"Number of ways to choose k items from n items without repetition and without order.\n"
"\n"
"Evaluates to n! / (k! * (n - k)!) when k <= n and evaluates\n"
"to zero when k > n.\n"
"\n"
"Also called the binomial coefficient because it is equivalent\n"
"to the coefficient of k-th term in polynomial expansion of the\n"
"expression (1 + x)**n.\n"
"\n"
"Raises TypeError if either of the arguments are not integers.\n"
"Raises ValueError if either of the arguments are negative.");
#define MATH_COMB_METHODDEF    \
    {"comb", _PyCFunction_CAST(math_comb), METH_FASTCALL, math_comb__doc__},
PyDoc_STRVAR(math_nextafter__doc__,
"nextafter($module, x, y, /, *, steps=None)\n"
"--\n"
"\n"
"Return the floating-point value the given number of steps after x towards y.\n"
"\n"
"If steps is not specified or is None, it defaults to 1.\n"
"\n"
"Raises a TypeError, if x or y is not a double, or if steps is not an integer.\n"
"Raises ValueError if steps is negative.");
#define MATH_NEXTAFTER_METHODDEF    \
    {"nextafter", _PyCFunction_CAST(math_nextafter), METH_FASTCALL|METH_KEYWORDS, math_nextafter__doc__},
PyDoc_STRVAR(math_ulp__doc__,
"ulp($module, x, /)\n"
"--\n"
"\n"
"Return the value of the least significant bit of the float x.");
#define MATH_ULP_METHODDEF    \
    {"ulp", (PyCFunction)math_ulp, METH_O, math_ulp__doc__},
