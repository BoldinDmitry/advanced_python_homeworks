#include <Python.h>
#include <iostream>

using namespace std;

typedef struct{
    PyObject_HEAD
    long int *matrix;
    int rows, columns;
} matrix;


PyObject* matrixes_amount(matrix *matrix1, matrix *matrix2);
PyObject* matrix_product(matrix *matrix1, matrix *matrix2);
PyObject *devide_matrix_by_num(matrix *self, PyObject *divider);
PyObject* matrix_transpose(matrix *self);
static int matrix_contains(matrix *self, PyObject *arg);


static Py_ssize_t matrix_length(matrix *self);
static void matrix_dealloc(matrix *self);
static PyObject *matrix_repr(matrix *self);
static PyObject *matrix_str(matrix *self);
static int matrix_init(matrix *self, PyObject *args, PyObject *kwargs);
static PyObject * matrix_new(PyTypeObject *type, PyObject *args, PyObject *kwargs);

static PySequenceMethods matrix_as_sequence = {
        (lenfunc)matrix_length,      /* sq_length */
        0,                           /* sq_concat */
        0,                           /* sq_repeat */
        0,                           /* sq_item */
        0,                           /* sq_slice */
        0,                           /* sq_ass_item */
        0,                           /* sq_ass_slice */
        (objobjproc)matrix_contains, /* sq_contains */
};

static PyMethodDef matrix_methods[] = {
        {"transpose", (PyCFunction)matrix_transpose, METH_NOARGS},
        { NULL, NULL, 0, NULL }
};

static PyNumberMethods matrix_as_number = {
        (binaryfunc)matrixes_amount,        // nb_add
        0,                                  // nb_subtract
        (binaryfunc)matrix_product,         // nb_multiply
        0,                                  // nb_remainder
        0,                                  // nb_divmod
        0,                                  // nb_power
        0,                                  // nb_negative
        0,                                  // nb_positive
        0,                                  // nb_absolute
        0,                                  // nb_bool
        0,                                  // nb_invert
        0,                                  // nb_lshift
        0,                                  // nb_rshift
        0,                                  // nb_and
        0,                                  // nb_xor
        0,                                  // nb_or
        0,                                  // nb_int
        0,                                  // nb_reserved
        0,                                  // nb_float
        0,                                  // nb_inplace_add
        0,                                  // nb_inplace_subtract
        0,                                  // nb_inplace_multiply
        0,                                  // nb_inplace_remainder
        0,                                  // nb_inplace_power
        0,                                  // nb_inplace_lshift
        0,                                  // nb_inplace_rshift
        0,                                  // nb_inplace_and
        0,                                  // nb_inplace_xor
        0,                                  // nb_inplace_or
        0,                                  // nb_floor_divide
        (binaryfunc)devide_matrix_by_num,   // nb_true_divide
        0,                                  // nb_inplace_floor_divide
        0,                                  // nb_inplace_true_divide
        0,                                  // nb_index
        0,                                  // nb_matrix_multiply
        0,                                  // nb_inplace_matrix_multiply
};


PyTypeObject matrix_Type = {
        PyVarObject_HEAD_INIT(NULL, 0)
        "matrix.Matrix",                                 /* tp_name */
        sizeof(matrix),                                  /* tp_basic_size */
        0,                                               /* tp_itemsize */
        (destructor)matrix_dealloc,                      /* tp_dealloc */
        0,                                               /* tp_print */
        0,                                               /* tp_getattr */
        0,                                               /* tp_setattr */
        0,                                               /* tp_reserved */
        (reprfunc)matrix_repr,                           /* tp_repr */
        &matrix_as_number,                               /* tp_as_number */
        &matrix_as_sequence,                             /* tp_as_sequence */
        0,                                               /* tp_as_mapping */
        0,                                               /* tp_hash */
        0,                                               /* tp_call */
        (reprfunc)matrix_str,                            /* tp_str */
        0,                                               /* tp_getattro */
        0,                                               /* tp_setattro */
        0,                                               /* tp_as_buffer */
        Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,        /* tp_flags */
        0,                                               /* tp_doc */
        0,                                               /* tp_traverse */
        0,                                               /* tp_clear */
        0,                                               /* tp_richcompare */
        0,                                               /* tp_weaklistoffset */
        0,                                               /* tp_iter */
        0,                                               /* tp_iternext */
        matrix_methods,                                  /* tp_methods */
        0,                                               /* tp_members */
        0,                                               /* tp_getset */
        0,                                               /* tp_base */
        0,                                               /* tp_dict */
        0,                                               /* tp_descr_get */
        0,                                               /* tp_descr_set */
        0,                                               /* tp_dictoffset */
        (initproc)matrix_init,                           /* tp_init */
        0,                                               /* tp_alloc */
        matrix_new,                                      /* tp_new */
        0,                                               /* tp_free */
};

static struct PyModuleDef matrix_module = {
        PyModuleDef_HEAD_INIT,
        "matrix", /* name of module */
        NULL,     /* module documentation, may be NULL */
        -1,       /* size of per-interpreter state of the module,
                 or -1 if the module keeps state in global variables. */
};

PyMODINIT_FUNC
PyInit_matrix(void)
{
    PyObject *m;
    if (PyType_Ready(&matrix_Type) < 0)
        return NULL;

    m = PyModule_Create(&matrix_module);
    if (m == NULL)
        return NULL;

    Py_INCREF(&matrix_Type);
    PyModule_AddObject(m, "Matrix", (PyObject *)&matrix_Type);
    return m;
}


static void matrix_dealloc(matrix *self) {
    delete self->matrix;
    Py_TYPE(self)->tp_free(self);
}

static PyObject * matrix_new(PyTypeObject *type, PyObject *args, PyObject *kwargs){
    matrix *self = (matrix *)type->tp_alloc(type, 0);

    if (self == NULL)
        return PyErr_NoMemory();

    self->matrix = NULL;

    return (PyObject *)self;
}

static int matrix_init(matrix *self, PyObject *args, PyObject *kwargs){
    PyObject *py_matrix;

    if (!PyArg_ParseTuple(args, "O", &py_matrix)) {
        return NULL;
    }

    if (!PyList_Check(py_matrix)) {
        PyErr_SetString(PyExc_TypeError, "Matrix should be list");
        return NULL;
    }

    self->rows = PyList_Size(py_matrix);
    if (self->rows == 0) {
        PyErr_SetString(PyExc_TypeError, "Matrix is empty");
        return NULL;
    }

    self->columns = PyList_Size(PyList_GetItem(py_matrix, 0));
    self->matrix = new long int[self->rows * self->columns];

    for(int i=0; i < self->rows; i++){
        PyObject *tmp_row = PyList_GetItem(py_matrix, i);

        Py_INCREF(tmp_row);

        if(!PyList_Check(tmp_row)){
            PyErr_SetString(PyExc_TypeError, "Object should be list");
            return -1;
        }

        if (PyList_Size(tmp_row) != self->columns) {
            PyErr_SetString(PyExc_ValueError, "Wrong row columns count");
            return NULL;
        }

        for (Py_ssize_t j = 0; j < self->columns; j++) {
            PyObject *num_tmp = PyList_GetItem(tmp_row, j);
            Py_INCREF(num_tmp);

            if (!PyLong_Check(num_tmp)) {
                PyErr_SetString(PyExc_TypeError, "Object should be int");
                return NULL;
            }
            self->matrix[i * self->columns + j] = PyLong_AsLong(num_tmp);
            Py_DECREF(num_tmp);
        }
        Py_DECREF(tmp_row);
    }
    return 0;
}

static PyObject *matrix_repr(matrix *self) {
    if (!self->rows || !self->columns) {
        return PyUnicode_FromString("<Matrix {}>");
    }

    _PyUnicodeWriter writer;
    _PyUnicodeWriter_Init(&writer);
    writer.overallocate = 1;
    writer.min_length = 10;
    PyObject *el_str = NULL;

    if (_PyUnicodeWriter_WriteASCIIString(&writer, "<Matrix([\n", 11) < 0) {
        goto error;
    }

    for (Py_ssize_t i = 0; i < self->rows * self->columns; i++) {
        if (i % self -> rows == 0)
            if (_PyUnicodeWriter_WriteASCIIString(&writer, "    [", 5) < 0) {
                goto error;
            }
        el_str = PyUnicode_FromFormat((i + 1) % self->columns ? "%d, " : "%d],\n",
                                      self->matrix[i]);

        if (_PyUnicodeWriter_WriteStr(&writer, el_str)) {
            Py_DECREF(el_str);
            goto error;
        }

        Py_DECREF(el_str);
    }

    writer.overallocate = 0;
    if (_PyUnicodeWriter_WriteASCIIString(&writer, "])>", 3) < 0) {
        goto error;
    }

    return _PyUnicodeWriter_Finish(&writer);

error:
Py_DECREF(el_str);
_PyUnicodeWriter_Dealloc(&writer);
Py_INCREF(tmp_row);
return NULL;
}

static PyObject *matrix_str(matrix *self) {
    if (!self->rows || !self->columns) {
        return PyUnicode_FromString("");
    }

    _PyUnicodeWriter writer;
    _PyUnicodeWriter_Init(&writer);
    writer.overallocate = 1;
    writer.min_length = 10;
    PyObject *el_str = NULL;

    for (Py_ssize_t i = 0; i < self->rows * self->columns; i++) {
        el_str = PyUnicode_FromFormat((i + 1) % self->columns ? "%d " : "%d\n",
                                      self->matrix[i]);

        if (_PyUnicodeWriter_WriteStr(&writer, el_str)) {
            Py_DECREF(el_str);
            goto error;
        }

        Py_DECREF(el_str);
    }

    writer.overallocate = 0;

    return _PyUnicodeWriter_Finish(&writer);

    error:
    Py_XDECREF(el_str);
    _PyUnicodeWriter_Dealloc(&writer);
    return NULL;
}

static Py_ssize_t matrix_length(matrix *self) {
    return (Py_ssize_t)(self->rows);
}


PyObject *devide_matrix_by_num(matrix *self, PyObject *divider) {
    if (!PyLong_Check(divider)) {
        PyErr_SetString(PyExc_TypeError, "Divider should be number");
        return NULL;
    }
    Py_ssize_t divider_int = PyLong_AsLong(divider);

    matrix *new_matrix = (matrix *) matrix_new(&matrix_Type, nullptr, nullptr);


    new_matrix->rows = self->rows;
    new_matrix->columns = self->columns;
    new_matrix->matrix = new long int[new_matrix->rows * new_matrix->columns];

    for (Py_ssize_t i = 0; i < self->rows * self->columns; i++) {
        new_matrix->matrix[i] = self->matrix[i] / divider_int;
    }

    return (PyObject *)new_matrix;
}

PyObject *mult_matrix_by_num(matrix *self, PyObject *multiplier){
    if (!PyLong_Check(multiplier)) {
        PyErr_SetString(PyExc_TypeError, "Divider should be number");
        return NULL;
    }
    Py_ssize_t multiplier_int = PyLong_AsLong(multiplier);

    matrix *new_matrix = (matrix *) matrix_new(&matrix_Type, nullptr, nullptr);


    new_matrix->rows = self->rows;
    new_matrix->columns = self->columns;
    new_matrix->matrix = new long int[new_matrix->rows * new_matrix->columns];

    for (Py_ssize_t i = 0; i < self->rows * self->columns; i++) {
        new_matrix->matrix[i] = self->matrix[i] * multiplier_int;
    }

    return (PyObject *)new_matrix;
}

PyObject* matrixes_amount(matrix *matrix1, matrix *matrix2) {
    if (matrix1->rows != matrix2->rows || matrix1->columns != matrix2->columns) {
        PyErr_SetString(PyExc_TypeError, "Matrixes should have the same size");
        return NULL;
    }

    matrix *new_matrix = (matrix *) matrix_new(&matrix_Type, nullptr, nullptr);

    new_matrix->rows = matrix1->rows;
    new_matrix->columns = matrix1->columns;

    new_matrix->matrix = new long int[new_matrix->rows * new_matrix->columns];

    for (Py_ssize_t i = 0; i < matrix1->rows * matrix1->columns; i++) {
        new_matrix->matrix[i] = matrix1->matrix[i] + matrix2->matrix[i];
    }

    return (PyObject *)new_matrix;
}

PyObject* matrix_product(matrix *matrix1, matrix *matrix2) {
    if ((matrix1->columns != matrix2->columns) || (matrix1->rows != matrix2->rows)) {
        PyErr_SetString(PyExc_TypeError, "Matrixes should have the same size");
        return NULL;
    }

    PyObject *args = nullptr, *kwds = nullptr;
    matrix *new_matrix = (matrix *) matrix_new(&matrix_Type, args, kwds);

    new_matrix->rows = matrix1->rows;
    new_matrix->columns = matrix2->columns;

    new_matrix->matrix = new long int[new_matrix->rows * new_matrix->columns];

    long int c=0;
    for (Py_ssize_t i = 0; i < matrix1->rows; i++) {
        for (Py_ssize_t j = 0; j < matrix2->columns; j++) {
            for (Py_ssize_t k = 0; k < matrix1->columns; k++) {
                c += matrix1->matrix[i * matrix1->columns + k]
                     * matrix2->matrix[k * matrix2->columns + j];
            }
            new_matrix->matrix[i * new_matrix->columns + j] = c;
            c = 0;
        }
    }

    return (PyObject *)new_matrix;
}

PyObject* matrix_transpose(matrix *self) {
    matrix *new_matrix = PyObject_New(matrix, &matrix_Type);

    new_matrix->rows = self->columns;
    new_matrix->columns = self->rows;
    new_matrix->matrix = new long int[self->columns + self->rows];

    for (Py_ssize_t i = 0; i < new_matrix->rows; i++) {
        for (Py_ssize_t j = 0; j < new_matrix->columns; j++) {
            new_matrix->matrix[i * new_matrix->columns + j]
                    = self->matrix[j * self->columns + i];
        }
    }

    return (PyObject *)new_matrix;
}

static int matrix_contains(matrix *self, PyObject *arg) {
    if (!PyLong_Check(arg)) {
        PyErr_SetString(PyExc_TypeError, "object must be number");
        return -1;
    }

    long int item = PyLong_AsLong(arg);
    for (Py_ssize_t i = 0; i < self->rows * self->columns; i++) {
        if (self->matrix[i] == item) {
            return 1;
        }
    }

    return 0;
}
