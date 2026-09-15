#define FUNC1(funcname, func, can_overflow, docstring)                  \
    static PyObject * math_##funcname(PyObject *self, PyObject *args) { \
        return math_1(args, func, can_overflow, NULL);                  \
    }\
    PyDoc_STRVAR(math_##funcname##_doc, docstring);
#define FUNC1D(funcname, func, can_overflow, docstring, err_msg)        \
    static PyObject * math_##funcname(PyObject *self, PyObject *args) { \
        return math_1(args, func, can_overflow, err_msg);               \
    }\
    PyDoc_STRVAR(math_##funcname##_doc, docstring);
#define FUNC1A(funcname, func, docstring)                               \
    static PyObject * math_##funcname(PyObject *self, PyObject *args) { \
        return math_1a(args, func, NULL);                               \
    }\
    PyDoc_STRVAR(math_##funcname##_doc, docstring);
#define FUNC1AD(funcname, func, docstring, err_msg)                     \
    static PyObject * math_##funcname(PyObject *self, PyObject *args) { \
        return math_1a(args, func, err_msg);                            \
    }\
    PyDoc_STRVAR(math_##funcname##_doc, docstring);
#define FUNC2(funcname, func, docstring) \
    static PyObject * math_##funcname(PyObject *self, PyObject *const *args, Py_ssize_t nargs) { \
        return math_2(args, nargs, func, #funcname); \
    }\
    PyDoc_STRVAR(math_##funcname##_doc, docstring);
FUNC1D(acos, acos, 0,
      "acos($module, x, /)\n--\n\n"
      "Return the arc cosine (measured in radians) of x.\n\n"
      "The result is between 0 and pi.",
      "expected a number in range from -1 up to 1, got %s")
FUNC1D(acosh, acosh, 0,
      "acosh($module, x, /)\n--\n\n"
      "Return the inverse hyperbolic cosine of x.",
      "expected argument value not less than 1, got %s")
FUNC1D(asin, asin, 0,
      "asin($module, x, /)\n--\n\n"
      "Return the arc sine (measured in radians) of x.\n\n"
      "The result is between -pi/2 and pi/2.",
      "expected a number in range from -1 up to 1, got %s")
FUNC1(asinh, asinh, 0,
      "asinh($module, x, /)\n--\n\n"
      "Return the inverse hyperbolic sine of x.")
FUNC1(atan, atan, 0,
      "atan($module, x, /)\n--\n\n"
      "Return the arc tangent (measured in radians) of x.\n\n"
      "The result is between -pi/2 and pi/2.")
FUNC2(atan2, atan2,
      "atan2($module, y, x, /)\n--\n\n"
      "Return the arc tangent (measured in radians) of y/x.\n\n"
      "Unlike atan(y/x), the signs of both x and y are considered.")
FUNC1D(atanh, atanh, 0,
      "atanh($module, x, /)\n--\n\n"
      "Return the inverse hyperbolic tangent of x.",
      "expected a number between -1 and 1, got %s")
FUNC1(cbrt, cbrt, 0,
      "cbrt($module, x, /)\n--\n\n"
      "Return the cube root of x.")
math_ceil(PyObject *module, PyObject *number)
/*[clinic end generated code: output=6c3b8a78bc201c67 input=2725352806399cab]*/
{
    double x;

    if (PyFloat_CheckExact(number)) {
        x = PyFloat_AS_DOUBLE(number);
    }
    else {
        PyObject *result = _PyObject_MaybeCallSpecialNoArgs(number, &_Py_ID(__ceil__));
        if (result != NULL) {
            return result;
        }
        else if (PyErr_Occurred()) {
            return NULL;
        }
        x = PyFloat_AsDouble(number);
        if (x == -1.0 && PyErr_Occurred()) {
            return NULL;
        }
    }
    return PyLong_FromDouble(ceil(x));
}
FUNC2(copysign, copysign,
      "copysign($module, x, y, /)\n--\n\n"
       "Return a float with the magnitude (absolute value) of x but the sign of y.\n\n"
      "On platforms that support signed zeros, copysign(1.0, -0.0)\n"
      "returns -1.0.\n")
FUNC1D(cos, cos, 0,
      "cos($module, x, /)\n--\n\n"
      "Return the cosine of x (measured in radians).",
      "expected a finite input, got %s")
FUNC1(cosh, cosh, 1,
      "cosh($module, x, /)\n--\n\n"
      "Return the hyperbolic cosine of x.")
FUNC1A(erf, erf,
       "erf($module, x, /)\n--\n\n"
       "Error function at x.")
FUNC1A(erfc, erfc,
       "erfc($module, x, /)\n--\n\n"
       "Complementary error function at x.")
FUNC1(exp, exp, 1,
      "exp($module, x, /)\n--\n\n"
      "Return e raised to the power of x.")
FUNC1(exp2, exp2, 1,
      "exp2($module, x, /)\n--\n\n"
      "Return 2 raised to the power of x.")
FUNC1(expm1, expm1, 1,
      "expm1($module, x, /)\n--\n\n"
      "Return exp(x)-1.\n\n"
      "This function avoids the loss of precision involved in the direct "
      "evaluation of exp(x)-1 for small x.")
FUNC1(fabs, fabs, 0,
      "fabs($module, x, /)\n--\n\n"
      "Return the absolute value of the float x.")
math_floor(PyObject *module, PyObject *number)
/*[clinic end generated code: output=c6a65c4884884b8a input=63af6b5d7ebcc3d6]*/
{
    double x;

    if (PyFloat_CheckExact(number)) {
        x = PyFloat_AS_DOUBLE(number);
    }
    else {
        PyObject *result = _PyObject_MaybeCallSpecialNoArgs(number, &_Py_ID(__floor__));
        if (result != NULL) {
            return result;
        }
        else if (PyErr_Occurred()) {
            return NULL;
        }
        x = PyFloat_AsDouble(number);
        if (x == -1.0 && PyErr_Occurred()) {
            return NULL;
        }
    }
    return PyLong_FromDouble(floor(x));
}
FUNC1AD(gamma, m_tgamma,
      "gamma($module, x, /)\n--\n\n"
      "Gamma function at x.",
      "expected a noninteger or positive integer, got %s")
FUNC1AD(lgamma, m_lgamma,
      "lgamma($module, x, /)\n--\n\n"
      "Natural logarithm of absolute value of Gamma function at x.",
      "expected a noninteger or positive integer, got %s")
FUNC1D(log1p, m_log1p, 0,
      "log1p($module, x, /)\n--\n\n"
      "Return the natural logarithm of 1+x (base e).\n\n"
      "The result is computed in a way which is accurate for x near zero.",
      "expected argument value > -1, got %s")
FUNC2(remainder, m_remainder,
      "remainder($module, x, y, /)\n--\n\n"
      "Difference between x and the closest integer multiple of y.\n\n"
      "Return x - n*y where n*y is the closest integer multiple of y.\n"
      "In the case where x is exactly halfway between two multiples of\n"
      "y, the nearest even value of n is used. The result is always exact.")
FUNC1D(sin, sin, 0,
      "sin($module, x, /)\n--\n\n"
      "Return the sine of x (measured in radians).",
      "expected a finite input, got %s")
FUNC1(sinh, sinh, 1,
      "sinh($module, x, /)\n--\n\n"
      "Return the hyperbolic sine of x.")
FUNC1D(sqrt, sqrt, 0,
      "sqrt($module, x, /)\n--\n\n"
      "Return the square root of x.",
      "expected a nonnegative input, got %s")
FUNC1D(tan, tan, 0,
      "tan($module, x, /)\n--\n\n"
      "Return the tangent of x (measured in radians).",
      "expected a finite input, got %s")
FUNC1(tanh, tanh, 0,
      "tanh($module, x, /)\n--\n\n"
      "Return the hyperbolic tangent of x.")
math_trunc(PyObject *module, PyObject *x)
/*[clinic end generated code: output=34b9697b707e1031 input=2168b34e0a09134d]*/
{
    if (PyFloat_CheckExact(x)) {
        return PyFloat_Type.tp_as_number->nb_int(x);
    }

    PyObject *result = _PyObject_MaybeCallSpecialNoArgs(x, &_Py_ID(__trunc__));
    if (result != NULL) {
        return result;
    }
    else if (!PyErr_Occurred()) {
        PyErr_Format(PyExc_TypeError,
            "type %.100s doesn't define __trunc__ method",
            Py_TYPE(x)->tp_name);
    }
    return NULL;
}
math_log(PyObject *module, PyObject * const *args, Py_ssize_t nargs)
{
    PyObject *num, *den;
    PyObject *ans;

    if (!_PyArg_CheckPositional("log", nargs, 1, 2))
        return NULL;

    num = loghelper(args[0], m_log);
    if (num == NULL || nargs == 1)
        return num;

    den = loghelper(args[1], m_log);
    if (den == NULL) {
        Py_DECREF(num);
        return NULL;
    }

    ans = PyNumber_TrueDivide(num, den);
    Py_DECREF(num);
    Py_DECREF(den);
    return ans;
}
PyDoc_STRVAR(math_log_doc,
"log(x, [base=math.e])\n\
Return the logarithm of x to the given base.\n\n\
If the base is not specified, returns the natural logarithm (base e) of x.");
static PyMethodDef math_methods[] = {
    {"acos",            math_acos,      METH_O,         math_acos_doc},
    {"acosh",           math_acosh,     METH_O,         math_acosh_doc},
    {"asin",            math_asin,      METH_O,         math_asin_doc},
    {"asinh",           math_asinh,     METH_O,         math_asinh_doc},
    {"atan",            math_atan,      METH_O,         math_atan_doc},
    {"atan2",           _PyCFunction_CAST(math_atan2),     METH_FASTCALL,  math_atan2_doc},
    {"atanh",           math_atanh,     METH_O,         math_atanh_doc},
    {"cbrt",            math_cbrt,      METH_O,         math_cbrt_doc},
    MATH_CEIL_METHODDEF
    {"copysign",        _PyCFunction_CAST(math_copysign),  METH_FASTCALL,  math_copysign_doc},
    {"cos",             math_cos,       METH_O,         math_cos_doc},
    {"cosh",            math_cosh,      METH_O,         math_cosh_doc},
    MATH_DEGREES_METHODDEF
    MATH_DIST_METHODDEF
    {"erf",             math_erf,       METH_O,         math_erf_doc},
    {"erfc",            math_erfc,      METH_O,         math_erfc_doc},
    {"exp",             math_exp,       METH_O,         math_exp_doc},
    {"exp2",            math_exp2,      METH_O,         math_exp2_doc},
    {"expm1",           math_expm1,     METH_O,         math_expm1_doc},
    {"fabs",            math_fabs,      METH_O,         math_fabs_doc},
    MATH_FACTORIAL_METHODDEF
    MATH_FLOOR_METHODDEF
    MATH_FMA_METHODDEF
    MATH_FMOD_METHODDEF
    MATH_FREXP_METHODDEF
    MATH_FSUM_METHODDEF
    {"gamma",           math_gamma,     METH_O,         math_gamma_doc},
    MATH_GCD_METHODDEF
    MATH_HYPOT_METHODDEF
    MATH_ISCLOSE_METHODDEF
    MATH_ISFINITE_METHODDEF
    MATH_ISINF_METHODDEF
    MATH_ISNAN_METHODDEF
    MATH_ISQRT_METHODDEF
    MATH_LCM_METHODDEF
    MATH_LDEXP_METHODDEF
    {"lgamma",          math_lgamma,    METH_O,         math_lgamma_doc},
    {"log",             _PyCFunction_CAST(math_log),       METH_FASTCALL,  math_log_doc},
    {"log1p",           math_log1p,     METH_O,         math_log1p_doc},
    MATH_LOG10_METHODDEF
    MATH_LOG2_METHODDEF
    MATH_MODF_METHODDEF
    MATH_POW_METHODDEF
    MATH_RADIANS_METHODDEF
    {"remainder",       _PyCFunction_CAST(math_remainder), METH_FASTCALL,  math_remainder_doc},
    {"sin",             math_sin,       METH_O,         math_sin_doc},
    {"sinh",            math_sinh,      METH_O,         math_sinh_doc},
    {"sqrt",            math_sqrt,      METH_O,         math_sqrt_doc},
    {"tan",             math_tan,       METH_O,         math_tan_doc},
    {"tanh",            math_tanh,      METH_O,         math_tanh_doc},
    MATH_SUMPROD_METHODDEF
    MATH_TRUNC_METHODDEF
    MATH_PROD_METHODDEF
    MATH_PERM_METHODDEF
    MATH_COMB_METHODDEF
    MATH_NEXTAFTER_METHODDEF
    MATH_ULP_METHODDEF
    {NULL,              NULL}           /* sentinel */
};
PyDoc_STRVAR(module_doc,
"This module provides access to the mathematical functions\n"
"defined by the C standard.");
