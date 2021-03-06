import timeit
from matrix import Matrix
from matrix_python import Matrix as PyMatrix


matrix_types = {"C++": Matrix, "Python": PyMatrix}

for matrix_name, matrix_type in matrix_types.items():
    start = timeit.default_timer()
    x = [[1, 2], [4, 5], [7, 8]]
    y = [[1, 2], [1, 2], [3, 4]]

    x_m = matrix_type(x)
    y_m = matrix_type(y)

    for i in range(100000000):
        a = x_m * y_m
        a.transpose()

    stop = timeit.default_timer()

    print(matrix_name, " time is ", stop - start)

# """
# C++  time is  45.58985962404404
# Python  time is  1203.591531381011
# """
#
